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


# ============ UI роуты для настроек (владелец) ============

@router.get("/settings", response_class=HTMLResponse)
async def notifications_settings_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Страница настроек уведомлений (владелец)."""
    if not current_user or current_user.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    telegram_id = current_user.get("id")
    features_service = SystemFeaturesService(session)
    is_feature_enabled = await features_service.is_feature_enabled(telegram_id, "notifications")
    
    # Получить User.id
    user_result = await session.execute(
        select(User.id).where(User.telegram_id == telegram_id)
    )
    user_id = user_result.scalar_one_or_none()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    notification_types = []
    if is_feature_enabled:
        # Получить все типы уведомлений из БД
        result = await session.execute(
            select(NotificationType).order_by(NotificationType.priority.desc(), NotificationType.type_code)
        )
        types_db = result.scalars().all()
        
        # Получить текущие настройки пользователя
        service = NotificationService()
        user_settings = await service.get_user_notification_settings(user_id)
        
        for ntype in types_db:
            setting_key = f"{ntype.type_code}"
            user_pref = user_settings.get(setting_key, {})
            notification_types.append({
                "type_code": ntype.type_code,
                "title": ntype.title,
                "description": ntype.description,
                "priority": ntype.priority,
                "priority_label": {
                    "critical": "Критический",
                    "high": "Высокий",
                    "medium": "Средний",
                    "low": "Низкий"
                }.get(ntype.priority, ntype.priority),
                "telegram_enabled": user_pref.get("telegram", True),
                "inapp_enabled": user_pref.get("inapp", True),
            })
    
    return templates.TemplateResponse(
        "owner/notifications_settings.html",
        {
            "request": request,
            "current_user": current_user,
            "is_feature_enabled": is_feature_enabled,
            "notification_types": notification_types,
        }
    )


@router.post("/settings")
async def notifications_settings_save(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Сохранение настроек уведомлений (владелец)."""
    if not current_user or current_user.get("role") != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    telegram_id = current_user.get("id")
    features_service = SystemFeaturesService(session)
    is_feature_enabled = await features_service.is_feature_enabled(telegram_id, "notifications")
    
    if not is_feature_enabled:
        return RedirectResponse(url="/owner/notifications/settings", status_code=status.HTTP_303_SEE_OTHER)
    
    # Получить User.id
    user_result = await session.execute(
        select(User.id).where(User.telegram_id == telegram_id)
    )
    user_id = user_result.scalar_one_or_none()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Парсинг формы
    form_data = await request.form()
    
    # Получить все типы уведомлений
    result = await session.execute(select(NotificationType))
    types_db = result.scalars().all()
    
    service = NotificationService()
    for ntype in types_db:
        telegram_key = f"telegram_{ntype.type_code}"
        inapp_key = f"inapp_{ntype.type_code}"
        
        telegram_enabled = telegram_key in form_data
        inapp_enabled = inapp_key in form_data
        
        await service.set_user_notification_preference(
            user_id=user_id,
            notification_type=ntype.type_code,
            channel_telegram=telegram_enabled,
            channel_inapp=inapp_enabled
        )
    
    logger.info(
        "Настройки уведомлений обновлены",
        user_id=user_id,
        telegram_id=telegram_id
    )
    
    return RedirectResponse(url="/owner/notifications/settings", status_code=status.HTTP_303_SEE_OTHER)