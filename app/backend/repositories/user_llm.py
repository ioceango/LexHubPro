"""用户 LLM 配置的数据访问。"""

from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_llm import UserLlmModel, UserLlmProvider


async def get_provider(
    session: AsyncSession, tenant_id: str, user_id: int, provider: str
) -> Optional[UserLlmProvider]:
    stmt = select(UserLlmProvider).where(
        UserLlmProvider.tenant_id == tenant_id,
        UserLlmProvider.user_id == user_id,
        UserLlmProvider.provider == provider,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_providers(session: AsyncSession, tenant_id: str, user_id: int) -> Sequence[UserLlmProvider]:
    stmt = select(UserLlmProvider).where(
        UserLlmProvider.tenant_id == tenant_id,
        UserLlmProvider.user_id == user_id,
    )
    return (await session.execute(stmt)).scalars().all()


async def upsert_provider(
    session: AsyncSession,
    tenant_id: str,
    user_id: int,
    provider: str,
    cipher: str,
    suffix: str,
) -> UserLlmProvider:
    record = await get_provider(session, tenant_id, user_id, provider)
    if record is None:
        record = UserLlmProvider(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            api_key_cipher=cipher,
            key_suffix=suffix,
        )
        session.add(record)
        await session.flush()
        return record
    record.api_key_cipher = cipher
    record.key_suffix = suffix
    await session.flush()
    return record


async def delete_provider(session: AsyncSession, tenant_id: str, user_id: int, provider: str) -> None:
    record = await get_provider(session, tenant_id, user_id, provider)
    if record is not None:
        await session.delete(record)  # AsyncSession.delete in 2.0.24+


async def list_models(session: AsyncSession, tenant_id: str, user_id: int) -> Sequence[UserLlmModel]:
    stmt = (
        select(UserLlmModel)
        .where(UserLlmModel.tenant_id == tenant_id, UserLlmModel.user_id == user_id)
        .order_by(UserLlmModel.id)
    )
    return (await session.execute(stmt)).scalars().all()


async def get_model(session: AsyncSession, tenant_id: str, user_id: int, model_pk: int) -> Optional[UserLlmModel]:
    stmt = select(UserLlmModel).where(
        UserLlmModel.id == model_pk,
        UserLlmModel.tenant_id == tenant_id,
        UserLlmModel.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_enabled_model(session: AsyncSession, tenant_id: str, user_id: int) -> Optional[UserLlmModel]:
    stmt = select(UserLlmModel).where(
        UserLlmModel.tenant_id == tenant_id,
        UserLlmModel.user_id == user_id,
        UserLlmModel.enabled.is_(True),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def upsert_model(
    session: AsyncSession,
    tenant_id: str,
    user_id: int,
    provider: str,
    model_id: str,
    display_name: str,
) -> UserLlmModel:
    stmt = select(UserLlmModel).where(
        UserLlmModel.tenant_id == tenant_id,
        UserLlmModel.user_id == user_id,
        UserLlmModel.provider == provider,
        UserLlmModel.model_id == model_id,
    )
    record = (await session.execute(stmt)).scalar_one_or_none()
    if record is None:
        record = UserLlmModel(
            tenant_id=tenant_id,
            user_id=user_id,
            provider=provider,
            model_id=model_id,
            display_name=display_name or model_id,
            enabled=False,
        )
        session.add(record)
        await session.flush()
        return record
    if display_name:
        record.display_name = display_name
    await session.flush()
    return record


async def disable_all_models(session: AsyncSession, tenant_id: str, user_id: int) -> None:
    await session.execute(
        update(UserLlmModel)
        .where(UserLlmModel.tenant_id == tenant_id, UserLlmModel.user_id == user_id)
        .values(enabled=False)
    )


async def set_model_enabled(session: AsyncSession, model_pk: int, enabled: bool) -> None:
    await session.execute(update(UserLlmModel).where(UserLlmModel.id == model_pk).values(enabled=enabled))


async def delete_model(session: AsyncSession, record: UserLlmModel) -> None:
    await session.delete(record)


async def delete_models_for_provider(
    session: AsyncSession, tenant_id: str, user_id: int, provider: str
) -> None:
    rows = await list_models(session, tenant_id, user_id)
    for row in rows:
        if row.provider == provider:
            await session.delete(row)
