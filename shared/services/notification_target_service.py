"""Сервис целевых чатов для уведомлений (TG/MAX)."""

from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.notification_target import NotificationTarget
from domain.entities.object import Object


async def upsert_object_report_target(
    session: AsyncSession,
    object_id: int,
    messenger: str,
    target_chat_id: Optional[str],
) -> None:
    """
    Создать или обновить запись notification_targets для объекта.
    messenger: telegram | max. target_chat_id пустой — отключить.
    """
    stmt = select(NotificationTarget).where(
        and_(
            NotificationTarget.scope_type == "object",
            NotificationTarget.scope_id == object_id,
            NotificationTarget.messenger == messenger,
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
                    messenger=messenger,
                    target_type="group",
                    target_chat_id=chat_id,
                    is_enabled=True,
                )
            )
    elif existing:
        existing.is_enabled = False


async def upsert_object_telegram_report_target(
    session: AsyncSession,
    object_id: int,
    target_chat_id: Optional[str],
) -> None:
    """Обёртка для Telegram (обратная совместимость)."""
    await upsert_object_report_target(session, object_id, "telegram", target_chat_id)


async def get_object_report_targets(
    session: AsyncSession,
    object_id: int,
) -> dict[str, str]:
    """Получить target_chat_id по messenger для объекта. Возвращает {telegram: ..., max: ...}."""
    stmt = select(NotificationTarget.messenger, NotificationTarget.target_chat_id).where(
        and_(
            NotificationTarget.scope_type == "object",
            NotificationTarget.scope_id == object_id,
            NotificationTarget.is_enabled.is_(True),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    return {r[0]: r[1] for r in rows if r[1]}


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
    if row is not None and str(row).strip():
        return str(row).strip()

    # 2. inherit: org_unit — targets, затем legacy колонка подразделения
    if obj.inherit_telegram_chat and obj.org_unit_id:
        legacy_org = None
        org = getattr(obj, "org_unit", None)
        if org is not None:
            legacy_org = getattr(org, "telegram_report_chat_id", None)
        tid = await get_telegram_report_chat_id_for_org_unit(
            session, obj.org_unit_id, legacy_org
        )
        if tid and str(tid).strip():
            return str(tid).strip()

    # 3. Fallback: legacy на объекте (и наследование через модель)
    return obj.get_effective_report_chat_id()


async def get_max_report_chat_id_for_object(
    session: AsyncSession,
    obj: Object,
) -> Optional[str]:
    """
    MAX chat_id группы для медиа-отчётов (notification_targets).
    Наследование — тот же флаг inherit_telegram_chat, что и для TG-чата отчётов.
    """
    stmt = select(NotificationTarget.target_chat_id).where(
        and_(
            NotificationTarget.scope_type == "object",
            NotificationTarget.scope_id == obj.id,
            NotificationTarget.messenger == "max",
            NotificationTarget.is_enabled.is_(True),
        )
    ).limit(1)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is not None and str(row).strip():
        return str(row).strip()

    if obj.inherit_telegram_chat and obj.org_unit_id:
        stmt = select(NotificationTarget.target_chat_id).where(
            and_(
                NotificationTarget.scope_type == "org_unit",
                NotificationTarget.scope_id == obj.org_unit_id,
                NotificationTarget.messenger == "max",
                NotificationTarget.is_enabled.is_(True),
            )
        ).limit(1)
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is not None and str(row).strip():
            return str(row).strip()

    return None


async def upsert_org_unit_report_target(
    session: AsyncSession,
    org_unit_id: int,
    messenger: str,
    target_chat_id: Optional[str],
) -> None:
    """Создать / обновить notification_targets для подразделения."""
    stmt = select(NotificationTarget).where(
        and_(
            NotificationTarget.scope_type == "org_unit",
            NotificationTarget.scope_id == org_unit_id,
            NotificationTarget.messenger == messenger,
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
                    scope_type="org_unit",
                    scope_id=org_unit_id,
                    messenger=messenger,
                    target_type="group",
                    target_chat_id=chat_id,
                    is_enabled=True,
                )
            )
    elif existing:
        existing.is_enabled = False


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
    if row is not None and str(row).strip():
        return str(row).strip()
    return legacy_chat_id
