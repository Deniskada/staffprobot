"""Служебные обработчики бота."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.shift_service import ShiftService
from apps.bot.services.object_service import ObjectService
from core.utils.timezone_helper import timezone_helper
from core.state import user_state_manager, UserAction, UserStep
# Импорты удаленных файлов убраны

# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()


async def _handle_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на нажатие кнопки 'Помощь' через callback."""
    query = update.callback_query
    help_text = """
❓ <b>Справка по StaffProBot</b>

<b>Основные команды:</b>
/start - Запуск бота и главное меню
/help - Эта справка
/status - Статус ваших смен

<b>Основные функции:</b>
🔄 <b>Открыть смену</b>
🔚 <b>Закрыть смену</b>
📅 <b>Запланировать смену</b>
🏢 <b>Создать объект</b>
⚙️ <b>Управление объектами</b>
📊 <b>Отчет</b>

<b>Геолокация:</b>
📍 Для открытия/закрытия смен требуется отправка геопозиции
📏 Проверяется расстояние до объекта (по умолчанию 500м)
🎯 Используйте кнопку "📍 Отправить геопозицию"

<b>Тайм-слоты:</b>
🕐 Планирование смен через предустановленные временные слоты
➕ Создание обычных и дополнительных слотов
📅 Управление расписанием на день/неделю
"""
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
    await query.edit_message_text(text=help_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


async def _handle_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на нажатие кнопки 'Статус' через callback."""
    query = update.callback_query
    user_id = query.from_user.id
    try:
        active_shifts = await shift_service.get_user_shifts(user_id, status='active')
        if not active_shifts:
            status_text = """
📈 <b>Статус смен</b>

✅ <b>Активных смен нет</b>

Вы можете открыть новую смену через главное меню.
"""
        else:
            shift = active_shifts[0]
            obj_data = object_service.get_object_by_id(shift['object_id'])
            user_timezone = timezone_helper.get_user_timezone(user_id)
            from datetime import datetime
            try:
                start_time_utc = datetime.strptime(shift['start_time'], '%Y-%m-%d %H:%M:%S')
                local_start_time = timezone_helper.format_local_time(start_time_utc, user_timezone)
            except Exception:
                local_start_time = shift.get('start_time', '')
            obj_name = obj_data['name'] if obj_data else 'Неизвестный'
            hourly_rate = obj_data['hourly_rate'] if obj_data else 0
            status_text = f"""
📈 <b>Статус смен</b>

🟢 <b>Активная смена:</b>
🏢 Объект: {obj_name}
🕐 Начало: {local_start_time}
💰 Ставка: {hourly_rate}₽/час

Для завершения смены используйте кнопку "🔚 Закрыть смену".
"""
    except Exception as e:
        logger.error(f"Error getting user status for {user_id}: {e}")
        status_text = """
📈 <b>Статус смен</b>

❌ <b>Ошибка получения статуса</b>

Попробуйте позже или обратитесь к администратору.
"""
    keyboard = [
        [InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"), InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
    ]
    await query.edit_message_text(text=status_text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений."""
    text = update.message.text
    user_id = update.effective_user.id
    
    logger.info(f"Received text message: user_id={user_id}, text='{text}'")
    
    # Обработка отмены
    if text == "❌ Отмена":
        await handle_cancel(update, context)
        return
    
    # Проверяем состояние пользователя для обработки диалогов создания объекта
    from .object_creation_handlers import user_object_creation_state, handle_create_object_input
    if user_id in user_object_creation_state:
        logger.info(f"User {user_id} is in object creation state, processing input")
        await handle_create_object_input(update, context, text)
        return
    
    # Проверяем состояние пользователя для редактирования объектов
    user_state = user_state_manager.get_state(user_id)
    if user_state and user_state.action == UserAction.EDIT_OBJECT:
        from .object_handlers import _handle_edit_object_input
        await _handle_edit_object_input(update, context, user_state)
        return
    
    # Проверяем состояние пользователя для планирования смен
    if user_state and user_state.action == UserAction.SCHEDULE_SHIFT:
        if user_state.step == UserStep.INPUT_DATE:
            from .schedule_handlers import handle_custom_date_input
            await handle_custom_date_input(update, context)
            return
    
    # Проверяем состояние пользователя для создания тайм-слотов
    if user_state and user_state.action == UserAction.CREATE_TIMESLOT:
        if user_state.step == UserStep.INPUT_DATE:
            await _handle_timeslot_date_input(update, context, user_state)
            return
    
    # Проверяем состояние пользователя для редактирования тайм-слотов
    if user_state and user_state.action in [UserAction.EDIT_TIMESLOT_TIME, UserAction.EDIT_TIMESLOT_RATE, 
                                           UserAction.EDIT_TIMESLOT_EMPLOYEES, UserAction.EDIT_TIMESLOT_NOTES]:
        await _handle_timeslot_edit_input(update, context, user_state)
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
    await update.message.reply_text(
        "❌ Действие отменено",
        reply_markup=ReplyKeyboardRemove()
    )


async def _handle_timeslot_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state):
    """Обработчик ввода даты для создания тайм-слота."""
    user_id = update.effective_user.id
    text = update.message.text
    object_id = user_state.selected_object_id
    slot_type = user_state.data.get('slot_type')
    
    # Парсим дату
    try:
        from datetime import datetime
        parsed_date = datetime.strptime(text, '%d.%m.%Y').date()
        slot_date = parsed_date.strftime('%Y-%m-%d')
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ (например: 15.09.2025)"
        )
        return
    
    # Очищаем состояние пользователя
    user_state_manager.clear_state(user_id)
    
    # Создаем тайм-слот
    from apps.bot.services.time_slot_service import TimeSlotService
    time_slot_service = TimeSlotService()
    
    result = await time_slot_service.create_timeslot_for_date(
        object_id=object_id,
        slot_date=slot_date,
        is_additional=(slot_type == 'additional')
    )
    
    if result['success']:
        message = f"✅ <b>Тайм-слот создан успешно!</b>\n\n"
        message += f"📅 <b>Дата:</b> {text}\n"
        message += f"🕐 <b>Время:</b> {result.get('start_time', '09:00')}-{result.get('end_time', '18:00')}\n"
        message += f"💰 <b>Ставка:</b> {result.get('hourly_rate', 0)}₽/час\n"
        message += f"📝 <b>Тип:</b> {'Дополнительный' if slot_type == 'additional' else 'Обычный'}\n"
    else:
        message = f"❌ <b>Ошибка создания тайм-слота:</b>\n{result['error']}"
    
    keyboard = [
        [InlineKeyboardButton("➕ Создать еще", callback_data=f"create_timeslot:{object_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_timeslot_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state) -> None:
    """Обработчик ввода данных для редактирования тайм-слотов."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Получаем данные из состояния
    timeslot_id = user_state.data.get('timeslot_id')
    action = user_state.action
    
    # Импортируем сервис
    from apps.bot.services.time_slot_service import TimeSlotService
    time_slot_service = TimeSlotService()
    
    # Обрабатываем в зависимости от действия
    if action == UserAction.EDIT_TIMESLOT_TIME:
        # Парсим время в формате HH:MM-HH:MM
        try:
            if '-' not in text:
                await update.message.reply_text("❌ Неверный формат времени. Используйте HH:MM-HH:MM")
                return
            
            start_time_str, end_time_str = text.split('-', 1)
            from datetime import time
            start_time = time.fromisoformat(start_time_str.strip())
            end_time = time.fromisoformat(end_time_str.strip())
            
            # Обновляем время
            result1 = time_slot_service.update_timeslot_field(timeslot_id, 'start_time', start_time_str.strip())
            result2 = time_slot_service.update_timeslot_field(timeslot_id, 'end_time', end_time_str.strip())
            
            if result1['success'] and result2['success']:
                message = f"✅ <b>Время тайм-слота обновлено!</b>\n\n"
                message += f"🕐 <b>Новое время:</b> {start_time_str.strip()}-{end_time_str.strip()}"
            else:
                message = f"❌ <b>Ошибка обновления времени:</b>\n{result1.get('error', result2.get('error'))}"
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Используйте HH:MM-HH:MM (например: 09:00-18:00)")
            return
    
    elif action == UserAction.EDIT_TIMESLOT_RATE:
        try:
            rate = float(text)
            result = time_slot_service.update_timeslot_field(timeslot_id, 'hourly_rate', rate)
            
            if result['success']:
                message = f"✅ <b>Ставка тайм-слота обновлена!</b>\n\n"
                message += f"💰 <b>Новая ставка:</b> {rate}₽/час"
            else:
                message = f"❌ <b>Ошибка обновления ставки:</b>\n{result['error']}"
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат ставки. Введите число (например: 500)")
            return
    
    elif action == UserAction.EDIT_TIMESLOT_EMPLOYEES:
        try:
            employees = int(text)
            if not 1 <= employees <= 10:
                await update.message.reply_text("❌ Количество сотрудников должно быть от 1 до 10")
                return
                
            result = time_slot_service.update_timeslot_field(timeslot_id, 'max_employees', employees)
            
            if result['success']:
                message = f"✅ <b>Количество сотрудников обновлено!</b>\n\n"
                message += f"👥 <b>Новое количество:</b> {employees}"
            else:
                message = f"❌ <b>Ошибка обновления:</b>\n{result['error']}"
                
        except ValueError:
            await update.message.reply_text("❌ Неверный формат. Введите число от 1 до 10")
            return
    
    elif action == UserAction.EDIT_TIMESLOT_NOTES:
        notes = text if text.lower() != 'удалить' else None
        result = time_slot_service.update_timeslot_field(timeslot_id, 'notes', notes)
        
        if result['success']:
            message = f"✅ <b>Заметки тайм-слота обновлены!</b>\n\n"
            if notes:
                message += f"📝 <b>Новые заметки:</b> {notes}"
            else:
                message += f"📝 <b>Заметки удалены</b>"
        else:
            message = f"❌ <b>Ошибка обновления заметок:</b>\n{result['error']}"
    
    # Очищаем состояние пользователя
    user_state_manager.clear_state(user_id)
    
    # Получаем информацию о тайм-слоте для кнопки "Назад"
    timeslot = time_slot_service.get_timeslot_by_id(timeslot_id)
    object_id = timeslot['object_id'] if timeslot else None
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад к тайм-слоту", callback_data=f"edit_timeslot:{timeslot_id}")],
        [InlineKeyboardButton("🔙 Назад к объекту", callback_data=f"manage_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
