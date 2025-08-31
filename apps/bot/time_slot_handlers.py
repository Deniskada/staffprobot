"""Обработчики для управления тайм-слотами объектов."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from datetime import datetime, date, time, timedelta
from core.logging.logger import logger
from apps.bot.services.time_slot_service import TimeSlotService
from apps.bot.services.schedule_service import ScheduleService
from apps.bot.services.object_service import ObjectService
from core.state.user_state_manager import UserStateManager


# Состояния диалога
SELECT_OBJECT, SELECT_DATE, SELECT_TIMESLOT, SELECT_INTERVAL, CONFIRM_BOOKING = range(5)

# Состояния для создания тайм-слотов
CREATE_SLOT_OBJECT, CREATE_SLOT_DATE, CREATE_SLOT_TIME, CREATE_SLOT_RATE, CREATE_SLOT_CONFIRM = range(5, 10)


class TimeSlotHandlers:
    """Обработчики для управления тайм-слотами."""
    
    def __init__(self):
        """Инициализация обработчиков."""
        self.time_slot_service = TimeSlotService()
        self.schedule_service = ScheduleService()
        self.object_service = ObjectService()
        self.state_manager = UserStateManager()
        logger.info("TimeSlotHandlers initialized")
    
    async def show_timeslot_planning_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показывает меню планирования через тайм-слоты."""
        try:
            user_id = update.effective_user.id
            
            # Получаем объекты пользователя
            user_objects = self.object_service.get_user_objects(user_id)
            
            if not user_objects:
                await update.callback_query.edit_message_text(
                    "❌ У вас нет объектов для планирования смен.\n"
                    "Сначала создайте объект через меню '🏢 Создать объект'."
                )
                return ConversationHandler.END
            
            # Создаем клавиатуру с объектами
            keyboard = []
            for obj in user_objects:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏢 {obj['name']} ({obj['working_hours']})", 
                        callback_data=f"select_object_{obj['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_timeslot")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = "📅 *Планирование смен через тайм-слоты*\n\n" \
                   "Выберите объект для планирования:"
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            return SELECT_OBJECT
            
        except Exception as e:
            logger.error(f"Error showing timeslot planning menu: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка загрузки меню")
            return ConversationHandler.END
    
    async def handle_object_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает выбор объекта."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_timeslot":
                return await self.cancel_timeslot_planning(update, context)
                return ConversationHandler.END
            
            # Извлекаем ID объекта
            object_id = int(query.data.split('_')[-1])
            
            # Сохраняем в контексте
            context.user_data['selected_object_id'] = object_id
            
            # Получаем информацию об объекте
            object_info = self.object_service.get_object_by_id(object_id)
            if not object_info:
                await query.edit_message_text("❌ Объект не найден")
                return ConversationHandler.END
            
            # Показываем выбор даты
            keyboard = [
                [
                    InlineKeyboardButton("📅 Сегодня", callback_data="date_today"),
                    InlineKeyboardButton("📅 Завтра", callback_data="date_tomorrow")
                ],
                [
                    InlineKeyboardButton("📅 Послезавтра", callback_data="date_day_after")
                ],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_timeslot")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"🏢 *Объект:* {object_info['name']}\n" \
                   f"📅 Выберите дату для планирования:"
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECT_DATE
            
        except Exception as e:
            logger.error(f"Error handling object selection: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка выбора объекта")
            return ConversationHandler.END
    
    async def handle_date_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает выбор даты."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_timeslot":
                return await self.cancel_timeslot_planning(update, context)
                return ConversationHandler.END
            
            # Определяем выбранную дату
            today = date.today()
            if query.data == "date_today":
                selected_date = today
            elif query.data == "date_tomorrow":
                selected_date = today + timedelta(days=1)
            elif query.data == "date_day_after":
                selected_date = today + timedelta(days=2)
            else:
                await query.edit_message_text("❌ Неизвестная дата")
                return ConversationHandler.END
            
            # Сохраняем дату в контексте
            context.user_data['selected_date'] = selected_date
            
            object_id = context.user_data.get('selected_object_id')
            if not object_id:
                await query.edit_message_text("❌ Ошибка: объект не выбран")
                return ConversationHandler.END
            
            # Получаем доступные тайм-слоты
            available_slots = await self.schedule_service.get_available_time_slots_for_date(
                object_id, selected_date
            )
            
            if not available_slots['success']:
                await query.edit_message_text(
                    f"❌ {available_slots['error']}\n\n"
                    f"Попробуйте другую дату или создайте дополнительные тайм-слоты."
                )
                return ConversationHandler.END
            
            # Показываем доступные тайм-слоты
            keyboard = []
            for slot in available_slots['available_slots']:
                slot_text = f"🕐 {slot['start_time']}-{slot['end_time']}"
                if slot['is_additional']:
                    slot_text += " ⭐"
                if slot['max_employees'] > 1:
                    slot_text += f" 👥{slot['max_employees']}"
                
                keyboard.append([
                    InlineKeyboardButton(
                        slot_text, 
                        callback_data=f"select_slot_{slot['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_timeslot")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"📅 *Дата:* {selected_date.strftime('%d.%m.%Y')}\n" \
                   f"🏢 *Объект:* {self.object_service.get_object_by_id(object_id)['name']}\n\n" \
                   f"🕐 *Доступные тайм-слоты:*\n" \
                   f"⭐ - дополнительные слоты\n" \
                   f"👥 - количество сотрудников\n\n" \
                   f"Выберите тайм-слот:"
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECT_TIMESLOT
            
        except Exception as e:
            logger.error(f"Error handling date selection: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка выбора даты")
            return ConversationHandler.END
    
    async def handle_timeslot_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает выбор тайм-слота."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_timeslot":
                return await self.cancel_timeslot_planning(update, context)
                return ConversationHandler.END
            
            # Извлекаем ID тайм-слота
            timeslot_id = int(query.data.split('_')[-1])
            
            # Сохраняем в контексте
            context.user_data['selected_timeslot_id'] = timeslot_id
            
            # Получаем информацию о тайм-слоте
            object_id = context.user_data.get('selected_object_id')
            selected_date = context.user_data.get('selected_date')
            
            available_slots = await self.schedule_service.get_available_time_slots_for_date(
                object_id, selected_date
            )
            
            if not available_slots['success']:
                await query.edit_message_text("❌ Ошибка получения тайм-слотов")
                return ConversationHandler.END
            
            # Находим выбранный слот
            selected_slot = None
            for slot in available_slots['available_slots']:
                if slot['id'] == timeslot_id:
                    selected_slot = slot
                    break
            
            if not selected_slot:
                await query.edit_message_text("❌ Тайм-слот не найден")
                return ConversationHandler.END
            
            # Показываем доступные интервалы
            keyboard = []
            for interval in selected_slot['available_intervals']:
                duration_text = f"({interval['duration_hours']}ч)"
                keyboard.append([
                    InlineKeyboardButton(
                        f"🕐 {interval['start']}-{interval['end']} {duration_text}", 
                        callback_data=f"select_interval_{interval['start']}_{interval['end']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_timeslot")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"🕐 *Тайм-слот:* {selected_slot['start_time']}-{selected_slot['end_time']}\n" \
                   f"💰 *Ставка:* {selected_slot['hourly_rate']}₽/час\n" \
                   f"👥 *Макс. сотрудников:* {selected_slot['max_employees']}\n\n" \
                   f"📅 *Доступные интервалы:*\n" \
                   f"Выберите время работы:"
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECT_INTERVAL
            
        except Exception as e:
            logger.error(f"Error handling timeslot selection: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка выбора тайм-слота")
            return ConversationHandler.END
    
    async def handle_interval_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает выбор временного интервала."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_timeslot":
                return await self.cancel_timeslot_planning(update, context)
                return ConversationHandler.END
            
            # Извлекаем время начала и окончания
            parts = query.data.split('_')
            start_time_str = parts[-2]
            end_time_str = parts[-1]
            
            # Парсим время
            start_time = datetime.strptime(start_time_str, '%H:%M').time()
            end_time = datetime.strptime(end_time_str, '%H:%M').time()
            
            # Сохраняем в контексте
            context.user_data['selected_start_time'] = start_time
            context.user_data['selected_end_time'] = end_time
            
            # Показываем подтверждение
            object_id = context.user_data.get('selected_object_id')
            selected_date = context.user_data.get('selected_date')
            timeslot_id = context.user_data.get('selected_timeslot_id')
            
            object_info = self.object_service.get_object_by_id(object_id)
            
            # Получаем информацию о тайм-слоте для ставки
            available_slots = await self.schedule_service.get_available_time_slots_for_date(
                object_id, selected_date
            )
            
            hourly_rate = None
            if available_slots['success']:
                for slot in available_slots['available_slots']:
                    if slot['id'] == timeslot_id:
                        hourly_rate = slot['hourly_rate']
                        break
            
            # Рассчитываем длительность и оплату
            duration_hours = round(
                (end_time.hour * 3600 + end_time.minute * 60 - 
                 start_time.hour * 3600 - start_time.minute * 60) / 3600, 2
            )
            
            total_payment = hourly_rate * duration_hours if hourly_rate else 0
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"),
                    InlineKeyboardButton("❌ Отмена", callback_data="cancel_timeslot")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"📋 *Подтверждение планирования смены*\n\n" \
                   f"🏢 *Объект:* {object_info['name']}\n" \
                   f"📅 *Дата:* {selected_date.strftime('%d.%m.%Y')}\n" \
                   f"🕐 *Время:* {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n" \
                   f"⏱️ *Длительность:* {duration_hours} ч\n" \
                   f"💰 *Ставка:* {hourly_rate}₽/час\n" \
                   f"💵 *Оплата:* {total_payment}₽\n\n" \
                   f"Подтвердите планирование смены:"
            
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return CONFIRM_BOOKING
            
        except Exception as e:
            logger.error(f"Error handling interval selection: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка выбора интервала")
            return ConversationHandler.END
    
    async def confirm_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Подтверждает бронирование тайм-слота."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_timeslot":
                return ConversationHandler.END
            
            # Получаем данные из контекста
            user_id = update.effective_user.id
            timeslot_id = context.user_data.get('selected_timeslot_id')
            start_time = context.user_data.get('selected_start_time')
            end_time = context.user_data.get('selected_end_time')
            
            if not all([timeslot_id, start_time, end_time]):
                await query.edit_message_text("❌ Ошибка: неполные данные для планирования")
                return ConversationHandler.END
            
            # Создаем запланированную смену
            result = await self.schedule_service.create_scheduled_shift_from_timeslot(
                user_id, timeslot_id, start_time, end_time
            )
            
            if result['success']:
                keyboard = [
                    [InlineKeyboardButton("📅 Запланировать еще", callback_data="plan_another_shift")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"✅ {result['message']}\n\n"
                    f"Смена успешно запланирована!",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка планирования:\n{result['error']}\n\n"
                    f"Попробуйте выбрать другой интервал времени."
                )
                return SELECT_INTERVAL
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error confirming booking: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка подтверждения бронирования")
            return ConversationHandler.END
    
    async def cancel_scheduled_shift(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отменяет конкретную запланированную смену."""
        try:
            query = update.callback_query
            await query.answer()
            
            # Извлекаем ID смены из callback_data
            shift_id = int(query.data.split('_')[-1])
            
            # Отменяем смену в базе данных
            result = await self.schedule_service.cancel_scheduled_shift(shift_id, update.effective_user.id)
            
            if result['success']:
                await query.edit_message_text(
                    f"✅ Смена отменена успешно!\n\n"
                    f"📅 Дата: {result.get('date', 'Неизвестно')}\n"
                    f"🕐 Время: {result.get('time', 'Неизвестно')}\n\n"
                    f"Используйте /start для возврата в главное меню."
                )
            else:
                await query.edit_message_text(
                    f"❌ Ошибка отмены смены:\n{result['error']}\n\n"
                    f"Используйте /start для возврата в главное меню."
                )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error canceling scheduled shift: {e}")
            await query.edit_message_text("❌ Ошибка отмены смены")
            return ConversationHandler.END
    
    async def cancel_timeslot_planning(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отменяет планирование тайм-слотов и возвращает в главное меню."""
        try:
            query = update.callback_query
            await query.answer()
            
            # Получаем информацию о пользователе
            user = query.from_user
            
            # Создаем главное меню
            response = f"""
🏠 <b>Главное меню</b>

👋 Привет, {user.first_name}!

Выберите действие кнопкой ниже:
"""
            
            # Создаем кнопки для главного меню
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Открыть смену", callback_data="open_shift"),
                    InlineKeyboardButton("🔚 Закрыть смену", callback_data="close_shift")
                ],
                [
                    InlineKeyboardButton("📅 Запланировать смену", callback_data="schedule_shift"),
                    InlineKeyboardButton("📋 Мои планы", callback_data="view_schedule")
                ],
                [
                    InlineKeyboardButton("🕐 Планирование через тайм-слоты", callback_data="plan_timeslot")
                ],
                [
                    InlineKeyboardButton("🏢 Создать объект", callback_data="create_object"),
                    InlineKeyboardButton("⚙️ Управление объектами", callback_data="manage_objects")
                ],
                [
                    InlineKeyboardButton("📊 Отчет", callback_data="get_report"),
                    InlineKeyboardButton("❓ Помощь", callback_data="help")
                ],
                [
                    InlineKeyboardButton("📈 Статус", callback_data="status")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем главное меню
            await query.edit_message_text(
                text=response,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error returning to main menu: {e}")
            await query.edit_message_text("❌ Ошибка возврата в главное меню")
            return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Получает обработчик диалога планирования тайм-слотов."""
        return ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.show_timeslot_planning_menu, pattern="^plan_timeslot$")
            ],
            states={
                SELECT_OBJECT: [
                    CallbackQueryHandler(self.handle_object_selection, pattern="^select_object_|cancel_timeslot$")
                ],
                SELECT_DATE: [
                    CallbackQueryHandler(self.handle_date_selection, pattern="^date_|cancel_timeslot$")
                ],
                SELECT_TIMESLOT: [
                    CallbackQueryHandler(self.handle_timeslot_selection, pattern="^select_slot_|cancel_timeslot$")
                ],
                SELECT_INTERVAL: [
                    CallbackQueryHandler(self.handle_interval_selection, pattern="^select_interval_|cancel_timeslot$")
                ],
                CONFIRM_BOOKING: [
                    CallbackQueryHandler(self.confirm_booking, pattern="^confirm_booking$"),
                    CallbackQueryHandler(self.cancel_timeslot_planning, pattern="^cancel_timeslot$")
                ]
            },
            fallbacks=[
                CallbackQueryHandler(self.cancel_timeslot_planning, pattern="^cancel_timeslot$")
            ]
        )
