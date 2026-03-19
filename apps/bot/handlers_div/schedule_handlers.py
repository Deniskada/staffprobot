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
from typing import List, Dict, Any, Optional, Tuple

# Создаем экземпляры сервисов
schedule_service = ScheduleServiceAdapter()
object_service = ObjectService()


def _build_interval_keyboard(available_slots: List[Dict[str, Any]]) -> Tuple[List[List[InlineKeyboardButton]], int]:
    keyboard: List[List[InlineKeyboardButton]] = []
    intervals_added = 0

    for slot in available_slots:
        free_intervals = slot.get('free_intervals') or []
        first_free = slot.get('first_free_interval')
        if not free_intervals and first_free:
            free_intervals = [{
                'start': first_free.get('start'),
                'end': first_free.get('end'),
                'duration_minutes': first_free.get('duration_minutes'),
                'position_index': first_free.get('position_index')
            }]

        for interval in free_intervals:
            start_label = interval.get('start')
            end_label = interval.get('end')
            if not start_label or not end_label:
                continue
            position_index = interval.get('position_index')

            button_text = f"🕐 {start_label}–{end_label}"
            availability = slot.get('availability')
            if slot.get('max_employees', 1) > 1 and position_index:
                button_text += f" • место {position_index}"
            if availability:
                button_text += f" • {availability}"
            if slot.get('hourly_rate'):
                button_text += f" • {slot['hourly_rate']}₽/ч"

            start_code = start_label.replace(":", "")
            end_code = end_label.replace(":", "")
            callback_parts = [
                "schedule_interval",
                str(slot['id']),
                start_code,
                end_code
            ]
            if position_index:
                callback_parts.append(str(position_index))

            callback_data = "_".join(callback_parts)
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            intervals_added += 1

    if intervals_added > 0:
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")])

    return keyboard, intervals_added


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
    
    today = date.today()
    date_buttons: List[InlineKeyboardButton] = []
    for offset in range(14):
        target_date = today + timedelta(days=offset)
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        label = f"{target_date.strftime('%d.%m')} ({weekdays[target_date.weekday()]})"
        callback = f"schedule_date_{target_date.strftime('%Y%m%d')}"
        date_buttons.append(InlineKeyboardButton(f"📅 {label}", callback_data=callback))

    keyboard = []
    for i in range(0, len(date_buttons), 2):
        keyboard.append(date_buttons[i:i + 2])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📅 **Выберите дату планирования на ближайшие 14 дней**",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_schedule_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора даты для планирования."""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()
    
    data = query.data or ""
    selected_date: Optional[date] = None
    if data.startswith("schedule_date_"):
        raw = data.split("_")[-1]
        try:
            year = int(raw[:4])
            month = int(raw[4:6])
            day = int(raw[6:])
            selected_date = date(year, month, day)
        except (ValueError, IndexError):
            selected_date = None
    elif data == "schedule_date_today":
        selected_date = date.today()
    elif data == "schedule_date_tomorrow":
        selected_date = date.today() + timedelta(days=1)

    if not selected_date:
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
        
        logger.info(
            "Bot scheduling: free intervals prepared",
            user_id=user_id,
            object_id=object_id,
            selected_date=selected_date.isoformat(),
            slots=len(available_slots)
        )

        keyboard, intervals_added = _build_interval_keyboard(available_slots)
        if intervals_added == 0:
            await query.edit_message_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет свободных интервалов для планирования.\n\n"
                "Попробуйте выбрать другую дату или создайте дополнительные тайм-слоты.",
                parse_mode='Markdown'
            )
            return
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🕐 **Свободные интервалы на {selected_date.strftime('%d.%m.%Y')}**\n\n"
            "Выберите свободный интервал для планирования смены:",
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
    await query.answer()
    
    data = query.data or ""
    interval_payload = None

    if data.startswith("schedule_interval_"):
        parts = data.split("_")
        if len(parts) < 5:
            await query.edit_message_text("❌ Ошибка: не удалось определить интервал.")
            return
        try:
            slot_id = int(parts[2])
            start_code = parts[3]
            end_code = parts[4]
            start_time = time(hour=int(start_code[:2]), minute=int(start_code[2:]))
            end_time = time(hour=int(end_code[:2]), minute=int(end_code[2:]))
            interval_payload = (start_time, end_time)
        except (ValueError, IndexError):
            await query.edit_message_text("❌ Ошибка: некорректные данные интервала.")
            return
    elif data.startswith("schedule_select_slot_"):
        slot_id = int(data.split("_")[-1])
    else:
        await query.edit_message_text("❌ Некорректный запрос.")
        return
    
    # Получаем данные из контекста
    object_id = context.user_data.get('selected_object_id')
    selected_date = context.user_data.get('selected_date')
    
    if not object_id or not selected_date:
        await query.edit_message_text("❌ Ошибка: данные сессии утеряны.")
        return
    
    try:
        # Получаем информацию о тайм-слоте
        from apps.bot.services.time_slot_service import TimeSlotService
        time_slot_service = TimeSlotService()
        timeslot_data = time_slot_service.get_timeslot_by_id(slot_id)
        
        if not timeslot_data:
            await query.edit_message_text("❌ Ошибка: тайм-слот не найден.")
            return
        
        if interval_payload:
            start_time, end_time = interval_payload
        else:
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

        logger.info(
            "Bot scheduling result",
            user_id=user_id,
            slot_id=slot_id,
            start_time=start_time.strftime('%H:%M'),
            end_time=end_time.strftime('%H:%M'),
            success=result.get('success'),
            error=result.get('error')
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
        
        # Определяем чат для отчетов (notification_targets + legacy)
        from shared.services.notification_target_service import get_telegram_report_chat_id_for_object
        report_chat_id = await get_telegram_report_chat_id_for_object(session, obj) if obj else None
        
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
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("✅ Готово", callback_data="cancel_done_photo"),
                    InlineKeyboardButton("⏩ Пропустить", callback_data="cancel_skip_photo"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📸 **Фото подтверждения** (опционально)\n\n"
                "Отправьте фото документа или нажмите **Готово** / **Пропустить**.",
                parse_mode="Markdown",
                reply_markup=reply_markup,
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
    """Добавить фото в поток отмены. Готово/Пропустить — в callback."""
    telegram_id = update.effective_user.id
    shift_id = context.user_data.get("cancelling_shift_id")
    reason = context.user_data.get("cancel_reason")
    if not shift_id or not reason:
        await update.message.reply_text("❌ Ошибка: данные отмены не найдены.")
        return

    photo = update.message.photo[-1] if update.message.photo else None
    if not photo:
        return

    from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    orchestrator = MediaOrchestrator()
    
    # Проверяем, есть ли активный поток, если нет - создаем
    flow = await orchestrator.get_flow(telegram_id)
    if not flow:
        logger.info("No media flow found, creating new one", telegram_id=telegram_id, shift_id=shift_id)
        flow_cfg = MediaFlowConfig(
            user_id=telegram_id,
            context_type="cancellation_doc",
            context_id=shift_id,
            collected_photos=[],
        )
        await orchestrator.begin_flow(flow_cfg)
        logger.info("Created media flow for cancellation", telegram_id=telegram_id, shift_id=shift_id)
    else:
        logger.info("Using existing media flow", telegram_id=telegram_id, shift_id=shift_id, photos_count=len(flow.collected_photos) if flow.collected_photos else 0)
    
    await orchestrator.add_photo(telegram_id, photo.file_id)
    n = await orchestrator.get_collected_count(telegram_id)
    can_add = await orchestrator.can_add_more(telegram_id)
    
    logger.info(
        "Photo added to cancellation flow",
        telegram_id=telegram_id,
        shift_id=shift_id,
        photo_count=n,
        can_add_more=can_add,
    )
    
    # Сохраняем фото в контекст на случай, если поток потеряется
    if "cancellation_photos" not in context.user_data:
        context.user_data["cancellation_photos"] = []
    context.user_data["cancellation_photos"].append(photo.file_id)
    
    await orchestrator.close()

    keyboard = [
        [
            InlineKeyboardButton("✅ Готово", callback_data="cancel_done_photo"),
            InlineKeyboardButton("⏩ Пропустить", callback_data="cancel_skip_photo"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"📸 Добавлено фото ({n}). Отправьте ещё или нажмите **Готово** / **Пропустить**."
    if not can_add:
        text = f"📸 Добавлено фото ({n}). Лимит достигнут. Нажмите **Готово**."
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_cancellation_skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пропустить фото → отмена потока, выполнить отмену смены без медиа."""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    shift_id = context.user_data.get("cancelling_shift_id")
    reason = context.user_data.get("cancel_reason")
    if not shift_id or not reason:
        await query.edit_message_text("❌ Ошибка: данные отмены не найдены.")
        return

    from shared.services.media_orchestrator import MediaOrchestrator
    from core.state.user_state_manager import user_state_manager

    orchestrator = MediaOrchestrator()
    await orchestrator.cancel(telegram_id)
    await orchestrator.close()
    await user_state_manager.clear_state(telegram_id)

    await _execute_shift_cancellation(
        shift_id=shift_id,
        telegram_id=telegram_id,
        reason=reason,
        reason_notes=context.user_data.get("cancel_reason_notes"),
        document_description=context.user_data.get("cancel_document_description"),
        context=context,
        query=query,
        media=None,
    )


async def handle_cancellation_done_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Готово с фото: finish → upload → опционально в группу → отмена смены с медиа."""
    query = update.callback_query
    await query.answer()
    telegram_id = update.effective_user.id
    shift_id = context.user_data.get("cancelling_shift_id")
    reason = context.user_data.get("cancel_reason")
    report_chat_id = context.user_data.get("report_chat_id")
    if not shift_id or not reason:
        await query.edit_message_text("❌ Ошибка: данные отмены не найдены.")
        return

    from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig
    from core.state.user_state_manager import user_state_manager
    from core.database.session import get_async_session
    from shared.services.owner_media_storage_service import get_storage_mode

    orchestrator = MediaOrchestrator()
    
    # Проверяем, есть ли активный поток медиа
    flow = await orchestrator.get_flow(telegram_id)
    logger.info(
        "Cancellation done photo: checking flow",
        telegram_id=telegram_id,
        shift_id=shift_id,
        has_flow=flow is not None,
        flow_collected_photos=len(flow.collected_photos) if flow and flow.collected_photos else 0,
        context_photos=len(context.user_data.get("cancellation_photos", [])),
    )
    
    if not flow:
        # Если потока нет, но есть фото в контексте, создаем поток
        collected_photos = context.user_data.get("cancellation_photos", [])
        if collected_photos:
            logger.info("Creating media flow from context photos", telegram_id=telegram_id, shift_id=shift_id, photos_count=len(collected_photos))
            # Создаем временный поток для загрузки медиа
            flow_cfg = MediaFlowConfig(
                user_id=telegram_id,
                context_type="cancellation_doc",
                context_id=shift_id,
                collected_photos=collected_photos,
            )
            await orchestrator.begin_flow(flow_cfg)
            flow = flow_cfg
        else:
            logger.warning("No media flow and no photos in context for cancellation", telegram_id=telegram_id, shift_id=shift_id)
    
    storage_mode = "telegram"
    async with get_async_session() as session:
        shift_result = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
        shift = shift_result.scalar_one_or_none()
        obj = None
        if shift:
            # Получаем объект с eager loading org_unit для определения report_chat_id
            from sqlalchemy.orm import joinedload
            object_query = select(Object).where(Object.id == shift.object_id).options(
                joinedload(Object.org_unit).joinedload('parent').joinedload('parent').joinedload('parent').joinedload('parent')
            )
            obj_result = await session.execute(object_query)
            obj = obj_result.scalar_one_or_none()
        
        if obj:
            storage_mode = await get_storage_mode(session, obj.owner_id, "cancellations")
            if not report_chat_id:
                from shared.services.notification_target_service import get_telegram_report_chat_id_for_object
                report_chat_id = await get_telegram_report_chat_id_for_object(session, obj)
                if report_chat_id:
                    context.user_data['report_chat_id'] = report_chat_id
                    logger.info("Determined report_chat_id from object", shift_id=shift_id, report_chat_id=report_chat_id)

    # Завершаем поток и загружаем медиа
    logger.info(
        "Finishing media flow",
        telegram_id=telegram_id,
        shift_id=shift_id,
        storage_mode=storage_mode,
        has_flow=flow is not None,
        flow_photos=len(flow.collected_photos) if flow and flow.collected_photos else 0,
    )
    
    flow = await orchestrator.finish(
        telegram_id, bot=context.bot, media_types=None, storage_mode=storage_mode
    )
    await orchestrator.close()
    await user_state_manager.clear_state(telegram_id)

    logger.info(
        "Media flow finished",
        telegram_id=telegram_id,
        shift_id=shift_id,
        has_flow=flow is not None,
        uploaded_count=len(flow.uploaded_media) if flow and flow.uploaded_media else 0,
        collected_count=len(flow.collected_photos) if flow and flow.collected_photos else 0,
    )

    media_list = None
    if flow and flow.uploaded_media:
        media_list = []
        for m in flow.uploaded_media:
            media_dict = {
                "key": m.key,
                "url": m.url,
                "type": m.type,
                "size": m.size,
                "mime_type": m.mime_type,
            }
            # Добавляем telegram_file_id в metadata, если есть
            if hasattr(m, "metadata") and m.metadata and "telegram_file_id" in m.metadata:
                media_dict["metadata"] = {"telegram_file_id": m.metadata["telegram_file_id"]}
            media_list.append(media_dict)
        logger.info("Cancellation media uploaded", shift_id=shift_id, media_count=len(media_list))
    elif flow and flow.collected_photos:
        logger.warning(
            "Cancellation has collected photos but no uploaded_media",
            shift_id=shift_id,
            photos_count=len(flow.collected_photos),
            storage_mode=storage_mode,
        )
    else:
        logger.warning("No media in flow after finish", shift_id=shift_id, has_flow=flow is not None)

    file_ids = (flow.collected_photos or []) if flow else []
    
    logger.info(
        "Checking conditions for sending to group",
        shift_id=shift_id,
        report_chat_id=report_chat_id,
        file_ids_count=len(file_ids),
        will_send=bool(report_chat_id and file_ids),
    )
    
    if report_chat_id and file_ids:
        try:
            from apps.bot.handlers_div.shift_handlers import _send_multiple_media_to_group
            async with get_async_session() as session:
                user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
                user = user_result.scalar_one_or_none()
                shift_result = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
                shift = shift_result.scalar_one_or_none()
                obj = None
                if shift:
                    obj_result = await session.execute(select(Object).where(Object.id == shift.object_id))
                    obj = obj_result.scalar_one_or_none()
                from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
                user_tz = get_user_timezone(user)
                local_start = convert_utc_to_local(shift.planned_start, user_tz) if shift else None
                reason_labels = {
                    "medical_cert": "🏥 Медицинская справка",
                    "emergency_cert": "🚨 Справка от МЧС",
                    "police_cert": "👮 Справка от полиции",
                    "other": "❓ Другая причина",
                }
                caption = (
                    f"❌ **Отмена смены**\n\n"
                    f"👤 Сотрудник: {user.full_name if user else 'Неизвестно'}\n"
                    f"🏢 Объект: {obj.name if obj else 'Неизвестно'}\n"
                    f"📅 Дата: {local_start.strftime('%d.%m.%Y %H:%M') if local_start else '—'}\n"
                    f"📋 Причина: {reason_labels.get(reason, reason)}\n"
                )
                doc_desc = context.user_data.get("cancel_document_description")
                reason_notes = context.user_data.get("cancel_reason_notes")
                if doc_desc:
                    caption += f"📄 Документ: {doc_desc}\n"
                if reason_notes:
                    caption += f"✍️ Объяснение: {reason_notes}\n"
                types_list = ["photo"] * len(file_ids)
                logger.info(
                    "Sending cancellation media to group",
                    shift_id=shift_id,
                    report_chat_id=report_chat_id,
                    file_ids_count=len(file_ids),
                )
                await _send_multiple_media_to_group(
                    context.bot, str(report_chat_id), file_ids, caption, types_list
                )
                logger.info("Cancellation media sent to group successfully", shift_id=shift_id, report_chat_id=report_chat_id)
        except Exception as e:
            logger.exception(
                "Error sending cancellation media to group",
                shift_id=shift_id,
                report_chat_id=report_chat_id,
                error=str(e),
            )

    await _execute_shift_cancellation(
        shift_id=shift_id,
        telegram_id=telegram_id,
        reason=reason,
        reason_notes=context.user_data.get("cancel_reason_notes"),
        document_description=context.user_data.get("cancel_document_description"),
        context=context,
        query=query,
        media=media_list,
    )


async def _execute_shift_cancellation(
    shift_id: int,
    telegram_id: int,
    reason: str,
    reason_notes: Optional[str],
    document_description: Optional[str],
    context: ContextTypes.DEFAULT_TYPE,
    query: Optional[Any] = None,
    message: Optional[Any] = None,
    media: Optional[list] = None,
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
                cancelled_by_type="employee",
                cancellation_reason=reason,
                reason_notes=reason_notes,
                document_description=document_description,
                actor_role="employee",
                source="bot",
                extra_payload={"bot_flow": True},
                media=media,
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
    
    await update.message.reply_text(
        "❌ Для планирования используйте кнопки с датами на экране.",
        parse_mode='Markdown'
    )
    await user_state_manager.clear_state(user_id)


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
        
        keyboard, intervals_added = _build_interval_keyboard(available_slots)
        if intervals_added == 0:
            await update.message.reply_text(
                f"❌ На {selected_date.strftime('%d.%m.%Y')} нет свободных интервалов для планирования.\n\n"
                "Попробуйте выбрать другую дату или создайте дополнительные тайм-слоты.",
                parse_mode='Markdown'
            )
            return
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🕐 **Свободные интервалы на {selected_date.strftime('%d.%m.%Y')}**\n\n"
            "Выберите свободный интервал для планирования смены:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error getting time slots: {e}")
        await update.message.reply_text("❌ Ошибка получения тайм-слотов. Попробуйте позже.")
