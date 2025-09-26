"""API для работы с уведомлениями."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import AsyncSession
from sqlalchemy import select, func

from core.database.session import get_db_session
from core.auth.jwt_auth import get_current_user_dependency
from domain.entities.notification import Notification
from shared.services.notification_service import NotificationService

router = APIRouter()


@router.get("/unread")
async def get_unread_notifications(
    limit: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка непрочитанных уведомлений для пользователя."""
    try:
        if isinstance(user, dict):
            user_id = user["id"]  # Это уже внутренний ID
        else:
            user_id = user.id
        
        notification_service = NotificationService(db)
        notifications = notification_service.get_unread(user_id, limit)
        
        return {
            "notifications": [
                {
                    "id": n.id,
                    "type": n.type,
                    "payload": n.payload,
                    "created_at": n.created_at.isoformat(),
                    "source": n.source,
                    "channel": n.channel,
                }
                for n in notifications
            ],
            "total": len(notifications),
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения уведомлений: {str(e)}")


@router.get("/count")
async def get_unread_count(
    user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение количества непрочитанных уведомлений."""
    try:
        if isinstance(user, dict):
            user_id = user["id"]  # Это уже внутренний ID
        else:
            user_id = user.id
        
        result = await db.execute(
            select(func.count(Notification.id))
            .where(
                Notification.user_id == user_id,
                Notification.is_read.is_(False)
            )
        )
        count = result.scalar()
        
        return {"count": count or 0}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения количества: {str(e)}")


@router.post("/mark-read")
async def mark_notifications_read(
    notification_ids: List[int],
    user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """Отметка уведомлений как прочитанных."""
    try:
        if isinstance(user, dict):
            user_id = user["id"]  # Это уже внутренний ID
        else:
            user_id = user.id
        
        notification_service = NotificationService(db)
        notification_service.mark_as_read(user_id, notification_ids)
        
        await db.commit()
        
        return {"success": True, "marked_count": len(notification_ids)}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка отметки уведомлений: {str(e)}")


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление уведомления."""
    try:
        if isinstance(user, dict):
            user_id = user["id"]  # Это уже внутренний ID
        else:
            user_id = user.id
        
        # Проверяем, что уведомление принадлежит пользователю
        result = await db.execute(
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Уведомление не найдено")
        
        await db.delete(notification)
        await db.commit()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка удаления уведомления: {str(e)}")
