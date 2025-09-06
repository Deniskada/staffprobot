"""Обработчики для аналитики и отчетов."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler
from core.logging.logger import logger
from apps.analytics.analytics_service import AnalyticsService
from apps.analytics.export_service import ExportService
from core.database.connection import get_sync_session
from domain.entities.object import Object
from sqlalchemy import select
from datetime import datetime, timedelta, date
from typing import Dict, Any

# Создаем экземпляры сервисов
analytics_service = AnalyticsService()
export_service = ExportService()

# Состояния для ConversationHandler
(ANALYTICS_MENU, SELECT_OBJECT, SELECT_PERIOD, SELECT_FORMAT, 
 GENERATE_REPORT, DASHBOARD_VIEW) = range(6)


class AnalyticsHandlers:
    """Класс для обработки аналитики и отчетов."""
    
    def __init__(self):
        """Инициализация обработчиков аналитики."""
        logger.info("AnalyticsHandlers initialized")
    
    async def start_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало работы с аналитикой."""
        user_id = update.effective_user.id
        
        # Проверяем, есть ли у пользователя объекты
        try:
            with get_sync_session() as session:
                # Сначала находим пользователя по telegram_id
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await update.callback_query.edit_message_text(
                        "❌ Пользователь не найден в базе данных."
                    )
                    return ConversationHandler.END
                
                # Теперь находим объекты пользователя
                objects_query = select(Object).where(Object.owner_id == user.id, Object.is_active == True)
                objects_result = session.execute(objects_query)
                objects = objects_result.scalars().all()
                
                if not objects:
                    await update.callback_query.edit_message_text(
                        "📊 **Аналитика и отчеты**\n\n"
                        "❌ У вас нет объектов для анализа.\n\n"
                        "Сначала создайте объекты через меню управления объектами."
                    )
                    return ConversationHandler.END
                
                # Создаем меню аналитики
                keyboard = [
                    [InlineKeyboardButton("📈 Дашборд", callback_data="analytics_dashboard")],
                    [InlineKeyboardButton("📊 Создать отчет", callback_data="analytics_report")],
                    [InlineKeyboardButton("❌ Отмена", callback_data="analytics_cancel")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    "📊 **Аналитика и отчеты**\n\n"
                    "Выберите действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                return ANALYTICS_MENU
                
        except Exception as e:
            logger.error(f"Error starting analytics: {e}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка загрузки аналитики. Попробуйте позже."
            )
            return ConversationHandler.END
    
    async def handle_analytics_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка меню аналитики."""
        query = update.callback_query
        
        if query.data == "analytics_dashboard":
            return await self.show_dashboard(update, context)
        elif query.data == "analytics_report":
            return await self.start_report_creation(update, context)
        elif query.data == "analytics_cancel":
            await query.edit_message_text("❌ Аналитика отменена.")
            return ConversationHandler.END
        
        return ANALYTICS_MENU
    
    async def show_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показ дашборда."""
        user_id = update.effective_user.id
        
        try:
            # Получаем внутренний user_id из базы данных
            with get_sync_session() as session:
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await update.callback_query.edit_message_text(
                        "❌ Пользователь не найден в базе данных."
                    )
                    return ConversationHandler.END
                
                internal_user_id = user.id
            
            # Получаем данные дашборда
            dashboard_data = analytics_service.get_owner_dashboard(internal_user_id)
            
            # Формируем текст дашборда
            dashboard_text = "📈 **Дашборд владельца**\n\n"
            
            if dashboard_data:
                dashboard_text += f"💰 Общая сумма к выплате: {dashboard_data.get('total_payments', 0)} ₽\n"
                dashboard_text += f"📊 Всего смен: {dashboard_data.get('total_shifts', 0)}\n"
                dashboard_text += f"🔄 Активных смен: {dashboard_data.get('active_shifts', 0)}\n\n"
                
                # Топ объекты
                top_objects = dashboard_data.get('top_objects', [])
                if top_objects:
                    dashboard_text += "🏆 **Топ объекты по активности:**\n"
                    for i, obj in enumerate(top_objects[:3], 1):
                        dashboard_text += f"{i}. {obj.get('name', 'N/A')} - {obj.get('shifts_count', 0)} смен\n"
            else:
                dashboard_text += "📊 Данных для отображения пока нет."
            
            # Кнопки управления
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="analytics_dashboard")],
                [InlineKeyboardButton("📊 Создать отчет", callback_data="analytics_report")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="analytics_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                dashboard_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
            return DASHBOARD_VIEW
            
        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка загрузки дашборда. Попробуйте позже."
            )
            return ConversationHandler.END
    
    async def start_report_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало создания отчета."""
        user_id = update.effective_user.id
        
        try:
            with get_sync_session() as session:
                # Сначала находим пользователя по telegram_id
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await update.callback_query.edit_message_text(
                        "❌ Пользователь не найден в базе данных."
                    )
                    return ConversationHandler.END
                
                # Теперь находим объекты пользователя
                objects_query = select(Object).where(Object.owner_id == user.id, Object.is_active == True)
                objects_result = session.execute(objects_query)
                objects = objects_result.scalars().all()
                
                # Создаем клавиатуру с объектами
                keyboard = []
                for obj in objects:
                    keyboard.append([InlineKeyboardButton(
                        f"🏢 {obj.name}",
                        callback_data=f"report_object_{obj.id}"
                    )])
                
                keyboard.append([InlineKeyboardButton("📊 Все объекты", callback_data="report_all_objects")])
                keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="analytics_cancel")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    "📊 **Создание отчета**\n\n"
                    "Выберите объект для отчета:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                
                return SELECT_OBJECT
                
        except Exception as e:
            logger.error(f"Error starting report creation: {e}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка создания отчета. Попробуйте позже."
            )
            return ConversationHandler.END
    
    async def select_object(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор объекта для отчета."""
        query = update.callback_query
        
        if query.data == "report_all_objects":
            context.user_data['selected_object_id'] = None
            object_name = "Все объекты"
        else:
            object_id = int(query.data.split("_")[-1])
            context.user_data['selected_object_id'] = object_id
            
            # Получаем название объекта
            try:
                with get_sync_session() as session:
                    object_query = select(Object).where(Object.id == object_id)
                    object_result = session.execute(object_query)
                    obj = object_result.scalar_one_or_none()
                    object_name = obj.name if obj else "Неизвестный объект"
            except Exception:
                object_name = "Неизвестный объект"
        
        # Создаем клавиатуру с периодами
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="period_today")],
            [InlineKeyboardButton("📅 Эта неделя", callback_data="period_week")],
            [InlineKeyboardButton("📅 Этот месяц", callback_data="period_month")],
            [InlineKeyboardButton("📅 Последние 3 месяца", callback_data="period_quarter")],
            [InlineKeyboardButton("📅 Произвольный период", callback_data="period_custom")],
            [InlineKeyboardButton("❌ Отмена", callback_data="analytics_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Отчет по объекту: {object_name}**\n\n"
            "Выберите период для отчета:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return SELECT_PERIOD
    
    async def select_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор периода для отчета."""
        query = update.callback_query
        
        # Определяем период
        today = date.today()
        if query.data == "period_today":
            start_date = today
            end_date = today
            period_name = "Сегодня"
        elif query.data == "period_week":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            period_name = "Эта неделя"
        elif query.data == "period_month":
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            period_name = "Этот месяц"
        elif query.data == "period_quarter":
            start_date = today - timedelta(days=90)
            end_date = today
            period_name = "Последние 3 месяца"
        elif query.data == "period_custom":
            # Произвольный период - запрашиваем даты
            await query.edit_message_text(
                "📅 **Произвольный период**\n\n"
                "Введите даты в формате:\n"
                "**ДД.ММ.ГГГГ - ДД.ММ.ГГГГ**\n\n"
                "Например: 01.09.2025 - 30.09.2025\n\n"
                "Или отправьте дату начала и конца периода в отдельных сообщениях:\n"
                "**Начало:** ДД.ММ.ГГГГ\n"
                "**Конец:** ДД.ММ.ГГГГ"
            )
            # Устанавливаем состояние для ввода дат
            context.user_data['waiting_for_dates'] = True
            return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Неверный выбор периода.")
            return ConversationHandler.END
        
        # Сохраняем период
        context.user_data['start_date'] = start_date
        context.user_data['end_date'] = end_date
        context.user_data['period_name'] = period_name
        
        # Создаем клавиатуру с форматами
        keyboard = [
            [InlineKeyboardButton("📄 Текстовый отчет", callback_data="format_text")],
            [InlineKeyboardButton("📊 PDF отчет", callback_data="format_pdf")],
            [InlineKeyboardButton("📈 Excel отчет", callback_data="format_excel")],
            [InlineKeyboardButton("❌ Отмена", callback_data="analytics_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📊 **Период: {period_name}**\n\n"
            "Выберите формат отчета:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        return SELECT_FORMAT
    
    async def select_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор формата отчета."""
        query = update.callback_query
        
        format_type = query.data.split("_")[-1]
        context.user_data['format'] = format_type
        
        # Генерируем отчет
        return await self.generate_report(update, context)
    
    async def generate_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Генерация отчета."""
        user_id = update.effective_user.id
        
        # Получаем данные из контекста
        object_id = context.user_data.get('selected_object_id')
        start_date = context.user_data.get('start_date')
        end_date = context.user_data.get('end_date')
        period_name = context.user_data.get('period_name')
        format_type = context.user_data.get('format')
        
        try:
            # Получаем внутренний user_id из базы данных
            with get_sync_session() as session:
                from domain.entities.user import User
                user_query = select(User).where(User.telegram_id == user_id)
                user_result = session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    await update.callback_query.edit_message_text(
                        "❌ Пользователь не найден в базе данных."
                    )
                    return ConversationHandler.END
                
                internal_user_id = user.id
            
            # Генерируем отчет
            if format_type == "text":
                # Текстовый отчет
                report_data = analytics_service.get_object_report(
                    owner_id=internal_user_id,
                    object_id=object_id,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if report_data and not report_data.get('error'):
                    # Информация об объекте
                    object_info = report_data.get('object', {})
                    report_text = f"📊 **Отчет за период: {period_name}**\n\n"
                    report_text += f"🏢 **Объект:** {object_info.get('name', 'N/A')}\n"
                    report_text += f"📅 **Период:** {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"
                    
                    # Общая статистика
                    summary = report_data.get('summary', {})
                    report_text += f"📊 **Общая статистика:**\n"
                    report_text += f"• Всего смен: {summary.get('total_shifts', 0)}\n"
                    report_text += f"• Завершенных: {summary.get('completed_shifts', 0)}\n"
                    report_text += f"• Активных: {summary.get('active_shifts', 0)}\n"
                    report_text += f"• Общее время: {summary.get('total_hours', 0)} часов\n"
                    report_text += f"• Общая сумма: {summary.get('total_payment', 0)} ₽\n\n"
                    
                    # Статистика по сотрудникам
                    employees = report_data.get('employees', [])
                    if employees:
                        report_text += "👥 **Статистика по сотрудникам:**\n"
                        for emp in employees:
                            report_text += f"• **{emp.get('name', 'N/A')}**\n"
                            report_text += f"  - Смен: {emp.get('shifts', 0)}\n"
                            report_text += f"  - Часов: {emp.get('hours', 0)}\n"
                            report_text += f"  - К оплате: {emp.get('payment', 0)} ₽\n\n"
                    else:
                        report_text += "👥 **Сотрудники:** Нет данных\n\n"
                    
                    await update.callback_query.edit_message_text(
                        report_text,
                        parse_mode='Markdown'
                    )
                else:
                    error_msg = report_data.get('error', 'Данных за выбранный период не найдено.')
                    await update.callback_query.edit_message_text(
                        f"📊 **Отчет за период: {period_name}**\n\n"
                        f"❌ {error_msg}"
                    )
            
            elif format_type == "excel":
                # Excel отчет
                try:
                    # Генерируем Excel файл
                    excel_file = export_service.generate_excel_report(
                        owner_id=internal_user_id,
                        object_id=object_id,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if excel_file:
                        # Отправляем файл
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=excel_file,
                            filename=f"report_{period_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx",
                            caption=f"📊 **Отчет за период: {period_name}**\n"
                                   f"📅 {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
                        )
                        
                        await update.callback_query.edit_message_text(
                            f"📊 **Отчет за период: {period_name}**\n\n"
                            "✅ Excel файл успешно сгенерирован и отправлен!"
                        )
                    else:
                        await update.callback_query.edit_message_text(
                            f"📊 **Отчет за период: {period_name}**\n\n"
                            "❌ Ошибка генерации Excel файла."
                        )
                except Exception as e:
                    logger.error(f"Error generating Excel report: {e}")
                    await update.callback_query.edit_message_text(
                        f"📊 **Отчет за период: {period_name}**\n\n"
                        "❌ Ошибка генерации Excel файла. Попробуйте позже."
                    )
            else:
                # PDF отчет
                await update.callback_query.edit_message_text(
                    "📊 Генерация отчета...\n\n"
                    "Функция экспорта в PDF временно недоступна.\n"
                    "Используйте текстовый формат или Excel."
                )
            
            # Кнопка возврата
            keyboard = [
                [InlineKeyboardButton("📊 Новый отчет", callback_data="analytics_report")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="analytics_cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
            
            return GENERATE_REPORT
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            await update.callback_query.edit_message_text(
                "❌ Ошибка генерации отчета. Попробуйте позже."
            )
            return ConversationHandler.END
    
    async def cancel_analytics(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена работы с аналитикой."""
        # Очищаем контекст
        context.user_data.clear()
        
        await update.callback_query.edit_message_text("❌ Аналитика отменена.")
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Получение ConversationHandler для аналитики."""
        from telegram.ext import MessageHandler, filters
        
        return ConversationHandler(
            entry_points=[CallbackQueryHandler(self.start_analytics, pattern="^analytics$")],
            states={
                ANALYTICS_MENU: [CallbackQueryHandler(self.handle_analytics_menu)],
                SELECT_OBJECT: [CallbackQueryHandler(self.select_object)],
                SELECT_PERIOD: [CallbackQueryHandler(self.select_period)],
                SELECT_FORMAT: [CallbackQueryHandler(self.select_format)],
                GENERATE_REPORT: [CallbackQueryHandler(self.handle_analytics_menu)],
                DASHBOARD_VIEW: [CallbackQueryHandler(self.handle_analytics_menu)]
            },
            fallbacks=[
                CallbackQueryHandler(self.cancel_analytics, pattern="^analytics_cancel$")
            ]
        )
