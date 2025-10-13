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
from datetime import datetime, timedelta, date, time
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
            user_state_manager.clear_state(user_id)
            context.user_data.clear()
            
            await query.edit_message_text(
                f"✅ **Смена успешно запланирована!**\n\n"
                f"📅 Дата: {selected_date.strftime('%d.%m.%Y')}\n"
                f"🕐 Время: {result.get('start_time', 'N/A')} - {result.get('end_time', 'N/A')}\n"
                f"💰 Ставка: {result.get('hourly_rate', 'N/A')} ₽/час\n\n"
                f"Вы получите напоминание за 2 часа до начала смены.",
                parse_mode='Markdown'
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
            shifts_query = select(ShiftSchedule).where(
                ShiftSchedule.user_id == user.id,
                ShiftSchedule.status == "planned"
            ).order_by(ShiftSchedule.planned_start)
            
            shifts_result = await session.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            
            if not shifts:
                await update.callback_query.edit_message_text(
                    "📅 **Ваши запланированные смены**\n\n"
                    "У вас нет запланированных смен."
                )
                return
            
            # Формируем список смен
            schedule_text = "📅 **Ваши запланированные смены:**\n\n"
            
            for shift in shifts:
                # Получаем информацию об объекте
                object_query = select(Object).where(Object.id == shift.object_id)
                object_result = await session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                object_name = obj.name if obj else "Неизвестный объект"
                
                schedule_text += f"🏢 **{object_name}**\n"
                schedule_text += f"📅 {shift.planned_start.strftime('%d.%m.%Y %H:%M')}\n"
                schedule_text += f"🕐 До {shift.planned_end.strftime('%H:%M')}\n"
                if shift.hourly_rate:
                    schedule_text += f"💰 {shift.hourly_rate} ₽/час\n"
                schedule_text += f"📊 Статус: {shift.status}\n\n"
            
            # Добавляем кнопки управления
            keyboard = []
            
            # Кнопки отмены для каждой смены (максимум 5)
            for shift in shifts[:5]:
                # Формируем текст кнопки с датой и временем
                button_text = f"❌ Отменить {shift.planned_start.strftime('%d.%m %H:%M')}"
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
            
            # Показываем кнопки выбора причины
            keyboard = [
                [InlineKeyboardButton("🏥 Медицинская справка", callback_data=f"cancel_reason_medical_cert")],
                [InlineKeyboardButton("🚨 Справка от МЧС", callback_data=f"cancel_reason_emergency_cert")],
                [InlineKeyboardButton("👮 Справка от полиции", callback_data=f"cancel_reason_police_cert")],
                [InlineKeyboardButton("❓ Другая причина", callback_data=f"cancel_reason_other")],
                [InlineKeyboardButton("🔙 Отмена", callback_data="view_schedule")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Получаем объект для отображения
            object_query = select(Object).where(Object.id == shift.object_id)
            object_result = await session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            object_name = obj.name if obj else "Неизвестный объект"
            
            await query.edit_message_text(
                f"❌ **Отмена смены**\n\n"
                f"🏢 **{object_name}**\n"
                f"📅 {shift.planned_start.strftime('%d.%m.%Y %H:%M')}\n"
                f"🕐 До {shift.planned_end.strftime('%H:%M')}\n\n"
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
    telegram_id = update.effective_user.id
    
    # Извлекаем причину из callback_data
    reason = query.data.replace("cancel_reason_", "")
    shift_id = context.user_data.get('cancelling_shift_id')
    
    if not shift_id:
        await query.edit_message_text("❌ Ошибка: смена не найдена в контексте.")
        return
    
    # Сохраняем причину в контекст
    context.user_data['cancel_reason'] = reason
    
    # Для справок просим ввести описание
    if reason in ['medical_cert', 'emergency_cert', 'police_cert']:
        reason_names = {
            'medical_cert': 'медицинской справки',
            'emergency_cert': 'справки от МЧС',
            'police_cert': 'справки от полиции'
        }
        
        # Устанавливаем состояние ожидания ввода
        from core.state.user_state_manager import user_state_manager, UserAction, UserStep
        user_state_manager.set_state(
            telegram_id,
            action=UserAction.CANCEL_SHIFT,
            step=UserStep.INPUT_DOCUMENT
        )
        
        await query.edit_message_text(
            f"📄 **Описание {reason_names[reason]}**\n\n"
            f"Укажите номер и дату документа.\n"
            f"Например: `№123 от 10.10.2025`\n\n"
            f"Справка будет проверена владельцем.",
            parse_mode='Markdown'
        )
    else:
        # Для других причин сразу отменяем
        await _execute_shift_cancellation(
            shift_id=shift_id,
            telegram_id=telegram_id,
            reason=reason,
            reason_notes=None,
            document_description=None,
            context=context,
            query=query
        )


async def handle_cancellation_document_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода описания документа для отмены."""
    telegram_id = update.effective_user.id
    document_description = update.message.text
    
    shift_id = context.user_data.get('cancelling_shift_id')
    reason = context.user_data.get('cancel_reason')
    
    if not shift_id or not reason:
        await update.message.reply_text("❌ Ошибка: данные отмены не найдены.")
        return
    
    # Очищаем состояние
    from core.state.user_state_manager import user_state_manager
    user_state_manager.clear_state(telegram_id)
    
    # Выполняем отмену
    await _execute_shift_cancellation(
        shift_id=shift_id,
        telegram_id=telegram_id,
        reason=reason,
        reason_notes=None,
        document_description=document_description,
        context=context,
        message=update.message
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
) -> None:
    """Выполнить отмену смены с использованием сервиса."""
    from core.database.session import get_async_session
    from shared.services.shift_cancellation_service import ShiftCancellationService
    
    try:
        async with get_async_session() as session:
            # Находим пользователя
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                text = "❌ Пользователь не найден."
                if query:
                    await query.edit_message_text(text)
                elif message:
                    await message.reply_text(text)
                return
            
            # Используем сервис для отмены
            cancellation_service = ShiftCancellationService(session)
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
                
                text = (
                    f"✅ **Смена отменена**\n\n"
                    f"🏢 **{object_name}**\n"
                    f"📅 {shift.planned_start.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🕐 До {shift.planned_end.strftime('%H:%M')}\n"
                )
                
                # Добавляем информацию о штрафе
                if result['fine_amount']:
                    text += f"\n💰 Штраф: {result['fine_amount']}₽"
                    if reason in ['medical_cert', 'emergency_cert', 'police_cert']:
                        text += "\n📄 Справка будет проверена владельцем."
                
                # Очищаем контекст
                context.user_data.pop('cancelling_shift_id', None)
                context.user_data.pop('cancel_reason', None)
                
                if query:
                    await query.edit_message_text(text, parse_mode='Markdown')
                elif message:
                    await message.reply_text(text, parse_mode='Markdown')
                
                # TODO: Отправить уведомление владельцу/управляющему
                
            else:
                text = f"❌ {result['message']}"
                if query:
                    await query.edit_message_text(text)
                elif message:
                    await message.reply_text(text)
    
    except Exception as e:
        logger.error(f"Error executing shift cancellation: {e}")
        text = "❌ Ошибка отмены смены. Попробуйте позже."
        if query:
            await query.edit_message_text(text)
        elif message:
            await message.reply_text(text)


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
    user_state_manager.clear_state(user_id)
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
