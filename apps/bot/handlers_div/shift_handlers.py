"""Обработчики для управления сменами."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from core.logging.logger import logger
from core.auth.user_manager import user_manager
from apps.bot.services.shift_service import ShiftService
from apps.bot.services.object_service import ObjectService
from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.object import Object
from domain.entities.shift import Shift
from sqlalchemy import select
from core.state import user_state_manager, UserAction, UserStep
# from .utils import get_location_keyboard  # Удалено, создаем клавиатуру прямо в коде

# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()


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
    
    # Ищем запланированные смены пользователя на сегодня
    try:
        from apps.bot.services.shift_schedule_service import ShiftScheduleService
        from datetime import date
        
        shift_schedule_service = ShiftScheduleService()
        today = date.today()
        
        # Получаем запланированные смены на сегодня
        planned_shifts = await shift_schedule_service.get_user_planned_shifts_for_date(user_id, today)
        
        if planned_shifts:
            # Есть запланированные смены - показываем их для выбора
            user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_SHIFT,
                step=UserStep.SHIFT_SELECTION
            )
            
            # Создаем кнопки для выбора запланированной смены
            keyboard = []
            for shift in planned_shifts:
                # Получаем часовой пояс объекта
                object_timezone = shift.get('object_timezone', 'Europe/Moscow')
                
                # Конвертируем время в часовой пояс объекта
                from core.utils.timezone_helper import timezone_helper
                local_start_time = timezone_helper.utc_to_local(shift['planned_start'], object_timezone)
                local_end_time = timezone_helper.utc_to_local(shift['planned_end'], object_timezone)
                
                start_time = local_start_time.strftime("%H:%M")
                end_time = local_end_time.strftime("%H:%M")
                keyboard.append([
                    InlineKeyboardButton(
                        f"📅 {shift['object_name']} {start_time}-{end_time}", 
                        callback_data=f"open_planned_shift:{shift['id']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="📅 <b>Запланированные смены на сегодня</b>\n\nВыберите смену для открытия:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            # Нет запланированных смен - показываем выбор объекта для спонтанной смены
            from apps.bot.services.employee_objects_service import EmployeeObjectsService
            
            employee_objects_service = EmployeeObjectsService()
            objects = await employee_objects_service.get_employee_objects(user_id)
            
            if not objects:
                await query.edit_message_text(
                    text="❌ <b>Нет доступных объектов</b>\n\nУ вас должен быть активный договор с владельцем объекта.",
                    parse_mode='HTML'
                )
                return
                
            # Создаем состояние пользователя
            user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_SHIFT,
                step=UserStep.OBJECT_SELECTION,
                shift_type="spontaneous"
            )
            
            # Создаем кнопки для выбора объекта
            keyboard = []
            for obj in objects:
                # Показываем количество договоров для объекта
                contracts_count = len(obj.get('contracts', []))
                contracts_info = f" ({contracts_count} договор)" if contracts_count > 1 else ""
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏢 {obj['name']}{contracts_info}", 
                        callback_data=f"open_shift_object:{obj['id']}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text="⚡ <b>Внеплановая смена</b>\n\nУ вас нет запланированных смен на сегодня.\nВыберите объект для открытия спонтанной смены:",
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
        
        # Если одна активная смена - переходим сразу к геопозиции
        # Phase 4A: Задачи теперь обрабатываются при закрытии смены из object.shift_tasks (JSONB)
        if len(active_shifts) == 1:
            shift = active_shifts[0]  # Это словарь, а не объект
            
            # Переходим к геопозиции
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
                
                # Конвертируем время начала смены в часовой пояс объекта
                from datetime import datetime
                try:
                    # Парсим строку времени из БД (формат: 'YYYY-MM-DD HH:MM:SS')
                    start_time_utc = datetime.strptime(shift['start_time'], '%Y-%m-%d %H:%M:%S')
                    # Используем часовой пояс объекта, если он есть
                    object_timezone = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                    local_start_time = timezone_helper.format_local_time(start_time_utc, object_timezone)
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
                    reply_markup=ReplyKeyboardMarkup(
                        [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
                        resize_keyboard=True,
                        one_time_keyboard=True
                    )
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
    
    # Проверяем доступ к объекту
    try:
        from apps.bot.services.employee_objects_service import EmployeeObjectsService
        
        employee_objects_service = EmployeeObjectsService()
        
        # Проверяем, есть ли у пользователя доступ к объекту
        has_access = await employee_objects_service.has_access_to_object(user_id, object_id)
        if not has_access:
            await query.edit_message_text(
                text="❌ <b>Доступ запрещен</b>\n\nУ вас нет активного договора с этим объектом.",
                parse_mode='HTML'
            )
            user_state_manager.clear_state(user_id)
            return
        
        # Получаем информацию об объекте
        logger.info(f"Getting object data for user_id={user_id}, object_id={object_id}")
        obj_data = await employee_objects_service.get_employee_object_by_id(user_id, object_id)
        logger.info(f"Object data: {obj_data}")
        if not obj_data:
            logger.warning(f"No object data found for user_id={user_id}, object_id={object_id}")
            await query.edit_message_text(
                text="❌ Объект не найден или недоступен.",
                parse_mode='HTML'
            )
            user_state_manager.clear_state(user_id)
            return
        
        # Проверяем, есть ли свободные тайм-слоты на сегодня для этого объекта
        from apps.bot.services.timeslot_service import TimeSlotService
        from datetime import date, datetime
        
        timeslot_service = TimeSlotService()
        today = date.today()
        
        # Получаем доступные тайм-слоты на сегодня
        free_timeslots = await timeslot_service.get_available_timeslots_for_object(obj_data['id'], today)
        
        hourly_rate = obj_data['hourly_rate']  # По умолчанию ставка объекта
        timeslot_info = ""
        
        if free_timeslots:
            # Есть свободные тайм-слоты - берем ставку из первого (самого раннего)
            first_timeslot = free_timeslots[0]
            hourly_rate = first_timeslot.get('hourly_rate', obj_data['hourly_rate'])
            
            # Формируем информацию о доступных тайм-слотах
            timeslot_count = len(free_timeslots)
            timeslot_info = f"\n📅 <b>Доступно тайм-слотов:</b> {timeslot_count}\n"
            
            logger.info(f"Found {timeslot_count} free timeslots for object {obj_data['id']} on {today}, using hourly_rate: {hourly_rate}")
        
        # Обновляем состояние - сохраняем выбранный объект и переходим к запросу геолокации
        user_state_manager.update_state(
            user_id=user_id,
            selected_object_id=object_id,
            step=UserStep.LOCATION_REQUEST,
            shift_type="spontaneous"
        )
        
        # Запрашиваем геопозицию для спонтанной смены
        await query.edit_message_text(
            text=f"⚡ <b>Внеплановая смена</b>\n\n"
                 f"🏢 <b>Объект:</b> {obj_data['name']}\n"
                 f"💰 <b>Часовая ставка:</b> {hourly_rate}₽{timeslot_info}\n\n"
                 f"📍 <b>Отправьте геопозицию</b>",
            parse_mode='HTML'
        )
        
        # Отправляем сообщение с клавиатурой для геопозиции
        location_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Используйте кнопку для отправки геопозиции:",
            reply_markup=location_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error handling object selection for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при обработке выбора объекта. Попробуйте позже.",
            parse_mode='HTML'
        )
        user_state_manager.clear_state(user_id)


async def _handle_open_planned_shift(update: Update, context: ContextTypes.DEFAULT_TYPE, schedule_id: int):
    """Обработчик выбора запланированной смены для открытия."""
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
    
    try:
        # Получаем информацию о запланированной смене
        from apps.bot.services.shift_schedule_service import ShiftScheduleService
        shift_schedule_service = ShiftScheduleService()
        
        logger.info(f"Getting shift schedule data for schedule_id: {schedule_id}")
        shift_data = await shift_schedule_service.get_shift_schedule_by_id(schedule_id)
        logger.info(f"Received shift_data: {shift_data}")
        if not shift_data:
            logger.warning(f"Shift schedule data not found for schedule_id: {schedule_id}")
            await query.edit_message_text(
                text="❌ Запланированная смена не найдена или недоступна.",
                parse_mode='HTML'
            )
            return
        
        # Обновляем состояние
        user_state_manager.update_state(
            user_id=user_id,
            selected_object_id=shift_data['object_id'],
            step=UserStep.LOCATION_REQUEST,
            shift_type="planned",
            selected_timeslot_id=shift_data.get('time_slot_id'),
            selected_schedule_id=schedule_id
        )
        
        # Форматируем время
        start_time = shift_data['planned_start'].strftime("%H:%M")
        end_time = shift_data['planned_end'].strftime("%H:%M")
        planned_date = shift_data['planned_start'].strftime("%d.%m.%Y")
        
        # Запрашиваем геопозицию
        await query.edit_message_text(
            text=f"📅 <b>Запланированная смена</b>\n\n"
                 f"🏢 <b>Объект:</b> {shift_data['object_name']}\n"
                 f"📅 <b>Дата:</b> {planned_date}\n"
                 f"🕐 <b>Время:</b> {start_time}-{end_time}\n\n"
                 f"📍 <b>Отправьте геопозицию</b>",
            parse_mode='HTML'
        )
        
        # Отправляем сообщение с клавиатурой для геопозиции
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Используйте кнопку для отправки геопозиции:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting planned shift {schedule_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при получении данных запланированной смены. Попробуйте позже.",
            parse_mode='HTML'
        )


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
            
            # Конвертируем время начала смены в часовой пояс объекта
            object_timezone = getattr(obj, 'timezone', None) or 'Europe/Moscow'
            local_start_time = timezone_helper.format_local_time(shift.start_time, object_timezone)
            
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
                reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            )
            
    except Exception as e:
        logger.error(f"Error handling close shift selection for user {user_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при обработке выбора смены. Попробуйте позже.",
            parse_mode='HTML'
        )
        user_state_manager.clear_state(user_id)


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
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
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
    
    # Форматируем время начала смены в часовой пояс объекта
    from core.utils.timezone_helper import timezone_helper
    object_timezone = obj_data.get('timezone', 'Europe/Moscow')
    local_start_time = timezone_helper.format_local_time(shift_data['start_time'], object_timezone)
    
    # Показываем сообщение с кнопкой для отправки геопозиции
    await query.edit_message_text(
        text=f"📍 <b>Отправьте геопозицию для закрытия смены</b>\n\n"
             f"🏢 Объект: <b>{obj_data['name']}</b>\n"
             f"📍 Адрес: {obj_data['address'] or 'не указан'}\n"
             f"🕐 Начало смены: {local_start_time}\n"
             f"📏 Максимальное расстояние: {max_distance}м\n\n"
             f"Нажмите кнопку ниже для отправки вашего местоположения:",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )


# Phase 4A: Функция _handle_complete_task удалена
# Задачи теперь обрабатываются автоматически при закрытии смены из object.shift_tasks (JSONB)


# Phase 4A: Функция _handle_close_shift_proceed удалена
# Задачи обрабатываются автоматически при закрытии смены


