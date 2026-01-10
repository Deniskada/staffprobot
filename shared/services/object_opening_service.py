"""Сервис управления состоянием объектов (открыт/закрыт)."""

from typing import Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.object_opening import ObjectOpening
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
from core.logging.logger import logger
from core.utils.timezone_helper import timezone_helper


class ObjectOpeningService:
    """Сервис для управления состоянием объектов.
    
    Не использует BaseService, т.к. требует передачи сессии.
    """
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса с сессией БД."""
        self.db = session
    
    async def is_object_open(self, object_id: int) -> bool:
        """Проверить: открыт ли объект.
        
        Args:
            object_id: ID объекта
            
        Returns:
            True если объект открыт (есть запись с closed_at IS NULL)
        """
        query = select(ObjectOpening).where(
            ObjectOpening.object_id == object_id,
            ObjectOpening.closed_at.is_(None)
        )
        result = await self.db.execute(query)
        opening = result.scalar_one_or_none()
        
        is_open = opening is not None
        logger.info(
            f"Object open status checked",
            object_id=object_id,
            is_open=is_open,
            opening_id=opening.id if opening else None
        )
        return is_open
    
    async def get_active_opening(self, object_id: int) -> Optional[ObjectOpening]:
        """Получить активную запись открытия объекта.
        
        Args:
            object_id: ID объекта
            
        Returns:
            ObjectOpening если объект открыт, иначе None
        """
        query = select(ObjectOpening).where(
            ObjectOpening.object_id == object_id,
            ObjectOpening.closed_at.is_(None)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def open_object(
        self,
        object_id: int,
        user_id: int,
        coordinates: Optional[str] = None
    ) -> ObjectOpening:
        """Открыть объект.
        
        Args:
            object_id: ID объекта
            user_id: ID пользователя, открывающего объект
            coordinates: Координаты в формате "lat,lon"
            
        Returns:
            Созданная запись ObjectOpening
            
        Raises:
            ValueError: Если объект уже открыт
        """
        # Проверить: уже открыт?
        if await self.is_object_open(object_id):
            raise ValueError(f"Object {object_id} is already open")
        
        # Создать запись
        opening = ObjectOpening(
            object_id=object_id,
            opened_by=user_id,
            opened_at=datetime.now(),
            open_coordinates=coordinates
        )
        
        self.db.add(opening)
        await self.db.commit()
        await self.db.refresh(opening)
        
        # Загружаем объект с owner для отправки уведомлений
        obj_query = select(Object).options(
            selectinload(Object.owner),
            selectinload(Object.org_unit)
        ).where(Object.id == object_id)
        obj_result = await self.db.execute(obj_query)
        obj = obj_result.scalar_one_or_none()
        
        if obj and obj.owner:
            # Отправляем уведомление об открытии объекта
            await self._notify_object_opened(obj, opening, user_id)
        
        logger.info(
            f"Object opened",
            object_id=object_id,
            user_id=user_id,
            opening_id=opening.id,
            coordinates=coordinates
        )
        
        return opening
    
    async def close_object(
        self,
        object_id: int,
        user_id: int,
        coordinates: Optional[str] = None
    ) -> ObjectOpening:
        """Закрыть объект.
        
        Args:
            object_id: ID объекта
            user_id: ID пользователя, закрывающего объект
            coordinates: Координаты в формате "lat,lon"
            
        Returns:
            Обновленная запись ObjectOpening
            
        Raises:
            ValueError: Если объект не открыт
        """
        # Получить активное открытие
        opening = await self.get_active_opening(object_id)
        if not opening:
            raise ValueError(f"Object {object_id} is not open")
        
        # Закрыть
        opening.closed_by = user_id
        opening.closed_at = datetime.now()
        opening.close_coordinates = coordinates
        
        await self.db.commit()
        await self.db.refresh(opening)
        
        # Загружаем объект с owner для отправки уведомлений
        obj_query = select(Object).options(
            selectinload(Object.owner),
            selectinload(Object.org_unit)
        ).where(Object.id == object_id)
        obj_result = await self.db.execute(obj_query)
        obj = obj_result.scalar_one_or_none()
        
        if obj and obj.owner:
            # Загружаем пользователя, который закрыл объект
            user_query = select(User).where(User.id == user_id)
            user_result = await self.db.execute(user_query)
            closing_user = user_result.scalar_one_or_none()
            
            # Отправляем уведомление о закрытии объекта
            await self._notify_object_closed(obj, opening, closing_user)
        
        logger.info(
            f"Object closed",
            object_id=object_id,
            user_id=user_id,
            opening_id=opening.id,
            duration_hours=opening.duration_hours,
            coordinates=coordinates
        )
        
        return opening
    
    async def get_active_shifts_count(self, object_id: int) -> int:
        """Подсчитать количество активных смен на объекте.
        
        Args:
            object_id: ID объекта
            
        Returns:
            Количество активных смен
        """
        query = select(func.count(Shift.id)).where(
            Shift.object_id == object_id,
            Shift.status == 'active'
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        
        logger.debug(
            f"Active shifts counted",
            object_id=object_id,
            count=count
        )
        
        return count
    
    async def _notify_object_opened(self, obj: Object, opening: ObjectOpening, opening_user_id: int) -> None:
        """Отправить уведомление об открытии объекта."""
        try:
            from shared.services.notification_service import NotificationService
            from shared.templates.notifications.base_templates import NotificationTemplateManager
            
            # Загружаем пользователя, который открыл объект
            user_query = select(User).where(User.id == opening_user_id)
            user_result = await self.db.execute(user_query)
            opening_user = user_result.scalar_one_or_none()
            
            if not opening_user:
                logger.warning(f"User {opening_user_id} not found for object opening notification")
                return
            
            # Проверяем настройки владельца
            prefs = obj.owner.notification_preferences or {}
            type_code = NotificationType.OBJECT_OPENED.value
            type_prefs = prefs.get(type_code, {})
            telegram_enabled = type_prefs.get("telegram", True) if type_code in prefs else True
            inapp_enabled = type_prefs.get("inapp", True) if type_code in prefs else True
            
            if not telegram_enabled and not inapp_enabled:
                logger.debug(f"Object opening notifications disabled for owner {obj.owner.id}")
                return
            
            # Определяем, вовремя ли открылся объект
            today_local = timezone_helper.utc_to_local(opening.opened_at).date()
            actual_open_local = timezone_helper.utc_to_local(opening.opened_at)
            
            delay_minutes = 0
            if obj.opening_time:
                expected_open = datetime.combine(today_local, obj.opening_time).replace(tzinfo=timezone_helper.local_tz)
                delay_minutes = int((actual_open_local - expected_open).total_seconds() / 60)
            
            # Выбираем тип уведомления
            if delay_minutes > 5:
                notif_type = NotificationType.OBJECT_LATE_OPENING
                priority = NotificationPriority.HIGH
                template_vars = {
                    "object_id": obj.id,
                    "date": str(today_local),
                    "object_name": obj.name,
                    "employee_name": f"{opening_user.first_name} {opening_user.last_name}".strip() or "Неизвестный",
                    "planned_time": expected_open.strftime("%H:%M"),
                    "actual_time": actual_open_local.strftime("%H:%M"),
                    "delay_minutes": str(delay_minutes)
                }
            else:
                notif_type = NotificationType.OBJECT_OPENED
                priority = NotificationPriority.NORMAL
                template_vars = {
                    "object_id": obj.id,
                    "date": str(today_local),
                    "object_name": obj.name,
                    "employee_name": f"{opening_user.first_name} {opening_user.last_name}".strip() or "Неизвестный",
                    "open_time": actual_open_local.strftime("%H:%M")
                }
            
            # Создаем уведомления
            notification_service = NotificationService()
            
            if telegram_enabled:
                rendered_tg = NotificationTemplateManager.render(notif_type, NotificationChannel.TELEGRAM, template_vars)
                notification_tg = await notification_service.create_notification(
                    user_id=obj.owner.id,
                    type=notif_type,
                    channel=NotificationChannel.TELEGRAM,
                    title=rendered_tg["title"],
                    message=rendered_tg["message"],
                    data={**template_vars, "object_id": obj.id},
                    priority=priority,
                    scheduled_at=None
                )
                
                # Отправляем Telegram уведомление через Celery
                if notification_tg and hasattr(notification_tg, 'id') and notification_tg.id:
                    try:
                        from core.celery.tasks.notification_tasks import send_notification_now
                        send_notification_now.apply_async(
                            args=[notification_tg.id],
                            queue="notifications"
                        )
                        logger.debug(
                            "Enqueued object opening Telegram notification for sending",
                            notification_id=notification_tg.id,
                            user_id=obj.owner.id,
                            notification_type=notif_type.value,
                        )
                    except Exception as send_exc:
                        logger.warning(
                            "Failed to enqueue object opening Telegram notification",
                            notification_id=notification_tg.id if notification_tg else None,
                            error=str(send_exc),
                        )
            
            if inapp_enabled:
                rendered_inapp = NotificationTemplateManager.render(notif_type, NotificationChannel.IN_APP, template_vars)
                await notification_service.create_notification(
                    user_id=obj.owner.id,
                    type=notif_type,
                    channel=NotificationChannel.IN_APP,
                    title=rendered_inapp["title"],
                    message=rendered_inapp["message"],
                    data=template_vars,
                    priority=priority,
                    scheduled_at=None
                )
            
            logger.info(
                f"Object opening notification created",
                object_id=obj.id,
                owner_id=obj.owner.id,
                type=notif_type.value,
                delay_minutes=delay_minutes
            )
        except Exception as e:
            logger.error(
                f"Error creating object opening notification: {e}",
                object_id=obj.id,
                error=str(e),
                exc_info=True
            )
    
    async def _notify_object_closed(self, obj: Object, opening: ObjectOpening, closing_user: Optional[User]) -> None:
        """Отправить уведомление о закрытии объекта."""
        try:
            from shared.services.notification_service import NotificationService
            from shared.templates.notifications.base_templates import NotificationTemplateManager
            
            if not closing_user:
                logger.warning(f"Closing user not found for object closing notification")
                return
            
            # Проверяем настройки владельца
            prefs = obj.owner.notification_preferences or {}
            type_code = NotificationType.OBJECT_CLOSED.value
            type_prefs = prefs.get(type_code, {})
            telegram_enabled = type_prefs.get("telegram", True) if type_code in prefs else True
            inapp_enabled = type_prefs.get("inapp", True) if type_code in prefs else True
            
            if not telegram_enabled and not inapp_enabled:
                logger.debug(f"Object closing notifications disabled for owner {obj.owner.id}")
                return
            
            # Определяем, вовремя ли закрылся объект
            today_local = timezone_helper.utc_to_local(opening.closed_at).date()
            actual_close_local = timezone_helper.utc_to_local(opening.closed_at)
            
            early_minutes = 0
            if obj.closing_time:
                expected_close = datetime.combine(today_local, obj.closing_time).replace(tzinfo=timezone_helper.local_tz)
                early_minutes = int((expected_close - actual_close_local).total_seconds() / 60)
            
            # Выбираем тип уведомления
            if early_minutes > 5:
                notif_type = NotificationType.OBJECT_EARLY_CLOSING
                priority = NotificationPriority.HIGH
                template_vars = {
                    "object_id": obj.id,
                    "date": str(today_local),
                    "object_name": obj.name,
                    "employee_name": f"{closing_user.first_name} {closing_user.last_name}".strip() or "Неизвестный",
                    "planned_time": expected_close.strftime("%H:%M"),
                    "actual_time": actual_close_local.strftime("%H:%M"),
                    "early_minutes": str(early_minutes)
                }
            else:
                notif_type = NotificationType.OBJECT_CLOSED
                priority = NotificationPriority.NORMAL
                template_vars = {
                    "object_id": obj.id,
                    "date": str(today_local),
                    "object_name": obj.name,
                    "employee_name": f"{closing_user.first_name} {closing_user.last_name}".strip() or "Неизвестный",
                    "close_time": actual_close_local.strftime("%H:%M")
                }
            
            # Создаем уведомления
            notification_service = NotificationService()
            
            if telegram_enabled:
                rendered_tg = NotificationTemplateManager.render(notif_type, NotificationChannel.TELEGRAM, template_vars)
                notification_tg = await notification_service.create_notification(
                    user_id=obj.owner.id,
                    type=notif_type,
                    channel=NotificationChannel.TELEGRAM,
                    title=rendered_tg["title"],
                    message=rendered_tg["message"],
                    data={**template_vars, "object_id": obj.id},
                    priority=priority,
                    scheduled_at=None
                )
                
                # Отправляем Telegram уведомление через Celery
                if notification_tg and hasattr(notification_tg, 'id') and notification_tg.id:
                    try:
                        from core.celery.tasks.notification_tasks import send_notification_now
                        send_notification_now.apply_async(
                            args=[notification_tg.id],
                            queue="notifications"
                        )
                        logger.debug(
                            "Enqueued object closing Telegram notification for sending",
                            notification_id=notification_tg.id,
                            user_id=obj.owner.id,
                            notification_type=notif_type.value,
                        )
                    except Exception as send_exc:
                        logger.warning(
                            "Failed to enqueue object closing Telegram notification",
                            notification_id=notification_tg.id if notification_tg else None,
                            error=str(send_exc),
                        )
            
            if inapp_enabled:
                rendered_inapp = NotificationTemplateManager.render(notif_type, NotificationChannel.IN_APP, template_vars)
                await notification_service.create_notification(
                    user_id=obj.owner.id,
                    type=notif_type,
                    channel=NotificationChannel.IN_APP,
                    title=rendered_inapp["title"],
                    message=rendered_inapp["message"],
                    data=template_vars,
                    priority=priority,
                    scheduled_at=None
                )
            
            logger.info(
                f"Object closing notification created",
                object_id=obj.id,
                owner_id=obj.owner.id,
                type=notif_type.value,
                early_minutes=early_minutes
            )
        except Exception as e:
            logger.error(
                f"Error creating object closing notification: {e}",
                object_id=obj.id,
                error=str(e),
                exc_info=True
            )

