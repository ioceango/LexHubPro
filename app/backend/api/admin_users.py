"""自建认证的管理端路由（仅 `AUTH_MODE=local` + 管理员角色）。"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth_providers import ROLE_ADMIN, AuthUser
from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from repositories import user as repository
from schemas.auth import (
    AdminUserListResponse,
    AuditListResponse,
    UserProfile,
    UserStatusUpdateRequest,
)
from services.auth_accounts import current_tenant_id, to_profile

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin-users"],
    dependencies=[Depends(bind_trace_id)],
)


def _require_admin(auth_user: AuthUser) -> None:
    if auth_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")


@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> AdminUserListResponse:
    """分页列出当前租户用户。"""
    _require_admin(auth_user)
    tenant_id = current_tenant_id()
    records = await repository.list_users(session, tenant_id, limit, offset, status_filter)
    total = await repository.count_users(session, tenant_id, status_filter)
    return AdminUserListResponse(items=[to_profile(item) for item in records], total=total)


@router.patch("/users/{user_id}/status", response_model=UserProfile)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    """启用或禁用账号。禁用时吊销其全部刷新令牌。"""
    _require_admin(auth_user)
    async with session.begin():
        user = await repository.get_user_by_id(session, user_id)
        if user is None or user.tenant_id != current_tenant_id():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        await repository.update_user_fields(session, user_id, status=payload.status)
        if payload.status == "disabled":
            await repository.revoke_all_user_tokens(session, user_id)
        await repository.write_audit(
            session,
            event="admin_status_change",
            user_id=user_id,
            context={"tenant_id": user.tenant_id, "detail": payload.status},
        )
        user.status = payload.status
        logger.info("[BIZ] admin updated user status")
        return to_profile(user)


@router.get("/login-audits", response_model=AuditListResponse)
async def list_login_audits(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> AuditListResponse:
    """查看认证审计。条目本身已脱敏。"""
    _require_admin(auth_user)
    tenant_id = current_tenant_id()
    records = await repository.list_audits(session, tenant_id, limit, offset)
    total = await repository.count_audits(session, tenant_id)
    return AuditListResponse(items=list(records), total=total)
