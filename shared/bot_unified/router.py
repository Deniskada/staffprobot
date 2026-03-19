"""UnifiedBotRouter — единый обработчик команд (TG/MAX)."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

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
        {"text": "🆔 Мой Telegram ID", "callback_data": "get_telegram_id"},
    ],
]


async def _handle_start(update: NormalizedUpdate, messenger: Messenger) -> None:
    """Обработка /start."""
    ext_id = update.external_user_id
    first_name = update.first_name or "Пользователь"
    chat_id = update.chat_id
    text = (update.text or "").strip()

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


class UnifiedBotRouter:
    """Единый роутер команд для TG и MAX."""

    async def handle(self, update: NormalizedUpdate, messenger: Messenger) -> bool:
        """
        Обрабатывает апдейт. Возвращает True если обработано.
        """
        if not update.is_message():
            return False

        text = (update.text or "").strip().lower()
        if text == "/start" or text.startswith("/start "):
            await _handle_start(update, messenger)
            return True
        if text == "/get_chat_id":
            await _handle_get_chat_id(update, messenger)
            return True
        return False


unified_router = UnifiedBotRouter()
