"""Обработчики для создания объектов в боте."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.shift_service import ShiftService
from apps.bot.services.object_service import ObjectService

# Создаем экземпляры сервисов
shift_service = ShiftService()
object_service = ObjectService()

# Глобальное хранилище для состояния создания объектов
user_object_creation_state = {}


async def handle_create_object_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало диалога создания объекта."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Инициализируем состояние пользователя
    user_object_creation_state[user_id] = {
        'step': 'name',
        'data': {}
    }
    
    response = """
🏢 <b>Создание нового объекта</b>

📝 <b>Шаг 1 из 5: Название объекта</b>

Введите название объекта (например: "Офис на Тверской", "Магазин №1", "Склад Восток")

📍 <b>Требования:</b>
• От 3 до 100 символов
• Уникальное название
• Понятное описание

✍️ Напишите название объекта:
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def handle_create_object_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str) -> None:
    """Обработка ввода данных для создания объекта."""
    user_id = update.effective_user.id
    
    if user_id not in user_object_creation_state:
        return  # Состояние потеряно
    
    state = user_object_creation_state[user_id]
    step = state['step']
    
    if step == 'name':
        await _handle_object_name_input(update, context, user_input)
    elif step == 'address':
        await _handle_object_address_input(update, context, user_input)
    elif step == 'coordinates':
        await _handle_object_coordinates_input(update, context, user_input)
    elif step == 'schedule':
        await _handle_object_schedule_input(update, context, user_input)
    elif step == 'hourly_rate':
        await _handle_object_hourly_rate_input(update, context, user_input)


async def _handle_object_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str) -> None:
    """Обработка ввода названия объекта."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Валидация названия
    if len(name.strip()) < 3:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Название слишком короткое. Минимум 3 символа. Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    if len(name.strip()) > 100:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Название слишком длинное. Максимум 100 символов. Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    # Сохраняем название и переходим к следующему шагу
    user_object_creation_state[user_id]['data']['name'] = name.strip()
    user_object_creation_state[user_id]['step'] = 'address'
    
    response = f"""
🏢 <b>Создание объекта: {name.strip()}</b>

📝 <b>Шаг 2 из 5: Адрес объекта</b>

Введите адрес объекта (например: "Москва, ул. Тверская, 1", "СПб, Невский пр., 50")

📍 <b>Требования:</b>
• Полный адрес с городом
• От 10 до 200 символов
• Понятное описание местоположения

✍️ Напишите адрес объекта:
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_object_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE, address: str) -> None:
    """Обработка ввода адреса объекта."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Валидация адреса
    if len(address.strip()) < 10:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Адрес слишком короткий. Минимум 10 символов. Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    if len(address.strip()) > 200:
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Адрес слишком длинный. Максимум 200 символов. Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    # Сохраняем адрес и переходим к следующему шагу
    user_object_creation_state[user_id]['data']['address'] = address.strip()
    user_object_creation_state[user_id]['step'] = 'coordinates'
    
    name = user_object_creation_state[user_id]['data']['name']
    
    # Получаем требования к геолокации
    location_requirements = shift_service.get_location_requirements()
    
    response = f"""
🏢 <b>Создание объекта: {name}</b>
📍 <b>Адрес:</b> {address.strip()}

📝 <b>Шаг 3 из 5: Координаты объекта</b>

Введите координаты объекта в формате: широта,долгота

📍 <b>Требования:</b>
• Формат: {location_requirements['coordinate_format']}
• Точность: {location_requirements['precision_required']}

💡 <b>Примеры:</b>
• Москва, Красная площадь: 55.7539,37.6208
• СПб, Дворцовая площадь: 59.9387,30.3162
• Новосибирск, центр: 55.0084,82.9357

✍️ Напишите координаты объекта:
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_object_coordinates_input(update: Update, context: ContextTypes.DEFAULT_TYPE, coordinates: str) -> None:
    """Обработка ввода координат объекта."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Валидируем координаты
    from core.geolocation.location_validator import LocationValidator
    validator = LocationValidator()
    validation = validator.validate_coordinates(coordinates.strip())
    
    if not validation['valid']:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Ошибка координат:</b>\n{validation['error']}\n\nПопробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    # Сохраняем координаты и переходим к следующему шагу
    user_object_creation_state[user_id]['data']['coordinates'] = coordinates.strip()
    user_object_creation_state[user_id]['step'] = 'schedule'
    
    name = user_object_creation_state[user_id]['data']['name']
    address = user_object_creation_state[user_id]['data']['address']
    
    response = f"""
🏢 <b>Создание объекта: {name}</b>
📍 <b>Адрес:</b> {address}
🌍 <b>Координаты:</b> {coordinates.strip()}

📝 <b>Шаг 4 из 5: Режим работы</b>

Введите время работы объекта в формате: ЧЧ:ММ-ЧЧ:ММ

📍 <b>Требования:</b>
• Формат: ЧЧ:ММ-ЧЧ:ММ (например: 09:00-18:00)
• Время открытия должно быть раньше времени закрытия
• Используйте 24-часовой формат

💡 <b>Примеры:</b>
• Офис: 09:00-18:00
• Магазин: 08:00-22:00
• Круглосуточно: 00:00-23:59

✍️ Напишите режим работы:
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_object_schedule_input(update: Update, context: ContextTypes.DEFAULT_TYPE, schedule: str) -> None:
    """Обработка ввода режима работы объекта."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Парсим режим работы
    try:
        if '-' not in schedule:
            raise ValueError("Неверный формат")
        
        opening_str, closing_str = schedule.strip().split('-', 1)
        opening_str = opening_str.strip()
        closing_str = closing_str.strip()
        
        # Проверяем формат времени
        from datetime import time
        opening_time = time.fromisoformat(opening_str)
        closing_time = time.fromisoformat(closing_str)
        
        if closing_time <= opening_time:
            raise ValueError("Время закрытия должно быть позже времени открытия")
        
    except ValueError as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Ошибка формата времени:</b>\n{str(e)}\n\nИспользуйте формат ЧЧ:ММ-ЧЧ:ММ (например: 09:00-18:00)\nПопробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    # Сохраняем режим работы и переходим к следующему шагу
    user_object_creation_state[user_id]['data']['opening_time'] = opening_str
    user_object_creation_state[user_id]['data']['closing_time'] = closing_str
    user_object_creation_state[user_id]['step'] = 'hourly_rate'
    
    name = user_object_creation_state[user_id]['data']['name']
    address = user_object_creation_state[user_id]['data']['address']
    coordinates = user_object_creation_state[user_id]['data']['coordinates']
    
    response = f"""
🏢 <b>Создание объекта: {name}</b>
📍 <b>Адрес:</b> {address}
🌍 <b>Координаты:</b> {coordinates}
🕒 <b>Режим работы:</b> {opening_str} - {closing_str}

📝 <b>Шаг 5 из 5: Часовая ставка</b>

Введите часовую ставку в рублях (число)

📍 <b>Требования:</b>
• Только число (например: 500, 1000, 1500)
• Минимум: 100 рублей
• Максимум: 10000 рублей

💡 <b>Примеры:</b>
• Офисная работа: 800
• Торговля: 600
• Склад: 1200

✍️ Напишите часовую ставку:
"""
    
    keyboard = [
        [InlineKeyboardButton("❌ Отменить", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_object_hourly_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE, hourly_rate_str: str) -> None:
    """Обработка ввода часовой ставки и создание объекта."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Валидация часовой ставки
    try:
        hourly_rate = float(hourly_rate_str.strip())
        
        if hourly_rate < 100:
            raise ValueError("Минимальная ставка: 100 рублей")
        
        if hourly_rate > 10000:
            raise ValueError("Максимальная ставка: 10000 рублей")
            
    except ValueError as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>Ошибка ставки:</b>\n{str(e)}\n\nВведите число от 100 до 10000. Попробуйте еще раз:",
            parse_mode='HTML'
        )
        return
    
    # Получаем все данные объекта
    data = user_object_creation_state[user_id]['data']
    data['hourly_rate'] = hourly_rate
    
    # Создаем объект через сервис
    result = object_service.create_object(
        name=data['name'],
        address=data['address'],
        coordinates=data['coordinates'],
        opening_time=data['opening_time'],
        closing_time=data['closing_time'],
        hourly_rate=data['hourly_rate'],
        owner_id=user_id
    )
    
    # Очищаем состояние пользователя
    if user_id in user_object_creation_state:
        del user_object_creation_state[user_id]
    
    if result['success']:
        response = f"""
✅ <b>Объект успешно создан!</b>

🏢 <b>Название:</b> {data['name']}
📍 <b>Адрес:</b> {data['address']}
🌍 <b>Координаты:</b> {data['coordinates']}
🕒 <b>Режим работы:</b> {data['opening_time']} - {data['closing_time']}
💰 <b>Часовая ставка:</b> {data['hourly_rate']} ₽

🎉 Теперь вы можете:
• Открывать смены на этом объекте
• Приглашать сотрудников
• Получать отчеты

Объект готов к использованию!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
                InlineKeyboardButton("🏢 Создать еще", callback_data="create_object")
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
                InlineKeyboardButton("📊 Статус", callback_data="status")
            ]
        ]
        
    else:
        response = f"""
❌ <b>Ошибка создания объекта</b>

{result['error']}

Попробуйте еще раз или обратитесь к администратору.
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Попробовать снова", callback_data="create_object"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=response,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
