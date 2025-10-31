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
    """Количество непрочитанных уведомлений текущего пользователя."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    service = NotificationService()
    count = await service.get_unread_count(current_user.id)
    return {"count": int(count)}


@router.get("/list")
async def api_notifications_list(
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Список последних уведомлений (по умолчанию 10)."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    limit = max(1, min(50, int(limit)))
    service = NotificationService()
    items = await service.get_user_notifications(
        user_id=current_user.id,
        status=None,
        type=None,
        limit=limit,
        offset=0,
        include_read=True,
    )
    return {"items": [n.to_dict() for n in items]}


@router.post("/mark-all-read")
async def api_mark_all_read(
    session: AsyncSession = Depends(get_db_session),
    current_user: Optional[User] = Depends(get_current_user_dependency())
):
    """Отметить все уведомления как прочитанные."""
    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    service = NotificationService()
    updated = await service.mark_all_as_read(current_user.id)
    return {"updated": int(updated)}