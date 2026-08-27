"""合同与报告编排。事务由本层界定，仓储只 flush。"""

from typing import Any, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from repositories import contract as repository
from repositories.contract import Owner


async def create_contract(session: AsyncSession, owner: Owner, payload: dict) -> Any:
    async with session.begin():
        return await repository.create_contract(session, owner, {**payload, "status": payload.get("status") or "pending"})


async def list_contracts(session: AsyncSession, owner: Owner, limit: int, offset: int):
    items = await repository.list_contracts(session, owner, limit=limit, offset=offset)
    total = await repository.count_contracts(session, owner)
    return items, total


async def get_contract(session: AsyncSession, owner: Owner, contract_id: int):
    return await repository.get_contract(session, owner, contract_id)


async def close_read_transaction(session: AsyncSession) -> None:
    """结束自动开启的只读事务。

    第一次 SELECT 会 autobegin。若不先结束，后续 `session.begin()` 会报
    「A transaction is already begun」。审查还要把事务关在 MinIO/AI 之前。
    """
    if session.in_transaction():
        await session.commit()


async def update_contract_status(
    session: AsyncSession,
    owner: Owner,
    contract_id: int,
    status: str,
    error_message: Optional[str] = None,
):
    async with session.begin():
        affected = await repository.update_contract_status(session, owner, contract_id, status, error_message)
        if affected == 0:
            return None
        return await repository.get_contract(session, owner, contract_id)


async def delete_contract(session: AsyncSession, owner: Owner, contract_id: int) -> int:
    async with session.begin():
        return await repository.delete_contract(session, owner, contract_id)


async def create_report(session: AsyncSession, owner: Owner, payload: dict):
    async with session.begin():
        contract = await repository.get_contract(session, owner, payload["contract_id"])
        if contract is None:
            return None
        return await repository.create_report(session, owner, payload)


async def list_reports(session: AsyncSession, owner: Owner, limit: int, offset: int):
    items = await repository.list_reports(session, owner, limit=limit, offset=offset)
    stats = await repository.summarize_reports(session, owner)
    return items, stats


async def get_report(session: AsyncSession, owner: Owner, report_id: int):
    return await repository.get_report(session, owner, report_id)


async def delete_report(session: AsyncSession, owner: Owner, report_id: int) -> int:
    async with session.begin():
        return await repository.delete_report(session, owner, report_id)


async def report_summary(session: AsyncSession, owner: Owner) -> dict:
    return await repository.summarize_reports(session, owner)
