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
    
    # Всегда показываем кнопку "Мои задачи" (без проверки наличия задач)
    
    # Создаем кнопки для основных действий
    keyboard = [
        [
            InlineKeyboardButton("🏢 Открыть объект", callback_data="open_object"),
            InlineKeyboardButton("🔒 Закрыть объект", callback_data="close_object")
        ],
        [
            InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
            InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
        ],
        [
            InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift"),
            InlineKeyboardButton("📋 Мои планы", callback_data="view_schedule")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="get_report"),
            InlineKeyboardButton("📝 Мои задачи", callback_data="my_tasks")
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
    
    logger.info(
        f"Location received from user",
        user_id=user_id,
        latitude=location.latitude,
        longitude=location.longitude
    )
    
    # Получаем состояние пользователя
    user_state = user_state_manager.get_state(user_id)
    if not user_state:
        logger.warning(f"No state found for user {user_id} when processing location")
        await update.message.reply_text(
            "❌ Сначала выберите действие (открыть или закрыть смену)"
        )
        return
    
    logger.info(
        f"User state retrieved",
        user_id=user_id,
        action=user_state.action,
        step=user_state.step
    )
    
    if user_state.step not in [UserStep.LOCATION_REQUEST, UserStep.OPENING_OBJECT_LOCATION, UserStep.CLOSING_OBJECT_LOCATION]:
        logger.warning(
            f"Location not expected at this step",
            user_id=user_id,
            current_step=user_state.step,
            expected_steps=[UserStep.LOCATION_REQUEST, UserStep.OPENING_OBJECT_LOCATION, UserStep.CLOSING_OBJECT_LOCATION]
        )
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
            shift_type = getattr(user_state, 'shift_type', 'spontaneous')
            timeslot_id = getattr(user_state, 'selected_timeslot_id', None)
            schedule_id = getattr(user_state, 'selected_schedule_id', None)
            
            logger.info(f"Opening shift with params: shift_type={shift_type}, timeslot_id={timeslot_id}, schedule_id={schedule_id}")
            
            result = await shift_service.open_shift(
                user_id=user_id,
                object_id=user_state.selected_object_id,
                coordinates=coordinates,
                shift_type=shift_type,
                timeslot_id=timeslot_id,
                schedule_id=schedule_id
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
                
                # Очищаем состояние ТОЛЬКО при успехе
                user_state_manager.clear_state(user_id)
                
            else:
                error_msg = f"❌ Ошибка при открытии смены: {result['error']}"
                if 'distance_meters' in result:
                    error_msg += f"\n📏 Расстояние: {result['distance_meters']:.0f}м"
                    error_msg += f"\n📐 Максимум: {result.get('max_distance_meters', 100)}м"
                
                # Добавляем кнопки для повторной отправки или отмены
                keyboard = [
                    [InlineKeyboardButton("📍 Отправить геопозицию повторно", callback_data=f"retry_location:{user_state.selected_object_id}")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(error_msg, reply_markup=reply_markup)
                # НЕ очищаем состояние - пользователь может попробовать снова
                            
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
                
                # Phase 4A: Сохраняем информацию о выполненных задачах в БД
                shift_tasks = getattr(user_state, 'shift_tasks', [])
                completed_tasks = getattr(user_state, 'completed_tasks', [])
                task_media = getattr(user_state, 'task_media', {})
                
                if shift_tasks:
                    # Сохраняем выполнение задач в shift.notes для Celery
                    async with get_async_session() as session:
                        from domain.entities.shift import Shift
                        import json
                        
                        shift_query = select(Shift).where(Shift.id == user_state.selected_shift_id)
                        shift_result = await session.execute(shift_query)
                        shift_obj = shift_result.scalar_one_or_none()
                        
                        if shift_obj:
                            # Добавляем JSON с completed_tasks и task_media в notes
                            completed_info = json.dumps({
                                'completed_tasks': completed_tasks,
                                'task_media': task_media
                            })
                            shift_obj.notes = (shift_obj.notes or '') + f"\n[TASKS]{completed_info}"
                            await session.commit()
                            
                            logger.info(
                                f"Saved completed tasks info",
                                shift_id=shift_obj.id,
                                completed_count=len(completed_tasks),
                                total_count=len(shift_tasks),
                                media_count=len(task_media)
                            )
                
                # Отладочный вывод
                logger.info(
                    f"Close shift result for user {user_id}: result={result}, "
                    f"total_hours={total_hours}, total_payment={total_payment}"
                )
                
                # Убираем клавиатуру
                from telegram import ReplyKeyboardRemove
                shift_close_message = (
                    f"✅ Смена успешно закрыта!\n"
                    f"⏱️ Отработано: {total_hours:.1f} часов\n"
                    f"💰 Заработано: {total_payment}₽"
                )
                
                await update.message.reply_text(shift_close_message, reply_markup=ReplyKeyboardRemove())
                
                # Проверяем: была ли это последняя смена на объекте?
                # Если да - автоматически закрываем объект
                from shared.services.object_opening_service import ObjectOpeningService
                from domain.entities.user import User
                
                # Получаем object_id из закрытой смены
                closed_shift_object_id = result.get('object_id')
                
                logger.info(
                    f"Checking for auto-close object",
                    user_id=user_id,
                    shift_id=result.get('shift_id'),
                    object_id=closed_shift_object_id,
                    result_keys=list(result.keys())
                )
                
                if closed_shift_object_id:
                    async with get_async_session() as session:
                        opening_service = ObjectOpeningService(session)
                        
                        # Проверяем: есть ли еще активные смены на этом объекте?
                        active_count = await opening_service.get_active_shifts_count(closed_shift_object_id)
                        
                        if active_count == 0:
                            # Это была последняя смена - закрываем объект
                            # Получить пользователя по telegram_id
                            user_query = select(User).where(User.telegram_id == user_id)
                            user_result = await session.execute(user_query)
                            db_user = user_result.scalar_one_or_none()
                            
                            if db_user:
                                try:
                                    opening = await opening_service.close_object(
                                        object_id=closed_shift_object_id,
                                        user_id=db_user.id,
                                        coordinates=coordinates
                                    )
                                    
                                    # Форматируем время с учетом часового пояса
                                    from core.utils.timezone_helper import timezone_helper
                                    # Получаем объект для timezone
                                    obj_query = select(Object).where(Object.id == closed_shift_object_id)
                                    obj_result = await session.execute(obj_query)
                                    obj = obj_result.scalar_one_or_none()
                                    
                                    object_timezone = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                                    close_time = timezone_helper.format_local_time(opening.closed_at, object_timezone, '%H:%M')
                                    
                                    await update.message.reply_text(
                                        f"✅ <b>Объект автоматически закрыт!</b>\n\n"
                                        f"(Это была последняя активная смена)\n\n"
                                        f"⏰ Время закрытия: {close_time}\n"
                                        f"⏱️ Время работы объекта: {opening.duration_hours:.1f}ч",
                                        parse_mode='HTML'
                                    )
                                    
                                    logger.info(
                                        f"Object auto-closed after last shift closed",
                                        object_id=closed_shift_object_id,
                                        user_id=user_id,
                                        shift_id=user_state.selected_shift_id
                                    )
                                except ValueError as e:
                                    logger.warning(
                                        f"Failed to auto-close object",
                                        object_id=closed_shift_object_id,
                                        error=str(e)
                                    )
                                    await update.message.reply_text(
                                        f"⚠️ Не удалось автоматически закрыть объект: {str(e)}\n"
                                        f"Используйте кнопку 'Закрыть объект' для закрытия вручную."
                                    )
                
                # Очищаем состояние ТОЛЬКО при успехе
                user_state_manager.clear_state(user_id)
                
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
                # НЕ очищаем состояние - пользователь может попробовать снова
        
        elif user_state.action == UserAction.OPEN_OBJECT:
            # Открытие объекта + автоматическое открытие смены
            from shared.services.object_opening_service import ObjectOpeningService
            from core.geolocation.location_validator import LocationValidator
            from domain.entities.user import User
            
            async with get_async_session() as session:
                opening_service = ObjectOpeningService(session)
                location_validator = LocationValidator()
                
                # Получить пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    await update.message.reply_text("❌ Пользователь не найден.")
                    user_state_manager.clear_state(user_id)
                    return
                
                # Получить объект
                obj_query = select(Object).where(Object.id == user_state.selected_object_id)
                obj_result = await session.execute(obj_query)
                obj = obj_result.scalar_one_or_none()
                
                if not obj:
                    await update.message.reply_text("❌ Объект не найден.")
                    user_state_manager.clear_state(user_id)
                    return
                
                # Проверить расстояние
                validation_result = location_validator.validate_shift_location(
                    user_coordinates=coordinates,
                    object_coordinates=obj.coordinates,
                    max_distance_meters=obj.max_distance_meters
                )
                
                if not validation_result['valid']:
                    await update.message.reply_text(
                        f"❌ Вы слишком далеко от объекта!\n"
                        f"📏 Расстояние: {validation_result['distance_meters']:.0f}м\n"
                        f"📐 Максимум: {validation_result['max_distance_meters']}м"
                    )
                    return
                
                # Открыть объект
                try:
                    opening = await opening_service.open_object(
                        object_id=obj.id,
                        user_id=db_user.id,  # Используем внутренний ID, а не telegram_id
                        coordinates=coordinates
                    )
                    
                    # Проверяем: есть ли запланированная смена на сегодня на этом объекте?
                    from apps.bot.services.shift_schedule_service import ShiftScheduleService
                    from datetime import date
                    
                    shift_schedule_service = ShiftScheduleService()
                    today = date.today()
                    planned_shifts = await shift_schedule_service.get_user_planned_shifts_for_date(user_id, today)
                    
                    # Ищем смену для текущего объекта
                    schedule_for_object = None
                    for shift_data in planned_shifts:
                        if shift_data.get('object_id') == obj.id:
                            schedule_for_object = shift_data
                            break
                    
                    # Определяем параметры для открытия смены
                    if schedule_for_object:
                        # Есть запланированная смена - открываем её
                        result = await shift_service.open_shift(
                            user_id=user_id,
                            object_id=obj.id,
                            coordinates=coordinates,
                            shift_type='planned',
                            timeslot_id=schedule_for_object.get('time_slot_id'),
                            schedule_id=schedule_for_object.get('id')
                        )
                    else:
                        # Нет запланированной смены - открываем спонтанную
                        result = await shift_service.open_shift(
                            user_id=user_id,
                            object_id=obj.id,
                            coordinates=coordinates,
                            shift_type='spontaneous'
                        )
                    
                    if result['success']:
                        # Форматируем время с учетом часового пояса объекта
                        from core.utils.timezone_helper import timezone_helper
                        object_timezone = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                        local_time = timezone_helper.format_local_time(opening.opened_at, object_timezone, '%H:%M')
                        
                        await update.message.reply_text(
                            f"✅ <b>Объект открыт!</b>\n\n"
                            f"🏢 Объект: {obj.name}\n"
                            f"⏰ Время: {local_time}\n\n"
                            f"✅ <b>Смена автоматически открыта</b>\n"
                            f"💰 Ставка: {result.get('hourly_rate', 0)}₽/час",
                            parse_mode='HTML'
                        )
                        user_state_manager.clear_state(user_id)
                    else:
                        # Откатываем открытие объекта
                        await opening_service.close_object(obj.id, db_user.id, coordinates)
                        await update.message.reply_text(
                            f"❌ Объект открыт, но не удалось открыть смену:\n{result['error']}"
                        )
                        user_state_manager.clear_state(user_id)
                        
                except ValueError as e:
                    await update.message.reply_text(f"❌ {str(e)}")
                    user_state_manager.clear_state(user_id)
        
        elif user_state.action == UserAction.CLOSE_OBJECT:
            # Закрытие объекта - СНАЧАЛА закрываем смену, ПОТОМ объект
            from shared.services.object_opening_service import ObjectOpeningService
            from domain.entities.user import User
            
            # Если step=TASK_COMPLETION, значит были задачи - сохраняем их в shift.notes
            if user_state.step == UserStep.TASK_COMPLETION:
                completed_tasks = user_state.completed_tasks or []
                task_media = user_state.task_media or {}
                
                # Обновляем shift.notes с информацией о выполненных задачах
                async with get_async_session() as session:
                    from domain.entities.shift import Shift
                    shift_query = select(Shift).where(Shift.id == user_state.selected_shift_id)
                    shift_result = await session.execute(shift_query)
                    shift = shift_result.scalar_one_or_none()
                    
                    if shift:
                        import json
                        shift.notes = json.dumps({
                            'completed_tasks': completed_tasks,
                            'task_media': task_media
                        }, ensure_ascii=False)
                        await session.commit()
            
            # 1. Закрыть смену
            result = await shift_service.close_shift(
                user_id=user_id,
                shift_id=user_state.selected_shift_id,
                coordinates=coordinates
            )
            
            if not result['success']:
                await update.message.reply_text(
                    f"❌ Ошибка при закрытии смены: {result.get('error', 'Неизвестная ошибка')}"
                )
                user_state_manager.clear_state(user_id)
                return
            
            # 2. Закрыть объект
            async with get_async_session() as session:
                opening_service = ObjectOpeningService(session)
                
                # Получить пользователя по telegram_id
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = await session.execute(user_query)
                db_user = user_result.scalar_one_or_none()
                
                if not db_user:
                    await update.message.reply_text("❌ Пользователь не найден.")
                    user_state_manager.clear_state(user_id)
                    return
                
                try:
                    opening = await opening_service.close_object(
                        object_id=user_state.selected_object_id,
                        user_id=db_user.id,
                        coordinates=coordinates
                    )
                    
                    # Форматируем время с учетом часового пояса
                    from core.utils.timezone_helper import timezone_helper
                    close_time = timezone_helper.format_local_time(opening.closed_at, 'Europe/Moscow', '%H:%M')
                    
                    await update.message.reply_text(
                        f"✅ <b>Смена и объект закрыты!</b>\n\n"
                        f"⏱️ Время смены: {result.get('total_hours', 0):.1f}ч\n"
                        f"💰 Оплата: {result.get('total_payment', 0):.0f}₽\n"
                        f"⏰ Объект закрыт в: {close_time}\n"
                        f"⏱️ Время работы объекта: {opening.duration_hours:.1f}ч",
                        parse_mode='HTML'
                    )
                    user_state_manager.clear_state(user_id)
                    
                except ValueError as e:
                    await update.message.reply_text(f"❌ {str(e)}")
                    user_state_manager.clear_state(user_id)
        
        else:
            logger.warning(
                f"No handler for action/step combination",
                user_id=user_id,
                action=user_state.action,
                step=user_state.step
            )
            await update.message.reply_text(
                "❌ Непредвиденная ситуация. Попробуйте начать с /start"
            )
            user_state_manager.clear_state(user_id)
    
    except Exception as e:
        logger.error(f"Error processing location for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке геопозиции. Попробуйте еще раз."
        )
        # НЕ очищаем состояние при ошибке - пользователь может попробовать снова


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
    if query.data == "open_object":
        from .object_state_handlers import _handle_open_object
        await _handle_open_object(update, context)
        return
    elif query.data == "close_object":
        from .object_state_handlers import _handle_close_object
        await _handle_close_object(update, context)
        return
    elif query.data.startswith("select_object_to_open:"):
        from .object_state_handlers import _handle_select_object_to_open
        await _handle_select_object_to_open(update, context)
        return
    elif query.data == "open_shift":
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
    # Задачи на смену (Phase 4A: восстановлено)
    elif query.data.startswith("complete_shift_task:"):
        from .shift_handlers import _handle_complete_shift_task
        parts = query.data.split(":", 2)
        shift_id = int(parts[1])
        task_idx = int(parts[2])
        await _handle_complete_shift_task(update, context, shift_id, task_idx)
        return
    elif query.data.startswith("close_shift_with_tasks:"):
        from .shift_handlers import _handle_close_shift_with_tasks
        shift_id = int(query.data.split(":", 1)[1])
        await _handle_close_shift_with_tasks(update, context, shift_id)
        return
    elif query.data.startswith("cancel_media_upload:"):
        # Отмена загрузки медиа - возврат к списку задач
        shift_id = int(query.data.split(":", 1)[1])
        user_state = user_state_manager.get_state(user_id)
        if user_state:
            user_state_manager.update_state(user_id, step=UserStep.TASK_COMPLETION, pending_media_task_idx=None)
            shift_tasks = getattr(user_state, 'shift_tasks', [])
            completed_tasks = getattr(user_state, 'completed_tasks', [])
            task_media = getattr(user_state, 'task_media', {})
            from .shift_handlers import _show_task_list
            await _show_task_list(context, user_id, shift_id, shift_tasks, completed_tasks, task_media)
        return
    # Мои задачи (во время смены)
    elif query.data == "my_tasks":
        from .shift_handlers import _handle_my_tasks
        await _handle_my_tasks(update, context)
        return
    elif query.data.startswith("complete_my_task:"):
        from .shift_handlers import _handle_complete_my_task
        parts = query.data.split(":", 2)
        shift_id = int(parts[1])
        task_idx = int(parts[2])
        await _handle_complete_my_task(update, context, shift_id, task_idx)
        return
    elif query.data.startswith("cancel_my_task_media:"):
        shift_id = int(query.data.split(":", 1)[1])
        user_state = user_state_manager.get_state(user_id)
        if user_state:
            user_state_manager.update_state(user_id, step=UserStep.TASK_COMPLETION, pending_media_task_idx=None)
            shift_tasks = getattr(user_state, 'shift_tasks', [])
            completed_tasks = getattr(user_state, 'completed_tasks', [])
            task_media = getattr(user_state, 'task_media', {})
            from .shift_handlers import _show_my_tasks_list
            await _show_my_tasks_list(context, user_id, shift_id, shift_tasks, completed_tasks, task_media)
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
        # Отчет по заработку: запускаем новый обработчик
        from .earnings_report_handlers import EarningsReportHandlers
        earnings_handler = EarningsReportHandlers()
        await earnings_handler.start_earnings_report(update, context)
        return
    elif query.data.startswith("week_") or query.data == "custom_dates" or query.data == "cancel_report":
        # Обработка выбора недели для отчета
        from .earnings_report_handlers import EarningsReportHandlers
        earnings_handler = EarningsReportHandlers()
        await earnings_handler.handle_week_selection(update, context)
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
            InlineKeyboardButton("🏢 Открыть объект", callback_data="open_object"),
            InlineKeyboardButton("🔒 Закрыть объект", callback_data="close_object")
        ],
        [
            InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
            InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
        ],
        [
            InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift"),
            InlineKeyboardButton("📋 Мои планы", callback_data="view_schedule")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="get_report"),
            InlineKeyboardButton("📝 Мои задачи", callback_data="my_tasks")
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
