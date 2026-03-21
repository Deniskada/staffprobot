"""Хендлеры для управления состоянием объектов (открытие/закрытие)."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Optional

from core.state.user_state_manager import user_state_manager, UserAction, UserStep
from core.database.session import get_async_session
from core.logging.logger import logger
from shared.services.object_opening_service import ObjectOpeningService
from shared.services.shift_service import ShiftService
from apps.bot.services.shift_service import ShiftService as BotShiftService
from domain.entities.object import Object
from domain.entities.contract import Contract
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload


async def _handle_open_object(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик открытия объекта."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} initiated object opening")

    async with get_async_session() as session:
        # Найти пользователя по telegram_id
        from domain.entities.user import User
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        db_user = user_result.scalar_one_or_none()
        
        if not db_user:
            await query.edit_message_text(
                text="❌ Пользователь не найден.\n\nИспользуйте /start для регистрации.",
                parse_mode='HTML'
            )
            return
        
        # Найти активные договоры по employee_id
        from shared.services.contract_validation_service import build_active_contract_filter
        from datetime import date
        
        contracts_query = select(Contract).where(
            and_(
                Contract.employee_id == db_user.id,
                build_active_contract_filter(date.today())
            )
        )
        contracts_result = await session.execute(contracts_query)
        contracts = contracts_result.scalars().all()
        
        # Собрать список объектов из договоров
        available_objects = []
        if contracts:
            for contract in contracts:
                if contract.allowed_objects:
                    for obj_id in contract.allowed_objects:
                        if obj_id not in [o['id'] for o in available_objects]:
                            obj_query = select(Object).where(Object.id == obj_id)
                            obj_result = await session.execute(obj_query)
                            obj = obj_result.scalar_one_or_none()
                            if obj and obj.is_active:
                                # Проверить: уже открыт?
                                opening_service = ObjectOpeningService(session)
                                is_open = await opening_service.is_object_open(obj.id)
                                available_objects.append({
                                    'id': obj.id,
                                    'name': obj.name,
                                    'is_open': is_open
                                })
        
        # Дополнительно: если пользователь владелец - добавляем его собственные объекты
        user_role = db_user.role if hasattr(db_user, 'role') else None
        user_roles = db_user.roles if hasattr(db_user, 'roles') else []
        
        if user_role == 'owner' or 'owner' in user_roles:
            # Получаем объекты владельца
            owner_objects_query = select(Object).where(
                and_(
                    Object.owner_id == db_user.id,
                    Object.is_active == True
                )
            )
            owner_objects_result = await session.execute(owner_objects_query)
            owner_objects_list = owner_objects_result.scalars().all()
            
            # Добавляем к списку, убирая дубли
            existing_ids = [o['id'] for o in available_objects]
            for owner_obj in owner_objects_list:
                if owner_obj.id not in existing_ids:
                    opening_service = ObjectOpeningService(session)
                    is_open = await opening_service.is_object_open(owner_obj.id)
                    available_objects.append({
                        'id': owner_obj.id,
                        'name': owner_obj.name,
                        'is_open': is_open
                    })
        
        if not available_objects:
            await query.edit_message_text(
                text="❌ У вас нет доступных объектов.",
                parse_mode='HTML'
            )
            return
        
        # Фильтровать только закрытые объекты
        closed_objects = [o for o in available_objects if not o['is_open']]
        
        if not closed_objects:
            await query.edit_message_text(
                text="ℹ️ Все ваши объекты уже открыты.\n\n"
                     "Используйте кнопку 'Открыть смену' для начала работы.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift")
                ]])
            )
            return
        
        # Если один объект - сразу запросить геолокацию
        if len(closed_objects) == 1:
            selected_object = closed_objects[0]
            
            # Создать состояние
            await user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_OBJECT,
                step=UserStep.OPENING_OBJECT_LOCATION,
                selected_object_id=selected_object['id']
            )
            
            await query.edit_message_text(
                text=f"🏢 <b>Открытие объекта</b>\n\n"
                     f"Объект: <b>{selected_object['name']}</b>\n\n"
                     f"📍 Нажмите кнопку ниже для отправки геопозиции:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
                ]])
            )
            
            # Отправляем клавиатуру для геопозиции
            from telegram import KeyboardButton, ReplyKeyboardMarkup
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="👇 Используйте кнопку для отправки геопозиции:",
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
        else:
            # Показать список объектов для выбора
            keyboard = []
            for obj in closed_objects:
                keyboard.append([InlineKeyboardButton(
                    f"🏢 {obj['name']}",
                    callback_data=f"select_object_to_open:{obj['id']}"
                )])
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="main_menu")])
            
            await user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.OPEN_OBJECT,
                step=UserStep.OBJECT_SELECTION
            )
            
            await query.edit_message_text(
                text="🏢 <b>Открытие объекта</b>\n\n"
                     "Выберите объект для открытия:",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def _handle_select_object_to_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора объекта для открытия."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    object_id = int(query.data.split(':')[1])
    
    async with get_async_session() as session:
        obj_query = select(Object).where(Object.id == object_id)
        obj_result = await session.execute(obj_query)
        obj = obj_result.scalar_one_or_none()
        
        if not obj:
            await query.edit_message_text(
                text="❌ Объект не найден.",
                parse_mode='HTML'
            )
            return
        
        # Создать состояние для геолокации
        await user_state_manager.create_state(
            user_id=user_id,
            action=UserAction.OPEN_OBJECT,
            step=UserStep.OPENING_OBJECT_LOCATION,
            selected_object_id=object_id
        )
        
        logger.info(
            f"State created for object opening",
            user_id=user_id,
            action=UserAction.OPEN_OBJECT,
            step=UserStep.OPENING_OBJECT_LOCATION,
            object_id=object_id
        )
        
        await query.edit_message_text(
            text=f"🏢 <b>Открытие объекта</b>\n\n"
                 f"Объект: <b>{obj.name}</b>\n\n"
                 f"📍 Нажмите кнопку ниже для отправки геопозиции:",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="main_menu")
            ]])
        )
        
        # Отправляем клавиатуру для геопозиции (новое сообщение!)
        from telegram import KeyboardButton, ReplyKeyboardMarkup
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="👇 Используйте кнопку для отправки геопозиции:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        )


async def _handle_close_object(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик закрытия объекта."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} initiated object closing")
    
    # Получить активные смены пользователя
    bot_shift_service = BotShiftService()
    active_shifts = await bot_shift_service.get_user_active_shifts(user_id)
    
    if not active_shifts:
        await query.edit_message_text(
            text="❌ У вас нет активных смен.",
            parse_mode='HTML'
        )
        return
    
    if len(active_shifts) > 1:
        await query.edit_message_text(
            text="⚠️ <b>Несколько активных смен</b>\n\n"
                 "Сначала закройте свою смену через кнопку 'Закрыть смену'.\n\n"
                 "Закрытие объекта доступно только когда у вас одна активная смена.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
            ]])
        )
        return
    
    # Одна активная смена - проверяем, последняя ли она на объекте
    shift = active_shifts[0]
    object_id = shift['object_id']
    
    async with get_async_session() as session:
        opening_service = ObjectOpeningService(session)
        active_count = await opening_service.get_active_shifts_count(object_id)
        
        if active_count > 1:
            await query.edit_message_text(
                text="⚠️ <b>На объекте работают другие сотрудники</b>\n\n"
                     "Вы можете закрыть только свою смену.\n\n"
                     "Закрытие объекта доступно только последнему сотруднику.",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
                ]])
            )
            return
        
        # Последняя смена - переходим к закрытию
        # Проверяем, есть ли уже состояние для этой смены
        existing_state = await user_state_manager.get_state(user_id)
        
        if existing_state and existing_state.selected_shift_id == shift['id']:
            # Обновляем существующий state, сохраняя completed_tasks и task_media
            # НО сбрасываем step, чтобы _handle_close_shift заново показал задачи
            await user_state_manager.update_state(
                user_id=user_id,
                action=UserAction.CLOSE_OBJECT,
                step=UserStep.SHIFT_SELECTION,  # КРИТИЧНО: сброс step!
                selected_object_id=object_id
            )
        else:
            # Создаем новый state
            await user_state_manager.create_state(
                user_id=user_id,
                action=UserAction.CLOSE_OBJECT,
                step=UserStep.SHIFT_SELECTION,
                selected_shift_id=shift['id'],
                selected_object_id=object_id
            )
        
        # Перенаправляем на обычный флоу закрытия смены
        # Он обработает задачи, геолокацию, и в конце мы закроем объект
        from apps.bot.handlers_div.shift_handlers import _handle_close_shift
        await _handle_close_shift(update, context)

