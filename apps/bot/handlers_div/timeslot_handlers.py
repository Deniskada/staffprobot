"""Обработчики для управления тайм-слотами объектов."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from core.logging.logger import logger
from apps.bot.services.time_slot_service import TimeSlotService
from apps.bot.services.object_service import ObjectService
from core.state import user_state_manager, UserAction, UserStep
from datetime import date, timedelta

# Создаем экземпляры сервисов
time_slot_service = TimeSlotService()
object_service = ObjectService()


async def _handle_manage_timeslots(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик управления тайм-слотами объекта."""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем информацию об объекте
    obj_data = object_service.get_object_by_id(object_id)
    if not obj_data:
        await query.edit_message_text(
            text="❌ Объект не найден.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
            ]])
        )
        return
    
    # Получаем существующие тайм-слоты
    timeslots = await time_slot_service.get_object_timeslots(object_id)
    
    # Формируем сообщение
    message = f"🕐 <b>Управление тайм-слотами</b>\n\n"
    message += f"🏢 <b>Объект:</b> {obj_data['name']}\n"
    message += f"⏰ <b>Рабочее время:</b> {obj_data.get('working_hours', 'Не указано')}\n"
    message += f"💰 <b>Базовая ставка:</b> {obj_data['hourly_rate']}₽/час\n\n"
    
    if timeslots:
        message += f"📅 <b>Существующие тайм-слоты:</b> {len(timeslots)}\n"
        # Показываем ближайшие 3 тайм-слота
        upcoming_timeslots = [ts for ts in timeslots if ts['slot_date'] >= date.today()][:3]
        for ts in upcoming_timeslots:
            status = "🟢" if ts['is_active'] else "🔴"
            additional = " (доп.)" if ts['is_additional'] else ""
            message += f"{status} {ts['slot_date'].strftime('%d.%m.%Y')} {ts['start_time']}-{ts['end_time']}{additional}\n"
    else:
        message += "📅 <b>Тайм-слоты не созданы</b>\n"
    
    # Создаем кнопки
    keyboard = [
        [
            InlineKeyboardButton("➕ Создать тайм-слот", callback_data=f"create_timeslot:{object_id}"),
            InlineKeyboardButton("📋 Просмотреть все", callback_data=f"view_timeslots:{object_id}")
        ],
        [
            InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_timeslots:{object_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_timeslots:{object_id}")
        ],
        [
            InlineKeyboardButton("🔙 Назад к объекту", callback_data=f"edit_object:{object_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_timeslot(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик создания тайм-слота."""
    query = update.callback_query
    await query.answer()
    
    obj_data = object_service.get_object_by_id(object_id)
    
    message = f"➕ <b>Создание тайм-слота</b>\n\n"
    message += f"🏢 <b>Объект:</b> {obj_data['name']}\n"
    message += f"⏰ <b>Рабочее время:</b> {obj_data.get('working_hours', 'Не указано')}\n\n"
    message += "Выберите тип тайм-слота:"
    
    keyboard = [
        [
            InlineKeyboardButton("🕐 Обычный слот", callback_data=f"create_regular_slot:{object_id}"),
            InlineKeyboardButton("➕ Дополнительный слот", callback_data=f"create_additional_slot:{object_id}")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_view_timeslots(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик просмотра всех тайм-слотов объекта."""
    query = update.callback_query
    await query.answer()
    
    timeslots = await time_slot_service.get_object_timeslots(object_id)
    
    if not timeslots:
        keyboard = [
            [InlineKeyboardButton("➕ Создать первый тайм-слот", callback_data=f"create_timeslot:{object_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📋 <b>Тайм-слоты объекта</b>\n\n"
            "У объекта пока нет созданных тайм-слотов.\n\n"
            "Хотите создать первый тайм-слот?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Группируем тайм-слоты по датам
    timeslots_by_date = {}
    for ts in timeslots:
        date_key = ts['slot_date']
        if date_key not in timeslots_by_date:
            timeslots_by_date[date_key] = []
        timeslots_by_date[date_key].append(ts)
    
    # Сортируем даты
    sorted_dates = sorted(timeslots_by_date.keys())
    
    message = f"📋 <b>Тайм-слоты объекта</b>\n\n"
    
    for slot_date in sorted_dates:
        date_timeslots = timeslots_by_date[slot_date]
        message += f"📅 <b>{slot_date.strftime('%d.%m.%Y')}</b>\n"
        
        for ts in date_timeslots:
            status = "🟢" if ts['is_active'] else "🔴"
            additional = " (доп.)" if ts['is_additional'] else ""
            rate = f" {ts['hourly_rate']}₽/час" if ts['hourly_rate'] else ""
            message += f"  {status} {ts['start_time']}-{ts['end_time']}{additional}{rate}\n"
        
        message += "\n"
    
    # Создаем кнопки навигации
    keyboard = [
        [InlineKeyboardButton("➕ Создать новый", callback_data=f"create_timeslot:{object_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_timeslots(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик редактирования тайм-слотов."""
    query = update.callback_query
    await query.answer()
    
    timeslots = await time_slot_service.get_object_timeslots(object_id)
    
    if not timeslots:
        keyboard = [
            [InlineKeyboardButton("➕ Создать первый тайм-слот", callback_data=f"create_timeslot:{object_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✏️ <b>Редактирование тайм-слотов</b>\n\n"
            "У объекта пока нет созданных тайм-слотов.\n\n"
            "Хотите создать первый тайм-слот?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Показываем список тайм-слотов для редактирования
    message = "✏️ <b>Редактирование тайм-слотов</b>\n\n"
    message += "Выберите тайм-слот для редактирования:\n\n"
    
    keyboard = []
    for ts in timeslots[:10]:  # Показываем первые 10
        status = "🟢" if ts['is_active'] else "🔴"
        additional = " (доп.)" if ts['is_additional'] else ""
        date_str = ts['slot_date'].strftime('%d.%m.%Y')
        time_str = f"{ts['start_time']}-{ts['end_time']}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {date_str} {time_str}{additional}",
                callback_data=f"edit_timeslot:{ts['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_delete_timeslots(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик удаления тайм-слотов."""
    query = update.callback_query
    await query.answer()
    
    timeslots = await time_slot_service.get_object_timeslots(object_id)
    
    if not timeslots:
        keyboard = [
            [InlineKeyboardButton("➕ Создать первый тайм-слот", callback_data=f"create_timeslot:{object_id}")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🗑️ <b>Удаление тайм-слотов</b>\n\n"
            "У объекта пока нет созданных тайм-слотов.\n\n"
            "Хотите создать первый тайм-слот?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Показываем список тайм-слотов для удаления
    message = "🗑️ <b>Удаление тайм-слотов</b>\n\n"
    message += "⚠️ <b>Внимание!</b> Удаление тайм-слота невозможно, если на него запланированы смены.\n\n"
    message += "Выберите тайм-слот для удаления:\n\n"
    
    keyboard = []
    for ts in timeslots[:10]:  # Показываем первые 10
        status = "🟢" if ts['is_active'] else "🔴"
        additional = " (доп.)" if ts['is_additional'] else ""
        date_str = ts['slot_date'].strftime('%d.%m.%Y')
        time_str = f"{ts['start_time']}-{ts['end_time']}"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {date_str} {time_str}{additional}",
                callback_data=f"delete_timeslot:{ts['id']}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_regular_slot(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик создания обычного тайм-слота."""
    query = update.callback_query
    await query.answer()
    
    obj_data = object_service.get_object_by_id(object_id)
    
    message = f"🕐 <b>Создание обычного тайм-слота</b>\n\n"
    message += f"🏢 <b>Объект:</b> {obj_data['name']}\n"
    message += f"⏰ <b>Рабочее время:</b> {obj_data.get('working_hours', 'Не указано')}\n\n"
    message += "Обычный тайм-слот создается в рабочее время объекта.\n"
    message += "Выберите дату для создания слота:"
    
    today = date.today()
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Сегодня", callback_data=f"create_slot_date:{object_id}:regular:{today.strftime('%Y-%m-%d')}"),
            InlineKeyboardButton("📅 Завтра", callback_data=f"create_slot_date:{object_id}:regular:{(today + timedelta(days=1)).strftime('%Y-%m-%d')}")
        ],
        [
            InlineKeyboardButton("📅 Выбрать дату", callback_data=f"create_slot_custom_date:{object_id}:regular"),
            InlineKeyboardButton("📅 Создать на неделю", callback_data=f"create_slot_week:{object_id}:regular")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data=f"create_timeslot:{object_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_additional_slot(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int):
    """Обработчик создания дополнительного тайм-слота."""
    query = update.callback_query
    await query.answer()
    
    obj_data = object_service.get_object_by_id(object_id)
    
    message = f"➕ <b>Создание дополнительного тайм-слота</b>\n\n"
    message += f"🏢 <b>Объект:</b> {obj_data['name']}\n"
    message += f"⏰ <b>Рабочее время:</b> {obj_data.get('working_hours', 'Не указано')}\n\n"
    message += "Дополнительный тайм-слот можно создать в любое время, даже вне рабочего времени.\n"
    message += "Выберите дату для создания слота:"
    
    today = date.today()
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Сегодня", callback_data=f"create_slot_date:{object_id}:additional:{today.strftime('%Y-%m-%d')}"),
            InlineKeyboardButton("📅 Завтра", callback_data=f"create_slot_date:{object_id}:additional:{(today + timedelta(days=1)).strftime('%Y-%m-%d')}")
        ],
        [
            InlineKeyboardButton("📅 Выбрать дату", callback_data=f"create_slot_custom_date:{object_id}:additional"),
            InlineKeyboardButton("📅 Создать на неделю", callback_data=f"create_slot_week:{object_id}:additional")
        ],
        [
            InlineKeyboardButton("🔙 Назад", callback_data=f"create_timeslot:{object_id}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_slot_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str, slot_date: str):
    """Обработчик создания тайм-слота на конкретную дату."""
    query = update.callback_query
    await query.answer()
    
    # Создаем тайм-слот
    result = await time_slot_service.create_timeslot_for_date(
        object_id=object_id,
        slot_date=slot_date,
        is_additional=(slot_type == 'additional')
    )
    
    if result['success']:
        message = f"✅ <b>Тайм-слот создан успешно!</b>\n\n"
        message += f"📅 <b>Дата:</b> {slot_date}\n"
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
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_slot_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик создания тайм-слота на выбранную дату."""
    query = update.callback_query
    await query.answer()
    
    # Создаем состояние пользователя для ввода даты
    user_state_manager.create_state(
        user_id=query.from_user.id,
        action=UserAction.CREATE_TIMESLOT,
        step=UserStep.INPUT_DATE,
        selected_object_id=object_id,
        data={'slot_type': slot_type}
    )
    
    message = f"📅 <b>Введите дату для создания тайм-слота</b>\n\n"
    message += f"Формат: ДД.ММ.ГГГГ (например: 15.09.2025)\n"
    message += f"Тип слота: {'Дополнительный' if slot_type == 'additional' else 'Обычный'}"
    
    keyboard = [
        [InlineKeyboardButton("❌ Отмена", callback_data=f"create_timeslot:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_create_slot_week(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик создания тайм-слотов на неделю."""
    query = update.callback_query
    await query.answer()
    
    # Создаем тайм-слоты на неделю
    result = await time_slot_service.create_timeslots_for_week(
        object_id=object_id,
        is_additional=(slot_type == 'additional')
    )
    
    if result['success']:
        message = f"✅ <b>Тайм-слоты на неделю созданы!</b>\n\n"
        message += f"📅 <b>Создано слотов:</b> {result.get('created_count', 0)}\n"
        message += f"📝 <b>Тип:</b> {'Дополнительные' if slot_type == 'additional' else 'Обычные'}\n"
        message += f"💰 <b>Ставка:</b> {result.get('hourly_rate', 0)}₽/час"
    else:
        message = f"❌ <b>Ошибка создания тайм-слотов:</b>\n{result['error']}"
    
    keyboard = [
        [InlineKeyboardButton("➕ Создать еще", callback_data=f"create_timeslot:{object_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data=f"manage_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_slot_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str, slot_date: str):
    """Обработчик редактирования тайм-слота на конкретную дату."""
    query = update.callback_query
    await query.answer()
    
    message = f"✏️ <b>Редактирование тайм-слота</b>\n\n"
    message += f"📅 <b>Дата:</b> {slot_date}\n"
    message += f"📝 <b>Тип:</b> {'Дополнительный' if slot_type == 'additional' else 'Обычный'}\n\n"
    message += "Функция редактирования в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_slot_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик редактирования тайм-слота на выбранную дату."""
    query = update.callback_query
    await query.answer()
    
    message = f"✏️ <b>Редактирование тайм-слота</b>\n\n"
    message += f"📝 <b>Тип:</b> {'Дополнительный' if slot_type == 'additional' else 'Обычный'}\n\n"
    message += "Функция редактирования в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_edit_slot_week(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик редактирования тайм-слотов на неделю."""
    query = update.callback_query
    await query.answer()
    
    message = f"✏️ <b>Редактирование тайм-слотов на неделю</b>\n\n"
    message += f"📝 <b>Тип:</b> {'Дополнительные' if slot_type == 'additional' else 'Обычные'}\n\n"
    message += "Функция редактирования в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"edit_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_delete_slot_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str, slot_date: str):
    """Обработчик удаления тайм-слота на конкретную дату."""
    query = update.callback_query
    await query.answer()
    
    message = f"🗑️ <b>Удаление тайм-слота</b>\n\n"
    message += f"📅 <b>Дата:</b> {slot_date}\n"
    message += f"📝 <b>Тип:</b> {'Дополнительный' if slot_type == 'additional' else 'Обычный'}\n\n"
    message += "Функция удаления в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"delete_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_delete_slot_custom_date(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик удаления тайм-слота на выбранную дату."""
    query = update.callback_query
    await query.answer()
    
    message = f"🗑️ <b>Удаление тайм-слота</b>\n\n"
    message += f"📝 <b>Тип:</b> {'Дополнительный' if slot_type == 'additional' else 'Обычный'}\n\n"
    message += "Функция удаления в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"delete_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def _handle_delete_slot_week(update: Update, context: ContextTypes.DEFAULT_TYPE, object_id: int, slot_type: str):
    """Обработчик удаления тайм-слотов на неделю."""
    query = update.callback_query
    await query.answer()
    
    message = f"🗑️ <b>Удаление тайм-слотов на неделю</b>\n\n"
    message += f"📝 <b>Тип:</b> {'Дополнительные' if slot_type == 'additional' else 'Обычные'}\n\n"
    message += "Функция удаления в разработке..."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data=f"delete_timeslots:{object_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
