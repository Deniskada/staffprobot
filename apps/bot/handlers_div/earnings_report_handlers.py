"""Обработчики для отчетов по заработку сотрудника."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler
from core.logging.logger import logger
from core.database.connection import get_sync_session
from domain.entities.user import User
from domain.entities.shift import Shift
from domain.entities.object import Object
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
import pytz

# Состояния для ConversationHandler
(SELECT_WEEK, CUSTOM_DATES, SHOW_REPORT) = range(3)


class EarningsReportHandlers:
    """Класс для обработки отчетов по заработку сотрудника."""
    
    def __init__(self):
        """Инициализация обработчиков отчетов."""
        logger.info("EarningsReportHandlers initialized")
    
    def get_last_4_weeks(self) -> List[Dict[str, Any]]:
        """Получить текущую и 3 предыдущие недели (с понедельника по воскресенье)."""
        today = date.today()
        
        # Находим понедельник текущей недели
        days_since_monday = today.weekday()
        current_monday = today - timedelta(days=days_since_monday)
        
        weeks = []
        # Сначала текущая неделя, потом 3 предыдущие
        for i in range(4):
            week_start = current_monday - timedelta(weeks=i)
            week_end = week_start + timedelta(days=6)
            
            label = f"{week_start.strftime('%d.%m')} - {week_end.strftime('%d.%m.%Y')}"
            if i == 0:
                label = f"📍 Текущая ({label})"
            
            weeks.append({
                'start': week_start,
                'end': week_end,
                'label': label
            })
        
        return weeks
    
    async def start_earnings_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало создания отчета по заработку."""
        query = update.callback_query
        user_id = query.from_user.id
        logger.info(f"Starting earnings report for user {user_id}")
        
        try:
            # Получаем внутренний user_id
            with get_sync_session() as session:
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await query.edit_message_text("❌ Пользователь не найден в базе данных.")
                    return ConversationHandler.END
                
                context.user_data['user_id'] = user.id
                
                # Получаем 4 последние недели
                weeks = self.get_last_4_weeks()
                context.user_data['weeks'] = weeks
                
                # Создаем клавиатуру с неделями
                keyboard = []
                for i, week in enumerate(weeks):
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📅 {week['label']}", 
                            callback_data=f"week_{i}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton("📝 Выбрать даты вручную", callback_data="custom_dates")
                ])
                keyboard.append([
                    InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "📊 **Отчет по заработку**\n\n"
                    "Выберите неделю для отчета:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                return SELECT_WEEK
                
        except Exception as e:
            logger.error(f"Error starting earnings report: {e}")
            await query.edit_message_text("❌ Ошибка загрузки отчета. Попробуйте позже.")
            return ConversationHandler.END
    
    async def handle_week_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора недели."""
        query = update.callback_query
        
        if query.data == "custom_dates":
            # Устанавливаем состояние пользователя для ввода дат
            from core.state import user_state_manager, UserAction, UserStep
            user_state_manager.set_state(
                query.from_user.id,
                UserAction.REPORT_DATES,
                UserStep.WAITING_INPUT
            )
            
            await query.edit_message_text(
                "📝 **Выбор дат вручную**\n\n"
                "Отправьте даты в формате:\n"
                "<code>01.01.2024 - 07.01.2024</code>\n\n"
                "Или отправьте <code>отмена</code> для возврата к выбору недель.",
                parse_mode='HTML'
            )
            return CUSTOM_DATES
        elif query.data == "cancel_report":
            # Очищаем состояние пользователя
            from core.state import user_state_manager
            user_state_manager.clear_state(query.from_user.id)
            
            await query.edit_message_text("❌ Создание отчета отменено.")
            return ConversationHandler.END
        elif query.data.startswith("week_"):
            week_index = int(query.data.split("_")[1])
            weeks = context.user_data['weeks']
            selected_week = weeks[week_index]
            
            context.user_data['start_date'] = selected_week['start']
            context.user_data['end_date'] = selected_week['end']
            
            return await self.generate_earnings_report(update, context)
        
        return SELECT_WEEK
    
    async def handle_custom_dates(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка ввода дат вручную."""
        text = update.message.text.strip().lower()
        
        if text == "отмена":
            # Создаем callback_query для совместимости
            fake_query = CallbackQuery(
                id="fake",
                from_user=update.effective_user,
                chat_instance="fake",
                data="get_report"
            )
            fake_query.message = update.message
            fake_update = Update(update_id=update.update_id, callback_query=fake_query)
            return await self.start_earnings_report(fake_update, context)
        
        try:
            # Парсим даты в формате "01.01.2024 - 07.01.2024"
            if " - " in text:
                start_str, end_str = text.split(" - ", 1)
                start_date = datetime.strptime(start_str.strip(), "%d.%m.%Y").date()
                end_date = datetime.strptime(end_str.strip(), "%d.%m.%Y").date()
                
                if start_date > end_date:
                    await update.message.reply_text("❌ Дата начала не может быть позже даты окончания.")
                    return CUSTOM_DATES
                
                context.user_data['start_date'] = start_date
                context.user_data['end_date'] = end_date
                
                # Получаем user_id из базы данных
                with get_sync_session() as session:
                    user_query = select(User).where(User.telegram_id == update.effective_user.id)
                    user_result = session.execute(user_query)
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        await update.message.reply_text("❌ Пользователь не найден в базе данных.")
                        return ConversationHandler.END
                    
                    context.user_data['user_id'] = user.id
                
                return await self.generate_earnings_report(update, context)
            else:
                await update.message.reply_text(
                    "❌ Неверный формат дат. Используйте:\n"
                    "<code>01.01.2024 - 07.01.2024</code>",
                    parse_mode='HTML'
                )
                return CUSTOM_DATES
                
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат дат. Используйте:\n"
                "<code>01.01.2024 - 07.01.2024</code>",
                parse_mode='HTML'
            )
            return CUSTOM_DATES
    
    async def generate_earnings_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Генерация отчета по заработку."""
        logger.info(f"Starting earnings report generation")
        
        user_id = context.user_data.get('user_id')
        start_date = context.user_data.get('start_date')
        end_date = context.user_data.get('end_date')
        
        logger.info(f"Report data: user_id={user_id}, start_date={start_date}, end_date={end_date}")
        
        if not user_id or not start_date or not end_date:
            logger.error(f"Missing report data: user_id={user_id}, start_date={start_date}, end_date={end_date}")
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text("❌ Ошибка: не найдены данные для отчета.")
            else:
                await update.message.reply_text("❌ Ошибка: не найдены данные для отчета.")
            return ConversationHandler.END
        
        try:
            with get_sync_session() as session:
                # Получаем все завершенные смены пользователя за период
                shifts_query = select(Shift, Object).join(
                    Object, Shift.object_id == Object.id
                ).where(
                    and_(
                        Shift.user_id == user_id,
                        Shift.status == 'completed',
                        func.date(Shift.start_time) >= start_date,
                        func.date(Shift.start_time) <= end_date
                    )
                ).order_by(Shift.start_time)
                
                shifts_result = session.execute(shifts_query)
                shifts_data = shifts_result.all()
                
                logger.info(f"Found {len(shifts_data)} completed shifts for period {start_date} - {end_date}")
                
                if not shifts_data:
                    message_text = (
                        f"📊 **Отчет по заработку**\n\n"
                        f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
                        f"❌ За этот период у вас не было завершенных смен."
                    )
                    if hasattr(update, 'callback_query') and update.callback_query:
                        await update.callback_query.edit_message_text(message_text, parse_mode='Markdown')
                    else:
                        await update.message.reply_text(message_text, parse_mode='Markdown')
                    return ConversationHandler.END
                
                # Группируем смены по дням и объектам
                daily_earnings = {}
                total_earnings = 0
                total_hours = 0
                
                for shift, object_obj in shifts_data:
                    shift_date = shift.start_time.date()
                    object_name = object_obj.name
                    hourly_rate = float(shift.hourly_rate or 0)
                    
                    # Вычисляем часы работы
                    if shift.start_time and shift.end_time:
                        duration = shift.end_time - shift.start_time
                        hours = duration.total_seconds() / 3600
                    else:
                        hours = 0
                    
                    earnings = hours * hourly_rate
                    
                    if shift_date not in daily_earnings:
                        daily_earnings[shift_date] = {}
                    
                    if object_name not in daily_earnings[shift_date]:
                        daily_earnings[shift_date][object_name] = {
                            'hours': 0,
                            'earnings': 0,
                            'shifts': 0
                        }
                    
                    daily_earnings[shift_date][object_name]['hours'] += hours
                    daily_earnings[shift_date][object_name]['earnings'] += earnings
                    daily_earnings[shift_date][object_name]['shifts'] += 1
                    
                    total_earnings += earnings
                    total_hours += hours
                
                # Формируем отчет
                report_text = f"📊 **Отчет по заработку**\n\n"
                report_text += f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
                
                # Сортируем дни по дате
                sorted_days = sorted(daily_earnings.keys())
                
                for day in sorted_days:
                    day_earnings = daily_earnings[day]
                    day_total = sum(obj['earnings'] for obj in day_earnings.values())
                    day_hours = sum(obj['hours'] for obj in day_earnings.values())
                    
                    report_text += f"📅 **{day.strftime('%d.%m.%Y')}** ({day.strftime('%A')})\n"
                    
                    for object_name, data in day_earnings.items():
                        report_text += f"  🏢 {object_name}: {data['hours']:.1f}ч × {data['earnings']/data['hours']:.0f}₽ = {data['earnings']:.0f}₽\n"
                    
                    report_text += f"  💰 **Итого за день: {day_total:.0f}₽ ({day_hours:.1f}ч)**\n\n"
                
                report_text += f"💰 **Общий итог: {total_earnings:.0f}₽ ({total_hours:.1f}ч)**\n"
                report_text += f"📈 Средняя ставка: {total_earnings/total_hours:.0f}₽/ч" if total_hours > 0 else "📈 Средняя ставка: 0₽/ч"
                
                # Создаем кнопку возврата
                keyboard = [[
                    InlineKeyboardButton("📊 Новый отчет", callback_data="get_report"),
                    InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(
                        report_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                else:
                    await update.message.reply_text(
                        report_text,
                        parse_mode='Markdown',
                        reply_markup=reply_markup
                    )
                
                # Очищаем состояние пользователя
                from core.state import user_state_manager
                user_state_manager.clear_state(update.effective_user.id)
                
                return ConversationHandler.END
                
        except Exception as e:
            logger.error(f"Error generating earnings report: {e}")
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text("❌ Ошибка генерации отчета. Попробуйте позже.")
            else:
                await update.message.reply_text("❌ Ошибка генерации отчета. Попробуйте позже.")
            return ConversationHandler.END
