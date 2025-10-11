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
        
        # Если одна активная смена - проверяем задачи
        if len(active_shifts) == 1:
            shift = active_shifts[0]  # Это словарь, а не объект
            
            # Получаем информацию об объекте и его задачах
            async with get_async_session() as session:
                obj_query = select(Object).where(Object.id == shift['object_id'])
                obj_result = await session.execute(obj_query)
                obj = obj_result.scalar_one_or_none()
                
                if not obj:
                    await query.edit_message_text(
                        text="❌ Объект смены не найден.",
                        parse_mode='HTML'
                    )
                    return
                
                # Получаем задачи из object.shift_tasks (JSONB)
                shift_tasks = list(obj.shift_tasks or [])
                
                # Добавляем маркер источника для задач объекта
                for task in shift_tasks:
                    if 'source' not in task:
                        task['source'] = 'object'
                
                # Если смена привязана к тайм-слоту, добавляем его задачи
                if shift.get('time_slot_id'):
                    from domain.entities.time_slot import TimeSlot
                    from domain.entities.timeslot_task_template import TimeslotTaskTemplate
                    from sqlalchemy.orm import selectinload
                    
                    timeslot_query = select(TimeSlot).options(
                        selectinload(TimeSlot.task_templates)
                    ).where(TimeSlot.id == shift['time_slot_id'])
                    timeslot_result = await session.execute(timeslot_query)
                    timeslot = timeslot_result.scalar_one_or_none()
                    
                    if timeslot and timeslot.task_templates:
                        # Преобразуем TimeslotTaskTemplate в формат shift_tasks
                        for task_template in timeslot.task_templates:
                            media_types_list = task_template.media_types.split(',') if task_template.media_types else ['photo', 'video']
                            shift_tasks.append({
                                'text': task_template.task_text,
                                'is_mandatory': task_template.is_mandatory,
                                'deduction_amount': float(task_template.deduction_amount) if task_template.deduction_amount else 0,
                                'requires_media': task_template.requires_media,
                                'media_types': media_types_list,
                                'source': 'timeslot',
                                'timeslot_task_id': task_template.id
                            })
                        
                        logger.info(
                            f"Combined tasks from object and timeslot",
                            shift_id=shift['id'],
                            object_tasks=len(obj.shift_tasks or []),
                            timeslot_tasks=len(timeslot.task_templates)
                        )
                
                # Если есть задачи - показываем их для подтверждения выполнения
                if shift_tasks:
                    # Формируем текст с задачами
                    tasks_text = "📋 <b>Задачи на смену:</b>\n\n"
                    tasks_text += "Отметьте выполненные задачи:\n\n"
                    
                    for idx, task in enumerate(shift_tasks):
                        task_text = task.get('text') or task.get('task_text', 'Задача')
                        is_mandatory = task.get('is_mandatory', True)
                        deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
                        requires_media = task.get('requires_media', False)
                        
                        # Иконки
                        mandatory_icon = "⚠️" if is_mandatory else "⭐"
                        media_icon = "📸 " if requires_media else ""
                        
                        # Стоимость
                        cost_text = ""
                        if deduction_amount and float(deduction_amount) != 0:
                            amount = float(deduction_amount)
                            if amount > 0:
                                cost_text = f" (+{amount}₽)"
                            else:
                                cost_text = f" ({amount}₽)"
                        
                        tasks_text += f"{media_icon}{mandatory_icon} {task_text}{cost_text}\n"
                    
                    # Создаем состояние со списком задач
                    user_state_manager.create_state(
                        user_id=user_id,
                        action=UserAction.CLOSE_SHIFT,
                        step=UserStep.TASK_COMPLETION,  # Новый шаг
                        selected_shift_id=shift['id'],
                        shift_tasks=shift_tasks,  # Сохраняем задачи
                        completed_tasks=[]  # Изначально пусто
                    )
                    
                    # Формируем кнопки для задач
                    keyboard = []
                    for idx, task in enumerate(shift_tasks):
                        task_text = task.get('text') or task.get('task_text', 'Задача')
                        is_mandatory = task.get('is_mandatory', True)
                        requires_media = task.get('requires_media', False)
                        
                        icon = "⚠️" if is_mandatory else "⭐"
                        media_icon = "📸 " if requires_media else ""
                        keyboard.append([
                            InlineKeyboardButton(
                                f"✓ {media_icon}{icon} {task_text[:30]}...",
                                callback_data=f"complete_shift_task:{shift['id']}:{idx}"
                            )
                        ])
                    
                    # Кнопка продолжить
                    keyboard.append([
                        InlineKeyboardButton(
                            "✅ Продолжить закрытие смены",
                            callback_data=f"close_shift_with_tasks:{shift['id']}"
                        )
                    ])
                    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])
                    
                    await query.edit_message_text(
                        text=tasks_text,
                        parse_mode='HTML',
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
            
            # Нет задач - переходим сразу к геопозиции
            # Создаем состояние пользователя
            user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.CLOSE_SHIFT,
                step=UserStep.LOCATION_REQUEST,
                selected_shift_id=shift['id'],
                completed_tasks=[]  # Пустой список
            )
            
            # Получаем информацию об объекте смены
            async with get_async_session() as session:
                obj_query = select(Object).where(Object.id == shift['object_id'])
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


async def _handle_complete_shift_task(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int, task_idx: int):
    """Обработчик отметки задачи смены как выполненной."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Получаем состояние
        user_state = user_state_manager.get_state(user_id)
        if not user_state or user_state.step != UserStep.TASK_COMPLETION:
            await query.answer("❌ Состояние утеряно. Начните заново", show_alert=True)
            return
        
        # Получаем задачи из состояния
        shift_tasks = getattr(user_state, 'shift_tasks', [])
        completed_tasks = getattr(user_state, 'completed_tasks', [])
        
        # Проверяем индекс
        if task_idx >= len(shift_tasks):
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Получаем информацию о задаче
        current_task = shift_tasks[task_idx]
        requires_media = current_task.get('requires_media', False)
        task_media = getattr(user_state, 'task_media', {})
        
        logger.info(f"Task toggle: idx={task_idx}, requires_media={requires_media}, completed={task_idx in completed_tasks}")
        
        # Переключаем статус
        if task_idx in completed_tasks:
            # Снимаем отметку
            completed_tasks.remove(task_idx)
            # Удаляем медиа, если было
            if task_idx in task_media:
                del task_media[task_idx]
            status_msg = "Задача снята с отметки"
            user_state_manager.update_state(user_id, completed_tasks=completed_tasks, task_media=task_media)
        else:
            # Проверяем, требуется ли медиа
            if requires_media:
                logger.info(f"Task requires media, calling _handle_media_upload")
                # Переходим к загрузке медиа
                await _handle_media_upload(update, context, shift_id, task_idx)
                return
            else:
                # Простая отметка без медиа
                completed_tasks.append(task_idx)
                status_msg = "✅ Задача отмечена"
                user_state_manager.update_state(user_id, completed_tasks=completed_tasks)
        
        # Формируем обновленный текст
        tasks_text = "📋 <b>Задачи на смену:</b>\n\n"
        tasks_text += "Отметьте выполненные задачи:\n\n"
        
        for idx, task in enumerate(shift_tasks):
            task_text = task.get('text') or task.get('task_text', 'Задача')
            is_mandatory = task.get('is_mandatory', True)
            deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
            requires_media = task.get('requires_media', False)
            
            # Иконки
            mandatory_icon = "⚠️" if is_mandatory else "⭐"
            completed_icon = "✅ " if idx in completed_tasks else ""
            media_icon = "📸 " if requires_media else ""
            
            # Стоимость
            cost_text = ""
            if deduction_amount and float(deduction_amount) != 0:
                amount = float(deduction_amount)
                if amount > 0:
                    cost_text = f" (+{amount}₽)"
                else:
                    cost_text = f" ({amount}₽)"
            
            task_line = f"{completed_icon}{media_icon}{mandatory_icon} {task_text}{cost_text}"
            if idx in completed_tasks:
                task_line = f"<s>{task_line}</s>"
            tasks_text += task_line + "\n"
        
        # Формируем кнопки
        keyboard = []
        for idx, task in enumerate(shift_tasks):
            task_text = task.get('text') or task.get('task_text', 'Задача')
            is_mandatory = task.get('is_mandatory', True)
            requires_media = task.get('requires_media', False)
            
            icon = "⚠️" if is_mandatory else "⭐"
            media_icon = "📸 " if requires_media else ""
            check = "✓ " if idx in completed_tasks else "☐ "
            keyboard.append([
                InlineKeyboardButton(
                    f"{check}{media_icon}{icon} {task_text[:30]}...",
                    callback_data=f"complete_shift_task:{shift_id}:{idx}"
                )
            ])
        
        # Кнопка продолжить
        keyboard.append([
            InlineKeyboardButton(
                "✅ Продолжить закрытие смены",
                callback_data=f"close_shift_with_tasks:{shift_id}"
            )
        ])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])
        
        await query.edit_message_text(
            text=tasks_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await query.answer(status_msg)
        
    except Exception as e:
        logger.error(f"Error toggling task: {e}")
        await query.answer("❌ Ошибка отметки задачи", show_alert=True)


async def _handle_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int, task_idx: int):
    """Запрос на загрузку медиа для задачи."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        user_state = user_state_manager.get_state(user_id)
        if not user_state:
            await query.answer("❌ Состояние утеряно", show_alert=True)
            return
        
        # Получаем telegram_report_chat_id ЗАРАНЕЕ (до изменения состояния)
        async with get_async_session() as session:
            from domain.entities.shift import Shift
            from domain.entities.object import Object
            from sqlalchemy.orm import selectinload
            
            shift_query = select(Shift).options(
                selectinload(Shift.object).selectinload(Object.org_unit)
            ).where(Shift.id == shift_id)
            shift_result = await session.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            
            if not shift or not shift.object:
                await query.answer("❌ Смена не найдена", show_alert=True)
                return
            
            # Наследование telegram_report_chat_id
            telegram_chat_id = None
            obj = shift.object
            
            if not obj.inherit_telegram_chat and obj.telegram_report_chat_id:
                telegram_chat_id = obj.telegram_report_chat_id
            elif obj.org_unit:
                org_unit = obj.org_unit
                while org_unit:
                    if org_unit.telegram_report_chat_id:
                        telegram_chat_id = org_unit.telegram_report_chat_id
                        break
                    org_unit = org_unit.parent
            
            if not telegram_chat_id:
                await query.edit_message_text(
                    text="❌ Telegram группа для отчетов не настроена.\n\n"
                         "Обратитесь к администратору для настройки группы в объекте или подразделении.",
                    parse_mode='HTML'
                )
                return
        
        # Обновляем состояние (ПОСЛЕ получения данных из БД)
        user_state_manager.update_state(
            user_id,
            step=UserStep.MEDIA_UPLOAD,
            pending_media_task_idx=task_idx,
            data={'telegram_chat_id': telegram_chat_id, 'object_name': obj.name}
        )
        
        shift_tasks = getattr(user_state, 'shift_tasks', [])
        task = shift_tasks[task_idx]
        task_text = task.get('text') or task.get('task_text', 'Задача')
        
        media_types = task.get('media_types', ['photo', 'video'])
        if isinstance(media_types, str):
            media_types = media_types.split(',')
        
        media_text = "фото" if media_types == ["photo"] else "видео" if media_types == ["video"] else "фото или видео"
        
        await query.edit_message_text(
            text=f"📸 <b>Требуется отчет</b>\n\n"
                 f"Задача: <i>{task_text}</i>\n\n"
                 f"📷 Отправьте {media_text} отчет о выполнении задачи.\n\n"
                 f"⚠️ <b>Важно:</b> отправьте медиа БЕЗ использования команд /start или других кнопок, иначе состояние потеряется!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_media_upload:{shift_id}")
            ]])
        )
        
    except Exception as e:
        logger.error(f"Error handling media upload: {e}")
        await query.answer("❌ Ошибка запроса медиа", show_alert=True)


async def _handle_close_shift_with_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int):
    """Обработчик продолжения закрытия смены с задачами."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Получаем состояние
        user_state = user_state_manager.get_state(user_id)
        if not user_state:
            await query.answer("❌ Состояние утеряно. Начните заново", show_alert=True)
            return
        
        # Обновляем шаг на запрос геопозиции
        user_state_manager.update_state(user_id, step=UserStep.LOCATION_REQUEST)
        
        # Получаем информацию об объекте смены
        async with get_async_session() as session:
            from domain.entities.shift import Shift
            
            shift_query = select(Shift).where(Shift.id == shift_id)
            shift_result = await session.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            
            if not shift:
                await query.answer("❌ Смена не найдена", show_alert=True)
                return
            
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
        logger.error(f"Error proceeding with tasks: {e}")
        await query.answer("❌ Ошибка продолжения", show_alert=True)


async def _handle_received_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного фото/видео для задачи."""
    logger.info(f"_handle_received_media CALLED")
    
    # Игнорируем, если это не личное сообщение
    if update.message.chat.type != 'private':
        logger.info(f"Ignoring media from non-private chat: {update.message.chat.type}")
        return
    
    user_id = update.message.from_user.id
    logger.info(f"Media received from user: {user_id}")
    
    user_state = user_state_manager.get_state(user_id)
    logger.info(f"User state: {user_state}, step: {user_state.step if user_state else None}")
    
    if not user_state or user_state.step != UserStep.MEDIA_UPLOAD:
        # Подсказка если состояние потеряно
        logger.info(f"Media received but no valid state: user_id={user_id}, state={user_state}, step={user_state.step if user_state else None}")
        await update.message.reply_text(
            "ℹ️ Фото/видео получено, но не в контексте отчета.\n\n"
            "Для отправки отчета:\n"
            "1. Закройте смену\n"
            "2. Нажмите на задачу с 📸\n"
            "3. Отправьте фото БЕЗ использования /start"
        )
        return
    
    task_idx = getattr(user_state, 'pending_media_task_idx', None)
    logger.info(f"pending_media_task_idx: {task_idx}")
    
    if task_idx is None:
        logger.warning(f"pending_media_task_idx is None, ignoring media")
        await update.message.reply_text("⚠️ Не удалось определить задачу. Попробуйте снова.")
        return
    
    shift_tasks = getattr(user_state, 'shift_tasks', [])
    logger.info(f"shift_tasks count: {len(shift_tasks)}, task_idx: {task_idx}")
    
    if task_idx >= len(shift_tasks):
        logger.error(f"task_idx {task_idx} >= shift_tasks length {len(shift_tasks)}")
        await update.message.reply_text("❌ Задача не найдена")
        return
    
    task = shift_tasks[task_idx]
    shift_id = user_state.selected_shift_id
    
    try:
        # Определяем тип медиа
        media_type = None
        media_file_id = None
        if update.message.photo:
            media_type = 'photo'
            media_file_id = update.message.photo[-1].file_id
        elif update.message.video:
            media_type = 'video'
            media_file_id = update.message.video.file_id
        else:
            await update.message.reply_text("❌ Неподдерживаемый тип файла. Отправьте фото или видео.")
            return
        
        logger.info(f"Media type: {media_type}, file_id: {media_file_id}")
        
        # Получаем telegram_chat_id и object_name из state.data (сохранены в _handle_media_upload)
        telegram_chat_id = user_state.data.get('telegram_chat_id')
        object_name = user_state.data.get('object_name', 'Объект')
        
        if not telegram_chat_id:
            logger.error(f"telegram_chat_id not found in state.data")
            await update.message.reply_text(
                "❌ Ошибка: группа не настроена.\n"
                "Попробуйте снова."
            )
            return
        
        logger.info(f"Sending media to Telegram group: {telegram_chat_id}")
        
        # Отправляем медиа в группу (БЕЗ вложенной сессии БД!)
        try:
            task_text = task.get('text') or task.get('task_text', 'Задача')
            user_name = f"{update.message.from_user.first_name} {update.message.from_user.last_name or ''}".strip()
            caption = f"📋 Отчет по задаче: {task_text}\n👤 {user_name}\n🏢 {object_name}"
            
            sent_message = None
            if media_type == 'photo':
                sent_message = await context.bot.send_photo(
                    chat_id=telegram_chat_id,
                    photo=media_file_id,
                    caption=caption
                )
            elif media_type == 'video':
                sent_message = await context.bot.send_video(
                    chat_id=telegram_chat_id,
                    video=media_file_id,
                    caption=caption
                )
            
            logger.info(f"Media sent to group, message_id: {sent_message.message_id}")
            
            # Формируем ссылку на пост
            # Формат: https://t.me/c/{chat_id без -100}/{message_id}
            chat_id_str = str(telegram_chat_id).replace('-100', '')
            media_url = f"https://t.me/c/{chat_id_str}/{sent_message.message_id}"
            
            # Сохраняем медиа в состоянии
            task_media = getattr(user_state, 'task_media', {})
            task_media[task_idx] = {
                'media_url': media_url,
                'media_type': media_type
            }
            
            # Отмечаем задачу как выполненную
            completed_tasks = getattr(user_state, 'completed_tasks', [])
            if task_idx not in completed_tasks:
                completed_tasks.append(task_idx)
            
            # Обновляем состояние
            user_state_manager.update_state(
                user_id,
                step=UserStep.TASK_COMPLETION,
                completed_tasks=completed_tasks,
                task_media=task_media,
                pending_media_task_idx=None
            )
            
            logger.info(
                f"Media uploaded for task",
                shift_id=shift_id,
                task_idx=task_idx,
                media_type=media_type,
                telegram_group=telegram_chat_id,
                media_url=media_url
            )
            
            # Отправляем подтверждение
            await update.message.reply_text(
                f"✅ <b>Отчет принят!</b>\n\n"
                f"📋 Задача: <i>{task_text}</i>\n"
                f"✅ Отмечена как выполненная\n"
                f"📤 Отправлено в группу отчетов",
                parse_mode='HTML'
            )
            
            # Возвращаемся к списку задач
            await _show_task_list(context, user_id, shift_id, shift_tasks, completed_tasks, task_media)
            
        except Exception as e:
            logger.error(f"Error sending media to Telegram group: {e}")
            await update.message.reply_text(
                "❌ Ошибка отправки отчета в группу.\n"
                "Проверьте, что бот добавлен в группу и имеет права на отправку медиа."
            )
                
    except Exception as e:
        logger.error(f"Error in _handle_received_media: {e}")
        await update.message.reply_text("❌ Ошибка обработки медиа")


async def _show_task_list(context, user_id: int, shift_id: int, shift_tasks: list, completed_tasks: list, task_media: dict):
    """Показать обновленный список задач."""
    tasks_text = "📋 <b>Задачи на смену:</b>\n\n"
    tasks_text += "Отметьте выполненные задачи:\n\n"
    
    for idx, task in enumerate(shift_tasks):
        task_text = task.get('text') or task.get('task_text', 'Задача')
        is_mandatory = task.get('is_mandatory', True)
        deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
        requires_media = task.get('requires_media', False)
        
        # Иконки
        mandatory_icon = "⚠️" if is_mandatory else "⭐"
        completed_icon = "✅ " if idx in completed_tasks else ""
        media_icon = "📸 " if requires_media else ""
        
        # Стоимость
        cost_text = ""
        if deduction_amount and float(deduction_amount) != 0:
            amount = float(deduction_amount)
            if amount > 0:
                cost_text = f" (+{amount}₽)"
            else:
                cost_text = f" ({amount}₽)"
        
        task_line = f"{completed_icon}{media_icon}{mandatory_icon} {task_text}{cost_text}"
        if idx in completed_tasks:
            task_line = f"<s>{task_line}</s>"
        tasks_text += task_line + "\n"
    
    # Формируем кнопки
    keyboard = []
    for idx, task in enumerate(shift_tasks):
        task_text = task.get('text') or task.get('task_text', 'Задача')
        is_mandatory = task.get('is_mandatory', True)
        requires_media = task.get('requires_media', False)
        
        icon = "⚠️" if is_mandatory else "⭐"
        media_icon = "📸 " if requires_media else ""
        check = "✓ " if idx in completed_tasks else "☐ "
        keyboard.append([
            InlineKeyboardButton(
                f"{check}{media_icon}{icon} {task_text[:30]}...",
                callback_data=f"complete_shift_task:{shift_id}:{idx}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            "✅ Продолжить закрытие смены",
            callback_data=f"close_shift_with_tasks:{shift_id}"
        )
    ])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=tasks_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


