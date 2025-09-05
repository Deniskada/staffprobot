"""Обработчики для планирования смен."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from shared.services.adapters import ScheduleServiceAdapter
from apps.bot.services.object_service import ObjectService
from core.state import user_state_manager, UserAction, UserStep
from core.database.connection import get_sync_session
from domain.entities.object import Object
from domain.entities.shift_schedule import ShiftSchedule
from sqlalchemy import select
from datetime import datetime, timedelta, date, time
from typing import List, Dict, Any

# Создаем экземпляры сервисов
schedule_service = ScheduleServiceAdapter()
object_service = ObjectService()


async def handle_schedule_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало планирования смены."""
    user_id = update.effective_user.id
    
    # Получаем доступные объекты пользователя
    try:
        with get_sync_session() as session:
            # Сначала находим пользователя по telegram_id
            from domain.entities.user import User
            user_query = select(User).where(User.telegram_id == user_id)
            user_result = session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                await update.callback_query.edit_message_text(
                    "❌ Пользователь не найден в базе данных."
                )
                return
            
            # Теперь находим объекты пользователя
            objects_query = select(Object).where(Object.owner_id == user.id, Object.is_active == True)
            objects_result = session.execute(objects_query)
            objects = objects_result.scalars().all()
            
            if not objects:
                await update.callback_query.edit_message_text(
                    "❌ У вас нет доступных объектов для планирования смен.\n\n"
                    "Сначала создайте объект через меню управления объектами."
                )
                return
            
            # Создаем клавиатуру с объектами
            keyboard = []
            for obj in objects:
                keyboard.append([InlineKeyboardButton(
                    f"🏢 {obj.name}",
                    callback_data=f"schedule_select_object_{obj.id}"
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
        # Создаем запланированную смену
        result = await schedule_service.create_scheduled_shift_from_timeslot(
            user_id=user_id,
            time_slot_id=slot_id,
            start_time=None,  # Будет использовано время из тайм-слота
            end_time=None,    # Будет использовано время из тайм-слота
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
    user_id = update.effective_user.id
    
    try:
        with get_sync_session() as session:
            # Получаем запланированные смены пользователя
            schedules_query = select(ShiftSchedule).where(
                ShiftSchedule.user_id == user_id,
                ShiftSchedule.status == "planned"
            ).order_by(ShiftSchedule.planned_start)
            
            schedules_result = session.execute(schedules_query)
            schedules = schedules_result.scalars().all()
            
            if not schedules:
                await update.callback_query.edit_message_text(
                    "📅 **Ваши запланированные смены**\n\n"
                    "У вас нет запланированных смен."
                )
                return
            
            # Формируем список смен
            schedule_text = "📅 **Ваши запланированные смены:**\n\n"
            
            for schedule in schedules:
                # Получаем информацию об объекте
                object_query = select(Object).where(Object.id == schedule.object_id)
                object_result = session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                object_name = obj.name if obj else "Неизвестный объект"
                
                schedule_text += f"🏢 **{object_name}**\n"
                schedule_text += f"📅 {schedule.planned_start.strftime('%d.%m.%Y %H:%M')}\n"
                schedule_text += f"🕐 До {schedule.planned_end.strftime('%H:%M')}\n"
                if schedule.hourly_rate:
                    schedule_text += f"💰 {schedule.hourly_rate} ₽/час\n"
                schedule_text += f"📊 Статус: {schedule.status}\n\n"
            
            # Добавляем кнопки управления
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="view_schedule")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_schedule")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                schedule_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Error viewing schedule: {e}")
        await update.callback_query.edit_message_text(
            "❌ Ошибка получения расписания. Попробуйте позже."
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
        
        # Создаем временный callback_query для вызова функции
        class TempCallback:
            def __init__(self, data):
                self.data = data
        
        temp_callback = TempCallback("schedule_date_custom")
        update.callback_query = temp_callback
        
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
