"""合同 REST：/api/v1/contracts。归属只取令牌。"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth_providers import AuthUser
from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from models.contract import Contract  # noqa: F401
from repositories.contract import MAX_PAGE_SIZE, Owner
from schemas.contracts import (
    ContractCreateRequest,
    ContractListResponse,
    ContractResponse,
    ContractStatusUpdateRequest,
    DeleteResultResponse,
)
from services import contracts as contract_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/contracts",
    tags=["contracts"],
    dependencies=[Depends(bind_trace_id)],
)

NOT_FOUND_DETAIL = "记录不存在"


def current_owner(auth_user: AuthUser = Depends(get_current_auth_user)) -> Owner:
    return Owner(tenant_id=auth_user.tenant_id, user_id=auth_user.id)


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreateRequest,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ContractResponse:
    record = await contract_service.create_contract(session, owner, payload.model_dump(exclude_none=True))
    return ContractResponse.model_validate(record)


@router.get("", response_model=ContractListResponse)
async def list_contracts(
    limit: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ContractListResponse:
    records, total = await contract_service.list_contracts(session, owner, limit=limit, offset=offset)
    return ContractListResponse(items=[ContractResponse.model_validate(item) for item in records], total=total)


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ContractResponse:
    record = await contract_service.get_contract(session, owner, contract_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return ContractResponse.model_validate(record)


@router.patch("/{contract_id}/status", response_model=ContractResponse)
async def update_contract_status(
    contract_id: int,
    payload: ContractStatusUpdateRequest,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> ContractResponse:
    record = await contract_service.update_contract_status(
        session, owner, contract_id, payload.status, payload.error_message
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return ContractResponse.model_validate(record)


@router.delete("/{contract_id}", response_model=DeleteResultResponse)
async def delete_contract(
    contract_id: int,
    owner: Owner = Depends(current_owner),
    session: AsyncSession = Depends(get_db),
) -> DeleteResultResponse:
    affected = await contract_service.delete_contract(session, owner, contract_id)
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND_DETAIL)
    return DeleteResultResponse(message="合同及其报告已删除")
