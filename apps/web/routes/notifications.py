"""API для работы с уведомлениями (In-App канал) и UI настроек."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logging.logger import logger
from core.database.session import get_db_session
from apps.web.dependencies import get_current_user_dependency
from apps.web.jinja import templates
from domain.entities.user import User
from shared.services.notification_service import NotificationService
from shared.services.system_features_service import SystemFeaturesService
from domain.entities.notification import Notification, NotificationStatus, NotificationType, NotificationChannel


router = APIRouter()


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