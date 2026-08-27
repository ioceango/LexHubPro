"""BUG-006 回归：审查先读合同与启用模型，再写状态不得重复 begin。"""

import sys
from pathlib import Path

import pytest
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import Base
from models.contract import Contract
from models.review_report import ReviewReport
from models.user import AUTH_MODELS, User
from models.user_llm import LLM_MODELS
from repositories import contract as contract_repo
from repositories import user as user_repo
from repositories.contract import Owner
from services import contracts as contract_service
from services import user_llm as llm
from utils.auth_crypto import hash_password


async def _factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [model.__table__ for model in AUTH_MODELS + LLM_MODELS] + [
        Contract.__table__,
        ReviewReport.__table__,
    ]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=tables)
    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, maker


async def _seed(session: AsyncSession) -> tuple[User, int]:
    owner_user = await user_repo.create_user(
        session,
        User(
            tenant_id="default",
            email="reviewer@gmail.com",
            password_hash=hash_password("letters12345"),
            role="user",
            status="active",
        ),
    )
    owner = Owner(tenant_id="default", user_id=owner_user.id)
    contract = await contract_repo.create_contract(
        session,
        owner,
        {
            "title": "采购合同",
            "file_name": "a.pdf",
            "bucket_name": "contracts",
            "object_key": "default/1/202608/a.pdf",
            "status": "pending",
        },
    )
    await llm.save_provider_key(session, "default", owner_user.id, "deepseek", "sk-bug006-key")
    await llm.add_model(
        session,
        "default",
        owner_user.id,
        {"provider": "deepseek", "model_id": "deepseek-chat", "enabled": True},
    )
    return owner_user, contract.id


@pytest.mark.asyncio
async def test_select_then_begin_raises_without_closing_read_tx(auth_env):
    """BUG-006 回归：autobegin 未结束后再次 begin() 必须失败。"""
    engine, maker = await _factory()
    async with maker() as setup:
        async with setup.begin():
            owner_user, contract_id = await _seed(setup)
            user_pk = owner_user.id
    owner = Owner(tenant_id="default", user_id=user_pk)
    async with maker() as session:
        loaded = await contract_service.get_contract(session, owner, contract_id)
        assert loaded is not None
        active = await llm.get_active(session, "default", user_pk)
        assert active is not None
        assert session.in_transaction()
        with pytest.raises(InvalidRequestError, match="already begun"):
            await contract_service.update_contract_status(session, owner, contract_id, "reviewing")
    await engine.dispose()


@pytest.mark.asyncio
async def test_close_read_transaction_allows_status_update(auth_env):
    """BUG-006 回归：结束只读事务后再改状态，会话不再处于事务中即可 begin。"""
    engine, maker = await _factory()
    async with maker() as setup:
        async with setup.begin():
            owner_user, contract_id = await _seed(setup)
            user_pk = owner_user.id
    owner = Owner(tenant_id="default", user_id=user_pk)
    async with maker() as session:
        loaded = await contract_service.get_contract(session, owner, contract_id)
        assert loaded is not None
        fields = {
            "id": loaded.id,
            "bucket_name": loaded.bucket_name,
            "object_key": loaded.object_key,
        }
        active = await llm.get_active(session, "default", user_pk)
        assert active is not None
        await contract_service.close_read_transaction(session)
        assert not session.in_transaction()
        updated = await contract_service.update_contract_status(session, owner, fields["id"], "reviewing")
        assert updated is not None
        assert updated.status == "reviewing"
        assert not session.in_transaction()
        assert fields["bucket_name"] == "contracts"
        assert fields["object_key"].endswith("a.pdf")
    await engine.dispose()
