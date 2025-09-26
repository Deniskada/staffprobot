"""Celery задачи для уведомлений."""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from celery import Task

from core.celery.celery_app import celery_app
from core.logging.logger import logger
from core.database.session import DatabaseManager


class NotificationTask(Task):
    """Базовый класс для задач уведомлений."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Обработка ошибок задач."""
        logger.error(
            f"Notification task failed: {self.name} (task_id: {task_id}, error: {str(exc)})"
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Обработка успешного выполнения."""
        logger.info(
            f"Notification task completed: {self.name} (task_id: {task_id})"
        )


@celery_app.task(base=NotificationTask, bind=True)
def send_shift_reminder(self, user_id: int, shift_schedule_id: int, shift_data: Dict[str, Any]):
    """Отправка напоминания о предстоящей смене."""
    try:
        from shared.services.notification_service import NotificationService
        from core.database.session import get_sync_session
        from domain.entities.shift_schedule import ShiftSchedule
        from sqlalchemy import select

        session = get_sync_session()
        try:
            notification_service = NotificationService(session=session)
            
            # Получаем объект смены из БД
            result = session.execute(
                select(ShiftSchedule).where(ShiftSchedule.id == shift_schedule_id)
            )
            shift_schedule = result.scalar_one_or_none()
            
            if shift_schedule:
                result = notification_service.send_shift_reminder(
                    schedule=shift_schedule,
                    send_telegram=True
                )
            else:
                logger.error(f"Shift schedule {shift_schedule_id} not found")
                return {"success": False, "user_id": user_id, "shift_schedule_id": shift_schedule_id}
        
        finally:
            session.close()
        
        logger.info(
            "Shift reminder sent",
            user_id=user_id,
            shift_schedule_id=shift_schedule_id
        )
        
        return {"success": True, "user_id": user_id, "shift_schedule_id": shift_schedule_id}
        
    except Exception as e:
        logger.error(
            f"Failed to send shift reminder: {e}",
            user_id=user_id,
            shift_schedule_id=shift_schedule_id,
            error=str(e)
        )
        raise


@celery_app.task(base=NotificationTask, bind=True)
def send_shift_notification(self, user_id: int, notification_type: str, data: Dict[str, Any]):
    """Отправка уведомления о смене."""
    try:
        from shared.services.notification_service import NotificationService
        from core.database.session import get_sync_session

        session = get_sync_session()
        try:
            notification_service = NotificationService(session=session)
            
            # Отправка уведомления через новый сервис
            notification_service.create(
                user_ids=[user_id],
                notification_type=notification_type,
                payload=data,
                send_telegram=True
            )
        
        finally:
            session.close()
        
        logger.info(
            "Shift notification sent",
            user_id=user_id,
            notification_type=notification_type
        )
        
        return {"success": True, "user_id": user_id, "type": notification_type}
        
    except Exception as e:
        logger.error(
            f"Failed to send shift notification: {e}",
            user_id=user_id,
            notification_type=notification_type,
            error=str(e)
        )
        raise


@celery_app.task(base=NotificationTask, bind=True)
def process_reminders(self):
    """Обработка всех напоминаний о предстоящих сменах."""
    try:
        from shared.services.notification_service import NotificationService
        from core.database.session import get_sync_session

        session = get_sync_session()
        try:
            notification_service = NotificationService(session=session)
            
            # Обрабатываем все ожидающие напоминания
            result = notification_service.process_pending_reminders(hours_before=2)
            
            logger.info(
                f"Processed reminders: "
                f"total_shifts={result['total_shifts']}, "
                f"sent_successfully={result['sent_successfully']}, "
                f"failed_to_send={result['failed_to_send']}"
            )
            
            return result
            
        finally:
            session.close()
        
    except Exception as e:
        logger.error(f"Failed to process reminders: {e}")
        raise


@celery_app.task(base=NotificationTask, bind=True)
def send_bulk_notifications(self, user_ids: List[int], notification_type: str, data: Dict[str, Any]):
    """Отправка массовых уведомлений."""
    try:
        from shared.services.notification_service import NotificationService
        from core.database.session import get_sync_session

        session = get_sync_session()
        try:
            notification_service = NotificationService(session=session)
            
            # Отправка уведомлений через новый сервис
            notification_service.create(
                user_ids=user_ids,
                notification_type=notification_type,
                payload=data,
                send_telegram=True
            )
        
        finally:
            session.close()
        
        logger.info(
            "Bulk notifications sent",
            total_users=len(user_ids),
            notification_type=notification_type
        )
        
        return {
            "total_users": len(user_ids),
            "notification_type": notification_type,
            "success": True
        }
        
    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        raise
