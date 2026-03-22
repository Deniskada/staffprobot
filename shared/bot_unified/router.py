"""UnifiedBotRouter — единый обработчик команд (TG/MAX)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from core.logging.logger import logger
from core.auth.user_manager import user_manager

from .normalized_update import NormalizedUpdate
from .messenger import Messenger

if TYPE_CHECKING:
    pass


# Логический формат кнопок: [[{"text": "...", "callback_data": "..."}, ...], ...]
START_KEYBOARD = [
    [
        {"text": "🏢 Открыть объект", "callback_data": "open_object"},
        {"text": "🔒 Закрыть объект", "callback_data": "close_object"},
    ],
    [
        {"text": "🔄 Открыть смену", "callback_data": "open_shift"},
        {"text": "🔚 Закрыть смену", "callback_data": "close_shift"},
    ],
    [
        {"text": "📅 Запланировать смену", "callback_data": "schedule_shift"},
        {"text": "📋 Мои планы", "callback_data": "view_schedule"},
    ],
    [
        {"text": "📊 Отчет", "callback_data": "get_report"},
        {"text": "📝 Мои задачи", "callback_data": "my_tasks"},
    ],
    [
        {"text": "📈 Статус", "callback_data": "status"},
        {"text": "🆔 Мой ID", "callback_data": "get_telegram_id"},
    ],
]


async def _handle_start(update: NormalizedUpdate, messenger: Messenger) -> None:
    """Обработка /start."""
    ext_id = update.external_user_id
    first_name = update.first_name or "Пользователь"
    chat_id = update.chat_id
    text = (update.text or "").strip()

    # Telegram: /start CODE — привязка TG к аккаунту (например после MAX-only)
    if update.messenger == "telegram" and text.startswith("/start ") and ext_id:
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and len(parts[1]) == 6 and parts[1].isalnum():
            from .my_id_linking import apply_telegram_start_link_code

            ok, msg = await apply_telegram_start_link_code(
                int(ext_id),
                str(chat_id),
                parts[1].upper(),
                update.first_name,
                update.from_username,
                update.last_name,
            )
            await messenger.send_text(chat_id, msg, keyboard=START_KEYBOARD)
            return

    # MAX linking: /start CODE — привязка к user_id по одноразовому коду
    if update.messenger == "max" and text.startswith("/start ") and ext_id:
        parts = text.split(maxsplit=1)
        if len(parts) == 2 and len(parts[1]) == 6 and parts[1].isalnum():
            from shared.services.messenger_link_service import consume_max_link_code
            from core.database.session import get_async_session
            from domain.entities.messenger_account import MessengerAccount

            user_id = await consume_max_link_code(parts[1])
            if user_id:
                async with get_async_session() as session:
                    from sqlalchemy import select, and_
                    q = select(MessengerAccount).where(
                        and_(
                            MessengerAccount.provider == "max",
                            MessengerAccount.external_user_id == str(ext_id),
                        )
                    )
                    ex = await session.execute(q)
                    existing = ex.scalar_one_or_none()
                    if not existing:
                        session.add(
                            MessengerAccount(
                                user_id=user_id,
                                provider="max",
                                external_user_id=str(ext_id),
                                chat_id=chat_id,
                                username=update.from_username,
                            )
                        )
                        await session.commit()
                    await messenger.send_text(
                        chat_id,
                        "✅ MAX успешно привязан к вашему аккаунту. Теперь вы можете получать уведомления здесь."
                    )
                return
            await messenger.send_text(
                chat_id,
                "❌ Код недействителен или истёк. Получите новый в ЛК → Профиль → Мессенджеры."
            )
            return
        # MAX без кода — не регистрируем через MAX, даём инструкцию
        await messenger.send_text(
            chat_id,
            "Для привязки MAX откройте личный кабинет StaffProBot, войдите и перейдите в Профиль → Мессенджеры.\nТам нажмите «Привязать MAX» и введите код в этом чате."
        )
        return

    if not ext_id:
        logger.error("start: external_user_id is None")
        await messenger.send_text(chat_id, "Ошибка: не удалось определить пользователя.")
        return

    try:
        is_registered = await asyncio.to_thread(user_manager.is_user_registered, int(ext_id))
    except Exception as e:
        logger.error(f"start: error checking registration {ext_id}: {e}", exc_info=True)
        is_registered = False

    if not is_registered:
        try:
            await asyncio.to_thread(
                user_manager.register_user,
                int(ext_id),
                first_name,
                update.from_username,
                update.last_name,
                None,
            )
            welcome = f"""👋 Привет, {first_name}!

🎉 <b>Добро пожаловать в StaffProBot!</b>

Вы успешно зарегистрированы в системе.
Теперь вы можете использовать все функции бота.

🔧 Выберите действие кнопкой ниже:

💡 Что я умею:
• Открывать и закрывать смены с геолокацией
• Планировать смены заранее с уведомлениями
• Создавать объекты
• Вести учет времени
• Формировать отчеты

📍 <b>Геолокация:</b>
• Проверка присутствия на объектах
• Автоматический учет времени
• Безопасность и контроль

Используйте кнопки для быстрого доступа к функциям!"""
        except Exception as e:
            logger.error(f"start: error registering {ext_id}: {e}", exc_info=True)
            welcome = f"👋 Привет, {first_name}! Добро пожаловать в StaffProBot!"
    else:
        try:
            await asyncio.to_thread(user_manager.update_user_activity, int(ext_id))
        except Exception as e:
            logger.warning(f"start: error updating activity {ext_id}: {e}")
        welcome = f"""👋 Привет, {first_name}!

🔄 <b>С возвращением в StaffProBot!</b>

Рад снова вас видеть!

🔧 Выберите действие кнопкой ниже:

💡 Что я умею:
• Открывать и закрывать смены с геолокацией
• Планировать смены заранее с уведомлениями
• Создавать объекты
• Вести учет времени
• Формировать отчеты

📍 <b>Геолокация:</b>
• Проверка присутствия на объектах
• Автоматический учет времени
• Безопасность и контроль

Используйте кнопки для быстрого доступа к функциям!"""

    await messenger.send_text(chat_id, welcome, keyboard=START_KEYBOARD)
    logger.info(f"Router /start: sent to {ext_id}, chat_id={chat_id}")


async def _handle_get_chat_id(update: NormalizedUpdate, messenger: Messenger) -> None:
    """Обработка /get_chat_id."""
    chat_id = update.chat_id
    # Для TG chat_id может быть int-like; для единообразия — всегда str
    display_id = chat_id
    text = f"""ℹ️ <b>ID чата</b>

🆔 Chat ID: <code>{display_id}</code>

💡 Для групп: добавьте бота в группу и вызовите /get_chat_id там.
Скопируйте ID в настройки объекта («Telegram группа для отчетов»)."""
    await messenger.send_text(chat_id, text)
    logger.info(f"Router /get_chat_id: chat_id={chat_id}")


async def _handle_help(update: NormalizedUpdate, messenger: Messenger) -> None:
    """Обработка /help."""
    chat_id = update.chat_id
    text = """❓ <b>Справка по StaffProBot</b>

<b>Основные команды:</b>
/start - Запуск бота и главное меню
/help - Эта справка
/status - Статус ваших смен
/get_chat_id - Узнать ID текущего чата (для настройки групп отчетов)

<b>Основные функции:</b>
🔄 <b>Открыть смену</b> - Начать рабочую смену с проверкой геолокации
🔚 <b>Закрыть смену</b> - Завершить смену и подсчитать заработок
🏢 <b>Открыть объект</b> - Начать работу на объекте
🔒 <b>Закрыть объект</b> - Завершить работу на объекте
📊 <b>Отчет</b> - Просмотр статистики работы

<b>Геолокация:</b>
📍 Для открытия/закрытия смен требуется отправка геопозиции
📏 Проверяется расстояние до объекта (по умолчанию 500м)

❓ Нужна помощь? Обратитесь к администратору."""
    keyboard = [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    logger.info("Router /help: sent")


def _telegram_employee_unified_callback(callback_data: str) -> bool:
    """Колбэки, для которых Telegram идёт через unified."""
    if callback_data in (
        "open_shift",
        "close_shift",
        "open_object",
        "close_object",
        "status",
        "view_schedule",
        "schedule_shift",
        "my_tasks",
        "cancel_task_v2_media",
        "main_menu",
    ):
        return True
    prefixes = (
        "open_shift_object:",
        "close_shift_select:",
        "open_planned_shift:",
        "select_object_to_open:",
        "complete_task_v2:",
        "complete_my_task:",
        "task_v2_done:",
    )
    return any(callback_data.startswith(p) for p in prefixes)


def _max_protected_employee_callback(callback_data: str) -> bool:
    """MAX: колбэк требует привязки — показываем сообщение, если user не найден."""
    if callback_data in (
        "open_shift",
        "close_shift",
        "open_object",
        "close_object",
        "status",
        "view_schedule",
        "schedule_shift",
        "get_report",
        "my_tasks",
        "cancel_task_v2_media",
        "main_menu",
    ):
        return True
    return any(
        callback_data.startswith(p)
        for p in (
            "open_shift_object:",
            "close_shift_select:",
            "open_planned_shift:",
            "select_object_to_open:",
            "complete_task_v2:",
            "complete_my_task:",
            "task_v2_done:",
        )
    )


async def _try_dispatch_employee_callbacks(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Смены/объекты/планы в MAX и (частично) TG. True если колбэк распознан и обработан."""
    from .shift_handlers_unified import (
        handle_open_shift,
        handle_close_shift,
        handle_open_shift_object_callback,
        handle_close_shift_select_callback,
        handle_open_planned_shift_callback,
    )
    from .object_handlers_unified import (
        handle_open_object,
        handle_close_object,
        handle_select_object_to_open,
    )

    callback_data = (update.callback_data or "").strip()
    msgr = update.messenger
    chat_id = update.chat_id

    if callback_data == "open_shift":
        return await handle_open_shift(update, messenger, internal_id, telegram_id)
    if callback_data == "close_shift":
        return await handle_close_shift(update, messenger, internal_id, telegram_id)
    if callback_data == "open_object":
        return await handle_open_object(update, messenger, internal_id, telegram_id)
    if callback_data == "close_object":
        return await handle_close_object(update, messenger, internal_id, telegram_id)

    if callback_data == "main_menu":
        from core.state import user_state_manager
        from .user_resolver import user_state_storage_key

        sk = user_state_storage_key(msgr, internal_id, telegram_id)
        await user_state_manager.clear_state(sk)
        name = update.first_name or "Пользователь"
        await messenger.send_text(
            chat_id,
            f"👋 {name}, выберите действие:",
            keyboard=START_KEYBOARD,
        )
        return True

    if callback_data.startswith("open_shift_object:"):
        try:
            obj_id = int(callback_data.split(":")[1])
            return await handle_open_shift_object_callback(
                update, messenger, internal_id, telegram_id, obj_id
            )
        except (ValueError, IndexError):
            return False
    if callback_data.startswith("close_shift_select:"):
        try:
            shift_id = int(callback_data.split(":")[1])
            return await handle_close_shift_select_callback(
                update, messenger, internal_id, telegram_id, shift_id
            )
        except (ValueError, IndexError):
            return False
    if callback_data.startswith("open_planned_shift:"):
        try:
            sched_id = int(callback_data.split(":")[1])
            return await handle_open_planned_shift_callback(
                update, messenger, internal_id, telegram_id, sched_id
            )
        except (ValueError, IndexError):
            return False
    if callback_data.startswith("select_object_to_open:"):
        try:
            obj_id = int(callback_data.split(":")[1])
            return await handle_select_object_to_open(
                update, messenger, internal_id, telegram_id, obj_id
            )
        except (ValueError, IndexError):
            return False

    if callback_data == "status":
        from .misc_handlers_unified import handle_status

        return await handle_status(update, messenger, internal_id, telegram_id)
    if callback_data == "view_schedule":
        from .misc_handlers_unified import handle_view_schedule

        return await handle_view_schedule(update, messenger, internal_id, telegram_id)
    if callback_data == "schedule_shift":
        from .misc_handlers_unified import handle_schedule_shift

        return await handle_schedule_shift(update, messenger, internal_id, telegram_id)
    if callback_data == "get_report":
        from .misc_handlers_unified import handle_get_report

        return await handle_get_report(update, messenger, internal_id, telegram_id)

    if callback_data == "my_tasks":
        from .misc_handlers_unified import handle_my_tasks

        return await handle_my_tasks(update, messenger, internal_id, telegram_id)

    if callback_data.startswith("complete_task_v2:"):
        try:
            entry_id = int(callback_data.split(":", 1)[1])
            from .misc_handlers_unified import handle_complete_task_v2

            return await handle_complete_task_v2(
                update, messenger, internal_id, telegram_id, entry_id
            )
        except (ValueError, IndexError):
            return False
    if callback_data.startswith("complete_my_task:"):
        try:
            parts = callback_data.split(":", 2)
            shift_id = int(parts[1])
            task_idx = int(parts[2])
            from .misc_handlers_unified import handle_complete_my_task

            return await handle_complete_my_task(
                update, messenger, internal_id, telegram_id, shift_id, task_idx
            )
        except (ValueError, IndexError):
            return False
    if callback_data.startswith("task_v2_done:"):
        try:
            entry_id = int(callback_data.split(":", 1)[1])
            from .misc_handlers_unified import handle_task_v2_done

            return await handle_task_v2_done(
                update, messenger, internal_id, telegram_id, entry_id
            )
        except (ValueError, IndexError):
            return False
    if callback_data == "cancel_task_v2_media":
        from .misc_handlers_unified import handle_cancel_task_v2_media

        return await handle_cancel_task_v2_media(
            update, messenger, internal_id, telegram_id
        )

    return False


async def _handle_callback(update: NormalizedUpdate, messenger: Messenger) -> bool:
    """Обработка inline-кнопки. True — не вызывать legacy TG handlers."""
    chat_id = update.chat_id
    callback_data = (update.callback_data or "").strip()
    if update.callback_id and update.messenger == "max":
        await messenger.answer_callback(update.callback_id, "ok")

    if callback_data == "get_telegram_id":
        from .my_id_linking import send_my_id_screen

        await send_my_id_screen(update, messenger)
        return True

    if callback_data == "link_bind_max":
        from .my_id_linking import send_link_second_messenger_instructions

        await send_link_second_messenger_instructions(update, messenger, "max")
        return True

    if callback_data == "link_bind_tg":
        from .my_id_linking import send_link_second_messenger_instructions

        await send_link_second_messenger_instructions(update, messenger, "telegram")
        return True

    if update.messenger == "telegram" and not _telegram_employee_unified_callback(callback_data):
        return False
    if update.messenger == "max":
        ext_resolve = (update.external_user_id or str(update.chat_id or "")).strip()
        if not ext_resolve:
            return False
    else:
        if not update.external_user_id:
            return False
        ext_resolve = str(update.external_user_id).strip()

    from .user_resolver import resolve_for_services

    prov = "max" if update.messenger == "max" else "telegram"
    internal_id, telegram_id = await resolve_for_services(prov, ext_resolve)

    if internal_id:
        if await _try_dispatch_employee_callbacks(
            update, messenger, internal_id, telegram_id
        ):
            return True
        if update.messenger == "max":
            labels = {
                "open_object": "Открыть объект",
                "close_object": "Закрыть объект",
                "open_shift": "Открыть смену",
                "close_shift": "Закрыть смену",
                "schedule_shift": "Запланировать смену",
                "view_schedule": "Мои планы",
                "get_report": "Отчет",
                "my_tasks": "Мои задачи",
                "status": "Статус",
            }
            label = labels.get(callback_data, callback_data or "действие")
            await messenger.send_text(
                chat_id,
                f"⏳ «{label}» — в разработке для MAX.\n"
                "Используйте Telegram-бота для полного функционала.",
                keyboard=START_KEYBOARD,
            )
            return True
        return False

    if update.messenger == "max" and _max_protected_employee_callback(callback_data):
        await messenger.send_text(
            chat_id,
            "❌ Аккаунт не привязан. Используйте /start с кодом из ЛК → Мессенджеры.",
        )
        return True
    return False


class UnifiedBotRouter:
    """Единый роутер команд для TG и MAX."""

    async def handle(self, update: NormalizedUpdate, messenger: Messenger) -> bool:
        """
        Обрабатывает апдейт. Возвращает True если обработано.
        """
        if update.is_callback():
            return await _handle_callback(update, messenger)

        if not update.is_message():
            return False

        text = (update.text or "").strip().lower()
        if text == "/start" or text.startswith("/start "):
            await _handle_start(update, messenger)
            return True
        if text in ("/get_chat_id", "get_chat_id"):
            await _handle_get_chat_id(update, messenger)
            return True
        if text == "/help":
            await _handle_help(update, messenger)
            return True
        if text == "/status":
            if not update.external_user_id:
                return False
            from .user_resolver import resolve_for_services
            from .misc_handlers_unified import handle_status

            prov = "max" if update.messenger == "max" else "telegram"
            internal_id, telegram_id = await resolve_for_services(
                prov, update.external_user_id
            )
            if internal_id:
                if await handle_status(update, messenger, internal_id, telegram_id):
                    return True
            if update.messenger == "max":
                await messenger.send_text(
                    update.chat_id,
                    "❌ Аккаунт не привязан. Используйте /start с кодом из ЛК → Мессенджеры.",
                    keyboard=START_KEYBOARD,
                )
                return True
            return False

        # MAX: фото для задачи v2 (URL и/или token вложения)
        if update.messenger == "max" and (update.photo_url or update.photo_token):
            from .misc_handlers_unified import (
                _max_media_flow_external_id,
                handle_task_v2_photo_message,
            )
            from .user_resolver import resolve_for_services

            ext_resolve = _max_media_flow_external_id(update)
            if ext_resolve:
                photo_ref = None
                if update.photo_url and str(update.photo_url).startswith("http"):
                    photo_ref = f"max:url:{update.photo_url}"
                elif update.photo_token:
                    photo_ref = f"max:token:{update.photo_token}"
                elif update.photo_url:
                    photo_ref = f"max:url:{update.photo_url}"
                if photo_ref:
                    internal_id, _ = await resolve_for_services("max", ext_resolve)
                    if internal_id and await handle_task_v2_photo_message(
                        update, messenger, internal_id, photo_ref
                    ):
                        return True

        # MAX: геолокация (location или текст lat,lon)
        if update.messenger == "max" and update.external_user_id:
            coordinates = None
            if update.location:
                coordinates = f"{update.location['latitude']},{update.location['longitude']}"
            else:
                from .shift_handlers_unified import _parse_coords_from_text
                coords = _parse_coords_from_text(update.text or "")
                if coords:
                    coordinates = f"{coords[0]},{coords[1]}"

            if coordinates:
                from core.logging.logger import logger
                from .user_resolver import resolve_for_services
                from .shift_handlers_unified import handle_location_message
                from core.state import user_state_manager, UserStep

                logger.info(
                    "MAX location received",
                    extra={
                        "chat_id": update.chat_id,
                        "external_user_id": update.external_user_id,
                        "has_location_att": bool(update.location),
                    },
                )
                internal_id, telegram_id = await resolve_for_services(
                    "max", update.external_user_id
                )
                if internal_id:
                    state = await user_state_manager.get_state(internal_id)
                    logger.info(
                        "MAX location state",
                        extra={
                            "internal_id": internal_id,
                            "has_state": bool(state),
                            "step": state.step.value if state else None,
                        },
                    )
                    if state and state.step in (
                        UserStep.LOCATION_REQUEST,
                        UserStep.OPENING_OBJECT_LOCATION,
                        UserStep.CLOSING_OBJECT_LOCATION,
                    ):
                        if await handle_location_message(
                            update, messenger, internal_id, telegram_id, coordinates
                        ):
                            return True

        return False


unified_router = UnifiedBotRouter()
