"""自托管业务数据访问层。

**核心不变量**：本模块导出的每个函数都要求显式传入 `owner`（租户 + 用户），
并在 SQL 层无条件附加这两个过滤条件。路由层拿不到「不带归属过滤」的查询入口，
因此越权读取无法通过忘记传参的方式发生。
"""

import logging
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.contract import Contract
from models.review_report import ReviewReport

logger = logging.getLogger(__name__)

# 列表接口的分页上限：防止调用方传入超大 limit 拖垮数据库与响应体。
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Owner:
    """数据归属标识。作为值对象传递，避免两个字符串参数被调换顺序。"""

    tenant_id: str
    user_id: int


def _owner_filter(model: Any, owner: Owner):
    """构造归属过滤条件。所有查询必须使用它。"""
    return (model.tenant_id == owner.tenant_id, model.user_id == owner.user_id)


def clamp_page_size(limit: Optional[int], default: int = 20) -> int:
    """把分页大小收敛到合法区间。"""
    if not limit or limit <= 0:
        return default
    return min(limit, MAX_PAGE_SIZE)


async def create_contract(session: AsyncSession, owner: Owner, payload: dict) -> Contract:
    """创建合同记录。

    归属列由服务端按当前登录身份写入，**忽略**请求体中的同名字段，
    否则客户端可通过伪造 `user_id` 把数据写到别人名下。
    """
    fields = {k: v for k, v in payload.items() if k not in {"tenant_id", "user_id", "id"}}
    record = Contract(tenant_id=owner.tenant_id, user_id=owner.user_id, **fields)
    session.add(record)
    await session.flush()
    logger.info("[DB_OP] local contract created id=%s", record.id)
    return record


async def get_contract(session: AsyncSession, owner: Owner, contract_id: int) -> Optional[Contract]:
    """按 ID 读取合同；不属于当前归属者时返回 None（对外统一表现为 404）。"""
    stmt = select(Contract).where(Contract.id == contract_id, *_owner_filter(Contract, owner))
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_contracts(
    session: AsyncSession,
    owner: Owner,
    limit: int = 20,
    offset: int = 0,
) -> Sequence[Contract]:
    """分页列出当前归属者的合同，按创建时间倒序。"""
    stmt = (
        select(Contract)
        .where(*_owner_filter(Contract, owner))
        .order_by(Contract.created_at.desc(), Contract.id.desc())
        .limit(clamp_page_size(limit))
        .offset(max(offset, 0))
    )
    return (await session.execute(stmt)).scalars().all()


async def count_contracts(session: AsyncSession, owner: Owner) -> int:
    """统计当前归属者的合同总数（供前端分页与概览使用）。"""
    stmt = select(func.count()).select_from(Contract).where(*_owner_filter(Contract, owner))
    return int((await session.execute(stmt)).scalar() or 0)


async def update_contract_status(
    session: AsyncSession,
    owner: Owner,
    contract_id: int,
    status: str,
    error_message: Optional[str] = None,
) -> int:
    """更新合同状态。

    `WHERE` 同时带 ID 与归属条件，因此越权更新的影响行数为 0，
    路由层据此返回 404 而不是静默「更新成功」。
    """
    result = await session.execute(
        update(Contract)
        .where(Contract.id == contract_id, *_owner_filter(Contract, owner))
        .values(status=status, error_message=error_message)
    )
    return result.rowcount or 0


async def delete_contract(session: AsyncSession, owner: Owner, contract_id: int) -> int:
    """删除合同并级联清理其报告。

    删除顺序为「先报告后合同」：反之若中途失败，会留下引用不存在合同的孤立报告。
    两次删除处于同一事务内，故整体原子。
    """
    await session.execute(
        delete(ReviewReport).where(
            ReviewReport.contract_id == contract_id, *_owner_filter(ReviewReport, owner)
        )
    )
    result = await session.execute(
        delete(Contract).where(Contract.id == contract_id, *_owner_filter(Contract, owner))
    )
    return result.rowcount or 0


async def create_report(session: AsyncSession, owner: Owner, payload: dict) -> ReviewReport:
    """创建审查报告记录。"""
    fields = {k: v for k, v in payload.items() if k not in {"tenant_id", "user_id", "id"}}
    record = ReviewReport(tenant_id=owner.tenant_id, user_id=owner.user_id, **fields)
    session.add(record)
    await session.flush()
    logger.info("[DB_OP] local review report created id=%s", record.id)
    return record


async def get_report(session: AsyncSession, owner: Owner, report_id: int) -> Optional[ReviewReport]:
    """按 ID 读取报告，附带归属过滤。"""
    stmt = select(ReviewReport).where(
        ReviewReport.id == report_id, *_owner_filter(ReviewReport, owner)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_reports(
    session: AsyncSession,
    owner: Owner,
    limit: int = 20,
    offset: int = 0,
) -> Sequence[ReviewReport]:
    """分页列出当前归属者的报告，按创建时间倒序。"""
    stmt = (
        select(ReviewReport)
        .where(*_owner_filter(ReviewReport, owner))
        .order_by(ReviewReport.created_at.desc(), ReviewReport.id.desc())
        .limit(clamp_page_size(limit))
        .offset(max(offset, 0))
    )
    return (await session.execute(stmt)).scalars().all()


async def delete_report(session: AsyncSession, owner: Owner, report_id: int) -> int:
    """删除报告。"""
    result = await session.execute(
        delete(ReviewReport).where(
            ReviewReport.id == report_id, *_owner_filter(ReviewReport, owner)
        )
    )
    return result.rowcount or 0


async def summarize_reports(session: AsyncSession, owner: Owner) -> dict:
    """汇总当前归属者的报告概览（总数、平均分、各风险等级计数）。

    统计交给数据库聚合而非取回全部行在应用层累加：后者在数据量增长后
    会把整张表读进内存。
    """
    stmt = select(
        func.count(ReviewReport.id),
        func.avg(ReviewReport.overall_score),
        func.sum(ReviewReport.high_risk_count),
        func.sum(ReviewReport.medium_risk_count),
        func.sum(ReviewReport.low_risk_count),
    ).where(*_owner_filter(ReviewReport, owner))

    total, avg_score, high, medium, low = (await session.execute(stmt)).one()
    return {
        "report_count": int(total or 0),
        "average_score": round(float(avg_score), 1) if avg_score is not None else None,
        "high_risk_total": int(high or 0),
        "medium_risk_total": int(medium or 0),
        "low_risk_total": int(low or 0),
    }