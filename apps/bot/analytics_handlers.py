"""Обработчики команд аналитики и отчетов."""

import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters
from core.logging.logger import logger
from core.state.user_state_manager import UserStateManager, UserAction, UserStep
from apps.analytics.analytics_service import AnalyticsService
from apps.analytics.export_service import ExportService
from apps.bot.services.object_service import ObjectService
from apps.bot.services.user_service import UserService

# Состояния для диалога отчетов
REPORT_TYPE, REPORT_OBJECT, REPORT_PERIOD, REPORT_FORMAT, DASHBOARD = range(5)


class AnalyticsHandlers:
    """Обработчики команд аналитики."""
    
    def __init__(self):
        """Инициализация обработчиков."""
        self.state_manager = UserStateManager()
        self.analytics_service = AnalyticsService()
        self.export_service = ExportService()
        self.object_service = ObjectService()
        self.user_service = UserService()
        logger.info("AnalyticsHandlers initialized")
    
    async def reports_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Главное меню отчетов."""
        try:
            user_id = update.effective_user.id
            logger.info(f"reports_menu called for user {user_id}")
            
            keyboard = [
                [InlineKeyboardButton("📊 Отчет по объекту", callback_data="report_object")],
                [InlineKeyboardButton("👤 Персональный отчет", callback_data="report_personal")],
                [InlineKeyboardButton("📈 Дашборд", callback_data="report_dashboard")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = "📋 *Отчеты и аналитика*\n\nВыберите тип отчета:"
            
            if update.callback_query:
                await update.callback_query.answer()
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
            
            return REPORT_TYPE
            
        except Exception as e:
            logger.error(f"Error in reports_menu: {e}")
            await update.effective_message.reply_text("❌ Произошла ошибка при загрузке меню отчетов")
            return ConversationHandler.END
    
    async def handle_report_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора типа отчета."""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            choice = query.data
            logger.info(f"handle_report_type called for user {user_id}, choice: {choice}")
            
            if choice == "cancel_report":
                await query.edit_message_text("❌ Создание отчета отменено")
                return ConversationHandler.END
            
            context.user_data['report_type'] = choice
            
            if choice == "report_dashboard":
                # Сразу показываем дашборд
                return await self._show_dashboard(update, context)
            
            elif choice == "report_personal":
                # Для персонального отчета сразу переходим к выбору периода
                return await self._select_report_period(update, context)
            
            elif choice == "report_object":
                # Показываем список объектов пользователя
                return await self._select_report_object(update, context)
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in handle_report_type: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке выбора")
            return ConversationHandler.END
    
    async def _select_report_object(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор объекта для отчета."""
        try:
            user_id = update.effective_user.id
            
            # Получаем объекты пользователя
            objects = self.object_service.get_user_objects(user_id)
            
            if not objects:
                # Создаем кнопки для возврата в главное меню
                keyboard = [
                    [InlineKeyboardButton("🏢 Создать объект", callback_data="create_object")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    "❌ У вас нет объектов для создания отчета\n\n"
                    "💡 Сначала создайте объект, чтобы получать отчеты по нему.",
                    reply_markup=reply_markup
                )
                return ConversationHandler.END
            
            keyboard = []
            for obj in objects:
                keyboard.append([
                    InlineKeyboardButton(
                        f"🏢 {obj['name']}", 
                        callback_data=f"object_{obj['id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text="🏢 *Выберите объект для отчета:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return REPORT_OBJECT
            
        except Exception as e:
            logger.error(f"Error in _select_report_object: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка при загрузке объектов")
            return ConversationHandler.END
    
    async def handle_object_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора объекта."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_report":
                await query.edit_message_text("❌ Создание отчета отменено")
                return ConversationHandler.END
            
            # Извлекаем ID объекта
            object_id = int(query.data.replace("object_", ""))
            context.user_data['object_id'] = object_id
            
            return await self._select_report_period(update, context)
            
        except Exception as e:
            logger.error(f"Error in handle_object_selection: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке выбора объекта")
            return ConversationHandler.END
    
    async def _select_report_period(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор периода для отчета."""
        try:
            keyboard = [
                [InlineKeyboardButton("📅 За сегодня", callback_data="period_today")],
                [InlineKeyboardButton("📅 За неделю", callback_data="period_week")],
                [InlineKeyboardButton("📅 За месяц", callback_data="period_month")],
                [InlineKeyboardButton("📅 За 3 месяца", callback_data="period_3months")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text="📅 *Выберите период для отчета:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return REPORT_PERIOD
            
        except Exception as e:
            logger.error(f"Error in _select_report_period: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка при выборе периода")
            return ConversationHandler.END
    
    async def handle_period_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора периода."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_report":
                await query.edit_message_text("❌ Создание отчета отменено")
                return ConversationHandler.END
            
            # Определяем период
            today = date.today()
            
            if query.data == "period_today":
                start_date = end_date = today
            elif query.data == "period_week":
                start_date = today - timedelta(days=6)
                end_date = today
            elif query.data == "period_month":
                start_date = today - timedelta(days=29)
                end_date = today
            elif query.data == "period_3months":
                start_date = today - timedelta(days=89)
                end_date = today
            else:
                await query.edit_message_text("❌ Неверный выбор периода")
                return ConversationHandler.END
            
            context.user_data['start_date'] = start_date
            context.user_data['end_date'] = end_date
            
            return await self._select_report_format(update, context)
            
        except Exception as e:
            logger.error(f"Error in handle_period_selection: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке периода")
            return ConversationHandler.END
    
    async def _select_report_format(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Выбор формата экспорта."""
        try:
            keyboard = [
                [InlineKeyboardButton("📱 Показать в чате", callback_data="format_text")],
                [InlineKeyboardButton("📄 PDF", callback_data="format_pdf")],
                [InlineKeyboardButton("📊 Excel", callback_data="format_excel")],
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_report")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text="📋 *Выберите формат отчета:*",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return REPORT_FORMAT
            
        except Exception as e:
            logger.error(f"Error in _select_report_format: {e}")
            await update.callback_query.edit_message_text("❌ Произошла ошибка при выборе формата")
            return ConversationHandler.END
    
    async def handle_format_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка выбора формата и генерация отчета."""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            
            if query.data == "cancel_report":
                await query.edit_message_text("❌ Создание отчета отменено")
                return ConversationHandler.END
            
            format_type = query.data.replace("format_", "")
            report_type = context.user_data.get('report_type')
            start_date = context.user_data.get('start_date')
            end_date = context.user_data.get('end_date')
            
            # Показываем сообщение о генерации
            await query.edit_message_text("⏳ Генерируем отчет...")
            
            # Генерируем отчет в зависимости от типа
            if report_type == "report_object":
                object_id = context.user_data.get('object_id')
                
                # Получаем User ID по Telegram ID
                user_record = self.user_service.get_user_by_telegram_id(user_id)
                if not user_record:
                    await query.edit_message_text("❌ Пользователь не найден")
                    return ConversationHandler.END
                
                report_data = self.analytics_service.get_object_report(
                    object_id=object_id,
                    start_date=start_date,
                    end_date=end_date,
                    owner_id=user_record['id']
                )
            elif report_type == "report_personal":
                # Получаем User ID по Telegram ID для персонального отчета
                user_record = self.user_service.get_user_by_telegram_id(user_id)
                if not user_record:
                    await query.edit_message_text("❌ Пользователь не найден")
                    return ConversationHandler.END
                
                report_data = self.analytics_service.get_personal_report(
                    user_id=user_record['id'],
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                await query.edit_message_text("❌ Неверный тип отчета")
                return ConversationHandler.END
            
            if "error" in report_data:
                await query.edit_message_text(f"❌ {report_data['error']}")
                return ConversationHandler.END
            
            # Отправляем отчет в выбранном формате
            if format_type == "text":
                await self._send_text_report(update, context, report_data, report_type)
            elif format_type == "pdf":
                await self._send_pdf_report(update, context, report_data, report_type)
            elif format_type == "excel":
                await self._send_excel_report(update, context, report_data, report_type)
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in handle_format_selection: {e}")
            await query.edit_message_text("❌ Произошла ошибка при генерации отчета")
            return ConversationHandler.END
    
    async def _send_text_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               report_data: Dict[str, Any], report_type: str) -> None:
        """Отправка текстового отчета."""
        try:
            if report_type == "report_object":
                text = self._format_object_report_text(report_data)
            else:
                text = self._format_personal_report_text(report_data)
            
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error sending text report: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при отправке текстового отчета")
    
    async def _send_pdf_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                              report_data: Dict[str, Any], report_type: str) -> None:
        """Отправка PDF отчета."""
        try:
            if report_type == "report_object":
                pdf_data = self.export_service.export_object_report_to_pdf(report_data)
                filename = f"object_report_{report_data['object']['name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
            else:
                pdf_data = self.export_service.export_personal_report_to_pdf(report_data)
                filename = f"personal_report_{report_data['user']['name']}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            await update.callback_query.edit_message_text("✅ Отчет сгенерирован!")
            
            # Отправляем файл
            pdf_file = io.BytesIO(pdf_data)
            pdf_file.name = filename
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=pdf_file,
                filename=filename,
                caption=f"📄 PDF отчет готов!"
            )
            
        except Exception as e:
            logger.error(f"Error sending PDF report: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при генерации PDF отчета")
    
    async def _send_excel_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                report_data: Dict[str, Any], report_type: str) -> None:
        """Отправка Excel отчета."""
        try:
            if report_type == "report_object":
                excel_data = self.export_service.export_object_report_to_excel(report_data)
                filename = f"object_report_{report_data['object']['name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            else:
                excel_data = self.export_service.export_personal_report_to_excel(report_data)
                filename = f"personal_report_{report_data['user']['name']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            await update.callback_query.edit_message_text("✅ Отчет сгенерирован!")
            
            # Отправляем файл
            excel_file = io.BytesIO(excel_data)
            excel_file.name = filename
            
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=excel_file,
                filename=filename,
                caption=f"📊 Excel отчет готов!"
            )
            
        except Exception as e:
            logger.error(f"Error sending Excel report: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при генерации Excel отчета")
    
    async def _show_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Показ дашборда с ключевыми метриками."""
        try:
            user_id = update.effective_user.id
            
            # Получаем User ID по Telegram ID для дашборда
            user_record = self.user_service.get_user_by_telegram_id(user_id)
            if not user_record:
                await update.callback_query.edit_message_text("❌ Пользователь не найден")
                return ConversationHandler.END
            
            # Получаем метрики дашборда
            metrics = self.analytics_service.get_dashboard_metrics(user_record['id'])
            
            if "error" in metrics:
                await update.callback_query.edit_message_text(f"❌ {metrics['error']}")
                return ConversationHandler.END
            
            text = self._format_dashboard_text(metrics)
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_dashboard")],
                [InlineKeyboardButton("❌ Закрыть", callback_data="cancel_report")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return DASHBOARD
            
        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            await update.callback_query.edit_message_text("❌ Ошибка при загрузке дашборда")
            return ConversationHandler.END
    
    def _format_object_report_text(self, report_data: Dict[str, Any]) -> str:
        """Форматирование текстового отчета по объекту."""
        obj = report_data['object']
        period = report_data['period']
        summary = report_data['summary']
        
        text = f"📊 *Отчет по объекту: {obj['name']}*\n\n"
        text += f"🏢 *Информация об объекте:*\n"
        text += f"• Адрес: {obj['address'] or 'Не указан'}\n"
        text += f"• Время работы: {obj['working_hours']}\n"
        text += f"• Ставка: {obj['hourly_rate']} ₽/час\n\n"
        
        text += f"📅 *Период:* {period['start_date']} - {period['end_date']} ({period['days']} дн.)\n\n"
        
        text += f"📈 *Общая статистика:*\n"
        text += f"• Всего смен: {summary['total_shifts']}\n"
        text += f"• Завершено: {summary['completed_shifts']}\n"
        text += f"• Активных: {summary['active_shifts']}\n"
        text += f"• Общее время: {summary['total_hours']} ч\n"
        text += f"• Общая оплата: {summary['total_payment']} ₽\n"
        text += f"• Средняя смена: {summary['avg_shift_duration']} ч\n"
        text += f"• Среднее в день: {summary['avg_daily_hours']} ч\n\n"
        
        if report_data.get('employees'):
            text += f"👥 *Топ сотрудники:*\n"
            for i, emp in enumerate(report_data['employees'][:5], 1):
                text += f"{i}. {emp['name']}: {emp['shifts']} смен, {emp['hours']} ч, {emp['payment']} ₽\n"
        
        return text
    
    def _format_personal_report_text(self, report_data: Dict[str, Any]) -> str:
        """Форматирование персонального текстового отчета."""
        user = report_data['user']
        period = report_data['period']
        summary = report_data['summary']
        
        text = f"👤 *Персональный отчет: {user['name']}*\n\n"
        text += f"📅 *Период:* {period['start_date']} - {period['end_date']} ({period['days']} дн.)\n\n"
        
        text += f"📈 *Общая статистика:*\n"
        text += f"• Всего смен: {summary['total_shifts']}\n"
        text += f"• Завершено: {summary['completed_shifts']}\n"
        text += f"• Активных: {summary['active_shifts']}\n"
        text += f"• Общее время: {summary['total_hours']} ч\n"
        text += f"• Общий заработок: {summary['total_earnings']} ₽\n"
        text += f"• Средняя смена: {summary['avg_shift_duration']} ч\n"
        text += f"• Средний заработок в день: {summary['avg_daily_earnings']} ₽\n\n"
        
        if report_data.get('objects'):
            text += f"🏢 *По объектам:*\n"
            for i, obj in enumerate(report_data['objects'][:5], 1):
                text += f"{i}. {obj['name']}: {obj['shifts']} смен, {obj['hours']} ч, {obj['earnings']} ₽\n"
        
        return text
    
    def _format_dashboard_text(self, metrics: Dict[str, Any]) -> str:
        """Форматирование текста дашборда."""
        text = f"📊 *Дашборд владельца*\n\n"
        
        text += f"🏢 *Объекты:* {metrics['objects_count']}\n"
        text += f"🟢 *Активные смены:* {metrics['active_shifts']}\n\n"
        
        today = metrics['today_stats']
        text += f"📅 *Сегодня:*\n"
        text += f"• Смены: {today['shifts']}\n"
        text += f"• Часы: {today['hours']} ч\n"
        text += f"• Доход: {today['earnings']} ₽\n\n"
        
        week = metrics['week_stats']
        text += f"📊 *За неделю:*\n"
        text += f"• Смены: {week['shifts']}\n"
        text += f"• Часы: {week['hours']} ч\n"
        text += f"• Доход: {week['earnings']} ₽\n\n"
        
        month = metrics['month_stats']
        text += f"📈 *За месяц:*\n"
        text += f"• Смены: {month['shifts']}\n"
        text += f"• Часы: {month['hours']} ч\n"
        text += f"• Доход: {month['earnings']} ₽\n\n"
        
        if metrics.get('top_objects'):
            text += f"🏆 *Топ объекты:*\n"
            for i, obj in enumerate(metrics['top_objects'][:3], 1):
                text += f"{i}. {obj['name']}: {obj['shifts']} смен\n"
        
        return text
    
    async def handle_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка действий в дашборде."""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "refresh_dashboard":
                # Обновляем дашборд
                return await self._show_dashboard(update, context)
            elif query.data == "cancel_report":
                await query.edit_message_text("❌ Дашборд закрыт")
                return ConversationHandler.END
            
            return DASHBOARD
            
        except Exception as e:
            logger.error(f"Error in handle_dashboard: {e}")
            await query.edit_message_text("❌ Произошла ошибка")
            return ConversationHandler.END
    
    async def cancel_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена создания отчета."""
        await update.message.reply_text("❌ Создание отчета отменено")
        return ConversationHandler.END
    
    def get_conversation_handler(self) -> ConversationHandler:
        """Получение обработчика диалога отчетов."""
        return ConversationHandler(
            entry_points=[
                CommandHandler("reports", self.reports_menu),
                CallbackQueryHandler(self.reports_menu, pattern="^get_report$")
            ],
            states={
                REPORT_TYPE: [CallbackQueryHandler(self.handle_report_type)],
                REPORT_OBJECT: [CallbackQueryHandler(self.handle_object_selection)],
                REPORT_PERIOD: [CallbackQueryHandler(self.handle_period_selection)],
                REPORT_FORMAT: [CallbackQueryHandler(self.handle_format_selection)],
                DASHBOARD: [CallbackQueryHandler(self.handle_dashboard)]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel_report),
                CallbackQueryHandler(self.cancel_report, pattern="^cancel_report$")
            ]
        )
