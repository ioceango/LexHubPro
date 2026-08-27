"""BUG-007 回归：合同/报告 user_id 与 tb_user.id 同为整型外键，1:N 基数成立。"""

import sys
from pathlib import Path

import pytest
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.database import Base
from models.contract import Contract
from models.review_report import ReviewReport
from models.user import AUTH_MODELS, User
from models.user_llm import UserLlmProvider
from repositories.contract import (
    Owner,
    create_contract,
    create_report,
    list_contracts,
    list_reports,
)
from utils.auth_crypto import hash_password


def test_owner_user_id_columns_match_user_pk():
    # BUG-007 回归
    for column in (Contract.__table__.c.user_id, ReviewReport.__table__.c.user_id, UserLlmProvider.__table__.c.user_id):
        assert isinstance(column.type, Integer)
        referred = {fk.column.table.name for fk in column.foreign_keys}
        assert referred == {"tb_user"}


async def _maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [model.__table__ for model in AUTH_MODELS] + [Contract.__table__, ReviewReport.__table__]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, tables=tables)
    return engine, async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.mark.asyncio
async def test_one_user_many_contracts_and_reports():
    # BUG-007 回归
    engine, maker = await _maker()
    async with maker() as session:
        async with session.begin():
            user = User(
                tenant_id="default",
                email="owner@gmail.com",
                password_hash=hash_password("letters12345"),
                role="user",
                status="active",
            )
            session.add(user)
            await session.flush()
            owner = Owner(tenant_id="default", user_id=user.id)
            first = await create_contract(
                session,
                owner,
                {
                    "title": "合同甲",
                    "file_name": "a.pdf",
                    "bucket_name": "contracts",
                    "object_key": "default/1/202608/a.pdf",
                },
            )
            second = await create_contract(
                session,
                owner,
                {
                    "title": "合同乙",
                    "file_name": "b.pdf",
                    "bucket_name": "contracts",
                    "object_key": "default/1/202608/b.pdf",
                },
            )
            assert first.user_id == user.id
            assert second.user_id == user.id
            payload = {
                "contract_title": "合同甲",
                "overall_score": 80,
                "risk_level": "low",
                "summary": "首轮审查",
            }
            report_one = await create_report(session, owner, {**payload, "contract_id": first.id})
            report_two = await create_report(
                session, owner, {**payload, "contract_id": first.id, "summary": "二轮审查"}
            )
            assert report_one.user_id == user.id
            assert report_two.contract_id == first.id
            contracts = await list_contracts(session, owner)
            reports = await list_reports(session, owner)
            assert {row.id for row in contracts} == {first.id, second.id}
            assert {row.id for row in reports} == {report_one.id, report_two.id}
    await engine.dispose()
