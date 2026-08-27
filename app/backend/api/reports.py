"""审查报告 REST：/api/v1/reports。归属只取令牌。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth_providers import AuthUser
from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from models.review_report import ReviewReport  # noqa: F401
from repositories.contract import MAX_PAGE_SIZE, Owner
from schemas.contracts import (
    DeleteResultResponse,
    ReportCreateRequest,
    ReportListResponse,
    ReportResponse,
    ReportSummaryResponse,
)
from services import contracts as contract_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["reports"],
    dependencies=[Depends(bind_trace_id)],
)

NOT_FOUND_DETAIL = "记录不存在"


def current_owner(auth_user: AuthUser = Depends(get_current_auth_user)) -> Owner:
    return Owner(tenant_id=auth_user.tenant_id, user_id=auth_user.id)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    record = await contract_service.create_report(session, owner, payload.model_dump())
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return ReportResponse.model_validate(record)


@router.get("", response_model=ReportListResponse)
async def list_reports(
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ReportListResponse:
    records, stats = await contract_service.list_reports(session, owner, limit=limit, offset=offset)
    return ReportListResponse(
        items=[ReportResponse.model_validate(item) for item in records],
        total=stats["report_count"],
    )


@router.get("/summary", response_model=ReportSummaryResponse)
async def report_summary(
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ReportSummaryResponse:
    stats = await contract_service.report_summary(session, owner)
    return ReportSummaryResponse(**stats)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ReportResponse:
    record = await contract_service.get_report(session, owner, report_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return ReportResponse.model_validate(record)


@router.delete("/{report_id}", response_model=DeleteResultResponse)
async def delete_report(
    report_id: int,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> DeleteResultResponse:
    affected = await contract_service.delete_report(session, owner, report_id)
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return DeleteResultResponse(message="报告已删除")
