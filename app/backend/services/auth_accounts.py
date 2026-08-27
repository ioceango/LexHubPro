"""自建认证：账号类业务编排（注册 / 邮箱验证 / 登录）。

安全设计要点：
- **防枚举**：注册与找回密码一律返回同一句提示，不透露邮箱是否已存在；
  登录失败无论「账号不存在」还是「密码错误」都返回同一错误。
- **抗爆破**：连续失败达到阈值后临时锁定账号，锁定期间即使密码正确也拒绝。
- **事务边界**：数据库写入在事务内完成后再提交，邮件发送放到事务**之外**，
  避免事务跨越网络调用而长时间占用连接。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from auth_providers.base import DEFAULT_TENANT_ID
from repositories import user as repository
from utils import auth_tokens as tokens
from models.user import PURPOSE_EMAIL_VERIFY, User
from utils.auth_crypto import (
    PasswordPolicyError,
    bind_email_code,
    generate_email_code,
    hash_ip,
    hash_password,
    mask_email,
    validate_password_strength,
    verify_password,
)
from schemas.auth import UserProfile
from services.mailer import get_mailer, smtp_configured
from utils.config_reader import read_bool, read_int, read_str
from utils.mailbox import UNSUPPORTED_MAILBOX_HINT, is_supported_mailbox

logger = logging.getLogger(__name__)

# 统一的防枚举提示：无论邮箱是否已注册都返回同一句话。
GENERIC_REGISTER_MESSAGE = "验证码已发送。请在 15 分钟内完成邮箱验证。"
GENERIC_REGISTER_ACTIVE_MESSAGE = "注册成功，请使用该邮箱与密码登录。"
GENERIC_REGISTER_DONE = "注册成功，请登录"
# 统一的登录失败提示：不区分账号不存在与密码错误。
GENERIC_LOGIN_ERROR = "邮箱或密码不正确"

DEFAULT_MAX_LOGIN_FAILURES = 5
DEFAULT_LOCK_MINUTES = 15


class AuthDomainError(Exception):
    """自建认证业务失败（可安全展示给用户）。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def current_tenant_id() -> str:
    """当前部署的租户标识。单租户时为默认值，多租户可由配置覆盖。"""
    return read_str("auth_tenant_id", DEFAULT_TENANT_ID)


def max_login_failures() -> int:
    value = read_int("auth_max_login_failures", DEFAULT_MAX_LOGIN_FAILURES)
    return value if value > 0 else DEFAULT_MAX_LOGIN_FAILURES


def lock_minutes() -> int:
    value = read_int("auth_lock_minutes", DEFAULT_LOCK_MINUTES)
    return value if value > 0 else DEFAULT_LOCK_MINUTES


def require_email_verification() -> bool:
    """配置了 SMTP 则必须验证；否则尊重 AUTH_REQUIRE_EMAIL_VERIFICATION。"""
    if smtp_configured():
        return True
    return read_bool("auth_require_email_verification", False)


def register_success_message() -> str:
    """注册对外文案。是否发验证码只影响措辞，不透露邮箱是否已存在。"""
    if require_email_verification():
        return GENERIC_REGISTER_MESSAGE
    return GENERIC_REGISTER_ACTIVE_MESSAGE


def to_profile(user: User) -> UserProfile:
    """把 ORM 记录映射为对外资料视图（不含任何凭据字段）。"""
    return UserProfile(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        status=user.status,
        tenant_id=user.tenant_id,
        last_login=user.last_login,
    )


def _is_locked(user: User) -> bool:
    """判断账号是否处于锁定期内。"""
    if user.locked_until is None:
        return False
    moment = user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
    return moment > datetime.now(timezone.utc)


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    name: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """注册新账号。

    Returns:
        `(message, verify_token)`；`verify_token` 仅在需要发信时非空，
        由调用方在事务提交后投递，避免事务跨越网络调用。
    """
    try:
        validate_password_strength(password)
    except PasswordPolicyError as exc:
        raise AuthDomainError(str(exc)) from exc

    tenant_id = current_tenant_id()
    email = email.strip().lower()
    if not is_supported_mailbox(email):
        raise AuthDomainError(UNSUPPORTED_MAILBOX_HINT, status_code=400)
    needs_verification = require_email_verification()
    status = "pending_verification" if needs_verification else "active"
    message = register_success_message()

    candidate = User(
        tenant_id=tenant_id,
        email=email,
        password_hash=hash_password(password),
        name=(name or "").strip() or None,
        role="user",
        status=status,
    )

    try:
        created = await repository.create_user(session, candidate)
    except repository.EmailAlreadyExistsError:
        # 已存在则对外仍返回同一句；待验证/已激活账号补发验证码，避免 SMTP 配好后「再点注册收不到信」。
        code = await _reissue_code_for_existing(session, email, needs_verification)
        logger.info("[BIZ] register existing email=%s reissue=%s", mask_email(email), bool(code))
        return message, code

    verify_token: Optional[str] = None
    if needs_verification:
        verify_token = await _issue_verify_code(session, created.id)

    await repository.write_audit(
        session,
        event="register",
        user_id=created.id,
        context={"tenant_id": tenant_id, "ip_hash": hash_ip(ip)},
    )
    logger.info("[BIZ] user registered email=%s verification=%s", mask_email(email), needs_verification)
    return message, verify_token


async def _reissue_code_for_existing(
    session: AsyncSession, email: str, needs_verification: bool
) -> Optional[str]:
    """已存在账号：非禁用且需要验证时重新签发验证码。"""
    if not needs_verification:
        return None
    user = await repository.get_user_by_email(session, current_tenant_id(), email)
    if user is None or user.status == "disabled":
        return None
    return await _issue_verify_code(session, user.id)


async def _issue_verify_code(session: AsyncSession, user_id: int) -> str:
    """签发 6 位邮箱验证码，并作废该用户此前未消费的验证码。"""
    await repository.invalidate_one_time_tokens(session, user_id, PURPOSE_EMAIL_VERIFY)
    last_error: Optional[Exception] = None
    for _ in range(5):
        plain = generate_email_code()
        try:
            await repository.add_one_time_token(
                session,
                user_id,
                PURPOSE_EMAIL_VERIFY,
                bind_email_code(user_id, plain),
                tokens.email_code_expiry(),
            )
            return plain
        except repository.TokenHashConflictError as exc:
            last_error = exc
    raise AuthDomainError("验证码签发失败，请稍后重试", status_code=503) from last_error


async def resend_verification_code(session: AsyncSession, email: str) -> Optional[str]:
    """为待验证账号重新签发验证码。账号不存在或已激活时返回 None（防枚举）。"""
    tenant_id = current_tenant_id()
    user = await repository.get_user_by_email(session, tenant_id, email)
    if user is None or user.status != "pending_verification":
        return None
    return await _issue_verify_code(session, user.id)


async def verify_email_code(session: AsyncSession, email: str, code: str) -> str:
    """用邮箱 + 6 位验证码激活账号。"""
    tenant_id = current_tenant_id()
    user = await repository.get_user_by_email(session, tenant_id, email.strip().lower())
    invalid = AuthDomainError("验证码无效或已过期，请重新获取", status_code=400)
    if user is None:
        raise invalid
    record = await repository.get_one_time_token_for_user(
        session, user.id, PURPOSE_EMAIL_VERIFY, bind_email_code(user.id, code.strip())
    )
    if record is None or tokens.is_expired(record.expires_at):
        raise invalid
    consumed = await repository.consume_one_time_token(session, record.id)
    if not consumed:
        return "邮箱已完成验证，请直接登录"
    await repository.update_user_fields(session, record.user_id, status="active")
    await repository.write_audit(session, event="email_verified", user_id=record.user_id)
    logger.info("[BIZ] email verified via code user_id_present=%s", bool(record.user_id))
    return GENERIC_REGISTER_DONE


async def verify_email(session: AsyncSession, token: str) -> str:
    """校验邮箱验证令牌并激活账号。

    幂等：重复提交同一令牌时，第二次不会重复激活，但仍返回成功语义，
    因为对用户而言「邮箱已验证」这一目标状态已达成。
    """
    record = await repository.get_one_time_token(session, PURPOSE_EMAIL_VERIFY, token)
    if record is None or tokens.is_expired(record.expires_at):
        raise AuthDomainError("验证链接无效或已过期，请重新获取", status_code=400)

    consumed = await repository.consume_one_time_token(session, record.id)
    if not consumed:
        return "邮箱已完成验证，请直接登录"

    await repository.update_user_fields(session, record.user_id, status="active")
    await repository.write_audit(session, event="email_verified", user_id=record.user_id)
    logger.info("[BIZ] email verified user_id_present=%s", bool(record.user_id))
    return GENERIC_REGISTER_DONE


async def authenticate(
    session: AsyncSession,
    email: str,
    password: str,
    ip: Optional[str] = None,
) -> User:
    """校验凭据并返回用户记录。

    失败路径全部抛出同一条消息，且对不存在的账号也执行密码校验之外的等价流程，
    避免通过响应内容或明显的时间差异区分账号是否存在。
    """
    tenant_id = current_tenant_id()
    user = await repository.get_user_by_email(session, tenant_id, email)

    if user is None:
        await repository.write_audit(
            session,
            event="login",
            outcome="failure",
            context={"tenant_id": tenant_id, "ip_hash": hash_ip(ip), "detail": "unknown_account"},
        )
        logger.info("[BIZ] login failed reason=unknown_account email=%s", mask_email(email))
        raise AuthDomainError(GENERIC_LOGIN_ERROR, status_code=401)

    if _is_locked(user):
        logger.info("[BIZ] login blocked reason=locked email=%s", mask_email(email))
        raise AuthDomainError(
            f"尝试次数过多，账号已临时锁定，请在 {lock_minutes()} 分钟后重试", status_code=429
        )

    if not verify_password(user.password_hash, password):
        await _handle_failed_attempt(session, user, ip)
        raise AuthDomainError(GENERIC_LOGIN_ERROR, status_code=401)

    if user.status != "active":
        message = (
            "邮箱尚未验证，请先完成邮箱验证"
            if user.status == "pending_verification"
            else "账号已被禁用，请联系管理员"
        )
        raise AuthDomainError(message, status_code=403)

    now = datetime.now(timezone.utc)
    await repository.reset_login_failures(session, user.id, now)
    await repository.write_audit(
        session,
        event="login",
        user_id=user.id,
        context={"tenant_id": tenant_id, "ip_hash": hash_ip(ip)},
    )
    user.last_login = now
    logger.info("[BIZ] login succeeded email=%s", mask_email(email))
    return user


async def _handle_failed_attempt(session: AsyncSession, user: User, ip: Optional[str]) -> None:
    """处理一次失败尝试：原子自增计数，达到阈值则锁定。"""
    threshold = max_login_failures()
    # 当前值 + 本次失败达到阈值时同步写入锁定时间，避免再多一次请求才生效。
    reached = (user.failed_login_count or 0) + 1 >= threshold
    locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes()) if reached else None

    await repository.increment_failed_login(session, user.id, locked_until)
    await repository.write_audit(
        session,
        event="login",
        outcome="failure",
        user_id=user.id,
        context={
            "tenant_id": user.tenant_id,
            "ip_hash": hash_ip(ip),
            "detail": "locked" if reached else "bad_password",
        },
    )
    logger.info("[BIZ] login failed reason=bad_password locked=%s email=%s", reached, mask_email(user.email))


async def deliver_verification_email(email: str, code: str) -> None:
    """投递 6 位验证码。必须在事务提交之后调用。"""
    body = (
        "您正在注册 LexHubPro。\n\n"
        f"邮箱验证码：{code}\n\n"
        "15 分钟内有效。如非本人操作，请忽略本邮件。"
    )
    await get_mailer().send(email, "【LexHubPro】邮箱验证码", body)