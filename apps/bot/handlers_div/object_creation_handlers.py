"""Обработчики для создания объектов."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.object_service import ObjectService
# from core.state import user_state_manager, UserAction, UserStep
from core.geolocation.location_validator import LocationValidator

# Создаем экземпляры сервисов
object_service = ObjectService()
location_validator = LocationValidator()

# Состояние создания объекта для каждого пользователя
user_object_creation_state = {}


async def _get_address_from_coordinates(lat: float, lon: float) -> str:
    """Получение адреса по координатам (обратное геокодирование)."""
    try:
        import httpx
        
        # Используем Nominatim API для обратного геокодирования
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            'lat': lat,
            'lon': lon,
            'format': 'json',
            'addressdetails': 1,
            'accept-language': 'ru'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            data = response.json()
            
            if 'display_name' in data:
                # Формируем краткий адрес
                address_parts = []
                address = data.get('address', {})
                
                # Добавляем основные части адреса
                if 'house_number' in address and 'road' in address:
                    address_parts.append(f"{address['road']}, {address['house_number']}")
                elif 'road' in address:
                    address_parts.append(address['road'])
                
                if 'city' in address:
                    address_parts.append(address['city'])
                elif 'town' in address:
                    address_parts.append(address['town'])
                elif 'village' in address:
                    address_parts.append(address['village'])
                
                if 'state' in address:
                    address_parts.append(address['state'])
                
                if address_parts:
                    return ', '.join(address_parts)
                else:
                    return data['display_name']
            else:
                return f"Координаты: {lat:.6f}, {lon:.6f}"
                
    except Exception as e:
        logger.error(f"Error getting address from coordinates: {e}")
        return f"Координаты: {lat:.6f}, {lon:.6f}"


async def handle_create_object_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса создания объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Инициализируем состояние создания объекта
    user_object_creation_state[user_id] = {
        'step': 'name',
        'data': {}
    }
    
    await query.edit_message_text(
        text="🏢 <b>Создание нового объекта</b>\n\n"
             "Введите название объекта:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
        ]])
    )


async def handle_create_object_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Обработка ввода данных при создании объекта."""
    user_id = update.effective_user.id
    
    if user_id not in user_object_creation_state:
        await update.message.reply_text("❌ Сессия создания объекта истекла. Начните заново.")
        return
    
    state = user_object_creation_state[user_id]
    step = state['step']
    
    if step == 'name':
        await _handle_name_input(update, context, text, state)
    elif step == 'address':
        await _handle_address_input(update, context, text, state)
    elif step == 'coordinates':
        await _handle_coordinates_input(update, context, text, state)
    elif step == 'hourly_rate':
        await _handle_hourly_rate_input(update, context, text, state)
    elif step == 'max_distance':
        await _handle_max_distance_input(update, context, text, state)
    elif step == 'opening_time':
        await _handle_opening_time_input(update, context, text, state)
    elif step == 'closing_time':
        await _handle_closing_time_input(update, context, text, state)
    elif step == 'auto_close_minutes':
        await _handle_auto_close_input(update, context, text, state)


async def _handle_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода названия объекта."""
    if not text.strip():
        await update.message.reply_text("❌ Название не может быть пустым. Попробуйте ещё раз:")
        return
    
    state['data']['name'] = text.strip()
    state['step'] = 'address'
    
    await update.message.reply_text(
        "📍 Введите адрес объекта (или отправьте геолокацию):",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
        ]])
    )


async def _handle_address_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода адреса объекта."""
    # Проверяем, есть ли геолокация в сообщении
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        
        # Получаем адрес по координатам (геокодирование)
        address = await _get_address_from_coordinates(lat, lon)
        state['data']['address'] = address
        state['data']['latitude'] = lat
        state['data']['longitude'] = lon
        
        # Переходим сразу к часовой ставке, пропуская ввод координат
        state['step'] = 'hourly_rate'
        
        await update.message.reply_text(
            f"✅ <b>Адрес определен:</b> {address}\n"
            f"📍 <b>Координаты:</b> {lat:.6f}, {lon:.6f}\n\n"
            "💰 Введите часовую ставку в рублях:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
    else:
        # Обычный ввод адреса
        state['data']['address'] = text.strip() if text.strip() else None
        state['step'] = 'coordinates'
        
        await update.message.reply_text(
            "📍 Введите координаты объекта в формате:\n"
            "<code>широта, долгота</code>\n\n"
            "Например: <code>55.7558, 37.6176</code>\n\n"
            "Или отправьте геолокацию:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )


async def _handle_coordinates_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода координат объекта."""
    # Проверяем, есть ли геолокация в сообщении
    if update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        state['data']['latitude'] = lat
        state['data']['longitude'] = lon
    else:
        # Парсим координаты из текста
        try:
            coords = text.strip().split(',')
            if len(coords) != 2:
                raise ValueError("Неверный формат координат")
            
            lat = float(coords[0].strip())
            lon = float(coords[1].strip())
            
            # Валидируем координаты
            validation_result = location_validator.validate_coordinates(text.strip())
            if not validation_result['valid']:
                await update.message.reply_text(
                    f"❌ {validation_result['error']}\n"
                    "Попробуйте ещё раз:"
                )
                return
            
            state['data']['latitude'] = lat
            state['data']['longitude'] = lon
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Неверный формат координат. Используйте формат:\n"
                "<code>широта, долгота</code>\n\n"
                "Например: <code>55.7558, 37.6176</code>",
                parse_mode='HTML'
            )
            return
    
    state['step'] = 'hourly_rate'
    
    await update.message.reply_text(
        "💰 Введите часовую ставку в рублях:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
        ]])
    )


async def _handle_hourly_rate_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода часовой ставки."""
    try:
        hourly_rate = float(text.strip())
        if hourly_rate <= 0:
            raise ValueError("Ставка должна быть больше 0")
        
        state['data']['hourly_rate'] = hourly_rate
        state['step'] = 'max_distance'
        
        await update.message.reply_text(
            "📏 Введите максимальное расстояние для геолокации в метрах (от 10 до 5000):\n\n"
            "По умолчанию: 500м",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат ставки. Введите число больше 0:\n"
            "Например: <code>500</code>",
            parse_mode='HTML'
        )


async def _handle_max_distance_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода максимального расстояния."""
    try:
        if text.strip():
            max_distance = int(text.strip())
            if max_distance < 10 or max_distance > 5000:
                raise ValueError("Расстояние должно быть от 10 до 5000 метров")
            state['data']['max_distance_meters'] = max_distance
        else:
            state['data']['max_distance_meters'] = 500  # По умолчанию
        
        state['step'] = 'opening_time'
        
        await update.message.reply_text(
            "🕐 Введите время открытия объекта в формате ЧЧ:ММ (например: 09:00):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверное значение расстояния. Введите число от 10 до 5000:\n"
            "Например: <code>500</code>",
            parse_mode='HTML'
        )


async def _handle_opening_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода времени открытия объекта."""
    try:
        # Парсим время в формате HH:MM
        time_parts = text.strip().split(':')
        if len(time_parts) != 2:
            raise ValueError("Неверный формат времени")
        
        hour, minute = int(time_parts[0]), int(time_parts[1])
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Неверное время")
        
        state['data']['opening_time'] = f"{hour:02d}:{minute:02d}"
        state['step'] = 'closing_time'
        
        await update.message.reply_text(
            f"✅ Время открытия: {state['data']['opening_time']}\n\n"
            "🕐 Введите время закрытия объекта в формате ЧЧ:ММ (например: 18:00):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например: 09:00):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )


async def _handle_closing_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода времени закрытия объекта."""
    try:
        # Парсим время в формате HH:MM
        time_parts = text.strip().split(':')
        if len(time_parts) != 2:
            raise ValueError("Неверный формат времени")
        
        hour, minute = int(time_parts[0]), int(time_parts[1])
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Неверное время")
        
        state['data']['closing_time'] = f"{hour:02d}:{minute:02d}"
        state['step'] = 'auto_close_minutes'
        
        await update.message.reply_text(
            f"✅ Время закрытия: {state['data']['closing_time']}\n\n"
            "⏰ Введите время автоматического закрытия смен в минутах (от 15 до 480):\n\n"
            "По умолчанию: 60 минут",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат времени. Используйте формат ЧЧ:ММ (например: 18:00):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )


async def _handle_auto_close_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, state: dict):
    """Обработка ввода времени автоматического закрытия и создание объекта."""
    try:
        if text.strip():
            auto_close = int(text.strip())
            if auto_close < 15 or auto_close > 480:
                raise ValueError("Время должно быть от 15 до 480 минут")
            state['data']['auto_close_minutes'] = auto_close
        else:
            state['data']['auto_close_minutes'] = 60  # По умолчанию
        
        # Создаем объект
        user_id = update.effective_user.id
        coordinates = f"{state['data']['latitude']},{state['data']['longitude']}"
        result = object_service.create_object(
            name=state['data']['name'],
            address=state['data'].get('address', ''),
            coordinates=coordinates,
            opening_time=state['data']['opening_time'],
            closing_time=state['data']['closing_time'],
            hourly_rate=state['data']['hourly_rate'],
            max_distance_meters=state['data']['max_distance_meters'],
            auto_close_minutes=state['data']['auto_close_minutes'],
            owner_id=user_id
        )
        
        # Очищаем состояние
        if user_id in user_object_creation_state:
            del user_object_creation_state[user_id]
        
        if result['success']:
            await update.message.reply_text(
                f"✅ <b>Объект успешно создан!</b>\n\n"
                f"🏢 <b>Название:</b> {state['data']['name']}\n"
                f"📍 <b>Адрес:</b> {state['data'].get('address', 'не указан')}\n"
                f"🕐 <b>Время работы:</b> {state['data']['opening_time']} - {state['data']['closing_time']}\n"
                f"💰 <b>Ставка:</b> {state['data']['hourly_rate']}₽/час\n"
                f"📏 <b>Макс. расстояние:</b> {state['data']['max_distance_meters']}м\n"
                f"⏰ <b>Авто-закрытие:</b> {state['data']['auto_close_minutes']} мин.\n\n"
                f"Теперь вы можете открывать смены на этом объекте!",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
        else:
            await update.message.reply_text(
                f"❌ <b>Ошибка создания объекта:</b>\n\n{result['error']}",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Попробовать снова", callback_data="create_object"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]])
            )
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверное значение времени. Введите число от 15 до 480:\n"
            "Например: <code>60</code>",
            parse_mode='HTML'
        )
