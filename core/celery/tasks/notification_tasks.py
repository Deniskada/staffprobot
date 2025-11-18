"""Celery задачи для уведомлений (универсальные)."""

from typing import Dict, Any, List
from celery import Task

from core.celery.celery_app import celery_app
from core.logging.logger import logger


class NotificationTask(Task):
    """Базовый класс для задач уведомлений."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(
            f"Notification task failed: {self.name} (task_id: {task_id}, error: {str(exc)})"
        )

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(
            f"Notification task completed: {self.name} (task_id: {task_id})"
        )


@celery_app.task(base=NotificationTask, name="send_notification_now")
def send_notification_now(notification_id: int) -> bool:
    """Отправить уведомление по ID через диспетчер."""
    try:
        from shared.services.notification_dispatcher import get_notification_dispatcher
        dispatcher = get_notification_dispatcher()
        import asyncio
        
        # Правильная работа с event loop в Celery
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(dispatcher.dispatch_notification(notification_id))
    except Exception as e:
        logger.error("send_notification_now failed", notification_id=notification_id, error=str(e))
        return False


@celery_app.task(base=NotificationTask, name="dispatch_scheduled_notifications")
def dispatch_scheduled_notifications() -> Dict[str, Any]:
    """Обработать и отправить все запланированные уведомления (scheduled <= now)."""
    try:
        from shared.services.notification_dispatcher import get_notification_dispatcher
        dispatcher = get_notification_dispatcher()
        import asyncio
        
        # Правильная работа с event loop в Celery
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(dispatcher.dispatch_scheduled_notifications())
    except Exception as e:
        logger.error("dispatch_scheduled_notifications failed", error=str(e))
        return {"processed": 0, "sent": 0, "failed": 0, "error": str(e)}


# Совместимость с существующим расписанием beat: используем то же имя
@celery_app.task(base=NotificationTask, bind=True)
def process_reminders(self):
    """Совместимая задача: делегирует на обработку запланированных уведомлений."""
    try:
        return dispatch_scheduled_notifications()
    except Exception as e:
        logger.error("process_reminders failed", error=str(e))
        raise
