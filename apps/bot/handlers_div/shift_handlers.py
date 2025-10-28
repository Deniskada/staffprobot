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
from domain.entities.time_slot import TimeSlot
from domain.entities.timeslot_task_template import TimeslotTaskTemplate
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from core.state import user_state_manager, UserAction, UserStep
from typing import List, Dict, Optional
# from .utils import get_location_keyboard  # Удалено, создаем клавиатуру прямо в коде

# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()


async def _load_timeslot_tasks(session: AsyncSession, timeslot: TimeSlot) -> list:
    """
    Загружает задачи тайм-слота из таблицы timeslot_task_templates.
    
    Args:
        session: Асинхронная сессия БД
        timeslot: Объект тайм-слота
    
    Returns:
        Список задач в формате [{'text': str, 'is_mandatory': bool, 'deduction_amount': int, 'source': 'timeslot'}]
    """
    tasks = []
    
    # Загружаем задачи из таблицы timeslot_task_templates
    template_query = select(TimeslotTaskTemplate).where(
        TimeslotTaskTemplate.timeslot_id == timeslot.id
    ).order_by(TimeslotTaskTemplate.display_order)
    template_result = await session.execute(template_query)
    templates = template_result.scalars().all()
    
    for template in templates:
        tasks.append({
            'text': template.task_text,
            'is_mandatory': template.is_mandatory if template.is_mandatory is not None else False,
            'deduction_amount': float(template.deduction_amount) if template.deduction_amount else 0,
            'requires_media': template.requires_media if template.requires_media is not None else False,
            'source': 'timeslot'
        })
    
    logger.info(
        f"Loaded {len(tasks)} timeslot tasks from table",
        timeslot_id=timeslot.id
    )
    
    return tasks


async def _collect_shift_tasks(
    session: AsyncSession,
    shift: Shift,
    timeslot: Optional[TimeSlot] = None,
    object_: Optional[Object] = None
) -> List[Dict]:
    """
    Собрать ВСЕ задачи смены из TaskEntryV2 (новая система) + legacy источников.
    
    Единая функция для загрузки задач везде вместо дублирования кода.
    
    Args:
        session: Асинхронная сессия БД
        shift: Смена для которой собираем задачи
        timeslot: TimeSlot (для legacy задач из TimeslotTaskTemplate)
        object_: Object (для legacy задач из shift_tasks JSONB)
    
    Returns:
        Список задач с метаданными: [{'text', 'is_mandatory', 'deduction_amount', 'requires_media', 'source', 'entry_id'}, ...]
    
    Logic:
        1. Загружаем TaskEntryV2 по shift.id (УНИВЕРСАЛЬНО для запланированных И спонтанных смен!)
        2. Если есть timeslot → загружаем из TimeslotTaskTemplate (legacy)
        3. Если есть object и не ignore_object_tasks → добавляем из object.shift_tasks (legacy)
    """
    all_tasks = []
    
    # НОВОЕ: Универсальная загрузка TaskEntryV2 по shift.id (работает для ВСЕХ смен!)
    try:
        from shared.services.task_service import TaskService
        task_service = TaskService(session)
        task_entries = await task_service.get_entries_for_shift(shift.id)
        
        for entry in task_entries:
            template = entry.template
            if template:
                all_tasks.append({
                    'text': template.title,
                    'description': template.description,
                    'is_mandatory': template.is_mandatory,
                    'deduction_amount': float(template.default_bonus_amount) if template.default_bonus_amount else 0,
                    'requires_media': template.requires_media,
                    'source': 'task_v2',
                    'entry_id': entry.id,
                    'is_completed': entry.is_completed,
                    'completion_notes': entry.completion_notes,
                    'completion_media': entry.completion_media or []
                })
        
        logger.info(
            f"Loaded {len(task_entries)} TaskEntryV2 for shift {shift.id} "
            f"(planned={bool(shift.schedule_id)})"
        )
    except Exception as e:
        logger.error(f"Error loading TaskEntryV2 for shift {shift.id}: {e}", exc_info=True)
    
    # LEGACY: Вариант 1 - Запланированная смена (с timeslot)
    if timeslot:
        # Загружаем задачи из TimeslotTaskTemplate
        timeslot_tasks = await _load_timeslot_tasks(session, timeslot)
        all_tasks.extend(timeslot_tasks)
        
        # Добавляем задачи объекта (если не игнорируются)
        if not timeslot.ignore_object_tasks and object_ and object_.shift_tasks:
            for task in object_.shift_tasks:
                task_copy = dict(task)
                task_copy['source'] = 'object'
                all_tasks.append(task_copy)
    else:
        # LEGACY: Вариант 2 - Спонтанная смена (без timeslot) - только задачи объекта
        if object_ and object_.shift_tasks:
            for task in object_.shift_tasks:
                task_copy = dict(task)
                task_copy['source'] = 'object'
                all_tasks.append(task_copy)
    
    logger.debug(
        f"Collected all shift tasks",
        shift_id=shift.id,
        schedule_id=shift.schedule_id,
        timeslot_id=timeslot.id if timeslot else None,
        object_id=object_.id if object_ else None,
        total_tasks=len(all_tasks),
        task_v2_count=len([t for t in all_tasks if t.get('source') == 'task_v2']),
        timeslot_tasks=len([t for t in all_tasks if t.get('source') == 'timeslot']),
        object_tasks=len([t for t in all_tasks if t.get('source') == 'object'])
    )
    
    return all_tasks


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
            logger.info(f"Creating user state for open_shift: user_id={user_id}")
            await user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_SHIFT,
                step=UserStep.SHIFT_SELECTION
            )
            logger.info(f"User state created successfully")
            
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
            
            logger.info(f"Sending planned shifts menu to user {user_id}")
            await query.edit_message_text(
                text="📅 <b>Запланированные смены на сегодня</b>\n\nВыберите смену для открытия:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            logger.info(f"Menu sent successfully")
        else:
            # Нет запланированных смен - проверяем открытые объекты для спонтанной смены
            from apps.bot.services.employee_objects_service import EmployeeObjectsService
            from shared.services.object_opening_service import ObjectOpeningService
            
            employee_objects_service = EmployeeObjectsService()
            objects = await employee_objects_service.get_employee_objects(user_id)
            
            if not objects:
                await query.edit_message_text(
                    text="❌ <b>Нет доступных объектов</b>\n\nУ вас должен быть активный договор с владельцем объекта.",
                    parse_mode='HTML'
                )
                return
            
            # Проверяем: есть ли среди них открытые?
            async with get_async_session() as session:
                opening_service = ObjectOpeningService(session)
                open_objects = []
                
                for obj in objects:
                    is_open = await opening_service.is_object_open(obj['id'])
                    if is_open:
                        open_objects.append(obj)
            
            if not open_objects:
                # Нет открытых объектов - предлагаем сначала открыть объект
                await query.edit_message_text(
                    text="⚠️ <b>Нет открытых объектов</b>\n\n"
                         "Для открытия спонтанной смены сначала откройте объект.\n\n"
                         "Используйте кнопку 'Открыть объект' в главном меню.",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏢 Открыть объект", callback_data="open_object")
                    ]])
                )
                return
            
            # Показываем только открытые объекты
            objects = open_objects
                
            # Создаем состояние пользователя
            await user_state_manager.create_state(
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


async def _handle_open_planned_shift(update: Update, context: ContextTypes.DEFAULT_TYPE, schedule_id: int):
    """Обработчик открытия запланированной смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Получаем информацию о запланированной смене
        from apps.bot.services.shift_schedule_service import ShiftScheduleService
        shift_schedule_service = ShiftScheduleService()
        schedule_data = await shift_schedule_service.get_shift_schedule_by_id(schedule_id)
        
        if not schedule_data:
            await query.edit_message_text(
                text="❌ Запланированная смена не найдена.",
                parse_mode='HTML'
            )
            return
        
        object_id = schedule_data.get('object_id')
        
        # Проверяем: объект открыт?
        async with get_async_session() as session:
            from shared.services.object_opening_service import ObjectOpeningService
            opening_service = ObjectOpeningService(session)
            is_open = await opening_service.is_object_open(object_id)
        
        if not is_open:
            # Объект закрыт - предлагаем сначала открыть объект
            await query.edit_message_text(
                text="⚠️ <b>Объект закрыт</b>\n\n"
                     "Для открытия запланированной смены сначала откройте объект.\n\n"
                     "Используйте кнопку 'Открыть объект' в главном меню.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏢 Открыть объект", callback_data="open_object")
                ]])
            )
            return
        
        # Объект открыт - продолжаем открытие смены
        # Создаем состояние для запроса геолокации
        await user_state_manager.create_state(
            user_id=user_id,
            action=UserAction.OPEN_SHIFT,
            step=UserStep.LOCATION_REQUEST,
            selected_object_id=object_id,
            shift_type="planned",
            selected_schedule_id=schedule_id,
            selected_timeslot_id=schedule_data.get('time_slot_id')
        )
        
        # Запрашиваем геолокацию
        object_name = schedule_data.get('object_name', 'Неизвестный объект')
        planned_start_str = schedule_data.get('planned_start_str', '')
        
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        location_keyboard = [
            [KeyboardButton("📍 Отправить геопозицию", request_location=True)]
        ]
        location_markup = ReplyKeyboardMarkup(
            location_keyboard, 
            one_time_keyboard=True, 
            resize_keyboard=True
        )
        
        await query.edit_message_text(
            text=f"📍 <b>Отправьте геопозицию для открытия смены</b>\n\n"
                 f"🏢 Объект: <b>{object_name}</b>\n"
                 f"🕐 Время: {planned_start_str}\n\n"
                 f"Нажмите кнопку ниже для отправки вашего местоположения:",
            parse_mode='HTML'
        )
        
        # Отправляем клавиатуру в отдельном сообщении
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Используйте кнопку ниже:",
            reply_markup=location_markup
        )
        
    except Exception as e:
        logger.error(f"Error opening planned shift {schedule_id}: {e}")
        await query.edit_message_text(
            text="❌ Ошибка при открытии смены. Попробуйте позже.",
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
            
            # Проверяем наличие object_id
            if not shift.get('object_id'):
                logger.error(f"Shift {shift.get('id')} has no object_id")
                await query.edit_message_text(
                    text="❌ Смена не привязана к объекту. Обратитесь к администратору.",
                    parse_mode='HTML'
                )
                return
            
            # Получаем информацию об объекте и его задачах
            async with get_async_session() as session:
                from sqlalchemy.orm import selectinload
                from domain.entities.org_structure import OrgStructureUnit
                
                # Загружаем объект с org_unit и всей цепочкой родителей
                def load_org_hierarchy():
                    loader = selectinload(Object.org_unit)
                    # Загружаем до 10 уровней иерархии (достаточно)
                    current = loader
                    for _ in range(10):
                        current = current.selectinload(OrgStructureUnit.parent)
                    return loader
                
                obj_query = select(Object).options(
                    load_org_hierarchy()
                ).where(Object.id == shift['object_id'])
                obj_result = await session.execute(obj_query)
                obj = obj_result.scalar_one_or_none()
                
                if not obj:
                    await query.edit_message_text(
                        text="❌ Объект смены не найден.",
                        parse_mode='HTML'
                    )
                    return
                
                # Загружаем объект Shift из БД для использования _collect_shift_tasks
                logger.info(f"[CLOSE_SHIFT] Loading Shift object from DB: shift_id={shift.get('id')}")
                shift_query = select(Shift).options(
                    selectinload(Shift.time_slot),
                    selectinload(Shift.object)
                ).where(Shift.id == shift['id'])
                shift_result = await session.execute(shift_query)
                shift_obj = shift_result.scalar_one_or_none()
                
                if not shift_obj:
                    logger.error(f"[CLOSE_SHIFT] Shift object not found: {shift['id']}")
                    await query.edit_message_text("❌ Смена не найдена в БД", parse_mode='HTML')
                    return
                
                # Используем _collect_shift_tasks для унифицированной загрузки
                logger.info(f"[CLOSE_SHIFT] Calling _collect_shift_tasks for shift {shift_obj.id}")
                shift_tasks = await _collect_shift_tasks(
                    session=session,
                    shift=shift_obj,
                    timeslot=shift_obj.time_slot,
                    object_=shift_obj.object
                )
                logger.info(f"[CLOSE_SHIFT] Loaded {len(shift_tasks)} total tasks via _collect_shift_tasks")
                
                # Если есть задачи - показываем их для подтверждения выполнения
                if shift_tasks:
                    # Получаем telegram_report_chat_id для медиа отчетов (наследование)
                    telegram_chat_id = None
                    if not obj.inherit_telegram_chat and obj.telegram_report_chat_id:
                        telegram_chat_id = obj.telegram_report_chat_id
                    elif obj.org_unit:
                        org_unit = obj.org_unit
                        while org_unit:
                            if org_unit.telegram_report_chat_id:
                                telegram_chat_id = org_unit.telegram_report_chat_id
                                break
                            org_unit = org_unit.parent
                    
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
                    
                    # Создаем или обновляем состояние со списком задач
                    # Проверяем существующий state (может быть CLOSE_OBJECT)
                    existing_state = await user_state_manager.get_state(user_id)
                    action = existing_state.action if existing_state else UserAction.CLOSE_SHIFT
                    selected_object_id = existing_state.selected_object_id if existing_state else None
                    
                    # Если уже есть state для этой смены - сохраняем completed_tasks, НО обновляем shift_tasks
                    if existing_state and existing_state.selected_shift_id == shift['id'] and existing_state.shift_tasks:
                        # Обновляем задачи (могли измениться), сохраняя completed_tasks
                        await user_state_manager.update_state(
                            user_id=user_id,
                            action=action,
                            step=UserStep.TASK_COMPLETION,
                            shift_tasks=shift_tasks,  # КРИТИЧНО: обновляем задачи свежими из БД!
                            data={'telegram_chat_id': telegram_chat_id, 'object_name': obj.name}  # Обновляем данные для медиа
                        )
                    else:
                        # Создаем новый state
                        await user_state_manager.create_state(
                            user_id=user_id,
                            action=action,  # Сохраняем исходный action
                            step=UserStep.TASK_COMPLETION,
                            selected_shift_id=shift['id'],
                            selected_object_id=selected_object_id,  # Сохраняем object_id если был
                            shift_tasks=shift_tasks,
                            completed_tasks=[],
                            data={'telegram_chat_id': telegram_chat_id, 'object_name': obj.name}
                        )
                    
                    # Формируем кнопки для задач
                    keyboard = []
                    # Получаем completed_tasks из existing_state
                    completed_tasks = existing_state.completed_tasks if (existing_state and existing_state.selected_shift_id == shift['id']) else []
                    
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
            # Проверяем существующий state (может быть CLOSE_OBJECT)
            existing_state = await user_state_manager.get_state(user_id)
            action = existing_state.action if existing_state else UserAction.CLOSE_SHIFT
            selected_object_id = existing_state.selected_object_id if existing_state else None
            
            await user_state_manager.create_state(
                user_id=user_id,
                action=action,  # Сохраняем исходный action
                step=UserStep.LOCATION_REQUEST,
                selected_shift_id=shift['id'],
                selected_object_id=selected_object_id,  # Сохраняем object_id если был
                completed_tasks=[]
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
                    await user_state_manager.clear_state(user_id)
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
    user_state = await user_state_manager.get_state(user_id)
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
            await user_state_manager.clear_state(user_id)
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
            await user_state_manager.clear_state(user_id)
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
        await user_state_manager.update_state(
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
        await user_state_manager.clear_state(user_id)


async def _handle_open_planned_shift(update: Update, context: ContextTypes.DEFAULT_TYPE, schedule_id: int):
    """Обработчик выбора запланированной смены для открытия."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем состояние пользователя
    user_state = await user_state_manager.get_state(user_id)
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
        await user_state_manager.update_state(
            user_id=user_id,
            selected_object_id=shift_data['object_id'],
            step=UserStep.LOCATION_REQUEST,
            shift_type="planned",
            selected_timeslot_id=shift_data.get('time_slot_id'),
            selected_schedule_id=schedule_id
        )
        
        # Форматируем время с учетом временной зоны объекта
        from core.utils.timezone_helper import timezone_helper
        object_timezone = shift_data.get('object_timezone', 'Europe/Moscow')
        
        start_time_local = timezone_helper.format_local_time(shift_data['planned_start'], object_timezone)
        end_time_local = timezone_helper.format_local_time(shift_data['planned_end'], object_timezone)
        planned_date = shift_data['planned_start'].strftime("%d.%m.%Y")
        
        # Запрашиваем геопозицию
        await query.edit_message_text(
            text=f"📅 <b>Запланированная смена</b>\n\n"
                 f"🏢 <b>Объект:</b> {shift_data['object_name']}\n"
                 f"📅 <b>Дата:</b> {planned_date}\n"
                 f"🕐 <b>Время:</b> {start_time_local}-{end_time_local}\n\n"
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
    await user_state_manager.create_state(
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
            await user_state_manager.clear_state(user_id)
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
                await user_state_manager.clear_state(user_id)
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
        await user_state_manager.clear_state(user_id)


async def _handle_retry_location_open(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик повторной отправки геопозиции для открытия смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Создаем состояние для открытия смены
    await user_state_manager.create_state(
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
    await user_state_manager.create_state(
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
        user_state = await user_state_manager.get_state(user_id)
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
            await user_state_manager.update_state(user_id, completed_tasks=completed_tasks, task_media=task_media)
            
            # Записать в журнал (снятие отметки)
            try:
                from core.database.session import get_async_session
                from shared.services.shift_task_journal import ShiftTaskJournal
                async with get_async_session() as db:
                    journal = ShiftTaskJournal(db)
                    await journal.mark_by_index(shift_id, task_idx, False, user_id)
            except Exception as e:
                logger.error(f"Error updating task journal (uncomplete): {e}")
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
                await user_state_manager.update_state(user_id, completed_tasks=completed_tasks)
                
                # Записать в журнал
                try:
                    from core.database.session import get_async_session
                    from shared.services.shift_task_journal import ShiftTaskJournal
                    async with get_async_session() as db:
                        journal = ShiftTaskJournal(db)
                        await journal.mark_by_index(shift_id, task_idx, True, user_id)
                except Exception as e:
                    logger.error(f"Error updating task journal (complete): {e}")
        
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
        user_state = await user_state_manager.get_state(user_id)
        if not user_state:
            await query.answer("❌ Состояние утеряно", show_alert=True)
            return
        
        # Проверяем наличие telegram_chat_id (уже получен в _handle_close_shift)
        telegram_chat_id = user_state.data.get('telegram_chat_id')
        
        if not telegram_chat_id:
            await query.edit_message_text(
                text="❌ Telegram группа для отчетов не настроена.\n\n"
                     "Обратитесь к администратору для настройки группы в объекте или подразделении.",
                parse_mode='HTML'
            )
            return
        
        # Обновляем состояние
        await user_state_manager.update_state(
            user_id,
            step=UserStep.MEDIA_UPLOAD,
            pending_media_task_idx=task_idx
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
        user_state = await user_state_manager.get_state(user_id)
        if not user_state:
            await query.answer("❌ Состояние утеряно. Начните заново", show_alert=True)
            return
        
        # Обновляем шаг на запрос геопозиции и действие на CLOSE_SHIFT, чтобы handle_location обработал закрытие
        await user_state_manager.update_state(user_id, action=UserAction.CLOSE_SHIFT, step=UserStep.LOCATION_REQUEST)
        
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
                await user_state_manager.clear_state(user_id)
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
    
    user_state = await user_state_manager.get_state(user_id)
    logger.info(f"User state: {user_state}, step: {user_state.step if user_state else None}")
    
    # ПРИОРИТЕТ 1: Tasks v2 медиа (САМЫЙ ВЫСОКИЙ!)
    if user_state and user_state.step == UserStep.TASK_V2_MEDIA_UPLOAD:
        await _handle_received_task_v2_media(update, context)
        return
    
    # ПРИОРИТЕТ 2: Отмена смены
    if user_state and user_state.action == UserAction.CANCEL_SCHEDULE and user_state.step == UserStep.INPUT_PHOTO:
        from .schedule_handlers import handle_cancellation_photo_upload
        await handle_cancellation_photo_upload(update, context)
        return
    
    # ПРИОРИТЕТ 3: Игнорируем медиа, если пользователь уже завершил загрузку
    if user_state and user_state.step == UserStep.TASK_COMPLETION:
        logger.info(f"Ignoring media - user already completed task upload: user_id={user_id}")
        return
    
    # ПРИОРИТЕТ 4: Legacy MEDIA_UPLOAD
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
            # Формат: https://t.me/c/{chat_id без -100 и минуса}/{message_id}
            chat_id_str = str(telegram_chat_id)
            # Убираем -100 для супергрупп, или просто - для обычных групп
            if chat_id_str.startswith('-100'):
                chat_id_str = chat_id_str[4:]  # Убираем -100
            elif chat_id_str.startswith('-'):
                chat_id_str = chat_id_str[1:]  # Убираем -
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
            await user_state_manager.update_state(
                user_id,
                step=UserStep.TASK_COMPLETION,
                completed_tasks=completed_tasks,
                task_media=task_media,
                pending_media_task_idx=None
            )
            
            # Записать в журнал задач
            try:
                from core.database.session import get_async_session
                from shared.services.shift_task_journal import ShiftTaskJournal
                async with get_async_session() as db:
                    journal = ShiftTaskJournal(db)
                    await journal.mark_by_index(
                        shift_id=shift_id,
                        task_idx=task_idx,
                        is_completed=True,
                        user_id=user_id,
                        media_meta={
                            'media_url': media_url,
                            'media_type': media_type,
                            'file_id': media_file_id
                        }
                    )
            except Exception as e:
                logger.error(f"Error updating task journal (media): {e}")
            
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
            
            # Возвращаемся к списку задач (выбираем функцию в зависимости от action)
            if user_state.action == UserAction.MY_TASKS:
                await _show_my_tasks_list(context, user_id, shift_id, shift_tasks, completed_tasks, task_media)
            else:
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
        # Для Tasks v2 используем отдельный callback с entry_id
        if task.get('source') == 'task_v2' and task.get('entry_id'):
            callback_data = f"complete_task_v2:{task['entry_id']}"
        else:
            # Legacy задачи - по индексу
            callback_data = f"complete_shift_task:{shift_id}:{idx}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{check}{media_icon}{icon} {task_text[:30]}...",
                callback_data=callback_data
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


async def _handle_my_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать задачи активной смены без закрытия смены."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Получаем информацию о смене
        async with get_async_session() as session:
            from domain.entities.user import User
            from domain.entities.time_slot import TimeSlot
            
            # Получаем внутренний user_id
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            db_user = user_result.scalar_one_or_none()
            
            if not db_user:
                await query.edit_message_text(
                    text="❌ Пользователь не найден.",
                    parse_mode='HTML'
                )
                return
            
            # Находим активную смену
            shifts_query = select(Shift).where(
                and_(
                    Shift.user_id == db_user.id,
                    Shift.status == "active"
                )
            )
            shifts_result = await session.execute(shifts_query)
            active_shifts = shifts_result.scalars().all()
            
            if not active_shifts:
                await query.edit_message_text(
                    text="📋 <b>Мои задачи</b>\n\n"
                         "❌ У вас нет активной смены.\n\n"
                         "Откройте смену, чтобы увидеть задачи.",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            shift_obj = active_shifts[0]
            shift_id = shift_obj.id
            
            # Получаем задачи через _collect_shift_tasks() - единая функция для всех мест
            timeslot = None
            obj = None
            
            if shift_obj.time_slot_id:
                timeslot_query = select(TimeSlot).where(TimeSlot.id == shift_obj.time_slot_id)
                timeslot_result = await session.execute(timeslot_query)
                timeslot = timeslot_result.scalar_one_or_none()
                
                # DEBUG логирование для БАГ #2
                if timeslot:
                    logger.info(
                        f"[DEBUG_IGNORE] Loaded timeslot for MY_TASKS",
                        timeslot_id=timeslot.id,
                        ignore_object_tasks=timeslot.ignore_object_tasks,
                        has_object_tasks=bool(obj and obj.shift_tasks) if obj else False
                    )
            
            if shift_obj.object_id:
                object_query = select(Object).where(Object.id == shift_obj.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
            
            shift_tasks = await _collect_shift_tasks(
                session=session,
                shift=shift_obj,
                timeslot=timeslot,
                object_=obj
            )
            
            if not shift_tasks:
                await query.edit_message_text(
                    text="📋 <b>Мои задачи</b>\n\n"
                         "✅ На эту смену задачи не назначены.\n\n"
                         "Выполняйте свою работу согласно инструкциям.",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                    ]])
                )
                return
            
            # Получаем или создаём состояние для отслеживания выполнения задач
            logger.info(f"[MY_TASKS] Loading/creating state for user {user_id}, shift {shift_id}, {len(shift_tasks)} tasks")
            
            existing_state = await user_state_manager.get_state(user_id)
            
            # Если состояние существует и для той же смены - сохраняем completed_tasks
            if existing_state and existing_state.selected_shift_id == shift_id:
                completed_tasks = existing_state.completed_tasks or []
                task_media = existing_state.task_media or {}
                logger.info(f"[MY_TASKS] Reusing existing state with {len(completed_tasks)} completed tasks")
                
                # Обновляем задачи (могли добавиться новые)
                await user_state_manager.update_state(
                    user_id=user_id,
                    shift_tasks=shift_tasks,
                    completed_tasks=completed_tasks,
                    task_media=task_media
                )
            else:
                # Создаём новое состояние
                completed_tasks = []
                task_media = {}
                await user_state_manager.create_state(
                    user_id=user_id,
                    action=UserAction.MY_TASKS,
                    step=UserStep.TASK_COMPLETION,
                    selected_shift_id=shift_id,
                    shift_tasks=shift_tasks,
                    completed_tasks=completed_tasks,
                    task_media=task_media
                )
                logger.info(f"[MY_TASKS] Created new state")
            
            # Показываем список задач
            await _show_my_tasks_list(context, user_id, shift_id, shift_tasks, completed_tasks, task_media)
            
            logger.info(f"[MY_TASKS] Task list shown successfully")
            
    except Exception as e:
        logger.error(f"Error showing my tasks: {e}", exc_info=True)
        await query.edit_message_text(
            text="❌ Ошибка загрузки задач. Попробуйте позже.",
            parse_mode='HTML'
        )


async def _show_my_tasks_list(context, user_id: int, shift_id: int, shift_tasks: list, completed_tasks: list, task_media: dict):
    """Показать список задач (версия для просмотра во время смены)."""
    tasks_text = "📋 <b>Мои задачи на смену:</b>\n\n"
    tasks_text += "Отметьте выполненные задачи:\n\n"
    
    for idx, task in enumerate(shift_tasks):
        task_text = task.get('text') or task.get('task_text', 'Задача')
        is_mandatory = task.get('is_mandatory', True)
        deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
        requires_media = task.get('requires_media', False)
        
        # Для Tasks v2 проверяем is_completed из базы, для legacy - из completed_tasks
        is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
        
        # Иконки
        mandatory_icon = "⚠️" if is_mandatory else "⭐"
        completed_icon = "✅ " if is_task_completed else ""
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
        if is_task_completed:
            task_line = f"<s>{task_line}</s>"
        tasks_text += task_line + "\n"
    
    # Формируем кнопки
    keyboard = []
    for idx, task in enumerate(shift_tasks):
        task_text = task.get('text') or task.get('task_text', 'Задача')
        is_mandatory = task.get('is_mandatory', True)
        requires_media = task.get('requires_media', False)
        
        # Для Tasks v2 проверяем is_completed из базы
        is_task_completed = task.get('is_completed', False) if task.get('source') == 'task_v2' else (idx in completed_tasks)
        
        icon = "⚠️" if is_mandatory else "⭐"
        media_icon = "📸 " if requires_media else ""
        check = "✓ " if is_task_completed else "☐ "
        
        # Для Tasks v2 используем отдельный callback с entry_id
        if task.get('source') == 'task_v2' and task.get('entry_id'):
            callback_data = f"complete_task_v2:{task['entry_id']}"
        else:
            # Legacy задачи - по индексу
            callback_data = f"complete_my_task:{shift_id}:{idx}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{check}{media_icon}{icon} {task_text[:30]}...",
                callback_data=callback_data
            )
        ])
    
    # Вместо "Продолжить закрытие смены" - кнопка "Главное меню"
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    await context.bot.send_message(
        chat_id=user_id,
        text=tasks_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _handle_complete_my_task(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int, task_idx: int):
    """Обработчик отметки задачи (во время смены, не при закрытии)."""
    query = update.callback_query
    user_id = query.from_user.id
    
    logger.info(f"[MY_TASKS] _handle_complete_my_task called: shift_id={shift_id}, task_idx={task_idx}, user_id={user_id}")
    
    try:
        await query.answer()  # Подтверждаем получение callback
        
        # Получаем состояние
        user_state = await user_state_manager.get_state(user_id)
        if not user_state or user_state.action != UserAction.MY_TASKS:
            logger.error(f"[MY_TASKS] Invalid state: user_state={user_state}, action={user_state.action if user_state else None}")
            await query.answer("❌ Состояние утеряно. Начните заново", show_alert=True)
            return
        
        # Получаем задачи из состояния
        shift_tasks = getattr(user_state, 'shift_tasks', [])
        completed_tasks = getattr(user_state, 'completed_tasks', [])
        
        logger.info(f"[MY_TASKS] Tasks count: {len(shift_tasks)}, completed: {completed_tasks}")
        
        # Проверяем индекс
        if task_idx >= len(shift_tasks):
            logger.error(f"[MY_TASKS] Task index out of range: {task_idx} >= {len(shift_tasks)}")
            await query.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Получаем информацию о задаче
        current_task = shift_tasks[task_idx]
        requires_media = current_task.get('requires_media', False)
        task_media = getattr(user_state, 'task_media', {})
        
        logger.info(f"[MY_TASKS] Task: {current_task.get('text')}, requires_media={requires_media}, already_completed={task_idx in completed_tasks}")
        
        # Переключаем статус
        if task_idx in completed_tasks:
            # Снимаем отметку
            completed_tasks.remove(task_idx)
            if task_idx in task_media:
                del task_media[task_idx]
            status_msg = "Задача снята с отметки"
            await user_state_manager.update_state(user_id, completed_tasks=completed_tasks, task_media=task_media)
            logger.info(f"[MY_TASKS] Task unmarked")
        else:
            # Проверяем, требуется ли медиа
            if requires_media:
                logger.info(f"[MY_TASKS] Task requires media, calling _handle_my_task_media_upload")
                # Переходим к загрузке медиа
                await _handle_my_task_media_upload(update, context, shift_id, task_idx)
                return
            else:
                # Простая отметка без медиа
                completed_tasks.append(task_idx)
                status_msg = "✅ Задача отмечена"
                await user_state_manager.update_state(user_id, completed_tasks=completed_tasks)
        
        # Обновляем список задач
        await _show_my_tasks_list_update(query, shift_id, shift_tasks, completed_tasks, task_media)
        await query.answer(status_msg)
        
    except Exception as e:
        logger.error(f"Error toggling my task: {e}")
        await query.answer("❌ Ошибка отметки задачи", show_alert=True)


async def _show_my_tasks_list_update(query, shift_id: int, shift_tasks: list, completed_tasks: list, task_media: dict):
    """Обновить список задач в существующем сообщении."""
    tasks_text = "📋 <b>Мои задачи на смену:</b>\n\n"
    tasks_text += "Отметьте выполненные задачи:\n\n"
    
    for idx, task in enumerate(shift_tasks):
        task_text = task.get('text') or task.get('task_text', 'Задача')
        is_mandatory = task.get('is_mandatory', True)
        deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
        requires_media = task.get('requires_media', False)
        
        mandatory_icon = "⚠️" if is_mandatory else "⭐"
        completed_icon = "✅ " if idx in completed_tasks else ""
        media_icon = "📸 " if requires_media else ""
        
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
                callback_data=f"complete_my_task:{shift_id}:{idx}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    await query.edit_message_text(
        text=tasks_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def _handle_my_task_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, shift_id: int, task_idx: int):
    """Запрос на загрузку медиа для задачи (во время смены)."""
    query = update.callback_query
    user_id = query.from_user.id
    
    logger.info(f"[MY_TASKS] _handle_my_task_media_upload called: shift_id={shift_id}, task_idx={task_idx}, user_id={user_id}")
    
    try:
        user_state = await user_state_manager.get_state(user_id)
        if not user_state:
            logger.error(f"[MY_TASKS] User state is None for user {user_id}")
            await query.answer("❌ Состояние утеряно", show_alert=True)
            return
        
        # Получаем telegram_chat_id из БД
        telegram_chat_id = user_state.data.get('telegram_chat_id')
        object_name = user_state.data.get('object_name')
        
        if not telegram_chat_id:
            logger.info(f"[MY_TASKS] Getting telegram_chat_id from DB for shift {shift_id}")
            # Получаем из БД
            async with get_async_session() as session:
                shift_query = select(Shift).where(Shift.id == shift_id)
                shift_result = await session.execute(shift_query)
                shift_obj = shift_result.scalar_one_or_none()
                
                logger.info(f"[MY_TASKS] Shift found: {shift_obj is not None}, object_id: {shift_obj.object_id if shift_obj else None}")
                
                if shift_obj:
                    try:
                        object_query = select(Object).where(Object.id == shift_obj.object_id)
                        logger.info(f"[MY_TASKS] Executing object query for object_id={shift_obj.object_id}")
                        object_result = await session.execute(object_query)
                        logger.info(f"[MY_TASKS] Object query executed, getting scalar")
                        obj = object_result.scalar_one_or_none()
                        logger.info(f"[MY_TASKS] Object scalar retrieved: {obj is not None}")
                        
                        if obj:
                            logger.info(f"[MY_TASKS] Object details: id={obj.id}, name={obj.name}, telegram_report_chat_id={obj.telegram_report_chat_id}")
                    except Exception as obj_err:
                        logger.error(f"[MY_TASKS] Error getting object: {obj_err}", exc_info=True)
                        obj = None
                    
                    logger.info(f"[MY_TASKS] Object found: {obj is not None}, telegram_report_chat_id: {obj.telegram_report_chat_id if obj else None}")
                    
                    if obj:
                        telegram_chat_id = obj.telegram_report_chat_id
                        object_name = obj.name
                        
                        logger.info(f"[MY_TASKS] telegram_chat_id={telegram_chat_id}, object_name={object_name}")
                        
                        # Если нет в объекте - проверяем подразделение
                        if not telegram_chat_id and obj.division_id:
                            logger.info(f"[MY_TASKS] Checking division {obj.division_id} for telegram_chat_id")
                            from domain.entities.org_structure_unit import OrgStructureUnit
                            division_query = select(OrgStructureUnit).where(OrgStructureUnit.id == obj.division_id)
                            division_result = await session.execute(division_query)
                            division = division_result.scalar_one_or_none()
                            if division:
                                telegram_chat_id = division.telegram_chat_id
                                logger.info(f"[MY_TASKS] Found telegram_chat_id in division: {telegram_chat_id}")
        
        logger.info(f"[MY_TASKS] Final telegram_chat_id check: {telegram_chat_id}")
        
        if not telegram_chat_id:
            logger.warning(f"[MY_TASKS] No telegram_chat_id found, showing error to user")
            await query.edit_message_text(
                text="❌ Telegram группа для отчетов не настроена.\n\n"
                     "Обратитесь к администратору для настройки группы в объекте или подразделении.",
                parse_mode='HTML'
            )
            return
        
        logger.info(f"[MY_TASKS] Updating user state with telegram_chat_id={telegram_chat_id}")
        
        # Обновляем состояние
        await user_state_manager.update_state(
            user_id,
            step=UserStep.MEDIA_UPLOAD,
            pending_media_task_idx=task_idx,
            data={'telegram_chat_id': telegram_chat_id, 'object_name': object_name}
        )
        
        shift_tasks = getattr(user_state, 'shift_tasks', [])
        task = shift_tasks[task_idx]
        task_text = task.get('text') or task.get('task_text', 'Задача')
        
        logger.info(f"[MY_TASKS] Task text: {task_text}, preparing media request")
        
        media_types = task.get('media_types', ['photo', 'video'])
        if isinstance(media_types, str):
            media_types = media_types.split(',')
        
        media_text = "фото" if media_types == ["photo"] else "видео" if media_types == ["video"] else "фото или видео"
        
        logger.info(f"[MY_TASKS] Sending media request message")
        
        await query.edit_message_text(
            text=f"📸 <b>Требуется отчет</b>\n\n"
                 f"Задача: <i>{task_text}</i>\n\n"
                 f"📷 Отправьте {media_text} отчет о выполнении задачи.\n\n"
                 f"⚠️ <b>Важно:</b> отправьте медиа БЕЗ использования команд /start или других кнопок, иначе состояние потеряется!",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data=f"cancel_my_task_media:{shift_id}")
            ]])
        )
        
        logger.info(f"[MY_TASKS] Media request sent successfully")
        
    except Exception as e:
        logger.error(f"Error handling my task media upload: {e}")
        await query.answer("❌ Ошибка запроса медиа", show_alert=True)


async def _handle_complete_task_v2(update: Update, context: ContextTypes.DEFAULT_TYPE, entry_id: int):
    """
    Обработчик выполнения задачи Tasks v2.
    
    Логика:
    - Если задача требует медиа → запрашиваем фото через Media Orchestrator
    - Если нет → просто отмечаем выполненной
    - Сохраняем в TaskEntryV2 через TaskService
    """
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        async with get_async_session() as session:
            from shared.services.task_service import TaskService
            from domain.entities.user import User
            from domain.entities.shift import Shift
            
            task_service = TaskService(session)
            
            # Получаем внутренний user_id
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            db_user = user_result.scalar_one_or_none()
            
            if not db_user:
                await query.answer("❌ Пользователь не найден", show_alert=True)
                return
            
            # Получаем TaskEntry
            from domain.entities.task_entry import TaskEntryV2
            from sqlalchemy.orm import selectinload
            
            entry_query = select(TaskEntryV2).where(
                TaskEntryV2.id == entry_id
            ).options(
                selectinload(TaskEntryV2.template),
                selectinload(TaskEntryV2.shift_schedule)
            )
            entry_result = await session.execute(entry_query)
            entry = entry_result.scalar_one_or_none()
            
            if not entry:
                await query.answer("❌ Задача не найдена", show_alert=True)
                return
            
            # Проверяем права (только владелец задачи может выполнить)
            if entry.employee_id != db_user.id:
                await query.answer("❌ Это не ваша задача", show_alert=True)
                return
            
            template = entry.template
            
            # Переключаем статус
            if entry.is_completed:
                # Снимаем отметку
                entry.is_completed = False
                entry.completed_at = None
                entry.completion_notes = None
                entry.completion_media = None
                await session.commit()
                
                await query.answer("☐ Задача снята с отметки", show_alert=False)
                logger.info(f"TaskEntryV2 {entry_id} unmarked by user {db_user.id}")
            else:
                # Отмечаем выполненной
                if template.requires_media:
                    # Требуется фото - переходим к загрузке
                    await _handle_task_v2_media_upload(update, context, entry_id)
                    return
                else:
                    # Простая отметка без медиа
                    from datetime import datetime
                    entry.is_completed = True
                    entry.completed_at = datetime.utcnow()
                    await session.commit()
                    
                    await query.answer("✅ Задача выполнена", show_alert=False)
                    logger.info(f"TaskEntryV2 {entry_id} completed by user {db_user.id}")
            
            # Обновляем список задач
            # Находим активную смену
            shifts_query = select(Shift).where(
                and_(
                    Shift.user_id == db_user.id,
                    Shift.status == "active"
                )
            )
            shifts_result = await session.execute(shifts_query)
            active_shift = shifts_result.scalar_one_or_none()
            
            if active_shift:
                # Перезагружаем и показываем список задач
                from domain.entities.time_slot import TimeSlot
                from domain.entities.object import Object
                
                timeslot = None
                obj = None
                
                if active_shift.time_slot_id:
                    timeslot_query = select(TimeSlot).where(TimeSlot.id == active_shift.time_slot_id)
                    timeslot_result = await session.execute(timeslot_query)
                    timeslot = timeslot_result.scalar_one_or_none()
                
                if active_shift.object_id:
                    object_query = select(Object).where(Object.id == active_shift.object_id)
                    object_result = await session.execute(object_query)
                    obj = object_result.scalar_one_or_none()
                
                shift_tasks = await _collect_shift_tasks(
                    session=session,
                    shift=active_shift,
                    timeslot=timeslot,
                    object_=obj
                )
                
                # Показываем обновлённый список
                await _show_my_tasks_list(context, user_id, active_shift.id, shift_tasks, [], {})
    
    except Exception as e:
        logger.error(f"Error in _handle_complete_task_v2: {e}", exc_info=True)
        await query.answer("❌ Ошибка обработки задачи", show_alert=True)


async def _handle_task_v2_media_upload(update: Update, context: ContextTypes.DEFAULT_TYPE, entry_id: int):
    """Запросить загрузку медиа для задачи v2."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        async with get_async_session() as session:
            from shared.services.task_service import TaskService
            from domain.entities.task_entry import TaskEntryV2
            from sqlalchemy.orm import selectinload
            
            task_service = TaskService(session)
            
            # Получаем TaskEntry
            entry_query = select(TaskEntryV2).where(
                TaskEntryV2.id == entry_id
            ).options(
                selectinload(TaskEntryV2.template)
            )
            entry_result = await session.execute(entry_query)
            entry = entry_result.scalar_one_or_none()
            
            if not entry or not entry.template:
                await query.answer("❌ Задача не найдена", show_alert=True)
                return
            
            template = entry.template
            
            # Запускаем Media Orchestrator
            from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig
            orchestrator = MediaOrchestrator()
            await orchestrator.begin_flow(
                MediaFlowConfig(
                    user_id=user_id,
                    context_type="task_v2_proof",
                    context_id=entry_id,
                    require_text=False,
                    require_photo=True,
                    max_photos=1,
                    allow_skip=False
                )
            )
            await orchestrator.close()
            
            # Сохраняем в состояние пользователя (для совместимости)
            await user_state_manager.update_state(
                user_id,
                step=UserStep.TASK_V2_MEDIA_UPLOAD,
                pending_task_v2_entry_id=entry_id
            )
            
            await query.edit_message_text(
                text=f"📸 <b>Фотоотчёт</b>\n\n"
                     f"Задача: <b>{template.title}</b>\n"
                     f"{template.description or ''}\n\n"
                     f"📤 Отправьте фото для отчёта.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отмена", callback_data="cancel_task_v2_media")
                ]])
            )
            
            logger.info(f"Media Orchestrator started for TaskEntryV2 {entry_id}")
    
    except Exception as e:
        logger.error(f"Error in _handle_task_v2_media_upload: {e}", exc_info=True)
        await query.answer("❌ Ошибка запроса медиа", show_alert=True)


async def _handle_cancel_task_v2_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена загрузки медиа для задачи v2."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Очищаем состояние
        await user_state_manager.update_state(
            user_id,
            step=UserStep.TASK_COMPLETION,
            pending_task_v2_entry_id=None
        )
        
        # Возвращаемся к списку задач
        async with get_async_session() as session:
            from domain.entities.user import User
            from domain.entities.shift import Shift
            from domain.entities.time_slot import TimeSlot
            from domain.entities.object import Object
            
            # Получаем внутренний user_id
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = await session.execute(user_query)
            db_user = user_result.scalar_one_or_none()
            
            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден")
                return
            
            # Находим активную смену
            shifts_query = select(Shift).where(
                and_(
                    Shift.user_id == db_user.id,
                    Shift.status == "active"
                )
            )
            shifts_result = await session.execute(shifts_query)
            active_shift = shifts_result.scalar_one_or_none()
            
            if not active_shift:
                await query.edit_message_text("❌ Активная смена не найдена")
                return
            
            # Загружаем задачи
            timeslot = None
            obj = None
            
            if active_shift.time_slot_id:
                timeslot_query = select(TimeSlot).where(TimeSlot.id == active_shift.time_slot_id)
                timeslot_result = await session.execute(timeslot_query)
                timeslot = timeslot_result.scalar_one_or_none()
            
            if active_shift.object_id:
                object_query = select(Object).where(Object.id == active_shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
            
            shift_tasks = await _collect_shift_tasks(
                session=session,
                shift=active_shift,
                timeslot=timeslot,
                object_=obj
            )
            
            # Показываем список задач
            await _show_my_tasks_list(context, user_id, active_shift.id, shift_tasks, [], {})
    
    except Exception as e:
        logger.error(f"Error in _handle_cancel_task_v2_media: {e}", exc_info=True)
        await query.answer("❌ Ошибка отмены", show_alert=True)


async def _handle_received_task_v2_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка полученного фото/видео для задачи Tasks v2 через Media Orchestrator."""
    user_id = update.message.from_user.id
    
    try:
        # Проверяем Media Orchestrator
        from shared.services.media_orchestrator import MediaOrchestrator
        orchestrator = MediaOrchestrator()
        media_flow = await orchestrator.get_flow(user_id)
        
        if not media_flow or media_flow.context_type != "task_v2_proof":
            await orchestrator.close()
            await update.message.reply_text("❌ Ошибка: медиа-поток не найден")
            return
        
        entry_id = media_flow.context_id
        
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
            await update.message.reply_text("❌ Отправьте фото или видео")
            return
        
        async with get_async_session() as session:
            from shared.services.task_service import TaskService
            from domain.entities.task_entry import TaskEntryV2
            from domain.entities.user import User
            from domain.entities.shift import Shift
            from domain.entities.object import Object
            from domain.entities.org_unit import OrgStructureUnit
            from sqlalchemy.orm import selectinload
            from datetime import datetime
            
            task_service = TaskService(session)
            
            # Получаем TaskEntry с template
            entry_query = select(TaskEntryV2).where(
                TaskEntryV2.id == entry_id
            ).options(
                selectinload(TaskEntryV2.template),
                selectinload(TaskEntryV2.shift_schedule)
            )
            entry_result = await session.execute(entry_query)
            entry = entry_result.scalar_one_or_none()
            
            if not entry or not entry.template:
                await update.message.reply_text("❌ Задача не найдена")
                return
            
            template = entry.template
            
            # Получаем информацию для отправки в группу
            db_user_query = select(User).where(User.telegram_id == user_id)
            db_user_result = await session.execute(db_user_query)
            db_user = db_user_result.scalar_one_or_none()
            
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Получаем активную смену для определения объекта
            shift_query = select(Shift).where(
                and_(
                    Shift.user_id == db_user.id,
                    Shift.status == "active"
                )
            )
            shift_result = await session.execute(shift_query)
            active_shift = shift_result.scalar_one_or_none()
            
            if not active_shift:
                await update.message.reply_text("❌ Активная смена не найдена")
                return
            
            # Получаем объект для определения telegram_chat_id
            object_query = select(Object).where(Object.id == active_shift.object_id)
            object_result = await session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            telegram_chat_id = None
            object_name = "Объект"
            
            if obj:
                object_name = obj.name
                telegram_chat_id = obj.telegram_chat_id
                
                # Если нет в объекте - ищем в division
                if not telegram_chat_id and obj.division_id:
                    division_query = select(OrgStructureUnit).where(OrgStructureUnit.id == obj.division_id)
                    division_result = await session.execute(division_query)
                    division = division_result.scalar_one_or_none()
                    if division:
                        telegram_chat_id = division.telegram_chat_id
            
            if not telegram_chat_id:
                await update.message.reply_text(
                    "❌ Telegram группа для отчетов не настроена.\n"
                    "Обратитесь к администратору."
                )
                return
            
            # Отправляем медиа в группу
            user_name = f"{update.message.from_user.first_name} {update.message.from_user.last_name or ''}".strip()
            caption = f"📋 Отчет (Tasks v2): {template.title}\n👤 {user_name}\n🏢 {object_name}"
            
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
            
            # Формируем ссылку на медиа
            chat_id_str = str(telegram_chat_id)
            if chat_id_str.startswith('-100'):
                chat_id_str = chat_id_str[4:]
            elif chat_id_str.startswith('-'):
                chat_id_str = chat_id_str[1:]
            media_url = f"https://t.me/c/{chat_id_str}/{sent_message.message_id}"
            
            # Добавляем медиа в Media Orchestrator
            await orchestrator.add_photo(user_id, media_file_id)
            
            # Завершаем поток и получаем финальные данные
            final_flow = await orchestrator.finish(user_id)
            await orchestrator.close()
            
            # Сохраняем результат выполнения в TaskEntryV2
            entry.is_completed = True
            entry.completed_at = datetime.utcnow()
            entry.completion_media = [{
                'url': media_url,
                'type': media_type,
                'file_id': media_file_id
            }]
            await session.commit()
            
            logger.info(
                f"TaskEntryV2 {entry_id} completed with media via Media Orchestrator",
                media_type=media_type,
                media_url=media_url,
                photos_count=len(final_flow.collected_photos) if final_flow else 0
            )
            
            # Очищаем состояние
            await user_state_manager.update_state(
                user_id,
                step=UserStep.TASK_COMPLETION,
                pending_task_v2_entry_id=None
            )
            
            # Подтверждение (БЕЗ автоматического показа списка задач)
            await update.message.reply_text(
                f"✅ <b>Отчет принят!</b>\n\n"
                f"📋 Задача: <i>{template.title}</i>\n"
                f"✅ Отмечена как выполненная\n"
                f"📤 Отправлено в группу отчетов\n\n"
                f"💡 Используйте '📋 Мои задачи' для продолжения.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 Мои задачи", callback_data="my_tasks"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
    
    except Exception as e:
        logger.error(f"Error in _handle_received_task_v2_media: {e}", exc_info=True)
        await update.message.reply_text("❌ Ошибка обработки медиа")


