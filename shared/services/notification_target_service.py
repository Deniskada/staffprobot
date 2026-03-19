"""Сервис целевых чатов для уведомлений (TG/MAX)."""

from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.notification_target import NotificationTarget
from domain.entities.object import Object


async def upsert_object_telegram_report_target(
    session: AsyncSession,
    object_id: int,
    target_chat_id: Optional[str],
) -> None:
    """
    Создать или обновить запись notification_targets для объекта (Telegram).
    Если target_chat_id пустой — удалить/отключить.
    """
    stmt = select(NotificationTarget).where(
        and_(
            NotificationTarget.scope_type == "object",
            NotificationTarget.scope_id == object_id,
            NotificationTarget.messenger == "telegram",
        )
    ).limit(1)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if target_chat_id and str(target_chat_id).strip():
        chat_id = str(target_chat_id).strip()
        if existing:
            existing.target_chat_id = chat_id
            existing.is_enabled = True
        else:
            session.add(
                NotificationTarget(
                    scope_type="object",
                    scope_id=object_id,
                    messenger="telegram",
                    target_type="group",
                    target_chat_id=chat_id,
                    is_enabled=True,
                )
            )
    elif existing:
        existing.is_enabled = False


async def get_telegram_report_chat_id_for_object(
    session: AsyncSession,
    obj: Object,
) -> Optional[str]:
    """
    Получить Telegram chat_id для медиа-отчетов объекта.

    Сначала notification_targets, fallback — legacy telegram_report_chat_id.
    Учитывает наследование (inherit_telegram_chat) от org_unit.
    """
    # 1. notification_targets: object
    stmt = select(NotificationTarget.target_chat_id).where(
        and_(
            NotificationTarget.scope_type == "object",
            NotificationTarget.scope_id == obj.id,
            NotificationTarget.messenger == "telegram",
            NotificationTarget.is_enabled.is_(True),
        )
    ).limit(1)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row and row[0]:
        return str(row[0])

    # 2. inherit: notification_targets org_unit
    if obj.inherit_telegram_chat and obj.org_unit_id:
        stmt = select(NotificationTarget.target_chat_id).where(
            and_(
                NotificationTarget.scope_type == "org_unit",
                NotificationTarget.scope_id == obj.org_unit_id,
                NotificationTarget.messenger == "telegram",
                NotificationTarget.is_enabled.is_(True),
            )
        ).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row and row[0]:
            return str(row[0])

    # 3. Fallback: legacy
    return obj.get_effective_report_chat_id()


async def get_telegram_report_chat_id_for_org_unit(
    session: AsyncSession,
    org_unit_id: int,
    legacy_chat_id: Optional[str] = None,
) -> Optional[str]:
    """
    Получить Telegram chat_id для org_unit.
    Сначала notification_targets, fallback — legacy.
    """
    stmt = select(NotificationTarget.target_chat_id).where(
        and_(
            NotificationTarget.scope_type == "org_unit",
            NotificationTarget.scope_id == org_unit_id,
            NotificationTarget.messenger == "telegram",
            NotificationTarget.is_enabled.is_(True),
        )
    ).limit(1)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row and row[0]:
        return str(row[0])
    return legacy_chat_id
