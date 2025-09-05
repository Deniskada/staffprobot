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
