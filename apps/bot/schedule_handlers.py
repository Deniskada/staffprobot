"""Обработчики команд планирования смен."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.schedule_service import ScheduleService
from apps.bot.services.object_service import ObjectService
from core.state import user_state_manager, UserAction, UserStep
from datetime import datetime, timedelta, timezone
import re


# Создаем экземпляры сервисов
schedule_service = ScheduleService()
object_service = ObjectService()


async def handle_schedule_shift(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало планирования смены."""
    user_id = update.effective_user.id
    
    try:
        # Очищаем предыдущее состояние
        user_state_manager.clear_state(user_id)
        
        # Получаем список объектов
        objects = object_service.get_all_objects()
        
        if not objects:
            await update.callback_query.edit_message_text(
                "❌ Нет доступных объектов для планирования смены.\n"
                "Сначала создайте объект."
            )
            return
        
        # Создаем состояние для планирования смены
        user_state_manager.create_state(
            user_id=user_id,
            action=UserAction.SCHEDULE_SHIFT,
            step=UserStep.OBJECT_SELECTION
        )
        
        # Создаем кнопки для выбора объекта
        keyboard = []
        for obj in objects:
            keyboard.append([
                InlineKeyboardButton(
                    f"🏢 {obj['name']} ({obj['opening_time']}-{obj['closing_time']})",
                    callback_data=f"schedule_select_object_{obj['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "📅 <b>Планирование смены</b>\n\n"
            "Выберите объект для планирования смены:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Schedule shift started for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_schedule_shift: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при планировании смены. Попробуйте позже."
        )


async def handle_schedule_object_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора объекта для планирования."""
    user_id = update.effective_user.id
    callback_data = update.callback_query.data
    
    try:
        # Извлекаем ID объекта из callback_data
        object_id = int(callback_data.split("_")[-1])
        
        # Получаем состояние пользователя
        state = user_state_manager.get_state(user_id)
        if not state or state.action != UserAction.SCHEDULE_SHIFT:
            await update.callback_query.edit_message_text(
                "❌ Сессия истекла. Начните планирование заново."
            )
            return
        
        # Обновляем состояние
        user_state_manager.update_state(
            user_id=user_id,
            selected_object_id=object_id,
            step=UserStep.INPUT_DATE
        )
        
        # Получаем информацию об объекте
        obj = object_service.get_object_by_id(object_id)
        if not obj:
            await update.callback_query.edit_message_text(
                "❌ Объект не найден."
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="schedule_date_today")],
            [InlineKeyboardButton("📅 Завтра", callback_data="schedule_date_tomorrow")],
            [InlineKeyboardButton("📅 Другая дата", callback_data="schedule_date_custom")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            f"📅 <b>Планирование смены</b>\n\n"
            f"🏢 Объект: <b>{obj['name']}</b>\n"
            f"⏰ Время работы: {obj['opening_time']}-{obj['closing_time']}\n"
            f"💰 Ставка: {obj['hourly_rate']}₽/час\n\n"
            f"Выберите дату для планирования смены:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Object {object_id} selected for scheduling by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_schedule_object_selection: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при выборе объекта."
        )


async def handle_schedule_date_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора даты для планирования."""
    user_id = update.effective_user.id
    callback_data = update.callback_query.data
    
    try:
        state = user_state_manager.get_state(user_id)
        if not state or state.action != UserAction.SCHEDULE_SHIFT:
            await update.callback_query.edit_message_text(
                "❌ Сессия истекла. Начните планирование заново."
            )
            return
        
        # Определяем дату
        if callback_data == "schedule_date_today":
            selected_date = datetime.now(timezone.utc).date()
        elif callback_data == "schedule_date_tomorrow":
            selected_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()
        elif callback_data == "schedule_date_custom":
            # Для упрощения пока используем завтрашний день
            # В будущем можно добавить календарь
            selected_date = (datetime.now(timezone.utc) + timedelta(days=1)).date()
            await update.callback_query.edit_message_text(
                "📅 Для выбора произвольной даты отправьте дату в формате ДД.ММ.ГГГГ\n"
                "Например: 25.12.2024\n\n"
                "Или используйте кнопки для быстрого выбора."
            )
            user_state_manager.update_state(
                user_id=user_id,
                step=UserStep.INPUT_DATE
            )
            return
        
        # Сохраняем выбранную дату
        user_state_manager.update_state(
            user_id=user_id,
            step=UserStep.INPUT_START_TIME,
            data={'selected_date': selected_date}
        )
        
        # Получаем информацию об объекте
        obj = object_service.get_object_by_id(state.selected_object_id)
        
        await update.callback_query.edit_message_text(
            f"📅 <b>Планирование смены</b>\n\n"
            f"🏢 Объект: <b>{obj['name']}</b>\n"
            f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"⏰ Время работы объекта: {obj['opening_time']}-{obj['closing_time']}\n\n"
            f"⏰ Введите время <b>начала</b> смены в формате ЧЧ:ММ\n"
            f"Например: 09:00",
            parse_mode='HTML'
        )
        
        logger.info(f"Date {selected_date} selected for scheduling by user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_schedule_date_selection: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при выборе даты."
        )


async def handle_schedule_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода времени для планирования."""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    try:
        state = user_state_manager.get_state(user_id)
        if not state or state.action != UserAction.SCHEDULE_SHIFT:
            await update.message.reply_text(
                "❌ Сессия планирования истекла. Начните заново командой /start."
            )
            return
        
        # Проверяем формат времени
        time_pattern = r'^([0-1]?[0-9]|2[0-3]):([0-5][0-9])$'
        if not re.match(time_pattern, message_text):
            await update.message.reply_text(
                "❌ Неверный формат времени. Используйте формат ЧЧ:ММ\n"
                "Например: 09:00 или 14:30"
            )
            return
        
        # Парсим время
        time_parts = message_text.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        if state.step == UserStep.INPUT_START_TIME:
            # Сохраняем время начала и запрашиваем время окончания
            user_state_manager.update_state(
                user_id=user_id,
                step=UserStep.INPUT_END_TIME,
                data={'start_time': f"{hour:02d}:{minute:02d}"}
            )
            
            obj = object_service.get_object_by_id(state.selected_object_id)
            selected_date = state.get_data('selected_date')
            
            await update.message.reply_text(
                f"📅 <b>Планирование смены</b>\n\n"
                f"🏢 Объект: <b>{obj['name']}</b>\n"
                f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
                f"🕐 Начало: <b>{hour:02d}:{minute:02d}</b>\n"
                f"⏰ Время работы объекта: {obj['opening_time']}-{obj['closing_time']}\n\n"
                f"⏰ Введите время <b>окончания</b> смены в формате ЧЧ:ММ\n"
                f"Например: 18:00",
                parse_mode='HTML'
            )
            
        elif state.step == UserStep.INPUT_END_TIME:
            # Сохраняем время окончания и показываем подтверждение
            start_time = state.get_data('start_time')
            end_time = f"{hour:02d}:{minute:02d}"
            
            # Создаем datetime объекты для валидации
            from core.utils.timezone_helper import timezone_helper
            selected_date = state.get_data('selected_date')
            
            # Создаем naive datetime объекты в локальном времени
            start_datetime_naive = datetime.combine(selected_date, datetime.strptime(start_time, '%H:%M').time())
            end_datetime_naive = datetime.combine(selected_date, datetime.strptime(end_time, '%H:%M').time())
            
            # Конвертируем в UTC для сохранения в базу
            start_datetime = timezone_helper.local_to_utc(start_datetime_naive)
            end_datetime = timezone_helper.local_to_utc(end_datetime_naive)
            
            # Проверяем, что время окончания позже времени начала
            if end_datetime <= start_datetime:
                await update.message.reply_text(
                    "❌ Время окончания должно быть позже времени начала.\n"
                    "Введите время окончания смены:"
                )
                return
            
            # Сохраняем данные и переходим к подтверждению
            user_state_manager.update_state(
                user_id=user_id,
                step=UserStep.CONFIRM_SCHEDULE,
                data={
                    'end_time': end_time,
                    'start_datetime': start_datetime,
                    'end_datetime': end_datetime
                }
            )
            
            obj = object_service.get_object_by_id(state.selected_object_id)
            duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
            planned_payment = float(obj['hourly_rate']) * duration_hours
            
            keyboard = [
                [InlineKeyboardButton("✅ Подтвердить", callback_data="schedule_confirm")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_action")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📅 <b>Подтверждение планирования смены</b>\n\n"
                f"🏢 Объект: <b>{obj['name']}</b>\n"
                f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
                f"🕐 Время: <b>{start_time} - {end_time}</b> (местное время)\n"
                f"⏱ Длительность: <b>{duration_hours:.1f} ч.</b>\n"
                f"💰 Планируемая оплата: <b>{planned_payment:.2f}₽</b>\n\n"
                f"Подтвердите планирование смены:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        logger.info(f"Time input processed for user {user_id}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error in handle_schedule_time_input: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке времени."
        )


async def handle_schedule_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение планирования смены."""
    user_id = update.effective_user.id
    
    try:
        state = user_state_manager.get_state(user_id)
        if not state or state.action != UserAction.SCHEDULE_SHIFT:
            await update.callback_query.edit_message_text(
                "❌ Сессия планирования истекла."
            )
            return
        
        # Получаем данные для создания смены
        start_datetime = state.get_data('start_datetime')
        end_datetime = state.get_data('end_datetime')
        
        # Создаем запланированную смену
        result = await schedule_service.create_scheduled_shift(
            user_id=user_id,
            object_id=state.selected_object_id,
            planned_start=start_datetime,
            planned_end=end_datetime
        )
        
        # Очищаем состояние
        user_state_manager.clear_state(user_id)
        
        if result['success']:
            await update.callback_query.edit_message_text(
                f"✅ <b>Смена успешно запланирована!</b>\n\n"
                f"🏢 Объект: <b>{result['object_name']}</b>\n"
                f"📅 {result['message']}\n"
                f"⏱ Длительность: <b>{result['planned_duration']:.1f} ч.</b>\n"
                f"💰 Планируемая оплата: <b>{result['planned_payment']:.2f}₽</b>\n\n"
                f"📱 Напоминание будет отправлено за 2 часа до начала смены.",
                parse_mode='HTML'
            )
        else:
            error_message = f"❌ <b>Ошибка планирования смены:</b>\n\n{result['error']}"
            
            if 'conflicts' in result:
                error_message += "\n\n<b>Конфликты:</b>\n"
                for conflict in result['conflicts']:
                    error_message += f"• {conflict['type']}: {conflict['time_range']}\n"
            
            await update.callback_query.edit_message_text(
                error_message,
                parse_mode='HTML'
            )
        
        logger.info(f"Schedule confirmation processed for user {user_id}: {result['success']}")
        
    except Exception as e:
        logger.error(f"Error in handle_schedule_confirmation: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при подтверждении планирования."
        )


async def handle_view_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Просмотр запланированных смен."""
    user_id = update.effective_user.id
    
    try:
        # Получаем запланированные смены пользователя
        scheduled_shifts = await schedule_service.get_user_scheduled_shifts(
            user_id=user_id,
            status_filter='planned'
        )
        
        if not scheduled_shifts:
            keyboard = [
                [InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "📅 <b>Мои запланированные смены</b>\n\n"
                "У вас пока нет запланированных смен.\n\n"
                "Хотите запланировать смену?",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        # Формируем сообщение со списком смен
        message = "📅 <b>Мои запланированные смены</b>\n\n"
        
        keyboard = []
        for shift in scheduled_shifts:
            status_emoji = "🟢" if shift['is_upcoming'] else "🟡"
            message += (
                f"{status_emoji} <b>{shift['object_name']}</b>\n"
                f"📅 {shift['formatted_time_range']}\n"
                f"⏱ {shift['planned_duration_hours']:.1f} ч. "
                f"💰 {shift['planned_payment']:.2f}₽\n"
            )
            
            if shift['can_be_cancelled']:
                message += "❌ Можно отменить\n"
                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ Отменить: {shift['object_name']} {shift['formatted_time_range'][:10]}",
                        callback_data=f"cancel_schedule_{shift['id']}"
                    )
                ])
            else:
                message += "⏰ Нельзя отменить (менее часа до начала)\n"
            
            message += "\n"
        
        keyboard.append([
            InlineKeyboardButton("📅 Запланировать ещё", callback_data="schedule_shift")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Schedule viewed by user {user_id}: {len(scheduled_shifts)} shifts")
        
    except Exception as e:
        logger.error(f"Error in handle_view_schedule: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при получении расписания."
        )


async def handle_cancel_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отмена запланированной смены."""
    user_id = update.effective_user.id
    callback_data = update.callback_query.data
    
    try:
        # Извлекаем ID запланированной смены
        schedule_id = int(callback_data.split("_")[-1])
        
        # Отменяем смену
        result = await schedule_service.cancel_scheduled_shift(
            user_id=user_id,
            schedule_id=schedule_id
        )
        
        if result['success']:
            await update.callback_query.edit_message_text(
                f"✅ <b>Смена отменена</b>\n\n"
                f"{result['message']}\n\n"
                f"Вы можете запланировать новую смену в любое время.",
                parse_mode='HTML'
            )
        else:
            await update.callback_query.edit_message_text(
                f"❌ <b>Ошибка отмены смены:</b>\n\n{result['error']}",
                parse_mode='HTML'
            )
        
        logger.info(f"Schedule cancellation processed for user {user_id}: {result['success']}")
        
    except Exception as e:
        logger.error(f"Error in handle_cancel_schedule: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при отмене смены."
        )


async def handle_custom_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода произвольной даты."""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    try:
        state = user_state_manager.get_state(user_id)
        if not state or state.action != UserAction.SCHEDULE_SHIFT or state.step != UserStep.INPUT_DATE:
            return
        
        # Проверяем формат даты
        date_pattern = r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$'
        match = re.match(date_pattern, message_text)
        
        if not match:
            await update.message.reply_text(
                "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ\n"
                "Например: 25.12.2024"
            )
            return
        
        # Парсим дату
        day, month, year = map(int, match.groups())
        
        try:
            selected_date = datetime(year, month, day).date()
        except ValueError:
            await update.message.reply_text(
                "❌ Некорректная дата. Проверьте правильность ввода."
            )
            return
        
        # Проверяем, что дата не в прошлом
        if selected_date < datetime.now(timezone.utc).date():
            await update.message.reply_text(
                "❌ Нельзя планировать смены на прошедшие даты."
            )
            return
        
        # Сохраняем дату и переходим к вводу времени
        user_state_manager.update_state(
            user_id=user_id,
            step=UserStep.INPUT_START_TIME,
            data={'selected_date': selected_date}
        )
        
        obj = object_service.get_object_by_id(state.selected_object_id)
        
        await update.message.reply_text(
            f"📅 <b>Планирование смены</b>\n\n"
            f"🏢 Объект: <b>{obj['name']}</b>\n"
            f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n"
            f"⏰ Время работы объекта: {obj['opening_time']}-{obj['closing_time']}\n\n"
            f"⏰ Введите время <b>начала</b> смены в формате ЧЧ:ММ\n"
            f"Например: 09:00",
            parse_mode='HTML'
        )
        
        logger.info(f"Custom date {selected_date} set for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_custom_date_input: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке даты."
        )
