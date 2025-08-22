"""Обработчики команд и сообщений бота."""

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
import asyncio
from apps.bot.object_creation_handlers import handle_create_object_start, handle_create_object_input, user_object_creation_state
from core.state import user_state_manager, UserAction, UserStep
from apps.bot.schedule_handlers import (
    handle_schedule_shift, handle_schedule_object_selection, handle_schedule_date_selection,
    handle_schedule_confirmation, handle_view_schedule, handle_cancel_schedule,
    handle_schedule_time_input, handle_custom_date_input
)


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
            InlineKeyboardButton("📈 Статус", callback_data="status")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=welcome_message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


def get_location_keyboard() -> ReplyKeyboardMarkup:
    """Создает клавиатуру для запроса геопозиции."""
    keyboard = [
        [KeyboardButton("📍 Отправить геопозицию", request_location=True)],
        [KeyboardButton("❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)


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
                coordinates=coordinates
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
        await handle_create_object_start(update, context)
        return
    elif query.data == "manage_objects":
        await _handle_manage_objects(update, context)
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
        await handle_schedule_shift(update, context)
        return
    elif query.data == "view_schedule":
        await handle_view_schedule(update, context)
        return
    elif query.data.startswith("schedule_select_object_"):
        await handle_schedule_object_selection(update, context)
        return
    elif query.data in ["schedule_date_today", "schedule_date_tomorrow", "schedule_date_custom"]:
        await handle_schedule_date_selection(update, context)
        return
    elif query.data == "schedule_confirm":
        await handle_schedule_confirmation(update, context)
        return
    elif query.data.startswith("cancel_schedule_"):
        await handle_cancel_schedule(update, context)
        return
    elif query.data == "help":
        await help_command(update, context)
        return
    elif query.data == "status":
        await status_command(update, context)
        return
    elif query.data == "main_menu":
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
            InlineKeyboardButton("📈 Статус", callback_data="status")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем ответ с кнопками
    await query.edit_message_text(
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_open_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик открытия смены."""
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    # Проверяем регистрацию пользователя
    if not user_manager.is_user_registered(user_id):
        await query.edit_message_text(
            text="❌ <b>Пользователь не зарегистрирован</b>\n\nИспользуйте /start для регистрации.",
            parse_mode='HTML'
        )
        return
    
    # Проверяем, нет ли уже активной смены
    try:
        active_shifts = await shift_service.get_user_shifts(user_id, status='active')
        if active_shifts:
            await query.edit_message_text(
                text="❌ <b>У вас уже есть активная смена</b>\n\nСначала закройте текущую смену.",
                parse_mode='HTML'
            )
            return
    except Exception as e:
        logger.error(f"Error checking active shifts for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при проверке активных смен. Попробуйте позже.",
            parse_mode='HTML'
        )
        return
    
    # Получаем список объектов пользователя
    try:
        async with get_async_session() as session:
            # Получаем объекты, к которым у пользователя есть доступ
            objects_query = select(Object).where(Object.is_active == True)
            objects_result = await session.execute(objects_query)
            objects = objects_result.scalars().all()
            
            if not objects:
                await query.edit_message_text(
                    text="❌ <b>Нет доступных объектов</b>\n\nСначала создайте объект или получите доступ к существующему.",
                    parse_mode='HTML'
                )
                return
            
            # Создаем состояние пользователя
            user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_SHIFT,
                step=UserStep.OBJECT_SELECTION
            )
            
            # Создаем кнопки для выбора объекта
            keyboard = []
            for obj in objects:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏢 {obj.name} ({obj.address or 'без адреса'})", 
                        callback_data=f"open_shift_object:{obj.id}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="🔄 <b>Открытие смены</b>\n\nВыберите объект для открытия смены:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error getting objects: {e}")
        await query.edit_message_text(
            text="❌ <b>Ошибка при получении объектов</b>\n\nПопробуйте позже или обратитесь к администратору.",
            parse_mode='HTML'
        )


async def _handle_close_shift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик закрытия смены."""
    query = update.callback_query
    user = query.from_user
    user_id = user.id
    
    # Проверяем регистрацию пользователя
    if not user_manager.is_user_registered(user_id):
        await query.edit_message_text(
            text="❌ <b>Пользователь не зарегистрирован</b>\n\nИспользуйте /start для регистрации.",
            parse_mode='HTML'
        )
        return
    
    # Получаем активные смены пользователя
    try:
        active_shifts = await shift_service.get_user_shifts(user_id, status='active')
        
        if not active_shifts:
            await query.edit_message_text(
                text="❌ <b>У вас нет активных смен</b>\n\nСначала откройте смену.",
                parse_mode='HTML'
            )
            return
        
        # Если одна активная смена - сразу переходим к геопозиции
        if len(active_shifts) == 1:
            shift = active_shifts[0]  # Это словарь, а не объект
            
            # Создаем состояние пользователя
            user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.CLOSE_SHIFT,
                step=UserStep.LOCATION_REQUEST,
                selected_shift_id=shift['id']  # Используем ключ словаря
            )
            
            # Получаем информацию об объекте смены
            async with get_async_session() as session:
                obj_query = select(Object).where(Object.id == shift['object_id'])  # Используем ключ словаря
                obj_result = await session.execute(obj_query)
                obj = obj_result.scalar_one_or_none()
                
                if not obj:
                    await query.edit_message_text(
                        text="❌ Объект смены не найден.",
                        parse_mode='HTML'
                    )
                    user_state_manager.clear_state(user_id)
                    return
                
                # Конвертируем время начала смены в локальную зону
                from datetime import datetime
                try:
                    # Парсим строку времени из БД (формат: 'YYYY-MM-DD HH:MM:SS')
                    start_time_utc = datetime.strptime(shift['start_time'], '%Y-%m-%d %H:%M:%S')
                    user_timezone = timezone_helper.get_user_timezone(user_id)
                    local_start_time = timezone_helper.format_local_time(start_time_utc, user_timezone)
                except (ValueError, KeyError):
                    local_start_time = shift['start_time']  # Fallback к исходному значению
                
                # Запрашиваем геопозицию
                await query.edit_message_text(
                    text=f"📍 <b>Отправьте геопозицию для закрытия смены</b>\n\n"
                         f"🏢 Объект: <b>{obj.name}</b>\n"
                         f"📍 Адрес: {obj.address or 'не указан'}\n"
                         f"🕐 Начало смены: {local_start_time}\n\n"
                         f"Нажмите кнопку ниже для отправки вашего местоположения:",
                    parse_mode='HTML'
                )
                
                # Отправляем клавиатуру для геопозиции
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="👇 Используйте кнопку для отправки геопозиции:",
                    reply_markup=get_location_keyboard()
                )
        
        else:
            # Несколько активных смен - предлагаем выбрать (устаревший случай, но на всякий случай)
            keyboard = []
            for shift in active_shifts:  # Это словари, а не объекты
                # Получаем информацию об объекте
                async with get_async_session() as session:
                    obj_query = select(Object).where(Object.id == shift['object_id'])  # Используем ключ словаря
                    obj_result = await session.execute(obj_query)
                    obj = obj_result.scalar_one_or_none()
                    
                    obj_name = obj.name if obj else "Неизвестный объект"
                    
                keyboard.append([
                    InlineKeyboardButton(
                        f"🔚 {obj_name} ({shift['start_time'][:5]})",  # Используем ключ словаря и берем только HH:MM
                        callback_data=f"close_shift_select:{shift['id']}"  # Используем ключ словаря
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="🔚 <b>Закрытие смены</b>\n\nВыберите смену для закрытия:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error handling close shift for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при получении активных смен. Попробуйте позже.",
            parse_mode='HTML'
        )


async def _handle_open_shift_object_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик выбора объекта для открытия смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем состояние пользователя
    user_state = user_state_manager.get_state(user_id)
    if not user_state or user_state.action != UserAction.OPEN_SHIFT:
        await query.edit_message_text(
            text="❌ Состояние сессии истекло. Попробуйте еще раз.",
            parse_mode='HTML'
        )
        return
    
    # Обновляем состояние - сохраняем выбранный объект
    user_state_manager.update_state(
        user_id=user_id,
        selected_object_id=object_id,
        step=UserStep.LOCATION_REQUEST
    )
    
    # Получаем информацию об объекте
    try:
        async with get_async_session() as session:
            obj_query = select(Object).where(Object.id == object_id)
            obj_result = await session.execute(obj_query)
            obj = obj_result.scalar_one_or_none()
            
            if not obj:
                await query.edit_message_text(
                    text="❌ Объект не найден.",
                    parse_mode='HTML'
                )
                user_state_manager.clear_state(user_id)
                return
            
            # Запрашиваем геопозицию
            await query.edit_message_text(
                text=f"📍 <b>Отправьте геопозицию</b>\n\n"
                     f"🏢 Объект: <b>{obj.name}</b>\n"
                     f"📍 Адрес: {obj.address or 'не указан'}\n\n"
                     f"Нажмите кнопку ниже для отправки вашего местоположения:",
                parse_mode='HTML'
            )
            
            # Отправляем клавиатуру для геопозиции
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👇 Используйте кнопку для отправки геопозиции:",
                reply_markup=get_location_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error handling object selection for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при обработке выбора объекта. Попробуйте позже.",
            parse_mode='HTML'
        )
        user_state_manager.clear_state(user_id)


async def _handle_close_shift_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int):
    """Обработчик выбора смены для закрытия."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Создаем состояние пользователя
    user_state_manager.create_state(
        user_id=user_id,
        action=UserAction.CLOSE_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_shift_id=shift_id
    )
    
    # Получаем информацию о смене и объекте
    try:
        shift = await shift_service.get_shift_by_id(shift_id)
        if not shift:
            await query.edit_message_text(
                text="❌ Смена не найдена.",
                parse_mode='HTML'
            )
            user_state_manager.clear_state(user_id)
            return
        
        async with get_async_session() as session:
            obj_query = select(Object).where(Object.id == shift.object_id)
            obj_result = await session.execute(obj_query)
            obj = obj_result.scalar_one_or_none()
            
            if not obj:
                await query.edit_message_text(
                    text="❌ Объект смены не найден.",
                    parse_mode='HTML'
                )
                user_state_manager.clear_state(user_id)
                return
            
            # Конвертируем время начала смены в локальную зону
            user_timezone = timezone_helper.get_user_timezone(user_id)
            local_start_time = timezone_helper.format_local_time(shift.start_time, user_timezone)
            
            # Запрашиваем геопозицию
            await query.edit_message_text(
                text=f"📍 <b>Отправьте геопозицию для закрытия смены</b>\n\n"
                     f"🏢 Объект: <b>{obj.name}</b>\n"
                     f"📍 Адрес: {obj.address or 'не указан'}\n"
                     f"🕐 Начало смены: {local_start_time}\n\n"
                     f"Нажмите кнопку ниже для отправки вашего местоположения:",
                parse_mode='HTML'
            )
            
            # Отправляем клавиатуру для геопозиции
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👇 Используйте кнопку для отправки геопозиции:",
                reply_markup=get_location_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Error handling close shift selection for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при обработке выбора смены. Попробуйте позже.",
            parse_mode='HTML'
        )
        user_state_manager.clear_state(user_id)


async def _handle_manage_objects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления объектами."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем объекты пользователя
    user_objects = object_service.get_user_objects(user_id)
    
    if not user_objects:
        await query.edit_message_text(
            text="📋 <b>Управление объектами</b>\n\n❌ У вас пока нет созданных объектов.\n\nСоздайте первый объект через главное меню.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    keyboard = []
    for obj in user_objects:
        # Теперь max_distance_meters уже есть в данных объекта
        max_distance = obj.get('max_distance_meters', 500)
            
        keyboard.append([
            InlineKeyboardButton(
                f"⚙️ {obj['name']} ({max_distance}м)", 
                callback_data=f"edit_object:{obj['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="📋 <b>Управление объектами</b>\n\nВыберите объект для редактирования:\n\n💡 В скобках указано максимальное расстояние для геолокации",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_object(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик редактирования объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Теперь max_distance_meters уже есть в obj_data
    max_distance = obj_data.get('max_distance_meters', 500)
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Название", callback_data=f"edit_field:{object_id}:name"),
            InlineKeyboardButton("📍 Адрес", callback_data=f"edit_field:{object_id}:address")
        ],
        [
            InlineKeyboardButton("💰 Часовая ставка", callback_data=f"edit_field:{object_id}:hourly_rate"),
            InlineKeyboardButton("📏 Макс. расстояние", callback_data=f"edit_field:{object_id}:max_distance_meters")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
             f"💰 <b>Часовая ставка:</b> {obj_data['hourly_rate']}₽\n"
             f"📏 <b>Максимальное расстояние:</b> {max_distance}м\n\n"
             f"Выберите поле для редактирования:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, field_name: str):
    """Обработчик редактирования конкретного поля."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Определяем название поля и подсказку
    field_names = {
        'name': 'название объекта',
        'address': 'адрес объекта',
        'hourly_rate': 'часовую ставку (в рублях)',
        'max_distance_meters': 'максимальное расстояние (в метрах, от 10 до 5000)'
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Создаем состояние пользователя для редактирования
    user_state_manager.create_state(
        user_id=user_id,
        action=UserAction.EDIT_OBJECT,
        step=UserStep.INPUT_FIELD_VALUE,
        selected_object_id=object_id,
        data={'field_name': field_name}
    )
    
    await query.edit_message_text(
        text=f"✏️ <b>Редактирование поля</b>\n\n"
             f"Введите новое значение для поля <b>{field_display}</b>:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_object:{object_id}")
        ]])
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Обработка отмены
    if text == "❌ Отмена":
        await handle_cancel(update, context)
        return
    
    # Проверяем состояние пользователя для обработки диалогов создания объекта
    if user_id in user_object_creation_state:
        await handle_create_object_input(update, context)
        return
    
    # Проверяем состояние пользователя для редактирования объектов
    user_state = user_state_manager.get_state(user_id)
    if user_state and user_state.action == UserAction.EDIT_OBJECT:
        await _handle_edit_object_input(update, context, user_state)
        return
    
    # Проверяем состояние пользователя для планирования смен
    if user_state and user_state.action == UserAction.SCHEDULE_SHIFT:
        if user_state.step in [UserStep.INPUT_START_TIME, UserStep.INPUT_END_TIME]:
            await handle_schedule_time_input(update, context)
            return
        elif user_state.step == UserStep.INPUT_DATE:
            await handle_custom_date_input(update, context)
            return
    
    # Если нет активного состояния, отправляем в главное меню
    await update.message.reply_text(
        "🤖 Используйте команды или кнопки для взаимодействия с ботом.\n"
        "Отправьте /start для главного меню."
    )


async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик отмены действия."""
    user_id = update.effective_user.id
    
    # Очищаем состояние пользователя
    user_state_manager.clear_state(user_id)
    
    # Убираем клавиатуру
    from telegram import ReplyKeyboardRemove
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )


async def _handle_edit_object_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state):
    """Обработчик ввода нового значения для поля объекта."""
    user_id = update.effective_user.id
    text = update.message.text
    object_id = user_state.selected_object_id
    field_name = user_state.data.get('field_name')
    
    if not field_name:
        await update.message.reply_text("❌ Ошибка: не удалось определить редактируемое поле.")
        user_state_manager.clear_state(user_id)
        return
    
    # Обновляем поле объекта
    result = object_service.update_object_field(object_id, field_name, text, user_id)
    
    # Очищаем состояние пользователя
    user_state_manager.clear_state(user_id)
    
    if result['success']:
        # Отображаем успешное обновление и возвращаемся к редактированию объекта
        await update.message.reply_text(
            f"✅ {result['message']}\n\nНовое значение: <b>{result['new_value']}</b>",
            parse_mode='HTML'
        )
        
        # Показываем обновленную информацию об объекте
        await _show_updated_object_info(update, context, object_id)
    else:
        # Показываем ошибку и возвращаемся к редактированию
        await update.message.reply_text(
            f"❌ {result['error']}\n\nПопробуйте ещё раз или вернитесь к редактированию объекта.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К редактированию", callback_data=f"edit_object:{object_id}"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )


async def _show_updated_object_info(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Показывает обновленную информацию об объекте."""
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await update.message.reply_text(
            "❌ Объект не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Теперь max_distance_meters уже есть в obj_data
    max_distance = obj_data.get('max_distance_meters', 500)
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Название", callback_data=f"edit_field:{object_id}:name"),
            InlineKeyboardButton("📍 Адрес", callback_data=f"edit_field:{object_id}:address")
        ],
        [
            InlineKeyboardButton("💰 Часовая ставка", callback_data=f"edit_field:{object_id}:hourly_rate"),
            InlineKeyboardButton("📏 Макс. расстояние", callback_data=f"edit_field:{object_id}:max_distance_meters")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
             f"💰 <b>Часовая ставка:</b> {obj_data['hourly_rate']}₽\n"
             f"📏 <b>Максимальное расстояние:</b> {max_distance}м\n\n"
             f"Выберите поле для редактирования:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_retry_location_open(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик повторной отправки геопозиции для открытия смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Создаем состояние для открытия смены
    user_state_manager.create_state(
        user_id=user_id,
        action=UserAction.OPEN_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_object_id=object_id
    )
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    max_distance = obj_data.get('max_distance_meters', 500)
    
    # Показываем сообщение с кнопкой для отправки геопозиции
    await query.edit_message_text(
        text=f"📍 <b>Отправьте геопозицию для открытия смены</b>\n\n"
             f"🏢 Объект: <b>{obj_data['name']}</b>\n"
             f"📍 Адрес: {obj_data['address'] or 'не указан'}\n"
             f"📏 Максимальное расстояние: {max_distance}м\n\n"
             f"Нажмите кнопку ниже для отправки вашего местоположения:",
        parse_mode='HTML',
        reply_markup=get_location_keyboard()
    )


async def _handle_retry_location_close(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int):
    """Обработчик повторной отправки геопозиции для закрытия смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Создаем состояние для закрытия смены
    user_state_manager.create_state(
        user_id=user_id,
        action=UserAction.CLOSE_SHIFT,
        step=UserStep.LOCATION_REQUEST,
        selected_shift_id=shift_id
    )
    
    # Получаем информацию о смене
    shift_data = shift_service.get_shift_by_id(shift_id)
    if not shift_data:
        await query.edit_message_text(
            text="❌ Смена не найдена.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(shift_data['object_id'])
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    max_distance = obj_data.get('max_distance_meters', 500)
    
    # Форматируем время начала смены
    from core.utils.timezone_helper import timezone_helper
    user_timezone = timezone_helper.get_user_timezone(user_id)
    local_start_time = timezone_helper.format_local_time(shift_data['start_time'], user_timezone)
    
    # Показываем сообщение с кнопкой для отправки геопозиции
    await query.edit_message_text(
        text=f"📍 <b>Отправьте геопозицию для закрытия смены</b>\n\n"
             f"🏢 Объект: <b>{obj_data['name']}</b>\n"
             f"📍 Адрес: {obj_data['address'] or 'не указан'}\n"
             f"🕐 Начало смены: {local_start_time}\n"
             f"📏 Максимальное расстояние: {max_distance}м\n\n"
             f"Нажмите кнопку ниже для отправки вашего местоположения:",
        parse_mode='HTML',
        reply_markup=get_location_keyboard()
    )

