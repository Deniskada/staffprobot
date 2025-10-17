"""Обработчики для управления объектами."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.object_service import ObjectService
from core.state import user_state_manager, UserAction, UserStep

# Создаем экземпляр сервиса
object_service = ObjectService()


async def _handle_manage_objects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик управления объектами."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем объекты пользователя
    user_objects = object_service.get_user_objects(user_id)
    
    if not user_objects:
        await query.edit_message_text(
            text="📋 <b>Управление объектами</b>\n\n❌ У вас пока нет созданных объектов.\n\nСоздайте первый объект через главное меню.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    keyboard = []
    for obj in user_objects:
        # Теперь max_distance_meters уже есть в данных объекта
        max_distance = obj.get('max_distance_meters', 500)
        auto_close_minutes = obj.get('auto_close_minutes', 60)
            
        keyboard.append([
            InlineKeyboardButton(
                f"⚙️ {obj['name']} ({max_distance}м, {auto_close_minutes} мин.)", 
                callback_data=f"edit_object:{obj['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="📋 <b>Управление объектами</b>\n\nВыберите объект для редактирования:\n\n💡 В скобках указано максимальное расстояние для геолокации и время автоматического закрытия смен",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_object(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик редактирования объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Теперь max_distance_meters уже есть в obj_data
    max_distance = obj_data.get('max_distance_meters', 500)
    auto_close_minutes = obj_data.get('auto_close_minutes', 60)
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Название", callback_data=f"edit_field:{object_id}:name"),
            InlineKeyboardButton("📍 Адрес", callback_data=f"edit_field:{object_id}:address")
        ],
        [
            InlineKeyboardButton("🕐 Время начала", callback_data=f"edit_field:{object_id}:opening_time"),
            InlineKeyboardButton("🕐 Время окончания", callback_data=f"edit_field:{object_id}:closing_time")
        ],
        [
            InlineKeyboardButton("💰 Часовая ставка", callback_data=f"edit_field:{object_id}:hourly_rate"),
            InlineKeyboardButton("📏 Макс. расстояние", callback_data=f"edit_field:{object_id}:max_distance_meters")
        ],
        [
            InlineKeyboardButton("⏰ Авто-закрытие смен", callback_data=f"edit_field:{object_id}:auto_close_minutes")
        ],
        [
            InlineKeyboardButton("🕐 Управление тайм-слотами", callback_data=f"manage_timeslots:{object_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Удалить объект", callback_data=f"delete_object:{object_id}")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Получаем время работы объекта
    opening_time = obj_data.get('opening_time', '09:00')
    closing_time = obj_data.get('closing_time', '18:00')
    
    await query.edit_message_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
             f"🕐 <b>Время работы:</b> {opening_time} - {closing_time}\n"
             f"💰 <b>Часовая ставка:</b> {obj_data['hourly_rate']}₽\n"
             f"📏 <b>Максимальное расстояние:</b> {max_distance}м\n"
             f"⏰ <b>Время автоматического закрытия:</b> {auto_close_minutes} мин.\n\n"
             f"Выберите поле для редактирования:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, field_name: str):
    """Обработчик редактирования конкретного поля."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Определяем название поля и подсказку
    field_names = {
        'name': 'название объекта',
        'address': 'адрес объекта',
        'opening_time': 'время начала работы (в формате HH:MM, например: 09:00)',
        'closing_time': 'время окончания работы (в формате HH:MM, например: 18:00)',
        'hourly_rate': 'часовую ставку (в рублях)',
        'max_distance_meters': 'максимальное расстояние (в метрах, от 10 до 5000)',
        'auto_close_minutes': 'время автоматического закрытия смен (в минутах, от 15 до 480)'
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Создаем состояние пользователя для редактирования
    await user_state_manager.create_state(
        user_id=user_id,
        action=UserAction.EDIT_OBJECT,
        step=UserStep.INPUT_FIELD_VALUE,
        selected_object_id=object_id,
        data={'field_name': field_name}
    )
    
    await query.edit_message_text(
        text=f"✏️ <b>Редактирование поля</b>\n\n"
             f"Введите новое значение для поля <b>{field_display}</b>:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_object:{object_id}")
        ]])
    )


async def _handle_edit_object_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_state):
    """Обработчик ввода нового значения для поля объекта."""
    user_id = update.effective_user.id
    text = update.message.text
    object_id = user_state.selected_object_id
    field_name = user_state.data.get('field_name')
    
    if not field_name:
        await update.message.reply_text("❌ Ошибка: не удалось определить редактируемое поле.")
        await user_state_manager.clear_state(user_id)
        return
    
    # Обновляем поле объекта
    result = object_service.update_object_field(object_id, field_name, text, user_id)
    
    # Очищаем состояние пользователя
    await user_state_manager.clear_state(user_id)
    
    if result['success']:
        # Отображаем успешное обновление и возвращаемся к редактированию объекта
        await update.message.reply_text(
            f"✅ {result['message']}\n\nНовое значение: <b>{result['new_value']}</b>",
            parse_mode='HTML'
        )
        
        # Показываем обновленную информацию об объекте
        await _show_updated_object_info(update, context, object_id)
    else:
        # Показываем ошибку и возвращаемся к редактированию
        await update.message.reply_text(
            f"❌ {result['error']}\n\nПопробуйте ещё раз или вернитесь к редактированию объекта.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К редактированию", callback_data=f"edit_object:{object_id}"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )


async def _show_updated_object_info(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Показывает обновленную информацию об объекте."""
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await update.message.reply_text(
            "❌ Объект не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Теперь max_distance_meters уже есть в obj_data
    max_distance = obj_data.get('max_distance_meters', 500)
    auto_close_minutes = obj_data.get('auto_close_minutes', 60)
    
    keyboard = [
        [
            InlineKeyboardButton("📝 Название", callback_data=f"edit_field:{object_id}:name"),
            InlineKeyboardButton("📍 Адрес", callback_data=f"edit_field:{object_id}:address")
        ],
        [
            InlineKeyboardButton("🕐 Время начала", callback_data=f"edit_field:{object_id}:opening_time"),
            InlineKeyboardButton("🕐 Время окончания", callback_data=f"edit_field:{object_id}:closing_time")
        ],
        [
            InlineKeyboardButton("💰 Часовая ставка", callback_data=f"edit_field:{object_id}:hourly_rate"),
            InlineKeyboardButton("📏 Макс. расстояние", callback_data=f"edit_field:{object_id}:max_distance_meters")
        ],
        [
            InlineKeyboardButton("⏰ Авто-закрытие смен", callback_data=f"edit_field:{object_id}:auto_close_minutes")
        ],
        [
            InlineKeyboardButton("🕐 Управление тайм-слотами", callback_data=f"manage_timeslots:{object_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Удалить объект", callback_data=f"delete_object:{object_id}")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Получаем время работы объекта
    opening_time = obj_data.get('opening_time', '09:00')
    closing_time = obj_data.get('closing_time', '18:00')
    
    await update.message.reply_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
             f"🕐 <b>Время работы:</b> {opening_time} - {closing_time}\n"
             f"💰 <b>Часовая ставка:</b> {obj_data['hourly_rate']}₽\n"
             f"📏 <b>Максимальное расстояние:</b> {max_distance}м\n"
             f"⏰ <b>Время автоматического закрытия:</b> {auto_close_minutes} мин.\n\n"
             f"Выберите поле для редактирования:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_delete_object(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик удаления объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Показываем подтверждение удаления
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_object:{object_id}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_object:{object_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"⚠️ <b>Подтверждение удаления</b>\n\n"
             f"Вы действительно хотите удалить объект <b>\"{obj_data['name']}\"</b>?\n\n"
             f"<b>ВНИМАНИЕ:</b> Это действие удалит:\n"
             f"• Все тайм-слоты объекта\n"
             f"• Все запланированные смены\n"
             f"• Все связанные данные\n\n"
             f"<b>Это действие нельзя отменить!</b>",
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_confirm_delete_object(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик подтверждения удаления объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Удаляем объект и все связанные данные
    result = object_service.delete_object(object_id, user_id)
    
    if result['success']:
        await query.edit_message_text(
            text=f"✅ <b>Объект успешно удален</b>\n\n"
                 f"Удалено:\n"
                 f"• Объект: {result.get('object_name', 'Неизвестно')}\n"
                 f"• Тайм-слотов: {result.get('timeslots_deleted', 0)}\n"
                 f"• Запланированных смен: {result.get('shifts_deleted', 0)}\n\n"
                 f"Все связанные данные были удалены.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Управление объектами", callback_data="manage_objects"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
    else:
        await query.edit_message_text(
            text=f"❌ <b>Ошибка удаления</b>\n\n{result['error']}",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 К редактированию", callback_data=f"edit_object:{object_id}"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
