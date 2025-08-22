"""Сервис уведомлений о предстоящих сменах."""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from core.logging.logger import logger
from apps.bot.services.schedule_service import ScheduleService
from telegram import Bot
from telegram.error import TelegramError


class NotificationService:
    """Сервис для отправки уведомлений о предстоящих сменах."""
    
    def __init__(self, bot_token: str):
        """
        Инициализация сервиса уведомлений.
        
        Args:
            bot_token: Токен Telegram бота
        """
        self.bot = Bot(token=bot_token)
        self.schedule_service = ScheduleService()
        logger.info("NotificationService initialized")
    
    async def send_shift_reminder(
        self,
        user_telegram_id: int,
        user_name: str,
        object_name: str,
        formatted_time_range: str,
        planned_start: datetime,
        time_until_start: timedelta
    ) -> bool:
        """
        Отправляет напоминание о предстоящей смене.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_name: Имя пользователя
            object_name: Название объекта
            formatted_time_range: Форматированное время смены
            planned_start: Время начала смены
            time_until_start: Время до начала смены
            
        Returns:
            Успешность отправки уведомления
        """
        try:
            # Форматируем время до начала смены
            total_minutes = int(time_until_start.total_seconds() / 60)
            hours = total_minutes // 60
            minutes = total_minutes % 60
            
            if hours > 0:
                time_str = f"{hours} ч. {minutes} мин."
            else:
                time_str = f"{minutes} мин."
            
            # Формируем сообщение
            message = (
                f"⏰ <b>Напоминание о смене!</b>\n\n"
                f"👋 Привет, {user_name}!\n\n"
                f"🏢 Объект: <b>{object_name}</b>\n"
                f"📅 Время: <b>{formatted_time_range}</b>\n"
                f"⏱ Начало через: <b>{time_str}</b>\n\n"
                f"📍 Не забудьте прийти на объект вовремя!\n"
                f"Геолокация будет проверена при открытии смены."
            )
            
            # Отправляем уведомление
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(
                f"Shift reminder sent successfully: user={user_telegram_id}, "
                f"object={object_name}, start={planned_start}"
            )
            
            return True
            
        except TelegramError as e:
            logger.error(
                f"Failed to send shift reminder to user {user_telegram_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending shift reminder: {e}"
            )
            return False
    
    async def process_pending_reminders(self, hours_before: int = 2) -> Dict[str, Any]:
        """
        Обрабатывает все отложенные напоминания.
        
        Args:
            hours_before: За сколько часов до начала отправлять напоминания
            
        Returns:
            Статистика обработки напоминаний
        """
        try:
            logger.info(f"Processing pending reminders ({hours_before}h before)")
            
            # Получаем список смен для напоминаний
            upcoming_shifts = await self.schedule_service.get_upcoming_shifts_for_reminder(
                hours_before=hours_before
            )
            
            if not upcoming_shifts:
                logger.info("No pending reminders found")
                return {
                    'total_shifts': 0,
                    'sent_successfully': 0,
                    'failed_to_send': 0,
                    'errors': []
                }
            
            logger.info(f"Found {len(upcoming_shifts)} shifts requiring reminders")
            
            sent_successfully = 0
            failed_to_send = 0
            errors = []
            
            # Отправляем напоминания
            for shift in upcoming_shifts:
                try:
                    success = await self.send_shift_reminder(
                        user_telegram_id=shift['user_telegram_id'],
                        user_name=shift['user_name'],
                        object_name=shift['object_name'],
                        formatted_time_range=shift['formatted_time_range'],
                        planned_start=shift['planned_start'],
                        time_until_start=shift['time_until_start']
                    )
                    
                    if success:
                        # Отмечаем, что уведомление отправлено
                        await self.schedule_service.mark_notification_sent(
                            shift['schedule_id']
                        )
                        sent_successfully += 1
                    else:
                        failed_to_send += 1
                        errors.append(f"Failed to send to user {shift['user_telegram_id']}")
                        
                except Exception as e:
                    failed_to_send += 1
                    error_msg = f"Error processing shift {shift['schedule_id']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
            
            result = {
                'total_shifts': len(upcoming_shifts),
                'sent_successfully': sent_successfully,
                'failed_to_send': failed_to_send,
                'errors': errors
            }
            
            logger.info(
                f"Reminders processing completed: "
                f"total={result['total_shifts']}, "
                f"sent={result['sent_successfully']}, "
                f"failed={result['failed_to_send']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing pending reminders: {e}")
            return {
                'total_shifts': 0,
                'sent_successfully': 0,
                'failed_to_send': 0,
                'errors': [f"Service error: {str(e)}"]
            }
    
    async def send_shift_cancelled_notification(
        self,
        user_telegram_id: int,
        user_name: str,
        object_name: str,
        formatted_time_range: str
    ) -> bool:
        """
        Отправляет уведомление об отмене смены.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_name: Имя пользователя
            object_name: Название объекта
            formatted_time_range: Форматированное время смены
            
        Returns:
            Успешность отправки уведомления
        """
        try:
            message = (
                f"❌ <b>Смена отменена</b>\n\n"
                f"👋 {user_name}, ваша смена была отменена:\n\n"
                f"🏢 Объект: <b>{object_name}</b>\n"
                f"📅 Время: <b>{formatted_time_range}</b>\n\n"
                f"Вы можете запланировать новую смену в любое время."
            )
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(
                f"Cancellation notification sent: user={user_telegram_id}, "
                f"object={object_name}"
            )
            
            return True
            
        except TelegramError as e:
            logger.error(
                f"Failed to send cancellation notification to user {user_telegram_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending cancellation notification: {e}"
            )
            return False
    
    async def send_shift_confirmed_notification(
        self,
        user_telegram_id: int,
        user_name: str,
        object_name: str,
        formatted_time_range: str,
        planned_payment: float
    ) -> bool:
        """
        Отправляет уведомление о подтверждении смены.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_name: Имя пользователя
            object_name: Название объекта
            formatted_time_range: Форматированное время смены
            planned_payment: Планируемая оплата
            
        Returns:
            Успешность отправки уведомления
        """
        try:
            message = (
                f"✅ <b>Смена подтверждена!</b>\n\n"
                f"👋 {user_name}, ваша смена подтверждена:\n\n"
                f"🏢 Объект: <b>{object_name}</b>\n"
                f"📅 Время: <b>{formatted_time_range}</b>\n"
                f"💰 Планируемая оплата: <b>{planned_payment:.2f}₽</b>\n\n"
                f"📱 Напоминание будет отправлено за 2 часа до начала.\n"
                f"📍 Не забудьте включить геолокацию при открытии смены!"
            )
            
            await self.bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(
                f"Confirmation notification sent: user={user_telegram_id}, "
                f"object={object_name}"
            )
            
            return True
            
        except TelegramError as e:
            logger.error(
                f"Failed to send confirmation notification to user {user_telegram_id}: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending confirmation notification: {e}"
            )
            return False
