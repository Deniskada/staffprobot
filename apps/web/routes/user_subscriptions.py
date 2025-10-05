"""Роуты для управления подписками пользователей."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.tariff_service import TariffService
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse, name="user_subscriptions_list")
async def user_subscriptions_list(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Список подписок пользователей."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            
            # Получаем все подписки с информацией о пользователях и тарифах
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from domain.entities.user_subscription import UserSubscription
            from domain.entities.user import User
            from domain.entities.tariff_plan import TariffPlan
            
            query = select(UserSubscription).options(
                selectinload(UserSubscription.user),
                selectinload(UserSubscription.tariff_plan)
            ).order_by(UserSubscription.created_at.desc())
            
            result = await session.execute(query)
            subscriptions = result.scalars().all()
            
            # Статистика
            statistics = await tariff_service.get_tariff_statistics()
        
        return templates.TemplateResponse("admin/user_subscriptions.html", {
            "request": request,
            "current_user": current_user,
            "title": "Управление подписками пользователей",
            "subscriptions": subscriptions,
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"Error loading user subscriptions: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки подписок: {str(e)}")


@router.get("/assign", response_class=HTMLResponse, name="assign_subscription_form")
async def assign_subscription_form(
    request: Request,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_superadmin)
):
    """Форма назначения подписки пользователю."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plans = await tariff_service.get_all_tariff_plans(active_only=True)
            
            # Получаем информацию о пользователе, если указан user_id
            selected_user = None
            if user_id:
                from sqlalchemy import select
                from domain.entities.user import User
                
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                selected_user = result.scalar_one_or_none()
        
        return templates.TemplateResponse("admin/assign_subscription.html", {
            "request": request,
            "current_user": current_user,
            "title": "Назначение подписки пользователю",
            "tariff_plans": tariff_plans,
            "selected_user": selected_user,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Error loading assign subscription form: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы: {str(e)}")


@router.post("/assign", name="assign_subscription_post")
async def assign_subscription(
    request: Request,
    user_id: int = Form(...),
    tariff_plan_id: int = Form(...),
    payment_method: str = Form("manual"),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(require_superadmin)
):
    """Назначение подписки пользователю."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            
            # Проверяем, что пользователь существует
            from sqlalchemy import select
            from domain.entities.user import User
            
            user_result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            # Создаем подписку
            subscription = await tariff_service.create_user_subscription(
                user_id=user_id,
                tariff_plan_id=tariff_plan_id,
                payment_method=payment_method,
                notes=notes
            )
            
            logger.info(f"Assigned subscription {subscription.id} to user {user_id} on tariff {tariff_plan_id}")
        
        return RedirectResponse(url="/admin/subscriptions/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка назначения подписки: {str(e)}")


@router.post("/{subscription_id}/cancel", name="cancel_subscription")
async def cancel_subscription(
    request: Request,
    subscription_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """Отмена подписки."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            
            # Получаем подписку
            from sqlalchemy import select
            from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
            
            result = await session.execute(
                select(UserSubscription).where(UserSubscription.id == subscription_id)
            )
            subscription = result.scalar_one_or_none()
            
            if not subscription:
                raise HTTPException(status_code=404, detail="Подписка не найдена")
            
            # Отменяем подписку
            subscription.status = SubscriptionStatus.CANCELLED
            await session.commit()
            
            logger.info(f"Cancelled subscription {subscription_id}")
        
        return RedirectResponse(url="/admin/subscriptions/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка отмены подписки: {str(e)}")


# API endpoints для AJAX запросов

@router.get("/api/list", response_class=JSONResponse, name="api_subscriptions_list")
async def api_subscriptions_list(
    current_user: dict = Depends(require_superadmin)
):
    """API: Список подписок пользователей."""
    try:
        async with get_async_session() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from domain.entities.user_subscription import UserSubscription
            
            query = select(UserSubscription).options(
                selectinload(UserSubscription.user),
                selectinload(UserSubscription.tariff_plan)
            ).order_by(UserSubscription.created_at.desc())
            
            result = await session.execute(query)
            subscriptions = result.scalars().all()
        
        return {
            "success": True,
            "data": [subscription.to_dict() for subscription in subscriptions]
        }
        
    except Exception as e:
        logger.error(f"API Error loading subscriptions: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/user/{user_id}", response_class=JSONResponse, name="api_user_subscription")
async def api_user_subscription(
    user_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """API: Подписка конкретного пользователя."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            subscription = await tariff_service.get_user_subscription(user_id)
        
        if not subscription:
            return {
                "success": True,
                "data": None,
                "message": "У пользователя нет активной подписки"
            }
        
        return {
            "success": True,
            "data": subscription.to_dict()
        }
        
    except Exception as e:
        logger.error(f"API Error loading user subscription: {e}")
        return {
            "success": False,
            "error": str(e)
        }
