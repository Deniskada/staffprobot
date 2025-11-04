"""Обработчики для планирования смен."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from shared.services.adapters import ScheduleServiceAdapter
from apps.bot.services.object_service import ObjectService
from core.state import user_state_manager, UserAction, UserStep
from domain.entities.object import Object
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift
from domain.entities.user import User
from sqlalchemy import select
from datetime import datetime, timedelta, date, time, timezone
from typing import List, Dict, Any, Optional

# Создаем экземпляры сервисов
schedule_service = ScheduleServiceAdapter()
object_service = ObjectService()


async def handle_schedule_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало планирования смены."""
    user_id = update.effective_user.id
    
    # Получаем доступные объекты сотрудника по договорам
    try:
        from apps.bot.services.employee_objects_service import EmployeeObjectsService
        
        employee_objects_service = EmployeeObjectsService()
        objects = await employee_objects_service.get_employee_objects(user_id)
        
        if not objects:
            await update.callback_query.edit_message_text(
                "❌ У вас нет доступных объектов для планирования смен.\n\n"
                "У вас должен быть активный договор с владельцем объекта."
            )
            return
        
        # Создаем клавиатуру с объектами
        keyboard = []
        for obj in objects:
            # Показываем количество договоров для объекта
            contracts_count = len(obj.get('contracts', []))
            contracts_info = f" ({contracts_count} договор)" if contracts_count > 1 else ""
            
            keyboard.append([InlineKeyboardButton(
                f"🏢 {obj['name']}{contracts_info}",
                callback_data=f"schedule_select_object_{obj['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "📅 **Планирование смены**\n\n"
            "Выберите объект для планирования:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting objects for scheduling: {e}")
        await update.callback_query.edit_message_text(
            "❌ Ошибка получения объектов. Попробуйте позже."
        )


async def handle_schedule_object_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора объекта для планирования."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Извлекаем ID объекта из callback_data
    object_id = int(query.data.split("_")[-1])
    
    # Сохраняем выбранный объект в контексте
    context.user_data['selected_object_id'] = object_id
    
    # Устанавливаем состояние пользователя
    user_state_manager.set_state(
        user_id=user_id,
        action=UserAction.SCHEDULE_SHIFT,
        step=UserStep.INPUT_DATE,
        selected_object_id=object_id
    )
    
    # Создаем клавиатуру с датами
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    keyboard = [
        [InlineKeyboardButton(f"📅 Сегодня ({today.strftime('%d.%m')})", callback_data="schedule_date_today")],
        [InlineKeyboardButton(f"📅 Завтра ({tomorrow.strftime('%d.%m')})", callback_data="schedule_date_tomorrow")],
        [InlineKeyboardButton("📅 Другая дата", callback_data="schedule_date_custom")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📅 **Выберите дату для смены**\n\n"
        "Выберите дату планирования:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_schedule_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора даты для планирования."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query.data == "schedule_date_today":
        selected_date = date.today()
    elif query.data == "schedule_date_tomorrow":
        selected_date = date.today() + timedelta(days=1)
    elif query.data == "schedule_date_custom":
        # Запрашиваем ввод даты
        user_state_manager.set_state(
            user_id=user_id,
            action=UserAction.SCHEDULE_SHIFT,
            step=UserStep.INPUT_DATE,
            selected_object_id=context.user_data.get('selected_object_id')
        )
        await query.edit_message_text(
            "📅 **Введите дату в формате ДД.ММ.ГГГГ**\n\n"
            "Например: `15.09.2025`",
            parse_mode='Markdown'
        )
        return
    else:
        await query.edit_message_text("❌ Неверный выбор даты.")
        return
    
    # Сохраняем выбранную дату
    context.user_data['selected_date'] = selected_date
    
    # Получаем доступные тайм-слоты для объекта на дату
    object_id = context.user_data.get('selected_object_id')
    if not object_id:
        await query.edit_message_text("❌ Ошибка: объект не выбран.")
        return
    
    try:
        result = await schedule_service.get_available_time_slots_for_date(object_id, selected_date)
        
        if not result['success']:
            await query.edit_message_text(f"❌ Ошибка получения тайм-слотов: {result['error']}")
            return
        
        available_slots = result['available_slots']
        
        if not available_slots:
            await query.edit_message_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет доступных тайм-слотов.\n\n"
                "Создайте тайм-слоты через меню управления объектами."
            )
            return
        
        # Создаем клавиатуру с доступными тайм-слотами
        keyboard = []
        for slot in available_slots:
            slot_text = f"🕐 {slot['start_time']}-{slot['end_time']}"
            if slot['hourly_rate']:
                slot_text += f" ({slot['hourly_rate']}₽/ч)"
            # Добавляем информацию о занятости
            if slot.get('max_employees', 1) > 1:
                slot_text += f" [{slot.get('availability', '0/1')}]"
            keyboard.append([InlineKeyboardButton(
                slot_text,
                callback_data=f"schedule_select_slot_{slot['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🕐 **Доступные тайм-слоты на {selected_date.strftime('%d.%m.%Y')}**\n\n"
            "Выберите подходящий тайм-слот:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting time slots: {e}")
        await query.edit_message_text("❌ Ошибка получения тайм-слотов. Попробуйте позже.")


async def handle_schedule_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение планирования смены."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # Извлекаем ID тайм-слота
    slot_id = int(query.data.split("_")[-1])
    
    # Получаем данные из контекста
    object_id = context.user_data.get('selected_object_id')
    selected_date = context.user_data.get('selected_date')
    
    if not object_id or not selected_date:
        await query.edit_message_text("❌ Ошибка: данные сессии утеряны.")
        return
    
    try:
        # Получаем информацию о тайм-слоте
        from apps.bot.services.time_slot_service import TimeSlotService
        from datetime import time
        time_slot_service = TimeSlotService()
        timeslot_data = time_slot_service.get_timeslot_by_id(slot_id)
        
        if not timeslot_data:
            await query.edit_message_text("❌ Ошибка: тайм-слот не найден.")
            return
        
        # Парсим время из строк
        start_time_str = timeslot_data['start_time']
        end_time_str = timeslot_data['end_time']
        
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
        
        # Создаем запланированную смену
        result = await schedule_service.create_scheduled_shift_from_timeslot(
            user_id=user_id,
            time_slot_id=slot_id,
            start_time=start_time,
            end_time=end_time,
            notes="Запланировано через бота"
        )
        
        if result['success']:
            # Очищаем состояние
            await user_state_manager.clear_state(user_id)
            context.user_data.clear()
            
            # Создаем клавиатуру с кнопкой возврата в главное меню
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ **Смена успешно запланирована!**\n\n"
                f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n"
                f"🕐 Время: {result.get('start_time', 'N/A')} - {result.get('end_time', 'N/A')}\n"
                f"💰 Ставка: {result.get('hourly_rate', 'N/A')} ₽/час\n\n"
                f"Вы получите напоминание за 2 часа до начала смены.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(f"❌ Ошибка планирования: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error scheduling shift: {e}")
        await query.edit_message_text("❌ Ошибка планирования смены. Попробуйте позже.")


async def handle_view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр запланированных смен."""
    telegram_id = update.effective_user.id
    
    try:
        from core.database.session import get_async_session
        async with get_async_session() as session:
            # Сначала находим пользователя по telegram_id
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await update.callback_query.edit_message_text(
                    "❌ Пользователь не найден в базе данных."
                )
                return
            
            # Получаем запланированные смены пользователя из таблицы ShiftSchedule
            # Фильтруем только будущие смены (от текущей даты)
            now_utc = datetime.now(timezone.utc)
            shifts_query = select(ShiftSchedule).where(
                ShiftSchedule.user_id == user.id,
                ShiftSchedule.status == "planned",
                ShiftSchedule.planned_start >= now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
            ).order_by(ShiftSchedule.planned_start)
            
            shifts_result = await session.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            
            if not shifts:
                keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    "📅 **Ваши запланированные смены**\n\n"
                    "У вас нет запланированных смен.",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                return
            
            # Формируем список смен
            schedule_text = "📅 **Ваши запланированные смены:**\n\n"
            
            # Получаем timezone пользователя
            from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
            user_tz = get_user_timezone(user)
            
            # Вспомогательная функция для экранирования Markdown
            def escape_markdown(text: str) -> str:
                """Экранировать спецсимволы Markdown."""
                special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                for char in special_chars:
                    text = text.replace(char, f'\\{char}')
                return text
            
            shifts_with_local_time = []
            for shift in shifts:
                # Получаем информацию об объекте
                object_query = select(Object).where(Object.id == shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                object_name = obj.name if obj else "Неизвестный объект"
                object_name_escaped = escape_markdown(object_name)
                
                # Конвертируем время в timezone пользователя
                local_start = convert_utc_to_local(shift.planned_start, user_tz)
                local_end = convert_utc_to_local(shift.planned_end, user_tz)
                
                shifts_with_local_time.append((shift, local_start, local_end))
                
                schedule_text += f"🏢 **{object_name_escaped}**\n"
                schedule_text += f"📅 {local_start.strftime('%d.%m.%Y %H:%M')}\n"
                schedule_text += f"🕐 До {local_end.strftime('%H:%M')}\n"
                if shift.hourly_rate:
                    schedule_text += f"💰 {shift.hourly_rate} ₽/час\n"
                schedule_text += f"📊 Статус: {escape_markdown(shift.status)}\n\n"
            
            # Добавляем кнопки управления
            keyboard = []
            
            # Кнопки отмены для каждой смены (максимум 5)
            for shift, local_start, local_end in shifts_with_local_time[:5]:
                # Формируем текст кнопки с датой и временем в local timezone
                button_text = f"❌ Отменить {local_start.strftime('%d.%m %H:%M')}"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"cancel_shift_{shift.id}"
                )])
            
            keyboard.extend([
                [InlineKeyboardButton("🔄 Обновить", callback_data="view_schedule")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="close_schedule")]
            ])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await update.callback_query.edit_message_text(
                    schedule_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as edit_error:
                logger.error(f"Error editing message: {edit_error}")
                # Если не удалось отредактировать, отправляем новое сообщение
                await update.callback_query.message.reply_text(
                    schedule_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
    except Exception as e:
        logger.error(f"Error viewing schedule: {e}")
        await update.callback_query.edit_message_text(
            "❌ Ошибка получения расписания. Попробуйте позже."
        )


async def handle_cancel_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена запланированной смены - выбор причины."""
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback
    
    telegram_id = update.effective_user.id
    
    # Извлекаем ID смены из callback_data
    shift_id = int(query.data.split("_")[-1])
    logger.info(f"User {telegram_id} initiating cancellation for shift {shift_id}")
    
    try:
        from core.database.session import get_async_session
        async with get_async_session() as session:
            # Находим пользователя
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await query.edit_message_text("❌ Пользователь не найден в базе данных.")
                return
            
            # Находим смену
            shift_query = select(ShiftSchedule).where(
                ShiftSchedule.id == shift_id,
                ShiftSchedule.user_id == user.id,
                ShiftSchedule.status == "planned"
            )
            shift_result = await session.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            
            if not shift:
                await query.edit_message_text("❌ Смена не найдена или уже отменена.")
                return
            
            # Сохраняем shift_id в контекст для следующего шага
            context.user_data['cancelling_shift_id'] = shift_id

            # Получаем объект (нужен для owner_id и отображения)
            object_query = select(Object).where(Object.id == shift.object_id)
            object_result = await session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            # Динамически получаем причины из БД по владельцу объекта
            from shared.services.cancellation_policy_service import CancellationPolicyService
            owner_id = obj.owner_id if obj else None
            reasons = await CancellationPolicyService.get_owner_reasons(session, owner_id) if owner_id else []
            keyboard_rows = []
            for r in reasons:
                keyboard_rows.append([InlineKeyboardButton(r.title, callback_data=f"cancel_reason_{r.code}")])
            keyboard_rows.append([InlineKeyboardButton("🔙 Отмена", callback_data="view_schedule")])
            reply_markup = InlineKeyboardMarkup(keyboard_rows)
            object_name = obj.name if obj else "Неизвестный объект"
            
            # Экранируем спецсимволы Markdown
            def escape_markdown(text: str) -> str:
                """Экранировать спецсимволы Markdown."""
                special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                for char in special_chars:
                    text = text.replace(char, f'\\{char}')
                return text
            
            object_name_escaped = escape_markdown(object_name)
            
            # Конвертируем время в timezone пользователя
            from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
            user_tz = get_user_timezone(user)
            local_start = convert_utc_to_local(shift.planned_start, user_tz)
            local_end = convert_utc_to_local(shift.planned_end, user_tz)
            
            await query.edit_message_text(
                f"❌ **Отмена смены**\n\n"
                f"🏢 **{object_name_escaped}**\n"
                f"📅 {local_start.strftime('%d.%m.%Y %H:%M')}\n"
                f"🕐 До {local_end.strftime('%H:%M')}\n\n"
                f"Выберите причину отмены:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error in cancellation flow: {e}")
        await query.edit_message_text("❌ Ошибка. Попробуйте позже.")


async def handle_cancel_reason_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора причины отмены."""
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback
    
    telegram_id = update.effective_user.id
    
    # Извлекаем причину из callback_data
    reason = query.data.replace("cancel_reason_", "")
    shift_id = context.user_data.get('cancelling_shift_id')

    logger.info(f"Cancel reason selection: user={telegram_id}, reason={reason}, shift_id={shift_id}")

    if not shift_id:
        logger.error(f"No shift_id in context for user {telegram_id}")
        await query.edit_message_text("❌ Ошибка: смена не найдена в контексте.")
        return

    # Сохраняем причину в контекст
    context.user_data['cancel_reason'] = reason

    # Получаем политику для владельца объекта
    from core.database.session import get_async_session
    async with get_async_session() as session:
        shift_query = select(ShiftSchedule).where(ShiftSchedule.id == shift_id)
        shift_result = await session.execute(shift_query)
        shift = shift_result.scalar_one_or_none()
        if not shift:
            await query.edit_message_text("❌ Смена не найдена.")
            return
        object_query = select(Object).where(Object.id == shift.object_id)
        obj = (await session.execute(object_query)).scalar_one_or_none()
        if not obj:
            await query.edit_message_text("❌ Объект не найден.")
            return
        from shared.services.cancellation_policy_service import CancellationPolicyService
        reason_map = await CancellationPolicyService.get_reason_map(session, obj.owner_id)
        policy = reason_map.get(reason)
        requires_document = bool(policy and policy.requires_document)

    # Ветвление по требованию документа
    if requires_document:
        # Устанавливаем состояние ожидания ввода
        from core.state.user_state_manager import user_state_manager, UserAction, UserStep
        user_state_manager.set_state(
            telegram_id,
            action=UserAction.CANCEL_SCHEDULE,
            step=UserStep.INPUT_DOCUMENT
        )

        title = policy.title if policy else 'документа'
        await query.edit_message_text(
            f"📄 **Описание {title}**\n\n"
            f"Укажите номер и дату документа.\n"
            f"Например: `№123 от 10.10.2025`\n\n"
            f"Справка будет проверена владельцем.",
            parse_mode='Markdown'
        )
    elif reason == 'other':
        # Для "Другая причина" просим объяснение
        from core.state.user_state_manager import user_state_manager, UserAction, UserStep
        user_state_manager.set_state(
            telegram_id,
            action=UserAction.CANCEL_SCHEDULE,
            step=UserStep.INPUT_DOCUMENT
        )
        
        await query.edit_message_text(
            "✍️ **Объяснение причины отмены**\n\n"
            "Опишите причину отмены смены.\n\n"
            "Ваше объяснение будет рассмотрено владельцем.",
            parse_mode='Markdown'
        )
    else:
        # Для остальных причин (не требующих документ) сразу выполняем отмену
        logger.info(f"Executing immediate cancellation for user {telegram_id}, reason={reason}, shift_id={shift_id}")
        success = await _execute_shift_cancellation(
            shift_id=shift_id,
            telegram_id=telegram_id,
            reason=reason,
            reason_notes=None,
            document_description=None,
            context=context,
            query=query
        )
        
        if not success:
            await query.edit_message_text("❌ Ошибка при отмене смены. Попробуйте позже.")


async def handle_cancellation_document_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода описания документа/объяснения для отмены."""
    telegram_id = update.effective_user.id
    description_text = update.message.text
    
    # Проверяем состояние пользователя
    from core.state.user_state_manager import user_state_manager, UserAction, UserStep
    user_state = await user_state_manager.get_state(telegram_id)
    
    if not user_state or user_state.action != UserAction.CANCEL_SCHEDULE or user_state.step != UserStep.INPUT_DOCUMENT:
        # Пользователь не в состоянии ввода документа для отмены - игнорируем
        return
    
    shift_id = context.user_data.get('cancelling_shift_id')
    reason = context.user_data.get('cancel_reason')
    
    if not shift_id or not reason:
        await update.message.reply_text("❌ Ошибка: данные отмены не найдены.")
        return
    
    # Сохраняем описание в контекст
    if reason == 'other':
        context.user_data['cancel_reason_notes'] = description_text  # Объяснение
    else:
        context.user_data['cancel_document_description'] = description_text  # Описание документа
    
    # Проверяем, нужно ли запрашивать фото
    from core.database.session import get_async_session
    async with get_async_session() as session:
        # Получаем смену
        shift_query = select(ShiftSchedule).where(ShiftSchedule.id == shift_id)
        shift_result = await session.execute(shift_query)
        shift = shift_result.scalar_one_or_none()
        
        if not shift:
            await update.message.reply_text("❌ Смена не найдена.")
            return
        
        # Получаем объект с eager loading org_unit и цепочки parent
        from sqlalchemy.orm import joinedload
        object_query = select(Object).where(Object.id == shift.object_id).options(
            joinedload(Object.org_unit).joinedload('parent').joinedload('parent').joinedload('parent')
        )
        object_result = await session.execute(object_query)
        obj = object_result.scalar_one_or_none()
        
        # Определяем чат для отчетов с учетом наследования
        report_chat_id = obj.get_effective_report_chat_id() if obj else None
        
        # Если есть группа для отчетов - запрашиваем фото через Media Orchestrator
        if report_chat_id:
            context.user_data['report_chat_id'] = report_chat_id
            
            # Запускаем Media Orchestrator
            from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig
            orchestrator = MediaOrchestrator()
            await orchestrator.begin_flow(
                MediaFlowConfig(
                    user_id=telegram_id,
                    context_type="cancellation_doc",
                    context_id=shift_id,
                    require_text=False,
                    require_photo=False,  # Опционально
                    max_photos=5,  # Разрешено до 5 файлов
                    allow_skip=True
                )
            )
            await orchestrator.close()
            
            # Устанавливаем состояние ожидания фото
            from core.state.user_state_manager import user_state_manager, UserAction, UserStep
            user_state_manager.set_state(
                telegram_id,
                action=UserAction.CANCEL_SCHEDULE,
                step=UserStep.INPUT_PHOTO
            )
            
            # Создаем кнопку "Пропустить"
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [[InlineKeyboardButton("⏩ Пропустить", callback_data="cancel_skip_photo")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📸 **Фото подтверждения** (опционально)\n\n"
                "Отправьте фото документа или подтверждения.\n"
                "Или нажмите '⏩ Пропустить', если фото нет.",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            # Нет группы для отчетов - сразу выполняем отмену
            from core.state.user_state_manager import user_state_manager
            await user_state_manager.clear_state(telegram_id)
            
            await _execute_shift_cancellation(
                shift_id=shift_id,
                telegram_id=telegram_id,
                reason=reason,
                reason_notes=context.user_data.get('cancel_reason_notes'),
                document_description=context.user_data.get('cancel_document_description'),
                context=context,
                message=update.message
            )


async def handle_cancellation_photo_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка загрузки фото для подтверждения отмены через Media Orchestrator."""
    telegram_id = update.effective_user.id
    
    shift_id = context.user_data.get('cancelling_shift_id')
    reason = context.user_data.get('cancel_reason')
    report_chat_id = context.user_data.get('report_chat_id')
    
    if not shift_id or not reason:
        await update.message.reply_text("❌ Ошибка: данные отмены не найдены.")
        return
    
    # Получаем фото
    photo = update.message.photo[-1] if update.message.photo else None
    
    # Добавляем в Media Orchestrator
    if photo:
        from shared.services.media_orchestrator import MediaOrchestrator
        orchestrator = MediaOrchestrator()
        await orchestrator.add_photo(telegram_id, photo.file_id)
        await orchestrator.close()
    
    # Если есть фото и группа - отправляем в группу
    if photo and report_chat_id:
        try:
            from core.database.session import get_async_session
            async with get_async_session() as session:
                # Получаем данные для сообщения
                user_query = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                shift_query = select(ShiftSchedule).where(ShiftSchedule.id == shift_id)
                shift_result = await session.execute(shift_query)
                shift = shift_result.scalar_one_or_none()
                
                object_query = select(Object).where(Object.id == shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                # Формируем сообщение для группы
                from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
                user_tz = get_user_timezone(user)
                local_start = convert_utc_to_local(shift.planned_start, user_tz)
                
                reason_labels = {
                    'medical_cert': '🏥 Медицинская справка',
                    'emergency_cert': '🚨 Справка от МЧС',
                    'police_cert': '👮 Справка от полиции',
                    'other': '❓ Другая причина'
                }
                
                caption = (
                    f"❌ **Отмена смены**\n\n"
                    f"👤 Сотрудник: {user.full_name if user else 'Неизвестно'}\n"
                    f"🏢 Объект: {obj.name if obj else 'Неизвестно'}\n"
                    f"📅 Дата: {local_start.strftime('%d.%m.%Y %H:%M')}\n"
                    f"📋 Причина: {reason_labels.get(reason, reason)}\n"
                )
                
                # Добавляем описание/объяснение
                doc_desc = context.user_data.get('cancel_document_description')
                reason_notes = context.user_data.get('cancel_reason_notes')
                if doc_desc:
                    caption += f"📄 Документ: {doc_desc}\n"
                if reason_notes:
                    caption += f"✍️ Объяснение: {reason_notes}\n"
                
                # Отправляем фото в группу
                await context.bot.send_photo(
                    chat_id=report_chat_id,
                    photo=photo.file_id,
                    caption=caption,
                    parse_mode='Markdown'
                )
                
                logger.info(f"Cancellation photo sent to chat {report_chat_id}")
                
        except Exception as e:
            logger.error(f"Error sending cancellation photo: {e}")
    
    # Очищаем состояние
    from core.state.user_state_manager import user_state_manager
    await user_state_manager.clear_state(telegram_id)
    
    # Выполняем отмену
    await _execute_shift_cancellation(
        shift_id=shift_id,
        telegram_id=telegram_id,
        reason=reason,
        reason_notes=context.user_data.get('cancel_reason_notes'),
        document_description=context.user_data.get('cancel_document_description'),
        context=context,
        message=update.message
    )


async def handle_cancellation_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопки 'Пропустить фото'."""
    query = update.callback_query
    await query.answer()
    
    telegram_id = update.effective_user.id
    shift_id = context.user_data.get('cancelling_shift_id')
    reason = context.user_data.get('cancel_reason')
    
    if not shift_id or not reason:
        await query.edit_message_text("❌ Ошибка: данные отмены не найдены.")
        return
    
    # Очищаем состояние
    from core.state.user_state_manager import user_state_manager
    await user_state_manager.clear_state(telegram_id)
    
    # Выполняем отмену без фото
    await _execute_shift_cancellation(
        shift_id=shift_id,
        telegram_id=telegram_id,
        reason=reason,
        reason_notes=context.user_data.get('cancel_reason_notes'),
        document_description=context.user_data.get('cancel_document_description'),
        context=context,
        query=query
    )


async def _execute_shift_cancellation(
    shift_id: int,
    telegram_id: int,
    reason: str,
    reason_notes: Optional[str],
    document_description: Optional[str],
    context: ContextTypes.DEFAULT_TYPE,
    query: Optional[Any] = None,
    message: Optional[Any] = None
) -> bool:
    """Выполнить отмену смены с использованием сервиса."""
    logger.info(f"Starting shift cancellation: shift_id={shift_id}, telegram_id={telegram_id}, reason={reason}")
    
    from core.database.session import get_async_session
    from shared.services.shift_cancellation_service import ShiftCancellationService
    
    try:
        async with get_async_session() as session:
            logger.info(f"Got database session for cancellation")
            
            # Находим пользователя
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            logger.info(f"Found user: {user.id if user else 'None'}")
            
            if not user:
                text = "❌ Пользователь не найден."
                if query:
                    await query.edit_message_text(text)
                elif message:
                    await message.reply_text(text)
                return False
            
            # Используем сервис для отмены
            logger.info(f"Creating ShiftCancellationService")
            cancellation_service = ShiftCancellationService(session)
            logger.info(f"Calling cancel_shift with shift_schedule_id={shift_id}, cancelled_by_user_id={user.id}")
            
            result = await cancellation_service.cancel_shift(
                shift_schedule_id=shift_id,
                cancelled_by_user_id=user.id,
                cancelled_by_type='employee',
                cancellation_reason=reason,
                reason_notes=reason_notes,
                document_description=document_description
            )
            
            if result['success']:
                # Получаем смену для отображения
                shift_query = select(ShiftSchedule).where(ShiftSchedule.id == shift_id)
                shift_result = await session.execute(shift_query)
                shift = shift_result.scalar_one_or_none()
                
                # Получаем объект
                object_query = select(Object).where(Object.id == shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                object_name = obj.name if obj else "Неизвестный объект"
                
                # Экранируем спецсимволы Markdown для названия объекта
                def escape_markdown(text: str) -> str:
                    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                    for char in special_chars:
                        text = text.replace(char, f'\\{char}')
                    return text
                object_name_escaped = escape_markdown(object_name)
                
                # Конвертируем время в timezone пользователя
                from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
                user_tz = get_user_timezone(user)
                local_start = convert_utc_to_local(shift.planned_start, user_tz)
                local_end = convert_utc_to_local(shift.planned_end, user_tz)
                
                result_message = result.get('message') or "Смена отменена."
                text = (
                    f"✅ Смена отменена\n\n"
                    f"🏢 {object_name}\n"
                    f"📅 {local_start.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🕐 До {local_end.strftime('%H:%M')}\n\n"
                    f"{result_message}"
                )
                
                # Очищаем контекст
                context.user_data.pop('cancelling_shift_id', None)
                context.user_data.pop('cancel_reason', None)
                context.user_data.pop('cancel_reason_notes', None)
                context.user_data.pop('cancel_document_description', None)
                context.user_data.pop('report_chat_id', None)
                
                # Кнопка "Главное меню"
                menu_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]])

                # Всегда отправляем НОВОЕ сообщение пользователю (не редактируем старое)
                try:
                    if message:
                        await message.reply_text(text, reply_markup=menu_keyboard)
                    elif query:
                        await query.message.reply_text(text, reply_markup=menu_keyboard)
                except Exception as send_err:
                    logger.error(f"Failed to send final cancellation message: {send_err}")
                    try:
                        # Повтор без клавиатуры как крайний случай
                        if message:
                            await message.reply_text(text)
                        elif query:
                            await query.message.reply_text(text)
                    except Exception as send_err2:
                        logger.error(f"Failed to send plain final message: {send_err2}")
                
                # TODO: Отправить уведомление владельцу/управляющему
                return True
                
            else:
                text = f"❌ {result['message']}"
                if query:
                    await query.edit_message_text(text)
                elif message:
                    await message.reply_text(text)
                return False
    
    except Exception as e:
        logger.error(f"Error executing shift cancellation: {e}", exc_info=True)
        logger.error(f"Exception details: type={type(e)}, args={e.args}")
    text = "❌ Ошибка отмены смены. Попробуйте позже."
    if query:
        try:
            await query.edit_message_text(text)
        except Exception:
            # Последняя попытка – отправить новое сообщение
            await query.message.reply_text(text)
    elif message:
        await message.reply_text(text)
        return False


async def handle_close_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Закрытие окна просмотра смен - возврат в главное меню."""
    query = update.callback_query
    
    # Удаляем сообщение с расписанием
    await query.delete_message()
    
    # Отправляем главное меню
    from .core_handlers import get_main_menu_keyboard
    keyboard = get_main_menu_keyboard()
    
    await query.message.reply_text(
        "🏠 **Главное меню**\n\nВыберите действие:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )


async def handle_cancel_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена планирования смены."""
    user_id = update.effective_user.id
    
    # Очищаем состояние
    await user_state_manager.clear_state(user_id)
    context.user_data.clear()
    
    await update.callback_query.edit_message_text(
        "❌ Планирование смены отменено."
    )


async def handle_schedule_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода времени для планирования."""
    # Заглушка - функция не используется в текущей реализации
    pass


async def handle_custom_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода пользовательской даты."""
    from datetime import date
    
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        # Парсим дату в формате ДД.ММ.ГГГГ
        day, month, year = text.split('.')
        selected_date = date(int(year), int(month), int(day))
        
        # Проверяем, что дата не в прошлом
        if selected_date < date.today():
            await update.message.reply_text("❌ Нельзя планировать смены в прошлом.")
            return
        
        # Сохраняем дату и переходим к выбору тайм-слотов
        
        # Устанавливаем дату в контекст
        context.user_data['selected_date'] = selected_date
        
        # Вызываем обработку выбора даты напрямую
        await _handle_schedule_date_selection_direct(update, context, selected_date)
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: `15.09.2025`)",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error parsing custom date: {e}")
        await update.message.reply_text("❌ Ошибка обработки даты. Попробуйте еще раз.")


async def _handle_schedule_date_selection_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: date) -> None:
    """Прямая обработка выбора даты для планирования."""
    user_id = update.effective_user.id
    
    # Сохраняем выбранную дату
    context.user_data['selected_date'] = selected_date
    
    # Получаем доступные тайм-слоты для объекта на дату
    object_id = context.user_data.get('selected_object_id')
    if not object_id:
        await update.message.reply_text("❌ Ошибка: объект не выбран.")
        return
    
    try:
        result = await schedule_service.get_available_time_slots_for_date(object_id, selected_date)
        
        if not result['success']:
            await update.message.reply_text(f"❌ Ошибка получения тайм-слотов: {result['error']}")
            return
        
        available_slots = result['available_slots']
        
        if not available_slots:
            await update.message.reply_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет доступных тайм-слотов.\n\n"
                "Создайте тайм-слоты через меню управления объектами."
            )
            return
        
        # Создаем клавиатуру с доступными тайм-слотами
        keyboard = []
        for slot in available_slots:
            slot_text = f"🕐 {slot['start_time']}-{slot['end_time']}"
            if slot['hourly_rate']:
                slot_text += f" ({slot['hourly_rate']}₽/ч)"
            # Добавляем информацию о занятости
            if slot.get('max_employees', 1) > 1:
                slot_text += f" [{slot.get('availability', '0/1')}]"
            keyboard.append([InlineKeyboardButton(
                slot_text,
                callback_data=f"schedule_select_slot_{slot['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🕐 **Доступные тайм-слоты на {selected_date.strftime('%d.%m.%Y')}**\n\n"
            "Выберите подходящий тайм-слот:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting time slots: {e}")
        await update.message.reply_text("❌ Ошибка получения тайм-слотов. Попробуйте позже.")
