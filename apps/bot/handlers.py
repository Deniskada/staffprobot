"""Обработчики команд и сообщений бота."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from core.auth.user_manager import user_manager
from apps.bot.services.shift_service import ShiftService
from apps.bot.services.object_service import ObjectService
from core.database.session import get_async_session
from core.database.connection import get_sync_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.object import Object
from sqlalchemy import select
import asyncio
# Импорт удаленного файла убран
from core.state import user_state_manager, UserAction, UserStep


# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    user = update.effective_user
    if not user:
        return
    
    help_text = """
❓ <b>Справка по StaffProBot</b>

<b>Основные команды:</b>
/start - Запуск бота и главное меню
/help - Эта справка
/status - Статус ваших смен
/get_chat_id - Узнать ID текущего чата (для настройки групп отчетов)

<b>Основные функции:</b>
🔄 <b>Открыть смену</b> - Начать рабочую смену с проверкой геолокации
🔚 <b>Закрыть смену</b> - Завершить смену и подсчитать заработок
🏢 <b>Создать объект</b> - Добавить новый рабочий объект
⚙️ <b>Управление объектами</b> - Редактировать существующие объекты
📊 <b>Отчет</b> - Просмотр статистики работы

<b>Геолокация:</b>
📍 Для открытия/закрытия смен требуется отправка геопозиции
📏 Проверяется расстояние до объекта (по умолчанию 500м)
🎯 Используйте кнопку "📍 Отправить геопозицию" для точного определения

<b>Полезные советы:</b>
• Убедитесь что GPS включен на устройстве
• Находитесь рядом с объектом при открытии/закрытии смен
• Используйте кнопки для быстрого доступа к функциям
• При ошибках геолокации можно повторить отправку

❓ Нужна помощь? Обратитесь к администратору.
"""
    
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        help_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def get_chat_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /get_chat_id — делегирует в UnifiedBotRouter."""
    from shared.bot_unified import TgAdapter, TgMessenger, unified_router

    nu = TgAdapter.parse(update)
    if nu:
        messenger = TgMessenger(update, context)
        try:
            if await unified_router.handle(nu, messenger):
                return
        except Exception as e:
            logger.error(f"get_chat_id_command: router error: {e}", exc_info=True)
    # Fallback: старый вывод
    chat = update.effective_chat
    if chat and update.message:
        chat_type = chat.type
        chat_id = chat.id
        if chat_type == "private":
            text = f"ℹ️ <b>ID чата</b>\n\n📱 Личный чат\n🆔 Chat ID: <code>{chat_id}</code>"
        else:
            title = chat.title or "Без названия"
            text = f"ℹ️ <b>ID чата</b>\n\n💬 {title}\n🆔 Chat ID: <code>{chat_id}</code>"
        await update.message.reply_text(text, parse_mode="HTML")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /status."""
    user = update.effective_user
    if not user:
        return
    
    user_id = user.id
    
    try:
        # Получаем активные смены пользователя
        active_shifts = await shift_service.get_user_active_shifts(user_id)
        
        if not active_shifts:
            status_text = """
📈 <b>Статус смен</b>

✅ <b>Активных смен нет</b>

Вы можете открыть новую смену через главное меню.
"""
        else:
            shift = active_shifts[0]  # Берем первую активную смену
            obj_data = object_service.get_object_by_id(shift['object_id'])
            
            # Конвертируем время в часовой пояс объекта
            object_timezone = obj_data.get('timezone', 'Europe/Moscow') if obj_data else 'Europe/Moscow'
            local_start_time = timezone_helper.format_local_time(shift['start_time'], object_timezone)
            
            status_text = f"""
📈 <b>Статус смен</b>

🟢 <b>Активная смена:</b>
🏢 Объект: {obj_data['name'] if obj_data else 'Неизвестный'}
🕐 Начало: {local_start_time}
💰 Ставка: {obj_data['hourly_rate'] if obj_data else 0}₽/час

Для завершения смены используйте кнопку "🔚 Закрыть смену".
"""
    except Exception as e:
        logger.error(f"Error getting user status for {user_id}: {e}")
        status_text = """
📈 <b>Статус смен</b>

❌ <b>Ошибка получения статуса</b>

Попробуйте позже или обратитесь к администратору.
"""
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
            InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
        ],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        status_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


# start_command перенесен в handlers_div/core_handlers.py


# get_location_keyboard перенесен в handlers_div/utils.py


# handle_location перенесен в handlers_div/core_handlers.py


# button_callback перенесен в handlers_div/core_handlers.py


# Все обработчики смен перенесены в handlers_div/


# Все обработчики смен перенесены в handlers_div/


# Все обработчики смен перенесены в handlers_div/


# Все обработчики перенесены в handlers_div/
