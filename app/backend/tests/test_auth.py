"""自建认证编排回归：注册登录、刷新轮换、重放吊销、锁定、防枚举（FEAT-005）。"""

import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import Base
from models.user import AUTH_MODELS
from services import auth_accounts as accounts
from services import auth_sessions as sessions
from services.auth_accounts import (
    GENERIC_LOGIN_ERROR,
    GENERIC_REGISTER_ACTIVE_MESSAGE,
    GENERIC_REGISTER_MESSAGE,
    AuthDomainError,
)


async def _session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[model.__table__ for model in AUTH_MODELS],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, maker


@pytest.mark.asyncio
async def test_register_login_refresh_and_replay(local_auth_env):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            message, token = await accounts.register_user(
                session, "user@example.com", "letters12345", "Tester"
            )
            assert message == GENERIC_REGISTER_ACTIVE_MESSAGE
            assert token is None
            user = await accounts.authenticate(session, "user@example.com", "letters12345")
            first = await sessions.issue_session(session, user)
            second = await sessions.rotate_session(session, first.refresh_token)
            assert second.refresh_token != first.refresh_token
            with pytest.raises(AuthDomainError) as replay:
                await sessions.rotate_session(session, first.refresh_token)
            assert replay.value.status_code == 401
            with pytest.raises(AuthDomainError):
                await sessions.rotate_session(session, second.refresh_token)
    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_register_does_not_enumerate(local_auth_env):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            first, _ = await accounts.register_user(session, "dup@example.com", "letters12345")
            second, token = await accounts.register_user(session, "dup@example.com", "letters12345")
            assert first == second == GENERIC_REGISTER_ACTIVE_MESSAGE
            assert token is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_account_same_error_as_bad_password(local_auth_env, caplog):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            await accounts.register_user(session, "known@example.com", "letters12345")
            with pytest.raises(AuthDomainError) as missing:
                await accounts.authenticate(session, "nobody@example.com", "letters12345")
            with pytest.raises(AuthDomainError) as wrong:
                await accounts.authenticate(session, "known@example.com", "wrong-pass-1")
            assert str(missing.value) == str(wrong.value) == GENERIC_LOGIN_ERROR
            combined = "\n".join(record.getMessage() for record in caplog.records)
            assert "nobody@example.com" not in combined
            assert "known@example.com" not in combined
    await engine.dispose()


@pytest.mark.asyncio
async def test_lockout_after_threshold(lockout_auth_env):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            await accounts.register_user(session, "lock@example.com", "letters12345")
            with pytest.raises(AuthDomainError):
                await accounts.authenticate(session, "lock@example.com", "bad-password")
            with pytest.raises(AuthDomainError) as second:
                await accounts.authenticate(session, "lock@example.com", "bad-password")
            assert second.value.status_code == 401
            with pytest.raises(AuthDomainError) as locked:
                await accounts.authenticate(session, "lock@example.com", "letters12345")
            assert locked.value.status_code == 429
    await engine.dispose()


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(local_auth_env):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            await accounts.register_user(session, "out@example.com", "letters12345")
            user = await accounts.authenticate(session, "out@example.com", "letters12345")
            pair = await sessions.issue_session(session, user)
            await sessions.logout(session, pair.refresh_token)
            with pytest.raises(AuthDomainError):
                await sessions.rotate_session(session, pair.refresh_token)
    await engine.dispose()


@pytest.mark.asyncio
async def test_disabled_user_cannot_login(local_auth_env):
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            await accounts.register_user(session, "off@example.com", "letters12345")
            from repositories import user as repository

            user = await repository.get_user_by_email(session, "default", "off@example.com")
            await repository.update_user_fields(session, user.id, status="disabled")
            with pytest.raises(AuthDomainError) as exc:
                await accounts.authenticate(session, "off@example.com", "letters12345")
            assert exc.value.status_code == 403
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_verification_code_activates_account(verify_auth_env):
    # BUG-004 回归
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            message, code = await accounts.register_user(session, "code@example.com", "letters12345")
            assert message == GENERIC_REGISTER_MESSAGE
            assert code is not None and len(code) == 6 and code.isdigit()
            with pytest.raises(AuthDomainError) as pending:
                await accounts.authenticate(session, "code@example.com", "letters12345")
            assert pending.value.status_code == 403
            ok = await accounts.verify_email_code(session, "code@example.com", code)
            assert "成功" in ok
            user = await accounts.authenticate(session, "code@example.com", "letters12345")
            assert user.status == "active"
            with pytest.raises(AuthDomainError):
                await accounts.verify_email_code(session, "code@example.com", "000000")
            resent = await accounts.resend_verification_code(session, "code@example.com")
            assert resent is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_same_code_can_belong_to_two_users(verify_auth_env):
    # BUG-004 回归：6 位码必须按用户绑定哈希，否则会撞全局唯一约束
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            _, first_code = await accounts.register_user(session, "one@example.com", "letters12345")
            _, second_code = await accounts.register_user(session, "two@example.com", "letters12345")
            assert first_code and second_code
            await accounts.verify_email_code(session, "one@example.com", first_code)
            await accounts.verify_email_code(session, "two@example.com", second_code)
    await engine.dispose()


@pytest.mark.asyncio
async def test_register_rejects_unsupported_mailbox(mailbox_strict_env):
    # BUG-004 回归：仅 163 / Gmail
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            with pytest.raises(AuthDomainError) as rejected:
                await accounts.register_user(session, "user@qq.com", "letters12345")
            assert rejected.value.status_code == 400
            message, token = await accounts.register_user(session, "user@163.com", "letters12345")
            assert token is None
            assert message == GENERIC_REGISTER_ACTIVE_MESSAGE
            gmail_msg, _ = await accounts.register_user(session, "user@gmail.com", "letters12345")
            assert gmail_msg == GENERIC_REGISTER_ACTIVE_MESSAGE
    await engine.dispose()


@pytest.mark.asyncio
async def test_reregister_existing_user_reissues_code(verify_auth_env):
    # BUG-005 回归：已存在账号再次注册必须重新签发验证码，否则 SMTP 配好后收不到信
    engine, maker = await _session_factory()
    async with maker() as session:
        async with session.begin():
            _, first = await accounts.register_user(session, "again@gmail.com", "letters12345")
            _, second = await accounts.register_user(session, "again@gmail.com", "letters12345")
            assert first and second and first != second
            ok = await accounts.verify_email_code(session, "again@gmail.com", second)
            assert "成功" in ok
            _, third = await accounts.register_user(session, "again@gmail.com", "letters12345")
            assert third is not None and len(third) == 6
            from repositories import user as repository

            user = await repository.get_user_by_email(session, "default", "again@gmail.com")
            await repository.update_user_fields(session, user.id, status="disabled")
            _, blocked = await accounts.register_user(session, "again@gmail.com", "letters12345")
            assert blocked is None
    await engine.dispose()

