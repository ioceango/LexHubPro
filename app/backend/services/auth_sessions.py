"""自建认证：会话与密码类业务编排。

刷新令牌采用**一次性轮换 + 族级吊销**：
1. 每次刷新都签发新令牌并把旧令牌标记为已使用，旧令牌立即失效；
2. 同一枚令牌被第二次使用即视为重放（令牌已泄露），吊销整族令牌并强制重新登录；
3. 轮换用带条件的 `UPDATE ... WHERE used_at IS NULL` 实现，并发下只有一次能成功。

密码相关操作成功后一律吊销该用户全部刷新令牌：改密的语义包含「踢掉所有旧会话」，
否则攻击者持有的旧刷新令牌仍可继续续期。
"""

import logging
import uuid
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import user as repository
from utils import auth_tokens as tokens
from models.user import PURPOSE_PASSWORD_RESET, User
from utils.auth_crypto import (
    PasswordPolicyError,
    hash_ip,
    hash_password,
    mask_email,
    validate_password_strength,
    verify_password,
)
from schemas.auth import TokenPairResponse
from services.auth_accounts import (
    AuthDomainError,
    current_tenant_id,
    to_profile,
)
from services.mailer import get_mailer
from utils.config_reader import read_str

logger = logging.getLogger(__name__)

# 统一的防枚举提示：无论邮箱是否注册都返回同一句话。
GENERIC_RESET_MESSAGE = "如果该邮箱已注册，我们已发送密码重置邮件，请查收。"


async def issue_session(
    session: AsyncSession,
    user: User,
    family_id: Optional[str] = None,
) -> TokenPairResponse:
    """为用户签发一对令牌。

    `family_id` 为空表示这是一次全新登录，会开启新的令牌族；
    刷新场景会传入原族标识，使整条链保持可追溯与可整族吊销。
    """
    access_token, expires_in = tokens.issue_access_token(user)
    refresh_plain, refresh_expires_at = tokens.issue_refresh_token()
    await repository.add_refresh_token(
        session, user, family_id or uuid.uuid4().hex, refresh_plain, refresh_expires_at
    )
    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_plain,
        expires_in=expires_in,
        user=to_profile(user),
    )


async def rotate_session(session: AsyncSession, refresh_token: str, ip: Optional[str] = None) -> TokenPairResponse:
    """校验并轮换刷新令牌。

    任何异常路径都返回同一条 401 提示，避免通过错误差异推断令牌状态。
    """
    record = await repository.get_refresh_token(session, refresh_token)
    if record is None:
        logger.info("[BIZ] refresh rejected reason=unknown_token")
        raise AuthDomainError("登录状态已失效，请重新登录", status_code=401)

    if record.used_at is not None:
        # 已使用的令牌再次出现 = 重放，整族吊销并强制重新登录。
        revoked = await repository.revoke_token_family(session, record.family_id)
        await repository.write_audit(
            session,
            event="refresh_replay",
            outcome="failure",
            user_id=record.user_id,
            context={"tenant_id": record.tenant_id, "ip_hash": hash_ip(ip), "detail": f"revoked={revoked}"},
        )
        logger.warning("[BIZ] refresh token replay detected, family revoked count=%s", revoked)
        raise AuthDomainError("登录状态已失效，请重新登录", status_code=401)

    if record.revoked_at is not None or tokens.is_expired(record.expires_at):
        logger.info("[BIZ] refresh rejected reason=revoked_or_expired")
        raise AuthDomainError("登录状态已失效，请重新登录", status_code=401)

    user = await repository.get_user_by_id(session, record.user_id)
    if user is None or user.status != "active":
        raise AuthDomainError("登录状态已失效，请重新登录", status_code=401)

    pair = await issue_session(session, user, family_id=record.family_id)
    successor = await repository.get_refresh_token(session, pair.refresh_token)
    rotated = await repository.mark_refresh_token_used(session, record.id, successor.id if successor else 0)
    if rotated != 1:
        # 并发刷新竞争失败：说明另一请求已完成轮换，本次不得放行。
        logger.warning("[BIZ] refresh rotation lost race, rejecting request")
        raise AuthDomainError("登录状态已失效，请重新登录", status_code=401)

    await repository.write_audit(
        session,
        event="refresh",
        user_id=user.id,
        context={"tenant_id": user.tenant_id, "ip_hash": hash_ip(ip)},
    )
    return pair


async def logout(session: AsyncSession, refresh_token: Optional[str], user_id: Optional[int] = None) -> str:
    """登出。

    提供刷新令牌时吊销其整族；否则吊销该用户全部令牌。
    未找到令牌也返回成功：登出是幂等操作，且不应暴露令牌是否存在。
    """
    if refresh_token:
        record = await repository.get_refresh_token(session, refresh_token)
        if record is not None:
            await repository.revoke_token_family(session, record.family_id)
            await repository.write_audit(session, event="logout", user_id=record.user_id)
            return "已退出登录"

    if user_id is not None:
        await repository.revoke_all_user_tokens(session, user_id)
        await repository.write_audit(session, event="logout", user_id=user_id)
    return "已退出登录"


async def request_password_reset(
    session: AsyncSession,
    email: str,
    ip: Optional[str] = None,
) -> Tuple[str, Optional[str], Optional[str]]:
    """发起密码重置。

    Returns:
        `(message, target_email, reset_token)`；后两项仅在账号存在时非空，
        由调用方在事务提交后投递邮件。
    """
    tenant_id = current_tenant_id()
    user = await repository.get_user_by_email(session, tenant_id, email)
    if user is None:
        # 不存在也返回同样的提示，消除枚举通道。
        logger.info("[BIZ] password reset requested for unknown email=%s", mask_email(email))
        return GENERIC_RESET_MESSAGE, None, None

    await repository.invalidate_one_time_tokens(session, user.id, PURPOSE_PASSWORD_RESET)
    plain = tokens.generate_token()
    await repository.add_one_time_token(
        session, user.id, PURPOSE_PASSWORD_RESET, plain, tokens.one_time_token_expiry(hours=2)
    )
    await repository.write_audit(
        session,
        event="password_reset_requested",
        user_id=user.id,
        context={"tenant_id": tenant_id, "ip_hash": hash_ip(ip)},
    )
    return GENERIC_RESET_MESSAGE, user.email, plain


async def confirm_password_reset(session: AsyncSession, token: str, new_password: str) -> str:
    """用一次性令牌重置密码。

    幂等：令牌已被消费时返回「已重置」而非报错，但**不会**再次改写密码。
    """
    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        raise AuthDomainError(str(exc)) from exc

    record = await repository.get_one_time_token(session, PURPOSE_PASSWORD_RESET, token)
    if record is None or tokens.is_expired(record.expires_at):
        raise AuthDomainError("重置链接无效或已过期，请重新获取", status_code=400)

    if not await repository.consume_one_time_token(session, record.id):
        return "密码已重置，请使用新密码登录"

    await repository.update_user_fields(
        session,
        record.user_id,
        password_hash=hash_password(new_password),
        failed_login_count=0,
        locked_until=None,
    )
    # 改密后吊销全部会话，防止旧刷新令牌继续可用。
    await repository.revoke_all_user_tokens(session, record.user_id)
    await repository.write_audit(session, event="password_reset", user_id=record.user_id)
    logger.info("[BIZ] password reset completed")
    return "密码已重置，请使用新密码登录"


async def change_password(
    session: AsyncSession,
    user_id: int,
    current_password: str,
    new_password: str,
) -> str:
    """已登录用户修改密码。"""
    try:
        validate_password_strength(new_password)
    except PasswordPolicyError as exc:
        raise AuthDomainError(str(exc)) from exc

    user = await repository.get_user_by_id(session, user_id)
    if user is None:
        raise AuthDomainError("账号不存在", status_code=404)

    if not verify_password(user.password_hash, current_password):
        await repository.write_audit(
            session, event="password_change", outcome="failure", user_id=user_id
        )
        raise AuthDomainError("当前密码不正确", status_code=400)

    await repository.update_user_fields(session, user_id, password_hash=hash_password(new_password))
    await repository.revoke_all_user_tokens(session, user_id)
    await repository.write_audit(session, event="password_change", user_id=user_id)
    logger.info("[BIZ] password changed successfully")
    return "密码修改成功，请重新登录"


async def deliver_reset_email(email: str, token: str) -> None:
    """投递密码重置邮件（必须在事务提交后调用）。"""
    base_url = (read_str("auth_public_base_url", "") or read_str("frontend_url", "")).rstrip("/")
    link = f"{base_url}/reset-password?token={token}" if base_url else f"/reset-password?token={token}"
    body = f"请点击以下链接重置密码（2 小时内有效）：\n{link}\n若非本人操作请忽略此邮件。"
    await get_mailer().send(email, "【LexHubPro】密码重置", body)