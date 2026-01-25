"""Сервис настроек хранилища медиа по владельцу (restruct1 Фаза 1.5)."""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.owner_media_storage_option import (
    CONTEXTS,
    STORAGE_MODES,
    OwnerMediaStorageOption,
)
from shared.services.system_features_service import SystemFeaturesService

SECURE_FEATURE_KEY = "secure_media_storage"


async def is_secure_media_enabled(session: AsyncSession, owner_id: int) -> bool:
    """Включена ли опция «Использовать защищённое хранилище» у владельца."""
    svc = SystemFeaturesService()
    return await svc.is_feature_enabled(session, owner_id, SECURE_FEATURE_KEY)


async def get_storage_mode(
    session: AsyncSession, owner_id: int, context: str
) -> str:
    """
    Режим хранения для контекста: telegram | storage | both.
    Если опция выключена или настройки нет — «telegram».
    """
    ok = await is_secure_media_enabled(session, owner_id)
    if not ok:
        return "telegram"
    q = select(OwnerMediaStorageOption).where(
        OwnerMediaStorageOption.owner_id == owner_id,
        OwnerMediaStorageOption.context == context,
    )
    r = await session.execute(q)
    row = r.scalar_one_or_none()
    if not row or row.storage not in STORAGE_MODES:
        return "telegram"
    return row.storage


async def get_all_modes(session: AsyncSession, owner_id: int) -> Dict[str, str]:
    """Все настройки по контекстам. Нет строки → telegram."""
    out: Dict[str, str] = {c: "telegram" for c in CONTEXTS}
    q = select(OwnerMediaStorageOption).where(
        OwnerMediaStorageOption.owner_id == owner_id
    )
    r = await session.execute(q)
    for row in r.scalars().all():
        if row.context in CONTEXTS and row.storage in STORAGE_MODES:
            out[row.context] = row.storage
    return out


async def set_storage_mode(
    session: AsyncSession,
    owner_id: int,
    context: str,
    storage: str,
    *,
    commit: bool = True,
) -> None:
    """Установить режим для контекста. storage: telegram | storage | both."""
    if context not in CONTEXTS or storage not in STORAGE_MODES:
        return
    q = select(OwnerMediaStorageOption).where(
        OwnerMediaStorageOption.owner_id == owner_id,
        OwnerMediaStorageOption.context == context,
    )
    r = await session.execute(q)
    row = r.scalar_one_or_none()
    if row:
        row.storage = storage
    else:
        session.add(
            OwnerMediaStorageOption(
                owner_id=owner_id,
                context=context,
                storage=storage,
            )
        )
    if commit:
        await session.commit()


async def set_all_modes(
    session: AsyncSession,
    owner_id: int,
    modes: Dict[str, str],
) -> None:
    """Обновить настройки по контекстам. Только валидные пары."""
    for ctx, st in modes.items():
        if ctx in CONTEXTS and st in STORAGE_MODES:
            await set_storage_mode(session, owner_id, ctx, st, commit=False)
    await session.commit()


def get_context_labels() -> List[Dict[str, str]]:
    """Метки контекстов для UI."""
    return [
        {"value": "tasks", "label": "Задачи (Tasks v2)"},
        {"value": "cancellations", "label": "Отмены смен"},
        {"value": "incidents", "label": "Инциденты"},
        {"value": "contracts", "label": "Договоры (сканы/приложения)"},
    ]


def get_storage_mode_labels() -> List[Dict[str, str]]:
    """Метки режимов для UI."""
    return [
        {"value": "telegram", "label": "Только Telegram"},
        {"value": "storage", "label": "Только хранилище (S3)"},
        {"value": "both", "label": "Оба (TG + хранилище)"},
    ]
