"""用户 LLM 配置编排：凭据、互斥启用、解析当前审查模型。"""

import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from llm_providers import LlmProviderError, all_providers, get_provider
from llm_providers.openai_compat import OpenAICompatChat
from repositories import user_llm as repository
from utils.secret_box import SecretBoxError, decrypt_secret, encrypt_secret, key_suffix

logger = logging.getLogger(__name__)

MIN_KEY_LENGTH = 8


class UserLlmError(Exception):
    """用户模型配置失败。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ActiveLlm:
    provider: str
    model_id: str
    display_name: str
    api_key: str
    base_url: str
    extra_headers: dict[str, str]


def _validate_key(api_key: str) -> str:
    value = (api_key or "").strip()
    if len(value) < MIN_KEY_LENGTH or value.startswith("$$"):
        raise UserLlmError("请填写有效的 API Key")
    return value


async def list_provider_views(session: AsyncSession, tenant_id: str, user_id: int) -> list[dict]:
    saved = {row.provider: row for row in await repository.list_providers(session, tenant_id, user_id)}
    views = []
    for item in all_providers():
        record = saved.get(item.provider_id)
        views.append(
            {
                "provider": item.provider_id,
                "name": item.display_name,
                "configured": record is not None,
                "key_suffix": record.key_suffix if record else "",
            }
        )
    return views


async def save_provider_key(
    session: AsyncSession, tenant_id: str, user_id: int, provider_id: str, api_key: str
) -> dict:
    adapter = get_provider(provider_id)
    plain = _validate_key(api_key)
    await repository.upsert_provider(
        session,
        tenant_id,
        user_id,
        adapter.provider_id,
        encrypt_secret(plain),
        key_suffix(plain),
    )
    logger.info("[BIZ] llm key saved provider=%s user_id=%s", adapter.provider_id, user_id)
    return {"configured": True, "key_suffix": key_suffix(plain)}


async def delete_provider_key(session: AsyncSession, tenant_id: str, user_id: int, provider_id: str) -> None:
    adapter = get_provider(provider_id)
    await repository.delete_models_for_provider(session, tenant_id, user_id, adapter.provider_id)
    await repository.delete_provider(session, tenant_id, user_id, adapter.provider_id)
    logger.info("[BIZ] llm key deleted provider=%s user_id=%s", adapter.provider_id, user_id)


async def refresh_catalog(session: AsyncSession, tenant_id: str, user_id: int, provider_id: str) -> list[dict]:
    adapter = get_provider(provider_id)
    record = await repository.get_provider(session, tenant_id, user_id, adapter.provider_id)
    if record is None:
        raise UserLlmError("请先保存该提供商的 API Key")
    try:
        plain = decrypt_secret(record.api_key_cipher)
    except SecretBoxError as exc:
        raise UserLlmError(str(exc)) from exc
    try:
        return await adapter.list_models(plain)
    except LlmProviderError as exc:
        raise UserLlmError(str(exc), exc.status_code) from exc


async def list_saved_models(session: AsyncSession, tenant_id: str, user_id: int) -> list[dict]:
    rows = await repository.list_models(session, tenant_id, user_id)
    return [
        {
            "id": row.id,
            "provider": row.provider,
            "model_id": row.model_id,
            "display_name": row.display_name,
            "enabled": bool(row.enabled),
        }
        for row in rows
    ]


async def add_model(
    session: AsyncSession, tenant_id: str, user_id: int, payload: dict
) -> dict:
    adapter = get_provider(str(payload["provider"]))
    cred = await repository.get_provider(session, tenant_id, user_id, adapter.provider_id)
    if cred is None:
        raise UserLlmError("请先保存该提供商的 API Key")
    model_id = str(payload["model_id"]).strip()
    display = str(payload.get("display_name") or model_id).strip()
    row = await repository.upsert_model(session, tenant_id, user_id, adapter.provider_id, model_id, display)
    if payload.get("enabled"):
        await _enable_exclusive(session, tenant_id, user_id, row.id)
    return await _view(session, tenant_id, user_id, row.id)


async def set_enabled(session: AsyncSession, tenant_id: str, user_id: int, model_pk: int, enabled: bool) -> dict:
    row = await repository.get_model(session, tenant_id, user_id, model_pk)
    if row is None:
        raise UserLlmError("模型不存在", 404)
    if enabled:
        await _enable_exclusive(session, tenant_id, user_id, row.id)
    else:
        await repository.set_model_enabled(session, row.id, False)
    return await _view(session, tenant_id, user_id, row.id)


async def remove_model(session: AsyncSession, tenant_id: str, user_id: int, model_pk: int) -> None:
    row = await repository.get_model(session, tenant_id, user_id, model_pk)
    if row is None:
        raise UserLlmError("模型不存在", 404)
    await repository.delete_model(session, row)


async def get_active(session: AsyncSession, tenant_id: str, user_id: int) -> Optional[ActiveLlm]:
    row = await repository.get_enabled_model(session, tenant_id, user_id)
    if row is None:
        return None
    cred = await repository.get_provider(session, tenant_id, user_id, row.provider)
    if cred is None:
        return None
    try:
        plain = decrypt_secret(cred.api_key_cipher)
    except SecretBoxError:
        logger.warning("[BIZ] llm key decrypt failed user_id=%s provider=%s", user_id, row.provider)
        return None
    adapter = get_provider(row.provider)
    return ActiveLlm(
        provider=row.provider,
        model_id=row.model_id,
        display_name=row.display_name,
        api_key=plain,
        base_url=adapter.base_url,
        extra_headers=adapter.extra_headers(),
    )


def build_chat_client(active: ActiveLlm) -> OpenAICompatChat:
    return OpenAICompatChat(active.api_key, active.base_url, active.extra_headers)


async def _enable_exclusive(session: AsyncSession, tenant_id: str, user_id: int, model_pk: int) -> None:
    await repository.disable_all_models(session, tenant_id, user_id)
    await repository.set_model_enabled(session, model_pk, True)


async def _view(session: AsyncSession, tenant_id: str, user_id: int, model_pk: int) -> dict:
    row = await repository.get_model(session, tenant_id, user_id, model_pk)
    if row is None:
        raise UserLlmError("模型不存在", 404)
    return {
        "id": row.id,
        "provider": row.provider,
        "model_id": row.model_id,
        "display_name": row.display_name,
        "enabled": bool(row.enabled),
    }
