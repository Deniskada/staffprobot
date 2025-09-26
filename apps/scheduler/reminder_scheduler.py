"""Планировщик напоминаний о предстоящих сменах."""

import asyncio
import schedule
import time
from datetime import datetime
from typing import Optional
from core.logging.logger import logger
from shared.services.notification_service import NotificationService
from core.database.session import get_sync_session


class ReminderScheduler:
    """Планировщик для отправки напоминаний о сменах."""
    
    def __init__(self, bot_token: str):
        """
        Инициализация планировщика.
        
        Args:
            bot_token: Токен Telegram бота
        """
        self.bot_token = bot_token
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        logger.info("ReminderScheduler initialized")
    
    async def process_reminders_job(self):
        """Задача для обработки напоминаний."""
        try:
            logger.info("Starting reminder processing job")
            
            # Создаем сессию для работы с БД
            session = get_sync_session()
            try:
                notification_service = NotificationService(session=session, telegram_token=self.bot_token)
                
                # Обрабатываем напоминания за 2 часа до начала
                result = notification_service.process_pending_reminders(hours_before=2)
                
                if result['total_shifts'] > 0:
                    logger.info(
                        f"Reminder job completed: "
                        f"processed {result['total_shifts']} shifts, "
                        f"sent {result['sent_successfully']}, "
                        f"failed {result['failed_to_send']}"
                    )
                    
                    if result['errors']:
                        logger.warning(f"Reminder errors: {result['errors']}")
                else:
                    logger.debug("No reminders to process")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in reminder processing job: {e}")
    
    def setup_schedule(self):
        """Настройка расписания выполнения задач."""
        # Запускаем проверку напоминаний каждые 30 минут
        schedule.every(30).minutes.do(
            lambda: asyncio.create_task(self.process_reminders_job())
        )
        
        # Дополнительные проверки в ключевые моменты дня
        schedule.every().day.at("08:00").do(
            lambda: asyncio.create_task(self.process_reminders_job())
        )
        schedule.every().day.at("12:00").do(
            lambda: asyncio.create_task(self.process_reminders_job())
        )
        schedule.every().day.at("16:00").do(
            lambda: asyncio.create_task(self.process_reminders_job())
        )
        schedule.every().day.at("20:00").do(
            lambda: asyncio.create_task(self.process_reminders_job())
        )
        
        logger.info("Reminder schedule configured")
    
    async def _run_scheduler(self):
        """Основной цикл планировщика."""
        logger.info("Reminder scheduler started")
        
        while self.is_running:
            try:
                # Выполняем запланированные задачи
                schedule.run_pending()
                
                # Ждем 60 секунд перед следующей проверкой
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(60)  # Ждем перед повторной попыткой
        
        logger.info("Reminder scheduler stopped")
    
    async def start(self):
        """Запуск планировщика."""
        if self.is_running:
            logger.warning("Reminder scheduler is already running")
            return
        
        self.is_running = True
        self.setup_schedule()
        
        # Запускаем планировщик в отдельной задаче
        self._task = asyncio.create_task(self._run_scheduler())
        
        logger.info("Reminder scheduler started successfully")
    
    async def stop(self):
        """Остановка планировщика."""
        if not self.is_running:
            logger.warning("Reminder scheduler is not running")
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # Очищаем расписание
        schedule.clear()
        
        logger.info("Reminder scheduler stopped successfully")
    
    async def send_test_reminder(self, user_telegram_id: int) -> bool:
        """
        Отправка тестового напоминания.
        
        Args:
            user_telegram_id: Telegram ID пользователя для тестирования
            
        Returns:
            Успешность отправки
        """
        try:
            from datetime import timedelta
            
            # Создаем сессию для работы с БД
            session = get_sync_session()
            try:
                notification_service = NotificationService(session=session, telegram_token=self.bot_token)
                
                # Создаем тестовое уведомление напрямую через create
                payload = {
                    "object_name": "Тестовый объект",
                    "time_range": "01.01.2024 09:00-17:00",
                }
                
                # Найдем пользователя по telegram_id
                from domain.entities.user import User
                from sqlalchemy import select
                
                result = session.execute(
                    select(User).where(User.telegram_id == str(user_telegram_id))
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User with telegram_id {user_telegram_id} not found")
                    return False
                
                notification_service.create([user.id], "shift_reminder", payload, send_telegram=True)
                
                logger.info(f"Test reminder sent to {user_telegram_id}")
                return True
                
            finally:
                session.close()
            
        except Exception as e:
            logger.error(f"Error sending test reminder: {e}")
            return False
    
    def get_status(self) -> dict:
        """
        Получение статуса планировщика.
        
        Returns:
            Словарь со статусом планировщика
        """
        return {
            'is_running': self.is_running,
            'scheduled_jobs': len(schedule.jobs),
            'next_run': str(schedule.next_run()) if schedule.jobs else None,
            'task_active': self._task is not None and not self._task.done()
        }
