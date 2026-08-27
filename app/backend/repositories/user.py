"""自建认证的数据访问层。

分层职责：本模块只做**单一目的的数据操作**，不含业务编排、不发邮件、不签令牌。
所有函数接收外部传入的 `AsyncSession`，由上层决定事务边界——这样才能把
「校验 + 写入」放进同一个事务，避免并发下的竞态。

并发与幂等的关键实现：
- 失败计数用 SQL 表达式 `failed_login_count + 1` 原子自增，而非「读出再写回」；
- 唯一性冲突交由数据库唯一约束裁决，应用层捕获 `IntegrityError`；
- 一次性令牌消费用带条件的 `UPDATE ... WHERE consumed_at IS NULL` 并检查影响行数，
  使并发重复提交中只有一个能真正消费成功。
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import (
    AuthAudit,
    OneTimeToken,
    RefreshToken,
    User,
)
from utils.auth_crypto import hash_token

logger = logging.getLogger(__name__)


class EmailAlreadyExistsError(Exception):
    """邮箱在该租户下已注册。上层需转换为防枚举的统一响应。"""


class TokenHashConflictError(Exception):
    """一次性令牌摘要冲突。上层可换一份明文后重试签发。"""


def normalize_email(email: str) -> str:
    """邮箱归一化：去空白并转小写，使唯一约束大小写不敏感。"""
    return (email or "").strip().lower()


async def get_user_by_email(session: AsyncSession, tenant_id: str, email: str) -> Optional[User]:
    """按租户 + 邮箱查询用户。"""
    stmt = select(User).where(
        User.tenant_id == tenant_id,
        User.email == normalize_email(email),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """按主键查询用户。"""
    return (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def create_user(session: AsyncSession, user: User) -> User:
    """插入新用户；邮箱重复时抛 `EmailAlreadyExistsError`。

    依赖数据库唯一约束而非「先查后插」：后者在并发注册下会双双通过检查。

    插入包在 SAVEPOINT（`begin_nested`）里：唯一约束冲突只回滚这一个保存点，
    外层事务仍然可用，因此调用方能在同一事务内继续写审计等后续操作。
    直接 `session.rollback()` 会摧毁外层事务，导致后续语句全部失败。
    """
    user.email = normalize_email(user.email)
    try:
        async with session.begin_nested():
            session.add(user)
            await session.flush()
    except IntegrityError as exc:
        raise EmailAlreadyExistsError("email already registered") from exc
    return user


async def update_user_fields(session: AsyncSession, user_id: int, **fields) -> None:
    """按主键更新指定字段。"""
    if not fields:
        return
    await session.execute(update(User).where(User.id == user_id).values(**fields))


async def increment_failed_login(session: AsyncSession, user_id: int, locked_until: Optional[datetime]) -> None:
    """原子自增失败计数，并可选地写入锁定截止时间。

    自增交给数据库执行，避免「读-改-写」在并发爆破下丢失计数。
    """
    values = {"failed_login_count": User.failed_login_count + 1}
    if locked_until is not None:
        values["locked_until"] = locked_until
    await session.execute(update(User).where(User.id == user_id).values(**values))


async def reset_login_failures(session: AsyncSession, user_id: int, last_login: datetime) -> None:
    """登录成功后清零失败计数、解除锁定并记录登录时间。"""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(failed_login_count=0, locked_until=None, last_login=last_login)
    )


async def add_refresh_token(
    session: AsyncSession,
    user: User,
    family_id: str,
    token_plain: str,
    expires_at: datetime,
) -> RefreshToken:
    """写入刷新令牌摘要记录。"""
    record = RefreshToken(
        user_id=user.id,
        tenant_id=user.tenant_id,
        family_id=family_id,
        token_hash=hash_token(token_plain),
        expires_at=expires_at,
    )
    session.add(record)
    await session.flush()
    return record


async def get_refresh_token(session: AsyncSession, token_plain: str) -> Optional[RefreshToken]:
    """按令牌明文的摘要查找记录。"""
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_token(token_plain))
    return (await session.execute(stmt)).scalar_one_or_none()


async def mark_refresh_token_used(session: AsyncSession, token_id: int, replaced_by_id: int) -> int:
    """把刷新令牌标记为已使用并指向后继令牌。

    条件 `used_at IS NULL` 使轮换本身具备原子性：并发两次刷新只有一次影响行数为 1，
    另一次得到 0，从而被判定为重放。

    Returns:
        受影响行数。
    """
    result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id, RefreshToken.used_at.is_(None))
        .values(used_at=datetime.now(timezone.utc), replaced_by_id=replaced_by_id)
    )
    return result.rowcount or 0


async def revoke_token_family(session: AsyncSession, family_id: str) -> int:
    """吊销整族刷新令牌（检测到重放或用户登出时使用）。

    Returns:
        实际吊销的记录数。
    """
    result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    return result.rowcount or 0


async def revoke_all_user_tokens(session: AsyncSession, user_id: int) -> int:
    """吊销某用户全部未失效刷新令牌（改密码、禁用账号时使用）。"""
    result = await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    return result.rowcount or 0


async def add_one_time_token(
    session: AsyncSession,
    user_id: int,
    purpose: str,
    token_plain: str,
    expires_at: datetime,
) -> OneTimeToken:
    """写入一次性令牌摘要记录。"""
    record = OneTimeToken(
        user_id=user_id,
        purpose=purpose,
        token_hash=hash_token(token_plain),
        expires_at=expires_at,
    )
    try:
        async with session.begin_nested():
            session.add(record)
            await session.flush()
    except IntegrityError as exc:
        raise TokenHashConflictError("token hash conflict") from exc
    return record


async def get_one_time_token(session: AsyncSession, purpose: str, token_plain: str) -> Optional[OneTimeToken]:
    """按用途 + 令牌摘要查找一次性令牌。"""
    stmt = select(OneTimeToken).where(
        OneTimeToken.purpose == purpose,
        OneTimeToken.token_hash == hash_token(token_plain),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_one_time_token_for_user(
    session: AsyncSession, user_id: int, purpose: str, token_plain: str
) -> Optional[OneTimeToken]:
    """按用户 + 用途 + 摘要查找（验证码空间小，必须绑用户）。"""
    stmt = select(OneTimeToken).where(
        OneTimeToken.user_id == user_id,
        OneTimeToken.purpose == purpose,
        OneTimeToken.token_hash == hash_token(token_plain),
        OneTimeToken.consumed_at.is_(None),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def consume_one_time_token(session: AsyncSession, token_id: int) -> bool:
    """消费一次性令牌。

    条件 `consumed_at IS NULL` 保证幂等：重复提交同一令牌时只有首次返回 True，
    后续返回 False，上层据此跳过副作用但仍可返回成功语义。
    """
    result = await session.execute(
        update(OneTimeToken)
        .where(OneTimeToken.id == token_id, OneTimeToken.consumed_at.is_(None))
        .values(consumed_at=datetime.now(timezone.utc))
    )
    return (result.rowcount or 0) == 1


async def invalidate_one_time_tokens(session: AsyncSession, user_id: int, purpose: str) -> int:
    """把某用户指定用途的未消费令牌全部作废（重新签发前调用）。"""
    result = await session.execute(
        update(OneTimeToken)
        .where(
            OneTimeToken.user_id == user_id,
            OneTimeToken.purpose == purpose,
            OneTimeToken.consumed_at.is_(None),
        )
        .values(consumed_at=datetime.now(timezone.utc))
    )
    return result.rowcount or 0


async def write_audit(
    session: AsyncSession,
    event: str,
    outcome: str = "success",
    user_id: Optional[int] = None,
    context: Optional[dict] = None,
) -> None:
    """写入审计记录。

    `context` 只接受已脱敏的字段（如 `ip_hash`、`tenant_id`、简短说明），
    调用方负责确保其中不含密码、令牌明文或完整邮箱。
    """
    payload = context or {}
    session.add(
        AuthAudit(
            tenant_id=payload.get("tenant_id") or "default",
            user_id=user_id,
            event=event,
            outcome=outcome,
            ip_hash=payload.get("ip_hash"),
            detail=payload.get("detail"),
        )
    )


async def list_users(
    session: AsyncSession,
    tenant_id: str,
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
) -> Sequence[User]:
    """分页列出租户下的用户（管理端使用）。"""
    conditions = [User.tenant_id == tenant_id]
    if status:
        conditions.append(User.status == status)
    stmt = (
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return (await session.execute(stmt)).scalars().all()


async def count_users(session: AsyncSession, tenant_id: str, status: Optional[str] = None) -> int:
    """统计租户下的用户数。"""
    conditions = [User.tenant_id == tenant_id]
    if status:
        conditions.append(User.status == status)
    stmt = select(func.count()).select_from(User).where(*conditions)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def list_audits(
    session: AsyncSession,
    tenant_id: str,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuthAudit]:
    """分页列出认证审计（管理端使用）。"""
    stmt = (
        select(AuthAudit)
        .where(AuthAudit.tenant_id == tenant_id)
        .order_by(AuthAudit.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return (await session.execute(stmt)).scalars().all()


async def count_audits(session: AsyncSession, tenant_id: str) -> int:
    """统计租户下的审计条数。"""
    stmt = select(func.count()).select_from(AuthAudit).where(AuthAudit.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)