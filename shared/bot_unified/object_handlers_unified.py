"""Unified handlers для открытия/закрытия объектов (MAX)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from core.database.session import get_async_session
from core.logging.logger import logger
from core.state import user_state_manager, UserAction, UserStep
from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.user import User
from sqlalchemy import select, and_

from .messenger import Messenger
from .normalized_update import NormalizedUpdate
from .router import START_KEYBOARD
from .shift_handlers_unified import LOCATION_FALLBACK_TEXT


async def handle_open_object(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Обработка open_object для MAX."""
    from apps.bot.services.shift_schedule_service import ShiftScheduleService

    chat_id = update.chat_id
    shift_schedule_service = ShiftScheduleService()
    today = date.today()
    planned = await shift_schedule_service.get_user_planned_shifts_for_date(
        user_telegram_id=telegram_id,
        target_date=today,
        internal_user_id=internal_user_id,
    )
    if planned:
        text = "📅 <b>У вас есть запланированные смены!</b>\n\n"
        text += "Используйте кнопку «Открыть смену» для их открытия."
        await messenger.send_text(
            chat_id,
            text,
            keyboard=[[{"text": "🔄 Открыть смену", "callback_data": "open_shift"}]],
        )
        return True

    async with get_async_session() as session:
        from shared.services.contract_validation_service import build_active_contract_filter
        from shared.services.object_opening_service import ObjectOpeningService

        user_res = await session.execute(select(User).where(User.id == internal_user_id))
        db_user = user_res.scalar_one_or_none()
        if not db_user:
            await messenger.send_text(chat_id, "❌ Пользователь не найден.")
            return True

        contracts_query = select(Contract).where(
            and_(
                Contract.employee_id == db_user.id,
                build_active_contract_filter(today),
            )
        )
        contracts_result = await session.execute(contracts_query)
        contracts = contracts_result.scalars().all()

        opening = ObjectOpeningService(session)
        available = []
        for c in contracts:
            if c.allowed_objects:
                for obj_id in c.allowed_objects:
                    if obj_id not in [o["id"] for o in available]:
                        obj_res = await session.execute(select(Object).where(Object.id == obj_id))
                        obj = obj_res.scalar_one_or_none()
                        if obj and obj.is_active:
                            is_open = await opening.is_object_open(obj.id)
                            available.append({"id": obj.id, "name": obj.name, "is_open": is_open})

        if db_user.role == "owner" or (hasattr(db_user, "roles") and "owner" in (db_user.roles or [])):
            owner_q = select(Object).where(
                and_(Object.owner_id == db_user.id, Object.is_active == True)
            )
            owner_res = await session.execute(owner_q)
            for obj in owner_res.scalars().all():
                if obj.id not in [o["id"] for o in available]:
                    is_open = await opening.is_object_open(obj.id)
                    available.append({"id": obj.id, "name": obj.name, "is_open": is_open})

        closed = [o for o in available if not o["is_open"]]
        if not closed:
            await messenger.send_text(
                chat_id,
                "ℹ️ Все объекты уже открыты. Используйте «Открыть смену».",
                keyboard=[[{"text": "🔄 Открыть смену", "callback_data": "open_shift"}]],
            )
            return True

        if len(closed) == 1:
            obj = closed[0]
            await user_state_manager.create_state(
                user_id=internal_user_id,
                action=UserAction.OPEN_OBJECT,
                step=UserStep.OPENING_OBJECT_LOCATION,
                selected_object_id=obj["id"],
            )
            await messenger.send_text(
                chat_id,
                f"📍 <b>Открытие объекта</b>\n\nОбъект: <b>{obj['name']}</b>\n\n{LOCATION_FALLBACK_TEXT}",
            )
            return True

        await user_state_manager.create_state(
            user_id=internal_user_id,
            action=UserAction.OPEN_OBJECT,
            step=UserStep.OBJECT_SELECTION,
        )
        keyboard = [[{"text": f"🏢 {o['name']}", "callback_data": f"select_object_to_open:{o['id']}"}] for o in closed]
        keyboard.append([{"text": "❌ Отмена", "callback_data": "main_menu"}])
        await messenger.send_text(chat_id, "🏢 <b>Выберите объект для открытия:</b>", keyboard=keyboard)
        return True


async def handle_close_object(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Обработка close_object для MAX."""
    from apps.bot.services.shift_service import ShiftService

    chat_id = update.chat_id
    shift_service = ShiftService()
    shifts = await shift_service.get_user_shifts(
        user_id=telegram_id or 0,
        status="active",
        internal_user_id=internal_user_id,
    )
    if not shifts:
        await messenger.send_text(chat_id, "❌ Нет активных смен.", keyboard=START_KEYBOARD)
        return True
    if len(shifts) > 1:
        await messenger.send_text(
            chat_id,
            "⚠️ Несколько активных смен. Сначала закройте смену.",
            keyboard=[[{"text": "🔚 Закрыть смену", "callback_data": "close_shift"}]],
        )
        return True

    shift = shifts[0]
    object_id = shift["object_id"]
    async with get_async_session() as session:
        from shared.services.object_opening_service import ObjectOpeningService

        opening = ObjectOpeningService(session)
        count = await opening.get_active_shifts_count(object_id)
        if count > 1:
            await messenger.send_text(
                chat_id,
                "⚠️ На объекте работают другие. Закрытие объекта — только последнему.",
                keyboard=[[{"text": "🔚 Закрыть смену", "callback_data": "close_shift"}]],
            )
            return True

    await user_state_manager.create_state(
        user_id=internal_user_id,
        action=UserAction.CLOSE_OBJECT,
        step=UserStep.LOCATION_REQUEST,
        selected_object_id=object_id,
        selected_shift_id=shift["id"],
    )
    await messenger.send_text(
        chat_id,
        f"📍 <b>Отправьте геопозицию для закрытия объекта</b>\n\n{LOCATION_FALLBACK_TEXT}",
    )
    return True


async def handle_select_object_to_open(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    object_id: int,
) -> bool:
    """Обработка select_object_to_open:N."""
    from core.database.session import get_async_session
    from domain.entities.object import Object
    from sqlalchemy import select

    chat_id = update.chat_id
    async with get_async_session() as session:
        obj_res = await session.execute(select(Object).where(Object.id == object_id))
        obj = obj_res.scalar_one_or_none()
    if not obj:
        await messenger.send_text(chat_id, "❌ Объект не найден.")
        return True

    await user_state_manager.create_state(
        user_id=internal_user_id,
        action=UserAction.OPEN_OBJECT,
        step=UserStep.OPENING_OBJECT_LOCATION,
        selected_object_id=object_id,
    )
    await messenger.send_text(
        chat_id,
        f"📍 <b>Открытие объекта</b>\n\nОбъект: <b>{obj.name}</b>\n\n{LOCATION_FALLBACK_TEXT}",
    )
    return True
