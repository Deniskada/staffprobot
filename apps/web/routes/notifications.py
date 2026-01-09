"""API для работы с уведомлениями (In-App канал) и UI настроек."""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Body, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.logging.logger import logger
from core.database.session import get_db_session
from apps.web.dependencies import get_current_user_dependency
from apps.web.jinja import templates
from domain.entities.user import User
from shared.services.notification_service import NotificationService
from shared.services.system_features_service import SystemFeaturesService
from domain.entities.notification import Notification, NotificationStatus, NotificationType, NotificationChannel


router = APIRouter()


# Pydantic models для request body
class BulkActionRequest(BaseModel):
    notification_ids: List[int]


@router.get("/unread-count")
async def api_unread_count(
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Количество непрочитанных In-App уведомлений текущего пользователя."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    service = NotificationService()
    # Фильтруем только In-App уведомления для колокольчика
    count = await service.get_unread_count(current_user.id, channel=NotificationChannel.IN_APP)
    return {"count": int(count)}


@router.get("/list")
async def api_notifications_list(
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Список последних In-App уведомлений (по умолчанию 10)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    try:
        limit = max(1, min(50, int(limit)))
        service = NotificationService()
        # Фильтруем только In-App уведомления для колокольчика
        # Показываем только непрочитанные (include_read=False)
        notifications = await service.get_user_notifications(
            user_id=current_user.id,
            status=None,
            type=None,
            channel=NotificationChannel.IN_APP,
            limit=limit,
            offset=0,
            include_read=False,  # Показываем только непрочитанные в дропдауне
        )
        return {"notifications": [n.to_dict() for n in notifications]}
    except Exception as e:
        logger.error(f"Error getting notifications list for user {current_user.id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mark-all-read")
async def api_mark_all_read(
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Отметить все In-App уведомления как прочитанные."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    service = NotificationService()
    # Отмечаем только In-App уведомления как прочитанные
    updated = await service.mark_all_as_read(current_user.id, channel=NotificationChannel.IN_APP)
    return {"updated": int(updated)}


@router.get("/center")
async def api_notifications_center(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    type_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    sort_by: str = Query("date", regex="^(date|priority)$"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """
    Получение уведомлений для центра уведомлений с пагинацией (infinite scroll).
    
    Args:
        limit: Количество уведомлений (по умолчанию 30)
        offset: Смещение для пагинации
        type_filter: Фильтр по типу уведомления (опционально)
        status_filter: Фильтр по статусу (all, unread, read)
        sort_by: Сортировка (date или priority)
    
    Returns:
        Список уведомлений + метаданные (total_count, has_more)
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        
        # Определяем статус для фильтрации
        status_enum = None
        include_read = True
        if status_filter == "unread":
            include_read = False
        elif status_filter == "read":
            status_enum = NotificationStatus.READ
        
        # Определяем тип для фильтрации
        type_enum = None
        if type_filter:
            try:
                type_enum = NotificationType(type_filter)
            except ValueError:
                pass
        
        # Получаем уведомления
        notifications = await service.get_user_notifications(
            user_id=current_user.id,
            status=status_enum,
            type=type_enum,
            channel=NotificationChannel.IN_APP,
            limit=limit + 1,  # Загружаем на 1 больше для проверки has_more
            offset=offset,
            include_read=include_read,
            sort_by=sort_by  # Передаем sort_by
        )
        
        # Проверяем, есть ли еще уведомления
        has_more = len(notifications) > limit
        if has_more:
            notifications = notifications[:limit]
        
        # Получаем общее количество
        total_count = await service.get_unread_count(current_user.id, channel=NotificationChannel.IN_APP)
        if status_filter == "read" or include_read:
            # Для полного списка нужно получить count через другой метод
            # Пока используем приближенное значение
            total_count = offset + len(notifications) + (1 if has_more else 0)
        
        return {
            "notifications": [n.to_dict() for n in notifications],
            "total_count": int(total_count),
            "has_more": has_more,
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        import traceback
        logger.error(f"Error getting notifications center for user {current_user.id}: {e}", error=str(e), traceback=traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/center/grouped")
async def api_notifications_center_grouped(
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    type_filter: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None),
    group_by: str = Query("category", regex="^(type|category)$"),
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """
    Получение уведомлений с группировкой по типам/категориям.
    
    Args:
        limit: Максимальное количество уведомлений
        offset: Смещение для пагинации
        type_filter: Фильтр по типу уведомления
        status_filter: Фильтр по статусу (all, unread, read)
        group_by: Группировка (type или category)
    
    Returns:
        Структура {category: {type: [notifications]}}
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        
        # Определяем статус для фильтрации
        status_enum = None
        include_read = True
        if status_filter == "unread":
            include_read = False
        elif status_filter == "read":
            status_enum = NotificationStatus.READ
        
        # Определяем тип для фильтрации
        type_enum = None
        if type_filter:
            try:
                type_enum = NotificationType(type_filter)
            except ValueError:
                pass
        
        # Получаем уведомления
        notifications = await service.get_user_notifications(
            user_id=current_user.id,
            status=status_enum,
            type=type_enum,
            channel=NotificationChannel.IN_APP,
            limit=limit,
            offset=offset,
            include_read=include_read
        )
        
        # Маппинг типов на категории
        CATEGORY_MAP = {
            # Смены
            "shift_reminder": "shifts",
            "shift_confirmed": "shifts",
            "shift_cancelled": "shifts",
            "shift_started": "shifts",
            "shift_completed": "shifts",
            # Объекты
            "object_opened": "objects",
            "object_closed": "objects",
            "object_late_opening": "objects",
            "object_no_shifts_today": "objects",
            "object_early_closing": "objects",
            # Договоры
            "contract_signed": "contracts",
            "contract_terminated": "contracts",
            "contract_expiring": "contracts",
            "contract_updated": "contracts",
            # Отзывы
            "review_received": "reviews",
            "review_moderated": "reviews",
            "appeal_submitted": "reviews",
            "appeal_decision": "reviews",
            # Платежи
            "payment_due": "payments",
            "payment_success": "payments",
            "payment_failed": "payments",
            "subscription_expiring": "payments",
            "subscription_expired": "payments",
            "usage_limit_warning": "payments",
            "usage_limit_exceeded": "payments",
            # Задачи
            "task_assigned": "tasks",
            "task_completed": "tasks",
            "task_overdue": "tasks",
            # Системные
            "welcome": "system",
            "password_reset": "system",
            "account_suspended": "system",
            "account_activated": "system",
            "system_maintenance": "system",
            "feature_announcement": "system",
        }
        
        # Группируем уведомления
        grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        
        for notification in notifications:
            # notification.type - это строка (из-за native_enum=False)
            # Используем type напрямую или через type_enum если нужно
            notif_type = notification.type if isinstance(notification.type, str) else notification.type.value
            category = CATEGORY_MAP.get(notif_type, "other")
            
            if category not in grouped:
                grouped[category] = {}
            
            if group_by == "type":
                # Группируем по типу внутри категории
                if notif_type not in grouped[category]:
                    grouped[category][notif_type] = []
                grouped[category][notif_type].append(notification.to_dict())
            else:
                # Группируем только по категории
                if "all" not in grouped[category]:
                    grouped[category]["all"] = []
                grouped[category]["all"].append(notification.to_dict())
        
        return {
            "grouped": grouped,
            "total_count": len(notifications)
        }
    except Exception as e:
        import traceback
        logger.error(f"Error getting grouped notifications for user {current_user.id}: {e}", error=str(e), traceback=traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{notification_id}/mark-read")
async def api_mark_notification_read(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Отметить одно уведомление как прочитанное."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        success = await service.mark_as_read(notification_id, user_id=current_user.id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
        return {"success": True, "notification_id": notification_id}
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/mark-read-bulk")
async def api_mark_notifications_read_bulk(
    request: BulkActionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Массовая отметка уведомлений как прочитанных."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        success_count = 0
        failed_count = 0
        
        for notification_id in request.notification_ids:
            try:
                success = await service.mark_as_read(notification_id, user_id=current_user.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.warning(f"Failed to mark notification {notification_id} as read: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "marked": success_count,
            "failed": failed_count,
            "total": len(request.notification_ids)
        }
    except Exception as e:
        logger.error(f"Error in bulk mark as read: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{notification_id}/delete")
async def api_delete_notification(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Удалить одно уведомление."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        success = await service.delete_notification(notification_id, user_id=current_user.id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
        return {"success": True, "notification_id": notification_id}
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/delete-bulk")
async def api_delete_notifications_bulk(
    request: BulkActionRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Массовое удаление уведомлений."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        service = NotificationService()
        success_count = 0
        failed_count = 0
        
        for notification_id in request.notification_ids:
            try:
                success = await service.delete_notification(notification_id, user_id=current_user.id)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete notification {notification_id}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "deleted": success_count,
            "failed": failed_count,
            "total": len(request.notification_ids)
        }
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{notification_id}/action-url")
async def api_notification_action_url(
    notification_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """
    Получить URL для перехода к связанному объекту уведомления.
    
    Returns:
        {"action_url": "/owner/shifts/123"} или {"action_url": null}
    """
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    
    try:
        from shared.services.notification_action_service import NotificationActionService
        
        # Получаем уведомление
        service = NotificationService()
        notifications = await service.get_user_notifications(
            user_id=current_user.id,
            status=None,
            type=None,
            channel=NotificationChannel.IN_APP,
            limit=1,
            offset=0,
            include_read=True
        )
        
        # Ищем нужное уведомление (упрощенная проверка)
        # TODO: Добавить метод get_notification_by_id в NotificationService
        notification = None
        result = await session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
        # Получаем роль пользователя
        user_role = "owner"  # По умолчанию
        if hasattr(current_user, 'roles') and current_user.roles:
            if 'owner' in current_user.roles:
                user_role = "owner"
            elif 'manager' in current_user.roles:
                user_role = "manager"
        
        # Получаем action_url
        action_service = NotificationActionService()
        action_url = action_service.get_action_url(notification, user_role)
        
        return {"action_url": action_url}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting action URL for notification {notification_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))