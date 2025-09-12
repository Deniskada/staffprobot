"""Основные обработчики команд и сообщений бота."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from core.auth.user_manager import user_manager
from apps.bot.services.shift_service import ShiftService
from apps.bot.services.object_service import ObjectService
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.object import Object
from sqlalchemy import select
from core.state import user_state_manager, UserAction, UserStep
from datetime import date, timedelta

# Импорты будут добавлены в button_callback для избежания циклических импортов

# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Проверяем и регистрируем пользователя
    if not user_manager.is_user_registered(user.id):
        user_data = user_manager.register_user(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username,
            last_name=user.last_name,
            language_code=user.language_code
        )
        welcome_message = f"""
👋 Привет, {user.first_name}!

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

Используйте кнопки для быстрого доступа к функциям!
"""
        logger.info(
            f"New user registered: user_id={user.id}, username={user.username}, chat_id={chat_id}"
        )
    else:
        # Обновляем активность существующего пользователя
        user_manager.update_user_activity(user.id)
        welcome_message = f"""
👋 Привет, {user.first_name}!

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

Используйте кнопки для быстрого доступа к функциям!
"""
        logger.info(
            f"Existing user returned: user_id={user.id}, username={user.username}, chat_id={chat_id}"
        )
    
    # Создаем кнопки для основных действий
    keyboard = [
        [
            InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
            InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
        ],
        [
            InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift"),
            InlineKeyboardButton("📋 Мои планы", callback_data="view_schedule")
        ],
        [
            InlineKeyboardButton("🏢 Создать объект", callback_data="create_object"),
            InlineKeyboardButton("⚙️ Управление объектами", callback_data="manage_objects")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="get_report"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ],
        [
            InlineKeyboardButton("📈 Статус", callback_data="status"),
            InlineKeyboardButton("🆔 Мой Telegram ID", callback_data="get_telegram_id")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


# Импортируем утилиты
from .utils import get_location_keyboard

# Импортируем обработчики для button_callback
from .shift_handlers import (
    _handle_open_shift, _handle_close_shift, _handle_open_shift_object_selection,
    _handle_close_shift_selection, _handle_retry_location_open, _handle_retry_location_close,
    _handle_open_planned_shift
)
from .object_handlers import (
    _handle_manage_objects, _handle_edit_object, _handle_edit_field
)
from .timeslot_handlers import (
    _handle_manage_timeslots, _handle_create_timeslot, _handle_view_timeslots,
    _handle_edit_timeslots, _handle_delete_timeslots, _handle_create_regular_slot,
    _handle_create_additional_slot, _handle_create_slot_date, _handle_create_slot_custom_date,
    _handle_create_slot_week, _handle_edit_slot_date, _handle_edit_slot_custom_date,
    _handle_edit_slot_week, _handle_delete_slot_date, _handle_delete_slot_custom_date,
    _handle_delete_slot_week
)
from .utility_handlers import (
    _handle_help_callback, _handle_status_callback, _handle_get_telegram_id
)


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик геопозиции пользователя."""
    user_id = update.effective_user.id
    location = update.message.location
    
    # Получаем состояние пользователя
    user_state = user_state_manager.get_state(user_id)
    if not user_state:
        await update.message.reply_text(
            "❌ Сначала выберите действие (открыть или закрыть смену)"
        )
        return
    
    if user_state.step != UserStep.LOCATION_REQUEST:
        await update.message.reply_text(
            "❌ Геопозиция не ожидается на данном этапе"
        )
        return
    
    # Обновляем состояние на обработку
    user_state_manager.update_state(user_id, step=UserStep.PROCESSING)
    
    coordinates = f"{location.latitude},{location.longitude}"
    
    try:
        if user_state.action == UserAction.OPEN_SHIFT:
        # Открываем смену
        result = await shift_service.open_shift(
            user_id=user_id,
            object_id=user_state.selected_object_id,
            coordinates=coordinates,
            shift_type=getattr(user_state, 'shift_type', 'spontaneous'),
            timeslot_id=getattr(user_state, 'selected_timeslot_id', None),
            schedule_id=getattr(user_state, 'selected_schedule_id', None)
        )
            
            if result['success']:
                object_name = result.get('object_name', 'Неизвестно') or 'Неизвестно'
                start_time = result.get('start_time', 'Сейчас') or 'Сейчас'
                hourly_rate = result.get('hourly_rate', 0) or 0
                
                # Убираем клавиатуру
                from telegram import ReplyKeyboardRemove
                await update.message.reply_text(
                    f"✅ Смена успешно открыта!\n"
                    f"📍 Объект: {object_name}\n"
                    f"🕐 Время начала: {start_time}\n"
                    f"💰 Часовая ставка: {hourly_rate}₽",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                error_msg = f"❌ Ошибка при открытии смены: {result['error']}"
                if 'distance_meters' in result:
                    error_msg += f"\n📏 Расстояние: {result['distance_meters']:.0f}м"
                    error_msg += f"\n📐 Максимум: {result.get('max_distance_meters', 100)}м"
                
                # Добавляем кнопки для повторной отправки или отмены
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [
                    [InlineKeyboardButton("📍 Отправить геопозицию повторно", callback_data=f"retry_location:{user_state.selected_object_id}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(error_msg, reply_markup=reply_markup)
                
        elif user_state.action == UserAction.CLOSE_SHIFT:
            # Закрываем смену
            result = await shift_service.close_shift(
                user_id=user_id,
                shift_id=user_state.selected_shift_id,
                coordinates=coordinates
            )
            
            if result['success']:
                total_hours = result.get('total_hours', 0) or 0
                total_payment = result.get('total_payment', 0) or 0
                
                # Отладочный вывод
                logger.info(
                    f"Close shift result for user {user_id}: result={result}, "
                    f"total_hours={total_hours}, total_payment={total_payment}"
                )
                
                # Убираем клавиатуру
                from telegram import ReplyKeyboardRemove
                await update.message.reply_text(
                    f"✅ Смена успешно закрыта!\n"
                    f"⏱️ Отработано: {total_hours:.1f} часов\n"
                    f"💰 Заработано: {total_payment}₽",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                error_msg = f"❌ Ошибка при закрытии смены: {result['error']}"
                if 'distance_meters' in result:
                    error_msg += f"\n📏 Расстояние: {result['distance_meters']:.0f}м"
                    error_msg += f"\n📐 Максимум: {result.get('max_distance_meters', 100)}м"
                
                # Добавляем кнопки для повторной отправки или отмены
                keyboard = [
                    [InlineKeyboardButton("📍 Отправить геопозицию повторно", callback_data=f"retry_close_location:{user_state.selected_shift_id}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(error_msg, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error processing location for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке геопозиции. Попробуйте еще раз."
        )
    
    finally:
        # Очищаем состояние пользователя
        user_state_manager.clear_state(user_id)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик нажатий на inline-кнопки."""
    query = update.callback_query
    await query.answer()  # Убираем "часики" у кнопки
    
    user = query.from_user
    chat_id = query.message.chat_id
    
    # Обновляем активность пользователя
    user_manager.update_user_activity(user.id)
    
    logger.info(
        f"Button callback received: user_id={user.id}, username={user.username}, callback_data={query.data}"
    )
    
    # Обработчики уже импортированы в начале файла
    
    # Обрабатываем разные типы кнопок
    if query.data == "open_shift":
        await _handle_open_shift(update, context)
        return
    elif query.data == "close_shift":
        await _handle_close_shift(update, context)
        return
    elif query.data.startswith("open_shift_object:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_open_shift_object_selection(update, context, object_id)
        return
    elif query.data.startswith("open_planned_shift:"):
        schedule_id = int(query.data.split(":", 1)[1])
        await _handle_open_planned_shift(update, context, schedule_id)
        return
    elif query.data.startswith("close_shift_select:"):
        shift_id = int(query.data.split(":", 1)[1])
        await _handle_close_shift_selection(update, context, shift_id)
        return
    elif query.data.startswith("edit_object:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_edit_object(update, context, object_id)
        return
    elif query.data.startswith("edit_field:"):
        # Формат: edit_field:object_id:field_name
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            field_name = parts[2]
            await _handle_edit_field(update, context, object_id, field_name)
        return
    elif query.data == "create_object":
        from .object_creation_handlers import handle_create_object_start
        await handle_create_object_start(update, context)
        return
    elif query.data == "manage_objects":
        await _handle_manage_objects(update, context)
        return
    elif query.data.startswith("delete_object:"):
        object_id = int(query.data.split(":", 1)[1])
        from .object_handlers import _handle_delete_object
        await _handle_delete_object(update, context, object_id)
        return
    elif query.data.startswith("confirm_delete_object:"):
        object_id = int(query.data.split(":", 1)[1])
        from .object_handlers import _handle_confirm_delete_object
        await _handle_confirm_delete_object(update, context, object_id)
        return
    elif query.data.startswith("retry_location:"):
        # Формат: retry_location:object_id
        object_id = int(query.data.split(":", 1)[1])
        await _handle_retry_location_open(update, context, object_id)
        return
    elif query.data.startswith("retry_close_location:"):
        # Формат: retry_close_location:shift_id
        shift_id = int(query.data.split(":", 1)[1])
        await _handle_retry_location_close(update, context, shift_id)
        return
    # Планирование смен
    elif query.data == "schedule_shift":
        from .schedule_handlers import handle_schedule_shift
        await handle_schedule_shift(update, context)
        return
    elif query.data == "view_schedule":
        from .schedule_handlers import handle_view_schedule
        await handle_view_schedule(update, context)
        return
    elif query.data.startswith("schedule_select_object_"):
        from .schedule_handlers import handle_schedule_object_selection
        await handle_schedule_object_selection(update, context)
        return
    elif query.data in ["schedule_date_today", "schedule_date_tomorrow", "schedule_date_custom"]:
        from .schedule_handlers import handle_schedule_date_selection
        await handle_schedule_date_selection(update, context)
        return
    elif query.data.startswith("schedule_select_slot_"):
        from .schedule_handlers import handle_schedule_confirmation
        await handle_schedule_confirmation(update, context)
        return
    elif query.data == "cancel_schedule":
        from .schedule_handlers import handle_cancel_schedule
        await handle_cancel_schedule(update, context)
        return
    elif query.data.startswith("cancel_shift_"):
        from .schedule_handlers import handle_cancel_shift
        await handle_cancel_shift(update, context)
        return
    elif query.data == "close_schedule":
        from .schedule_handlers import handle_close_schedule
        await handle_close_schedule(update, context)
        return
    elif query.data == "get_report":
        # Аналитика и отчеты: сразу запускаем мастер создания отчета
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.start_report_creation(update, context)
        return
    elif query.data.startswith("report_object_") or query.data == "report_all_objects":
        # Выбор объекта для отчета
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.select_object(update, context)
        return
    elif query.data.startswith("period_"):
        # Выбор периода для отчета
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.select_period(update, context)
        return
    elif query.data.startswith("format_"):
        # Выбор формата отчета
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.select_format(update, context)
        return
    elif query.data == "analytics_cancel":
        # Отмена аналитики
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.cancel_analytics(update, context)
        return
    elif query.data == "analytics_dashboard":
        # Показ дашборда
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.show_dashboard(update, context)
        return
    elif query.data == "analytics_report":
        # Создание отчета
        from .analytics_handlers import AnalyticsHandlers
        analytics = AnalyticsHandlers()
        await analytics.start_report_creation(update, context)
        return
    elif query.data == "help":
        await _handle_help_callback(update, context)
        return
    elif query.data == "status":
        await _handle_status_callback(update, context)
        return
    elif query.data == "get_telegram_id":
        await _handle_get_telegram_id(update, context)
        return
    # Управление тайм-слотами
    elif query.data.startswith("manage_timeslots:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_manage_timeslots(update, context, object_id)
        return
    elif query.data.startswith("create_timeslot:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_create_timeslot(update, context, object_id)
        return
    elif query.data.startswith("view_timeslots:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_view_timeslots(update, context, object_id)
        return
    elif query.data.startswith("edit_timeslots:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_edit_timeslots(update, context, object_id)
        return
    elif query.data.startswith("edit_timeslot:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_edit_single_timeslot
        await _handle_edit_single_timeslot(update, context, timeslot_id)
        return
    elif query.data.startswith("edit_timeslot_time:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_edit_timeslot_time
        await _handle_edit_timeslot_time(update, context, timeslot_id)
        return
    elif query.data.startswith("edit_timeslot_rate:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_edit_timeslot_rate
        await _handle_edit_timeslot_rate(update, context, timeslot_id)
        return
    elif query.data.startswith("edit_timeslot_employees:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_edit_timeslot_employees
        await _handle_edit_timeslot_employees(update, context, timeslot_id)
        return
    elif query.data.startswith("edit_timeslot_notes:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_edit_timeslot_notes
        await _handle_edit_timeslot_notes(update, context, timeslot_id)
        return
    elif query.data.startswith("toggle_timeslot_status:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_toggle_timeslot_status
        await _handle_toggle_timeslot_status(update, context, timeslot_id)
        return
    elif query.data.startswith("delete_timeslot:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_delete_timeslot
        await _handle_delete_timeslot(update, context, timeslot_id)
        return
    elif query.data.startswith("confirm_delete_timeslot:"):
        timeslot_id = int(query.data.split(":", 1)[1])
        from .timeslot_handlers import _handle_confirm_delete_timeslot
        await _handle_confirm_delete_timeslot(update, context, timeslot_id)
        return
    elif query.data.startswith("delete_timeslots:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_delete_timeslots(update, context, object_id)
        return
    elif query.data.startswith("create_regular_slot:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_create_regular_slot(update, context, object_id)
        return
    elif query.data.startswith("create_additional_slot:"):
        object_id = int(query.data.split(":", 1)[1])
        await _handle_create_additional_slot(update, context, object_id)
        return
    elif query.data.startswith("create_slot_date:"):
        # Формат: create_slot_date:object_id:type:date
        parts = query.data.split(":", 3)
        if len(parts) == 4:
            object_id = int(parts[1])
            slot_type = parts[2]
            slot_date = parts[3]
            await _handle_create_slot_date(update, context, object_id, slot_type, slot_date)
        return
    elif query.data.startswith("create_slot_custom_date:"):
        # Формат: create_slot_custom_date:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_create_slot_custom_date(update, context, object_id, slot_type)
        return
    elif query.data.startswith("create_slot_week:"):
        # Формат: create_slot_week:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_create_slot_week(update, context, object_id, slot_type)
        return
    elif query.data.startswith("edit_slot_date:"):
        # Формат: edit_slot_date:object_id:type:date
        parts = query.data.split(":", 3)
        if len(parts) == 4:
            object_id = int(parts[1])
            slot_type = parts[2]
            slot_date = parts[3]
            await _handle_edit_slot_date(update, context, object_id, slot_type, slot_date)
        return
    elif query.data.startswith("edit_slot_custom_date:"):
        # Формат: edit_slot_custom_date:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_edit_slot_custom_date(update, context, object_id, slot_type)
        return
    elif query.data.startswith("edit_slot_week:"):
        # Формат: edit_slot_week:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_edit_slot_week(update, context, object_id, slot_type)
        return
    elif query.data.startswith("delete_slot_date:"):
        # Формат: delete_slot_date:object_id:type:date
        parts = query.data.split(":", 3)
        if len(parts) == 4:
            object_id = int(parts[1])
            slot_type = parts[2]
            slot_date = parts[3]
            await _handle_delete_slot_date(update, context, object_id, slot_type, slot_date)
        return
    elif query.data.startswith("delete_slot_custom_date:"):
        # Формат: delete_slot_custom_date:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_delete_slot_custom_date(update, context, object_id, slot_type)
        return
    elif query.data.startswith("delete_slot_week:"):
        # Формат: delete_slot_week:object_id:type
        parts = query.data.split(":", 2)
        if len(parts) == 3:
            object_id = int(parts[1])
            slot_type = parts[2]
            await _handle_delete_slot_week(update, context, object_id, slot_type)
        return    
    elif query.data == "main_menu" or query.data == "back_to_menu":
        response = f"""
🏠 <b>Главное меню</b>

👋 Привет, {user.first_name}!

Выберите действие кнопкой ниже:
"""
    else:
        response = """
❌ <b>Неизвестная команда</b>

Произошла ошибка при обработке кнопки.
Используйте команду /start для возврата в главное меню.
"""
    
    # Создаем кнопки для ответа
    keyboard = [
        [
            InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
            InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
        ],
        [
            InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift"),
            InlineKeyboardButton("📋 Мои планы", callback_data="view_schedule")
        ],
        [
            InlineKeyboardButton("🏢 Создать объект", callback_data="create_object"),
            InlineKeyboardButton("⚙️ Управление объектами", callback_data="manage_objects")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="get_report"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ],
        [
            InlineKeyboardButton("📈 Статус", callback_data="status"),
            InlineKeyboardButton("🆔 Мой Telegram ID", callback_data="get_telegram_id")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем ответ с кнопками
    await query.edit_message_text(
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
