"""自托管业务数据越权回归：非属主记录必须 404（FEAT-005）。"""

import sys
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import Base
from models.contract import Contract
from models.review_report import ReviewReport
from repositories.contract import Owner, create_contract, delete_contract, get_contract


async def _maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=[Contract.__table__, ReviewReport.__table__])
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.mark.asyncio
async def test_owner_cannot_read_others_contract():
    engine, maker = await _maker()
    alice = Owner(tenant_id="default", user_id=1)
    bob = Owner(tenant_id="default", user_id=2)
    async with maker() as session:
        async with session.begin():
            record = await create_contract(
                session,
                alice,
                {
                    "title": "Alice contract",
                    "file_name": "a.pdf",
                    "bucket_name": "contracts",
                    "object_key": "default/1/202608/x.pdf",
                },
            )
            visible = await get_contract(session, alice, record.id)
            hidden = await get_contract(session, bob, record.id)
            deleted = await delete_contract(session, bob, record.id)
            assert visible is not None
            assert hidden is None
            assert deleted == 0
            still_there = await get_contract(session, alice, record.id)
            assert still_there is not None
    await engine.dispose()
