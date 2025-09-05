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
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
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
        'hourly_rate': 'часовую ставку (в рублях)',
        'max_distance_meters': 'максимальное расстояние (в метрах, от 10 до 5000)',
        'auto_close_minutes': 'время автоматического закрытия смен (в минутах, от 15 до 480)'
    }
    
    field_display = field_names.get(field_name, field_name)
    
    # Создаем состояние пользователя для редактирования
    user_state_manager.create_state(
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
        user_state_manager.clear_state(user_id)
        return
    
    # Обновляем поле объекта
    result = object_service.update_object_field(object_id, field_name, text, user_id)
    
    # Очищаем состояние пользователя
    user_state_manager.clear_state(user_id)
    
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
            InlineKeyboardButton("🔙 Назад", callback_data="manage_objects"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"⚙️ <b>Редактирование объекта</b>\n\n"
             f"🏢 <b>Название:</b> {obj_data['name']}\n"
             f"📍 <b>Адрес:</b> {obj_data['address'] or 'не указан'}\n"
             f"💰 <b>Часовая ставка:</b> {obj_data['hourly_rate']}₽\n"
             f"📏 <b>Максимальное расстояние:</b> {max_distance}м\n"
             f"⏰ <b>Время автоматического закрытия:</b> {auto_close_minutes} мин.\n\n"
             f"Выберите поле для редактирования:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )
