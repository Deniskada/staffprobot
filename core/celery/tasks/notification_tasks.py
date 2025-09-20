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
        from apps.notification.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        # Отправка напоминания
        result = notification_service.send_shift_reminder(
            user_id=user_id,
            shift_schedule_id=shift_schedule_id,
            shift_data=shift_data
        )
        
        logger.info(
            "Shift reminder sent",
            user_id=user_id,
            shift_schedule_id=shift_schedule_id,
            success=result
        )
        
        return {"success": result, "user_id": user_id, "shift_schedule_id": shift_schedule_id}
        
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
        from apps.notification.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        # Отправка уведомления
        result = notification_service.send_notification(
            user_id=user_id,
            notification_type=notification_type,
            data=data
        )
        
        logger.info(
            "Shift notification sent",
            user_id=user_id,
            notification_type=notification_type,
            success=result
        )
        
        return {"success": result, "user_id": user_id, "type": notification_type}
        
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
        from apps.bot.services.schedule_service import ScheduleService
        from core.database.session import DatabaseManager
        
        db_manager = DatabaseManager()
        
        async def _process_reminders():
            async with db_manager.get_session() as session:
                schedule_service = ScheduleService(session)
                
                # Получаем смены, которые начинаются в ближайшие 2 часа
                upcoming_shifts = await schedule_service.get_upcoming_shifts(
                    hours_ahead=2
                )
                
                processed_count = 0
                for shift_schedule in upcoming_shifts:
                    try:
                        # Отправляем напоминание асинхронно
                        send_shift_reminder.delay(
                            user_id=shift_schedule.user_id,
                            shift_schedule_id=shift_schedule.id,
                            shift_data={
                                'object_name': shift_schedule.object.name if shift_schedule.object else 'Unknown',
                                'planned_start': shift_schedule.planned_start.isoformat(),
                                'planned_end': shift_schedule.planned_end.isoformat()
                            }
                        )
                        processed_count += 1
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to schedule reminder for shift {shift_schedule.id}: {e}"
                        )
                
                return processed_count
        
        import asyncio
        processed_count = asyncio.run(_process_reminders())
        
        logger.info(f"Processed {processed_count} shift reminders")
        return {"processed_count": processed_count}
        
    except Exception as e:
        logger.error(f"Failed to process reminders: {e}")
        raise


@celery_app.task(base=NotificationTask, bind=True)
def send_bulk_notifications(self, user_ids: List[int], notification_type: str, data: Dict[str, Any]):
    """Отправка массовых уведомлений."""
    try:
        from apps.notification.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        successful_sends = 0
        failed_sends = 0
        
        for user_id in user_ids:
            try:
                result = notification_service.send_notification(
                    user_id=user_id,
                    notification_type=notification_type,
                    data=data
                )
                
                if result:
                    successful_sends += 1
                else:
                    failed_sends += 1
                    
            except Exception as e:
                logger.error(
                    f"Failed to send notification to user {user_id}: {e}"
                )
                failed_sends += 1
        
        logger.info(
            "Bulk notifications completed",
            total_users=len(user_ids),
            successful=successful_sends,
            failed=failed_sends
        )
        
        return {
            "total_users": len(user_ids),
            "successful": successful_sends,
            "failed": failed_sends
        }
        
    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        raise


@celery_app.task(base=NotificationTask, bind=True)
def send_report_notification(self, user_id: int, report_data: Dict[str, Any], report_file_path: str = None):
    """Отправка уведомления с готовым отчетом."""
    try:
        from apps.notification.notification_service import NotificationService
        
        notification_service = NotificationService()
        
        # Отправка уведомления с отчетом
        result = notification_service.send_report_notification(
            user_id=user_id,
            report_data=report_data,
            report_file_path=report_file_path
        )
        
        logger.info(
            "Report notification sent",
            user_id=user_id,
            has_file=bool(report_file_path),
            success=result
        )
        
        return {"success": result, "user_id": user_id}
        
    except Exception as e:
        logger.error(
            f"Failed to send report notification: {e}",
            user_id=user_id,
            error=str(e)
        )
        raise
