"""FEAT-008：用户 LLM 配置。提供商 HTTP 一律 mock。"""

import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import Base
from models.user import AUTH_MODELS
from models.user_llm import LLM_MODELS
from repositories import user as user_repo
from models.user import User
from services import user_llm as llm
from utils.auth_crypto import hash_password


async def _factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[model.__table__ for model in AUTH_MODELS + LLM_MODELS],
        )
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, maker


async def _user(session: AsyncSession) -> User:
    created = await user_repo.create_user(
        session,
        User(
            tenant_id="default",
            email="owner@gmail.com",
            password_hash=hash_password("letters12345"),
            role="user",
            status="active",
        ),
    )
    return created


@pytest.mark.asyncio
async def test_save_key_returns_suffix_not_plaintext(auth_env):
    engine, maker = await _factory()
    plain = "sk-test-secret-key-aaa"
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            view = await llm.save_provider_key(session, "default", owner.id, "deepseek", plain)
            assert view["key_suffix"] == plain[-4:]
            assert plain not in str(view)
            rows = await llm.list_provider_views(session, "default", owner.id)
            deepseek = next(item for item in rows if item["provider"] == "deepseek")
            assert deepseek["configured"] is True
            assert "sk-test" not in json_blob(deepseek)
    await engine.dispose()


def json_blob(value) -> str:
    return str(value)


@pytest.mark.asyncio
async def test_enable_second_model_disables_first(auth_env):
    engine, maker = await _factory()
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            await llm.save_provider_key(session, "default", owner.id, "deepseek", "sk-aaaaaaaa")
            first = await llm.add_model(
                session,
                "default",
                owner.id,
                {"provider": "deepseek", "model_id": "deepseek-chat", "enabled": True},
            )
            assert first["enabled"] is True
            second = await llm.add_model(
                session,
                "default",
                owner.id,
                {"provider": "deepseek", "model_id": "deepseek-reasoner", "enabled": True},
            )
            assert second["enabled"] is True
            models = await llm.list_saved_models(session, "default", owner.id)
            enabled = [item for item in models if item["enabled"]]
            assert len(enabled) == 1
            assert enabled[0]["model_id"] == "deepseek-reasoner"
            active = await llm.get_active(session, "default", owner.id)
            assert active is not None
            assert active.model_id == "deepseek-reasoner"
            assert active.api_key == "sk-aaaaaaaa"
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_catalog_uses_adapter_and_invalid_key(auth_env, monkeypatch):
    engine, maker = await _factory()

    async def fake_list(self, api_key: str):
        assert api_key.startswith("sk-")
        return [{"id": "deepseek-chat", "name": "DeepSeek Chat"}]

    from llm_providers.deepseek import DeepSeekProvider

    monkeypatch.setattr(DeepSeekProvider, "list_models", fake_list)
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            await llm.save_provider_key(session, "default", owner.id, "deepseek", "sk-bbbbbbbb")
            catalog = await llm.refresh_catalog(session, "default", owner.id, "deepseek")
            assert catalog[0]["id"] == "deepseek-chat"
    await engine.dispose()


@pytest.mark.asyncio
async def test_unknown_provider_rejected(auth_env):
    engine, maker = await _factory()
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            with pytest.raises(Exception) as exc:
                await llm.save_provider_key(session, "default", owner.id, "openai", "sk-not-allowed")
            assert "提供商" in str(exc.value)
    await engine.dispose()


@pytest.mark.asyncio
async def test_placeholder_key_rejected(auth_env):
    engine, maker = await _factory()
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            with pytest.raises(llm.UserLlmError):
                await llm.save_provider_key(session, "default", owner.id, "deepseek", "$$SECRET$$")
    await engine.dispose()


@pytest.mark.asyncio
async def test_disable_enabled_model_clears_active(auth_env):
    engine, maker = await _factory()
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            await llm.save_provider_key(session, "default", owner.id, "deepseek", "sk-cccccccc")
            row = await llm.add_model(
                session,
                "default",
                owner.id,
                {"provider": "deepseek", "model_id": "deepseek-chat", "enabled": True},
            )
            await llm.set_enabled(session, "default", owner.id, row["id"], False)
            assert await llm.get_active(session, "default", owner.id) is None
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_catalog_invalid_key(auth_env, monkeypatch):
    engine, maker = await _factory()

    async def boom(self, api_key: str):
        from llm_providers.base import LlmProviderError

        raise LlmProviderError("密钥无效，请核对后重试", 400)

    from llm_providers.deepseek import DeepSeekProvider

    monkeypatch.setattr(DeepSeekProvider, "list_models", boom)
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            await llm.save_provider_key(session, "default", owner.id, "deepseek", "sk-dddddddd")
            with pytest.raises(llm.UserLlmError) as exc:
                await llm.refresh_catalog(session, "default", owner.id, "deepseek")
            assert "密钥无效" in str(exc.value)
            assert "sk-dddddddd" not in str(exc.value)
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_isolation_hides_other_keys(auth_env):
    engine, maker = await _factory()
    async with maker() as session:
        async with session.begin():
            owner = await _user(session)
            other = await user_repo.create_user(
                session,
                User(
                    tenant_id="default",
                    email="other@gmail.com",
                    password_hash=hash_password("letters12345"),
                    role="user",
                    status="active",
                ),
            )
            await llm.save_provider_key(session, "default", owner.id, "deepseek", "sk-eeeeeeee")
            views = await llm.list_provider_views(session, "default", other.id)
            deepseek = next(item for item in views if item["provider"] == "deepseek")
            assert deepseek["configured"] is False
            assert deepseek["key_suffix"] == ""
            assert await llm.get_active(session, "default", other.id) is None
    await engine.dispose()
