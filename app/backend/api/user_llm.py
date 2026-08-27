"""用户 LLM 配置路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from auth_providers.base import AuthUser
from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from llm_providers import LlmProviderError
from schemas.user_llm import (
    ActiveModelView,
    CatalogResponse,
    ModelView,
    PatchModelRequest,
    ProviderView,
    SaveKeyRequest,
    SaveModelRequest,
)
from services import user_llm as service
from services.user_llm import UserLlmError
from utils.secret_box import SecretBoxError

router = APIRouter(
    prefix="/api/v1/llm",
    tags=["llm"],
    dependencies=[Depends(bind_trace_id)],
)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, (UserLlmError, LlmProviderError)):
        return HTTPException(status_code=exc.status_code, detail=str(exc))
    if isinstance(exc, SecretBoxError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/providers", response_model=list[ProviderView])
async def list_providers(
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProviderView]:
    rows = await service.list_provider_views(session, auth_user.tenant_id, auth_user.id)
    return [ProviderView(**row) for row in rows]


@router.put("/providers/{provider}/key")
async def save_key(
    provider: str,
    payload: SaveKeyRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        async with session.begin():
            return await service.save_provider_key(
                session, auth_user.tenant_id, auth_user.id, provider, payload.api_key
            )
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)


@router.delete("/providers/{provider}/key")
async def delete_key(
    provider: str,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        async with session.begin():
            await service.delete_provider_key(session, auth_user.tenant_id, auth_user.id, provider)
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)
    return {"ok": True}


@router.post("/providers/{provider}/models/refresh", response_model=CatalogResponse)
async def refresh_models(
    provider: str,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> CatalogResponse:
    try:
        items = await service.refresh_catalog(session, auth_user.tenant_id, auth_user.id, provider)
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)
    return CatalogResponse(items=items)


@router.get("/models", response_model=list[ModelView])
async def list_models(
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> list[ModelView]:
    rows = await service.list_saved_models(session, auth_user.tenant_id, auth_user.id)
    return [ModelView(**row) for row in rows]


@router.put("/models", response_model=ModelView)
async def save_model(
    payload: SaveModelRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> ModelView:
    try:
        async with session.begin():
            row = await service.add_model(
                session, auth_user.tenant_id, auth_user.id, payload.model_dump()
            )
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)
    return ModelView(**row)


@router.patch("/models/{model_pk}", response_model=ModelView)
async def patch_model(
    model_pk: int,
    payload: PatchModelRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> ModelView:
    try:
        async with session.begin():
            row = await service.set_enabled(
                session, auth_user.tenant_id, auth_user.id, model_pk, payload.enabled
            )
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)
    return ModelView(**row)


@router.delete("/models/{model_pk}")
async def delete_model(
    model_pk: int,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    try:
        async with session.begin():
            await service.remove_model(session, auth_user.tenant_id, auth_user.id, model_pk)
    except (UserLlmError, LlmProviderError) as exc:
        raise _http(exc)
    return {"ok": True}


@router.get("/active", response_model=ActiveModelView)
async def active_model(
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> ActiveModelView:
    active = await service.get_active(session, auth_user.tenant_id, auth_user.id)
    if active is None:
        return ActiveModelView(configured=False)
    return ActiveModelView(
        configured=True,
        provider=active.provider,
        model_id=active.model_id,
        display_name=active.display_name,
    )
