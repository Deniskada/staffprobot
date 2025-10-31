"""Сервис уведомлений для StaffProBot."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from core.logging.logger import logger
from core.cache.redis_cache import cached
from core.cache.cache_service import CacheService
from domain.entities.notification import (
    Notification,
    NotificationType,
    NotificationStatus,
    NotificationChannel,
    NotificationPriority
)
from domain.entities.user import User


class NotificationService:
    """Сервис для управления уведомлениями."""
    
    # TTL для кэша уведомлений
    NOTIFICATIONS_TTL = timedelta(minutes=5)
    UNREAD_COUNT_TTL = timedelta(minutes=1)
    
    async def create_notification(
        self,
        user_id: int,
        type: NotificationType,
        channel: NotificationChannel,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[Notification]:
        """
        Создание уведомления.
        
        Args:
            user_id: ID пользователя
            type: Тип уведомления
            channel: Канал доставки
            title: Заголовок
            message: Текст сообщения
            data: Дополнительные данные (object_id, shift_id, etc.)
            priority: Приоритет (по умолчанию NORMAL)
            scheduled_at: Время планируемой отправки (опционально)
            
        Returns:
            Созданное уведомление или None при ошибке
        """
        try:
            async with get_async_session() as session:
                # Проверяем существование пользователя
                user_query = select(User).where(User.id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User {user_id} not found")
                    return None
                
                notification = Notification(
                    user_id=user_id,
                    type=type,
                    channel=channel,
                    status=NotificationStatus.PENDING,
                    priority=priority,
                    title=title,
                    message=message,
                    data=data or {},
                    scheduled_at=scheduled_at
                )
                
                session.add(notification)
                await session.commit()
                await session.refresh(notification)
                
                # Инвалидируем кэш пользователя
                await self._invalidate_user_cache(user_id)
                
                logger.info(
                    f"Created notification {notification.id} for user {user_id}, "
                    f"type={type.value}, channel={channel.value}, priority={priority.value}"
                )
                
                return notification
                
        except Exception as e:
            logger.error(f"Error creating notification for user {user_id}: {e}")
            return None
    
    @cached(ttl=timedelta(minutes=5), key_prefix="user_notifications")
    async def get_user_notifications(
        self,
        user_id: int,
        status: Optional[NotificationStatus] = None,
        type: Optional[NotificationType] = None,
        limit: int = 50,
        offset: int = 0,
        include_read: bool = True
    ) -> List[Notification]:
        """
        Получение уведомлений пользователя с фильтрацией.
        
        Args:
            user_id: ID пользователя
            status: Фильтр по статусу (опционально)
            type: Фильтр по типу (опционально)
            limit: Макс. кол-во результатов
            offset: Смещение для пагинации
            include_read: Включать ли прочитанные (по умолчанию да)
            
        Returns:
            Список уведомлений
        """
        try:
            async with get_async_session() as session:
                # Базовый запрос
                query = select(Notification).where(Notification.user_id == user_id)
                
                # Применяем фильтры
                if status:
                    query = query.where(Notification.status == status)
                
                if type:
                    query = query.where(Notification.type == type)
                
                if not include_read:
                    query = query.where(Notification.status != NotificationStatus.READ)
                
                # Сортировка: сначала непрочитанные, затем по дате создания
                query = query.order_by(
                    desc(Notification.status != NotificationStatus.READ),
                    desc(Notification.created_at)
                )
                
                # Пагинация
                query = query.limit(limit).offset(offset)
                
                result = await session.execute(query)
                notifications = result.scalars().all()
                
                return list(notifications)
                
        except Exception as e:
            logger.error(f"Error getting user notifications for user {user_id}: {e}")
            return []
    
    @cached(ttl=timedelta(minutes=1), key_prefix="unread_count")
    async def get_unread_count(self, user_id: int) -> int:
        """
        Получение количества непрочитанных уведомлений.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество непрочитанных уведомлений
        """
        try:
            async with get_async_session() as session:
                query = select(func.count(Notification.id)).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.status != NotificationStatus.READ
                    )
                )
                
                result = await session.execute(query)
                count = result.scalar_one()
                
                return count
                
        except Exception as e:
            logger.error(f"Error getting unread count for user {user_id}: {e}")
            return 0
    
    async def mark_as_read(
        self,
        notification_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Отметить уведомление как прочитанное.
        
        Args:
            notification_id: ID уведомления
            user_id: ID пользователя (для проверки владения)
            
        Returns:
            True если успешно
        """
        try:
            async with get_async_session() as session:
                # Получаем уведомление
                query = select(Notification).where(Notification.id == notification_id)
                
                if user_id:
                    query = query.where(Notification.user_id == user_id)
                
                result = await session.execute(query)
                notification = result.scalar_one_or_none()
                
                if not notification:
                    logger.warning(f"Notification {notification_id} not found")
                    return False
                
                # Отмечаем как прочитанное
                notification.mark_as_read()
                await session.commit()
                
                # Инвалидируем кэш
                await self._invalidate_user_cache(notification.user_id)
                
                logger.info(f"Marked notification {notification_id} as read")
                return True
                
        except Exception as e:
            logger.error(f"Error marking notification {notification_id} as read: {e}")
            return False
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """
        Отметить все уведомления пользователя как прочитанные.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Количество обновленных уведомлений
        """
        try:
            async with get_async_session() as session:
                # Получаем все непрочитанные
                query = select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.status != NotificationStatus.READ
                    )
                )
                
                result = await session.execute(query)
                notifications = result.scalars().all()
                
                count = 0
                for notification in notifications:
                    notification.mark_as_read()
                    count += 1
                
                await session.commit()
                
                # Инвалидируем кэш
                await self._invalidate_user_cache(user_id)
                
                logger.info(f"Marked {count} notifications as read for user {user_id}")
                return count
                
        except Exception as e:
            logger.error(f"Error marking all as read for user {user_id}: {e}")
            return 0
    
    async def delete_notification(
        self,
        notification_id: int,
        user_id: Optional[int] = None
    ) -> bool:
        """
        Удаление уведомления.
        
        Args:
            notification_id: ID уведомления
            user_id: ID пользователя (для проверки владения)
            
        Returns:
            True если успешно
        """
        try:
            async with get_async_session() as session:
                query = select(Notification).where(Notification.id == notification_id)
                
                if user_id:
                    query = query.where(Notification.user_id == user_id)
                
                result = await session.execute(query)
                notification = result.scalar_one_or_none()
                
                if not notification:
                    logger.warning(f"Notification {notification_id} not found")
                    return False
                
                await session.delete(notification)
                await session.commit()
                
                # Инвалидируем кэш
                await self._invalidate_user_cache(notification.user_id)
                
                logger.info(f"Deleted notification {notification_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting notification {notification_id}: {e}")
            return False
    
    async def get_scheduled_notifications(
        self,
        before: Optional[datetime] = None
    ) -> List[Notification]:
        """
        Получение запланированных уведомлений для отправки.
        
        Args:
            before: Время "до которого" (по умолчанию текущее время)
            
        Returns:
            Список запланированных уведомлений готовых к отправке
        """
        try:
            if before is None:
                before = datetime.now(timezone.utc)
            
            async with get_async_session() as session:
                query = select(Notification).where(
                    and_(
                        Notification.status == NotificationStatus.PENDING,
                        Notification.scheduled_at.isnot(None),
                        Notification.scheduled_at <= before
                    )
                ).order_by(
                    desc(Notification.priority),  # Сначала с высоким приоритетом
                    Notification.scheduled_at
                )
                
                result = await session.execute(query)
                notifications = result.scalars().all()
                
                return list(notifications)
                
        except Exception as e:
            logger.error(f"Error getting scheduled notifications: {e}")
            return []
    
    async def get_overdue_notifications(self) -> List[Notification]:
        """
        Получение просроченных уведомлений (не отправленных вовремя).
        
        Returns:
            Список просроченных уведомлений
        """
        try:
            now = datetime.now(timezone.utc)
            
            async with get_async_session() as session:
                query = select(Notification).where(
                    and_(
                        Notification.status == NotificationStatus.PENDING,
                        Notification.scheduled_at.isnot(None),
                        Notification.scheduled_at < now
                    )
                ).order_by(Notification.scheduled_at)
                
                result = await session.execute(query)
                notifications = result.scalars().all()
                
                return list(notifications)
                
        except Exception as e:
            logger.error(f"Error getting overdue notifications: {e}")
            return []
    
    async def group_notifications(
        self,
        user_id: int,
        period: timedelta = timedelta(hours=1)
    ) -> Dict[str, List[Notification]]:
        """
        Группировка уведомлений пользователя по типу за период.
        
        Args:
            user_id: ID пользователя
            period: Период группировки (по умолчанию 1 час)
            
        Returns:
            Словарь {notification_type: [notifications]}
        """
        try:
            since = datetime.now(timezone.utc) - period
            
            async with get_async_session() as session:
                query = select(Notification).where(
                    and_(
                        Notification.user_id == user_id,
                        Notification.created_at >= since,
                        Notification.status == NotificationStatus.PENDING
                    )
                ).order_by(Notification.created_at)
                
                result = await session.execute(query)
                notifications = result.scalars().all()
                
                # Группируем по типу
                grouped = {}
                for notification in notifications:
                    type_key = notification.type.value
                    if type_key not in grouped:
                        grouped[type_key] = []
                    grouped[type_key].append(notification)
                
                return grouped
                
        except Exception as e:
            logger.error(f"Error grouping notifications for user {user_id}: {e}")
            return {}
    
    async def update_notification_status(
        self,
        notification_id: int,
        status: NotificationStatus,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Обновление статуса уведомления.
        
        Args:
            notification_id: ID уведомления
            status: Новый статус
            error_message: Сообщение об ошибке (если failed)
            
        Returns:
            True если успешно
        """
        try:
            async with get_async_session() as session:
                query = select(Notification).where(Notification.id == notification_id)
                result = await session.execute(query)
                notification = result.scalar_one_or_none()
                
                if not notification:
                    logger.warning(f"Notification {notification_id} not found")
                    return False
                
                # Обновляем статус
                if status == NotificationStatus.SENT:
                    notification.mark_as_sent()
                elif status == NotificationStatus.DELIVERED:
                    notification.mark_as_delivered()
                elif status == NotificationStatus.READ:
                    notification.mark_as_read()
                elif status == NotificationStatus.FAILED:
                    notification.mark_as_failed(error_message)
                else:
                    notification.status = status
                
                await session.commit()
                
                # Инвалидируем кэш
                await self._invalidate_user_cache(notification.user_id)
                
                logger.info(
                    f"Updated notification {notification_id} status to {status.value}"
                )
                return True
                
        except Exception as e:
            logger.error(f"Error updating notification {notification_id} status: {e}")
            return False
    
    async def _invalidate_user_cache(self, user_id: int) -> None:
        """
        Инвалидация кэша уведомлений пользователя.
        
        Args:
            user_id: ID пользователя
        """
        try:
            # Инвалидируем все кэшированные ключи пользователя
            await CacheService.invalidate_pattern(f"user_notifications:*:{user_id}*")
            await CacheService.invalidate_pattern(f"unread_count:*:{user_id}*")
            
            logger.debug(f"Invalidated notification cache for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to invalidate cache for user {user_id}: {e}")
    
    async def get_user_notification_settings(self, user_id: int) -> Dict[str, Dict[str, bool]]:
        """
        Получить настройки уведомлений пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Словарь {type_code: {"telegram": bool, "inapp": bool}}
        """
        try:
            async with get_async_session() as session:
                # Получить User для доступа к JSON-полю notification_preferences
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return {}
                
                # notification_preferences - это JSON поле: {type_code: {"telegram": bool, "inapp": bool}}
                prefs = user.notification_preferences or {}
                return prefs
        except Exception as e:
            logger.error(f"Ошибка получения настроек уведомлений для user {user_id}: {e}")
            return {}
    
    async def set_user_notification_preference(
        self,
        user_id: int,
        notification_type: str,
        channel_telegram: bool,
        channel_inapp: bool
    ) -> bool:
        """
        Установить настройки уведомлений для конкретного типа.
        
        Args:
            user_id: ID пользователя
            notification_type: Код типа уведомления
            channel_telegram: Включить/выключить Telegram
            channel_inapp: Включить/выключить In-App
            
        Returns:
            True если успешно, False при ошибке
        """
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    logger.error(f"User {user_id} не найден")
                    return False
                
                prefs = user.notification_preferences or {}
                prefs[notification_type] = {
                    "telegram": channel_telegram,
                    "inapp": channel_inapp
                }
                user.notification_preferences = prefs
                await session.commit()
                
                logger.info(
                    f"Обновлены настройки уведомлений user {user_id}, type={notification_type}, "
                    f"telegram={channel_telegram}, inapp={channel_inapp}"
                )
                return True
        except Exception as e:
            logger.error(f"Ошибка установки настроек уведомлений для user {user_id}: {e}")
            return False