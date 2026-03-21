"""Unified handlers для открытия/закрытия смен (MAX + TG)."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Optional

from core.logging.logger import logger
from core.state import user_state_manager, UserAction, UserStep

from .messenger import Messenger
from .normalized_update import NormalizedUpdate
from .router import START_KEYBOARD
from .user_resolver import user_state_storage_key

async def handle_open_shift(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Обработка open_shift для MAX. Возвращает True если обработано."""
    from apps.bot.services.shift_service import ShiftService
    from apps.bot.services.employee_objects_service import EmployeeObjectsService
    from apps.bot.services.shift_schedule_service import ShiftScheduleService
    from shared.services.object_opening_service import ObjectOpeningService
    from core.database.session import get_async_session

    shift_service = ShiftService()
    employee_objects_service = EmployeeObjectsService()
    shift_schedule_service = ShiftScheduleService()
    chat_id = update.chat_id

    active_shifts = await shift_service.get_user_shifts(
        user_id=telegram_id or 0,
        status="active",
        internal_user_id=internal_user_id,
    )
    if active_shifts:
        await messenger.send_text(
            chat_id,
            "❌ <b>У вас уже есть активная смена</b>\n\nСначала закройте текущую смену.",
            keyboard=[[{"text": "🔚 Закрыть смену", "callback_data": "close_shift"}]],
        )
        return True

    today = date.today()
    planned_shifts = await shift_schedule_service.get_user_planned_shifts_for_date(
        user_telegram_id=telegram_id,
        target_date=today,
        internal_user_id=internal_user_id,
    )

    if planned_shifts:
        sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
        await user_state_manager.create_state(
            user_id=sk,
            action=UserAction.OPEN_SHIFT,
            step=UserStep.SHIFT_SELECTION,
        )
        keyboard = []
        for shift in planned_shifts:
            time_str = shift.get("planned_start_str", "")
            keyboard.append([
                {
                    "text": f"📅 {shift['object_name']} {time_str}",
                    "callback_data": f"open_planned_shift:{shift['id']}",
                }
            ])
        keyboard.append([{"text": "❌ Отмена", "callback_data": "main_menu"}])
        await messenger.send_text(
            chat_id,
            "📅 <b>Запланированные смены на сегодня</b>\n\nВыберите смену для открытия:",
            keyboard=keyboard,
        )
        return True

    objects = await employee_objects_service.get_employee_objects(
        internal_user_id=internal_user_id,
    )
    if not objects:
        await messenger.send_text(
            chat_id,
            "❌ <b>Нет доступных объектов</b>\n\nУ вас должен быть активный договор с владельцем объекта.",
            keyboard=[[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]],
        )
        return True

    async with get_async_session() as session:
        opening_service = ObjectOpeningService(session)
        open_objects = []
        for obj in objects:
            if await opening_service.is_object_open(obj["id"]):
                open_objects.append(obj)

    if not open_objects:
        await messenger.send_text(
            chat_id,
            "⚠️ <b>Нет открытых объектов</b>\n\n"
            "Для открытия спонтанной смены сначала откройте объект.",
            keyboard=[[{"text": "🏢 Открыть объект", "callback_data": "open_object"}]],
        )
        return True

    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.create_state(
        user_id=sk,
        action=UserAction.OPEN_SHIFT,
        step=UserStep.OBJECT_SELECTION,
        shift_type="spontaneous",
    )
    keyboard = []
    for obj in open_objects:
        n = len(obj.get("contracts", []))
        suffix = f" ({n} договор)" if n > 1 else ""
        keyboard.append([
            {"text": f"🏢 {obj['name']}{suffix}", "callback_data": f"open_shift_object:{obj['id']}"}
        ])
    keyboard.append([{"text": "❌ Отмена", "callback_data": "main_menu"}])
    await messenger.send_text(
        chat_id,
        "🏢 <b>Выберите объект для открытия смены:</b>",
        keyboard=keyboard,
    )
    return True


async def handle_close_shift(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Обработка close_shift для MAX."""
    from apps.bot.services.shift_service import ShiftService

    shift_service = ShiftService()
    chat_id = update.chat_id

    shifts = await shift_service.get_user_shifts(
        user_id=telegram_id or 0,
        status="active",
        internal_user_id=internal_user_id,
    )
    if not shifts:
        await messenger.send_text(
            chat_id,
            "ℹ️ У вас нет активных смен для закрытия.",
            keyboard=START_KEYBOARD,
        )
        return True

    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.create_state(
        user_id=sk,
        action=UserAction.CLOSE_SHIFT,
        step=UserStep.OBJECT_SELECTION,
    )
    keyboard = []
    for s in shifts:
        keyboard.append([
            {
                "text": f"🔚 Смена #{s['id']} (объект {s['object_id']})",
                "callback_data": f"close_shift_select:{s['id']}",
            }
        ])
    keyboard.append([{"text": "❌ Отмена", "callback_data": "main_menu"}])
    await messenger.send_text(
        chat_id,
        "🔚 <b>Выберите смену для закрытия:</b>",
        keyboard=keyboard,
    )
    return True


async def handle_open_shift_object_callback(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    object_id: int,
) -> bool:
    """Обработка open_shift_object:N — сохранить state, запросить геолокацию."""
    from core.database.session import get_async_session
    from domain.entities.object import Object
    from sqlalchemy import select

    chat_id = update.chat_id
    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.create_state(
        user_id=sk,
        action=UserAction.OPEN_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_object_id=object_id,
        shift_type="spontaneous",
    )
    async with get_async_session() as session:
        obj_result = await session.execute(select(Object).where(Object.id == object_id))
        obj = obj_result.scalar_one_or_none()
    obj_name = obj.name if obj else f"Объект #{object_id}"
    await messenger.send_text(
        chat_id,
        f"📍 <b>Отправьте геопозицию для открытия смены</b>\n\n"
        f"🏢 Объект: <b>{obj_name}</b>",
    )
    return True


async def handle_close_shift_select_callback(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    shift_id: int,
) -> bool:
    """Обработка close_shift_select:N — сохранить state, запросить геолокацию (без задач)."""
    from core.database.session import get_async_session
    from domain.entities.object import Object
    from domain.entities.shift import Shift
    from sqlalchemy import select

    chat_id = update.chat_id
    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.create_state(
        user_id=sk,
        action=UserAction.CLOSE_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_shift_id=shift_id,
    )
    obj_name = "Объект"
    async with get_async_session() as session:
        shift_result = await session.execute(select(Shift).where(Shift.id == shift_id))
        shift = shift_result.scalar_one_or_none()
        if shift and shift.object_id:
            obj_res = await session.execute(select(Object).where(Object.id == shift.object_id))
            obj = obj_res.scalar_one_or_none()
            obj_name = obj.name if obj else obj_name
    await messenger.send_text(
        chat_id,
        f"📍 <b>Отправьте геопозицию для закрытия смены</b>\n\n"
        f"🏢 Объект: <b>{obj_name}</b>",
    )
    return True


async def handle_open_planned_shift_callback(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    schedule_id: int,
) -> bool:
    """Обработка open_planned_shift:N — сохранить state, запросить геолокацию."""
    from apps.bot.services.shift_schedule_service import ShiftScheduleService

    chat_id = update.chat_id
    shift_schedule_service = ShiftScheduleService()
    schedule_data = await shift_schedule_service.get_shift_schedule_by_id(schedule_id)
    if not schedule_data:
        await messenger.send_text(chat_id, "❌ Запланированная смена не найдена.")
        return True

    object_id = schedule_data.get("object_id")
    from apps.bot.services.employee_objects_service import EmployeeObjectsService
    employee_objects_service = EmployeeObjectsService()
    has_access = await employee_objects_service.has_access_to_object(
        telegram_id or 0, object_id, internal_user_id=internal_user_id
    )
    if not has_access:
        await messenger.send_text(
            chat_id,
            "❌ Доступ запрещён. У вас должен быть активный договор с владельцем объекта.",
        )
        return True

    # Объект может быть закрыт: при отправке геолокации ShiftService.open_shift сам откроет объект.

    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.create_state(
        user_id=sk,
        action=UserAction.OPEN_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_object_id=object_id,
        shift_type="planned",
        selected_schedule_id=schedule_id,
        selected_timeslot_id=schedule_data.get("time_slot_id"),
    )
    obj_name = schedule_data.get("object_name", "Объект")
    planned_str = schedule_data.get("planned_start_str", "")
    await messenger.send_text(
        chat_id,
        f"📍 <b>Отправьте геопозицию для открытия смены</b>\n\n"
        f"🏢 Объект: <b>{obj_name}</b>\n🕐 {planned_str}",
    )
    return True


def _parse_coords_from_text(text: str) -> Optional[tuple[float, float]]:
    """Парсит координаты из текста вида '55.75,37.61' или '55.75, 37.61'."""
    if not text or not text.strip():
        return None
    m = re.match(r"^\s*(-?\d+\.?\d*)\s*[,;]\s*(-?\d+\.?\d*)\s*$", text.strip())
    if m:
        try:
            return (float(m.group(1)), float(m.group(2)))
        except ValueError:
            pass
    return None


async def handle_location_message(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    coordinates: str,
) -> bool:
    """
    Обработка сообщения с геолокацией (location или текст lat,lon).
    Вызывается когда state.step in (LOCATION_REQUEST, OPENING_OBJECT_LOCATION, CLOSING_OBJECT_LOCATION).
    """
    from apps.bot.services.shift_service import ShiftService
    from core.database.session import get_async_session
    from domain.entities.user import User
    from shared.services.object_opening_service import ObjectOpeningService
    from sqlalchemy import select

    chat_id = update.chat_id
    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    user_state = await user_state_manager.get_state(sk)
    if not user_state:
        await messenger.send_text(chat_id, "❌ Состояние утеряно. Начните заново.", keyboard=START_KEYBOARD)
        return True

    await user_state_manager.update_state(sk, step=UserStep.PROCESSING)
    shift_service = ShiftService()

    if user_state.action == UserAction.OPEN_SHIFT:
        object_id = user_state.selected_object_id
        if not object_id:
            await messenger.send_text(chat_id, "❌ Объект не выбран.")
            await user_state_manager.clear_state(sk)
            return True

        result = await shift_service.open_shift(
            user_id=telegram_id or 0,
            object_id=object_id,
            coordinates=coordinates,
            shift_type=user_state.shift_type or "spontaneous",
            timeslot_id=user_state.selected_timeslot_id,
            schedule_id=user_state.selected_schedule_id,
            internal_user_id=internal_user_id,
        )
        await user_state_manager.clear_state(sk)
        if result.get("success"):
            await messenger.send_text(
                chat_id,
                "✅ Смена успешно открыта!",
                keyboard=START_KEYBOARD,
            )
        else:
            err = result.get("error", "Ошибка")
            msg = f"❌ {err}"
            if "distance_meters" in result:
                msg += f"\n📏 Расстояние: {result['distance_meters']:.0f}м"
            await messenger.send_text(chat_id, msg, keyboard=START_KEYBOARD)

    elif user_state.action == UserAction.CLOSE_SHIFT:
        shift_id = user_state.selected_shift_id
        if not shift_id:
            await messenger.send_text(chat_id, "❌ Смена не выбрана.")
            await user_state_manager.clear_state(sk)
            return True

        result = await shift_service.close_shift(
            user_id=telegram_id or 0,
            shift_id=shift_id,
            coordinates=coordinates,
            internal_user_id=internal_user_id,
        )
        await user_state_manager.clear_state(sk)
        if result.get("success"):
            total_hours = result.get("total_hours", 0)
            total_payment = result.get("total_payment", 0)
            await messenger.send_text(
                chat_id,
                f"✅ Смена закрыта!\n⏱️ {total_hours:.1f}ч\n💰 {total_payment}₽",
                keyboard=START_KEYBOARD,
            )
            closed_obj_id = result.get("object_id")
            if closed_obj_id:
                async with get_async_session() as session:
                    opening_service = ObjectOpeningService(session)
                    count = await opening_service.get_active_shifts_count(closed_obj_id)
                    if count == 0:
                        user_res = await session.execute(select(User).where(User.id == internal_user_id))
                        db_user = user_res.scalar_one_or_none()
                        if db_user:
                            try:
                                await opening_service.close_object(
                                    object_id=closed_obj_id,
                                    user_id=db_user.id,
                                    coordinates=coordinates,
                                )
                                await messenger.send_text(
                                    chat_id,
                                    "✅ Объект автоматически закрыт (последняя смена).",
                                    keyboard=START_KEYBOARD,
                                )
                            except ValueError:
                                pass
        else:
            err = result.get("error", "Ошибка")
            msg = f"❌ {err}"
            if "distance_meters" in result:
                msg += f"\n📏 Расстояние: {result['distance_meters']:.0f}м"
            await messenger.send_text(chat_id, msg, keyboard=START_KEYBOARD)

    elif user_state.action == UserAction.OPEN_OBJECT:
        object_id = user_state.selected_object_id
        if not object_id:
            await messenger.send_text(chat_id, "❌ Объект не выбран.")
            await user_state_manager.clear_state(sk)
            return True

        from apps.bot.services.shift_schedule_service import ShiftScheduleService
        from domain.entities.object import Object
        from core.geolocation.location_validator import LocationValidator

        db_user_id: Optional[int] = None
        async with get_async_session() as session:
            opening_service = ObjectOpeningService(session)
            user_res = await session.execute(select(User).where(User.id == internal_user_id))
            db_user = user_res.scalar_one_or_none()
            if not db_user:
                await messenger.send_text(chat_id, "❌ Пользователь не найден.")
                await user_state_manager.clear_state(sk)
                return True
            db_user_id = db_user.id

            obj_res = await session.execute(select(Object).where(Object.id == object_id))
            obj = obj_res.scalar_one_or_none()
            if not obj:
                await messenger.send_text(chat_id, "❌ Объект не найден.")
                await user_state_manager.clear_state(sk)
                return True

            validator = LocationValidator()
            val = validator.validate_shift_location(
                coordinates, obj.coordinates, obj.max_distance_meters
            )
            if not val["valid"]:
                await messenger.send_text(
                    chat_id,
                    f"❌ Слишком далеко! 📏 {val['distance_meters']:.0f}м",
                    keyboard=START_KEYBOARD,
                )
                await user_state_manager.clear_state(sk)
                return True

            await opening_service.open_object(
                object_id=object_id,
                user_id=db_user.id,
                coordinates=coordinates,
            )

        shift_schedule_service = ShiftScheduleService()
        planned_shifts = await shift_schedule_service.get_user_planned_shifts_for_date(
            user_telegram_id=telegram_id,
            target_date=date.today(),
            internal_user_id=internal_user_id,
        )
        schedule_for_object = next(
            (s for s in planned_shifts if s.get("object_id") == object_id),
            None,
        )
        if schedule_for_object:
            result = await shift_service.open_shift(
                user_id=telegram_id or 0,
                object_id=object_id,
                coordinates=coordinates,
                shift_type="planned",
                timeslot_id=schedule_for_object.get("time_slot_id"),
                schedule_id=schedule_for_object.get("id"),
                internal_user_id=internal_user_id,
            )
        else:
            result = await shift_service.open_shift(
                user_id=telegram_id or 0,
                object_id=object_id,
                coordinates=coordinates,
                shift_type="spontaneous",
                internal_user_id=internal_user_id,
            )
        await user_state_manager.clear_state(sk)
        if result.get("success"):
            await messenger.send_text(
                chat_id,
                "✅ Объект открыт, смена начата!",
                keyboard=START_KEYBOARD,
            )
        else:
            if db_user_id:
                async with get_async_session() as session:
                    opening_service = ObjectOpeningService(session)
                    try:
                        await opening_service.close_object(
                            object_id=object_id,
                            user_id=db_user_id,
                            coordinates=coordinates,
                        )
                    except ValueError:
                        pass
            err = result.get("error", "ошибка")
            await messenger.send_text(
                chat_id,
                f"❌ Объект открыт, но не удалось открыть смену:\n{err}",
                keyboard=START_KEYBOARD,
            )

    elif user_state.action == UserAction.CLOSE_OBJECT:
        object_id = user_state.selected_object_id
        shift_id = user_state.selected_shift_id
        if not object_id or not shift_id:
            await messenger.send_text(chat_id, "❌ Данные неполные.")
            await user_state_manager.clear_state(sk)
            return True

        result = await shift_service.close_shift(
            user_id=telegram_id or 0,
            shift_id=shift_id,
            coordinates=coordinates,
            internal_user_id=internal_user_id,
        )
        await user_state_manager.clear_state(sk)
        if result.get("success"):
            async with get_async_session() as session:
                opening_service = ObjectOpeningService(session)
                user_res = await session.execute(select(User).where(User.id == internal_user_id))
                db_user = user_res.scalar_one_or_none()
                if db_user:
                    try:
                        await opening_service.close_object(
                            object_id=object_id,
                            user_id=db_user.id,
                            coordinates=coordinates,
                        )
                        await messenger.send_text(
                            chat_id,
                            "✅ Объект и смена закрыты!",
                            keyboard=START_KEYBOARD,
                        )
                    except ValueError as e:
                        await messenger.send_text(
                            chat_id,
                            f"✅ Смена закрыта. ⚠️ Объект: {e}",
                            keyboard=START_KEYBOARD,
                        )
        else:
            await messenger.send_text(
                chat_id,
                f"❌ {result.get('error', 'Ошибка')}",
                keyboard=START_KEYBOARD,
            )

    else:
        await user_state_manager.clear_state(sk)
        await messenger.send_text(chat_id, "❌ Неизвестное действие.", keyboard=START_KEYBOARD)

    return True
