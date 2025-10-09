"""Диспетчер уведомлений для StaffProBot."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from core.logging.logger import logger
from core.database.session import get_async_session
from domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus
)
from domain.entities.user import User
from sqlalchemy import select

from .notification_service import NotificationService
from .senders.telegram_sender import get_telegram_sender


class NotificationDispatcher:
    """
    Диспетчер для отправки уведомлений через различные каналы.
    
    Координирует работу NotificationService и различных отправщиков (Telegram, Email, SMS).
    """
    
    def __init__(self):
        """Инициализация диспетчера."""
        self.notification_service = NotificationService()
        self.telegram_sender = get_telegram_sender()
        # email_sender и sms_sender будут добавлены позже
        self.email_sender = None
        self.sms_sender = None
    
    async def dispatch_notification(
        self,
        notification_id: int
    ) -> bool:
        """
        Отправка уведомления по его ID.
        
        Args:
            notification_id: ID уведомления из БД
            
        Returns:
            True если успешно отправлено
        """
        try:
            # Получаем уведомление из БД
            async with get_async_session() as session:
                query = select(Notification).where(Notification.id == notification_id)
                result = await session.execute(query)
                notification = result.scalar_one_or_none()
                
                if not notification:
                    logger.error(f"Notification {notification_id} not found")
                    return False
                
                # Проверяем статус - отправляем только PENDING
                if notification.status != NotificationStatus.PENDING:
                    logger.warning(
                        f"Notification {notification_id} has status {notification.status.value}, skipping"
                    )
                    return False
                
                # Получаем пользователя для telegram_id
                user_query = select(User).where(User.id == notification.user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {notification.user_id} not found for notification {notification_id}")
                    await self.notification_service.update_notification_status(
                        notification_id=notification_id,
                        status=NotificationStatus.FAILED,
                        error_message="User not found"
                    )
                    return False
                
                # Отправляем через соответствующий канал
                success = await self._send_via_channel(
                    notification=notification,
                    user=user
                )
                
                # Обновляем статус
                if success:
                    await self.notification_service.update_notification_status(
                        notification_id=notification_id,
                        status=NotificationStatus.SENT
                    )
                else:
                    await self.notification_service.update_notification_status(
                        notification_id=notification_id,
                        status=NotificationStatus.FAILED,
                        error_message="Send failed"
                    )
                
                return success
                
        except Exception as e:
            logger.error(
                f"Error dispatching notification {notification_id}: {e}",
                notification_id=notification_id,
                error=str(e)
            )
            
            # Помечаем как failed
            try:
                await self.notification_service.update_notification_status(
                    notification_id=notification_id,
                    status=NotificationStatus.FAILED,
                    error_message=str(e)
                )
            except Exception as update_error:
                logger.error(f"Failed to update notification status: {update_error}")
            
            return False
    
    async def _send_via_channel(
        self,
        notification: Notification,
        user: User
    ) -> bool:
        """
        Отправка уведомления через соответствующий канал.
        
        Args:
            notification: Объект уведомления
            user: Пользователь-получатель
            
        Returns:
            True если успешно отправлено
        """
        try:
            if notification.channel == NotificationChannel.TELEGRAM:
                # Проверяем наличие telegram_id
                if not user.telegram_id:
                    logger.warning(
                        f"User {user.id} has no telegram_id",
                        user_id=user.id,
                        notification_id=notification.id
                    )
                    return False
                
                # Отправляем через Telegram
                return await self.telegram_sender.send_notification(
                    notification=notification,
                    telegram_id=user.telegram_id,
                    variables=notification.data
                )
                
            elif notification.channel == NotificationChannel.EMAIL:
                # TODO: Email отправка будет реализована в Фазе 2.2
                logger.warning(
                    f"Email notifications not yet implemented",
                    notification_id=notification.id
                )
                return False
                
            elif notification.channel == NotificationChannel.SMS:
                # TODO: SMS отправка будет реализована в Фазе 2.3
                logger.warning(
                    f"SMS notifications not yet implemented",
                    notification_id=notification.id
                )
                return False
                
            elif notification.channel == NotificationChannel.IN_APP:
                # In-app уведомления не требуют отправки, только сохранение в БД
                logger.info(
                    f"In-app notification {notification.id} stored in DB",
                    notification_id=notification.id
                )
                return True
                
            else:
                logger.warning(
                    f"Unsupported notification channel: {notification.channel.value}",
                    notification_id=notification.id,
                    channel=notification.channel.value
                )
                return False
                
        except Exception as e:
            logger.error(
                f"Error sending via channel {notification.channel.value}: {e}",
                notification_id=notification.id,
                channel=notification.channel.value,
                error=str(e)
            )
            return False
    
    async def dispatch_scheduled_notifications(self) -> Dict[str, Any]:
        """
        Отправка запланированных уведомлений.
        
        Вызывается планировщиком для обработки уведомлений с scheduled_at <= now.
        
        Returns:
            Статистика: {processed: int, sent: int, failed: int}
        """
        try:
            # Получаем запланированные уведомления
            notifications = await self.notification_service.get_scheduled_notifications(
                before=datetime.now(timezone.utc)
            )
            
            stats = {
                "processed": len(notifications),
                "sent": 0,
                "failed": 0
            }
            
            for notification in notifications:
                success = await self.dispatch_notification(notification.id)
                
                if success:
                    stats["sent"] += 1
                else:
                    stats["failed"] += 1
            
            logger.info(
                f"Scheduled notifications dispatched",
                processed=stats["processed"],
                sent=stats["sent"],
                failed=stats["failed"]
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error dispatching scheduled notifications: {e}", error=str(e))
            return {
                "processed": 0,
                "sent": 0,
                "failed": 0,
                "error": str(e)
            }
    
    async def dispatch_bulk(
        self,
        notification_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Массовая отправка уведомлений.
        
        Args:
            notification_ids: Список ID уведомлений
            
        Returns:
            Статистика: {total: int, sent: int, failed: int}
        """
        stats = {
            "total": len(notification_ids),
            "sent": 0,
            "failed": 0
        }
        
        for notification_id in notification_ids:
            success = await self.dispatch_notification(notification_id)
            
            if success:
                stats["sent"] += 1
            else:
                stats["failed"] += 1
        
        logger.info(
            f"Bulk dispatch completed",
            total=stats["total"],
            sent=stats["sent"],
            failed=stats["failed"]
        )
        
        return stats
    
    async def retry_failed_notifications(
        self,
        max_retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Повторная отправка неудачных уведомлений.
        
        Args:
            max_retry_count: Максимальное количество попыток
            
        Returns:
            Статистика: {retried: int, sent: int, failed: int}
        """
        try:
            # Получаем неудачные уведомления с retry_count < max_retry_count
            async with get_async_session() as session:
                from sqlalchemy import and_
                
                query = select(Notification).where(
                    and_(
                        Notification.status == NotificationStatus.FAILED,
                        Notification.retry_count < max_retry_count
                    )
                )
                
                result = await session.execute(query)
                failed_notifications = result.scalars().all()
                
                stats = {
                    "retried": len(failed_notifications),
                    "sent": 0,
                    "failed": 0
                }
                
                for notification in failed_notifications:
                    # Сбрасываем статус на PENDING для повторной отправки
                    notification.status = NotificationStatus.PENDING
                    await session.commit()
                    
                    # Пытаемся отправить
                    success = await self.dispatch_notification(notification.id)
                    
                    if success:
                        stats["sent"] += 1
                    else:
                        stats["failed"] += 1
                
                logger.info(
                    f"Failed notifications retry completed",
                    retried=stats["retried"],
                    sent=stats["sent"],
                    failed=stats["failed"]
                )
                
                return stats
                
        except Exception as e:
            logger.error(f"Error retrying failed notifications: {e}", error=str(e))
            return {
                "retried": 0,
                "sent": 0,
                "failed": 0,
                "error": str(e)
            }


# Глобальный экземпляр диспетчера
_dispatcher: Optional[NotificationDispatcher] = None


def get_notification_dispatcher() -> NotificationDispatcher:
    """
    Получение глобального экземпляра диспетчера уведомлений.
    
    Returns:
        Экземпляр NotificationDispatcher
    """
    global _dispatcher
    
    if _dispatcher is None:
        _dispatcher = NotificationDispatcher()
    
    return _dispatcher

