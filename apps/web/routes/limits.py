"""Роуты для контроля лимитов и платных функций."""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_owner_or_superadmin, require_superadmin
from apps.web.services.limits_service import LimitsService
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse, name="limits_dashboard")
async def limits_dashboard(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Дашборд контроля лимитов."""
    try:
        # Получаем user_id из current_user
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            limits_summary = await limits_service.get_user_limits_summary(user_id)
        
        return templates.TemplateResponse("owner/limits_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Контроль лимитов",
            "limits_summary": limits_summary
        })
        
    except Exception as e:
        logger.error(f"Error loading limits dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


# API endpoints для проверки лимитов

@router.get("/api/check/object", response_class=JSONResponse, name="check_object_limit")
async def check_object_limit(
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """API: Проверка лимита на создание объектов."""
    try:
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            allowed, message, details = await limits_service.check_object_creation_limit(user_id)
        
        return {
            "success": True,
            "allowed": allowed,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        logger.error(f"API Error checking object limit: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/check/employee", response_class=JSONResponse, name="check_employee_limit")
async def check_employee_limit(
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """API: Проверка лимита на добавление сотрудников."""
    try:
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            allowed, message, details = await limits_service.check_employee_creation_limit(user_id, object_id)
        
        return {
            "success": True,
            "allowed": allowed,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        logger.error(f"API Error checking employee limit: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/check/manager", response_class=JSONResponse, name="check_manager_limit")
async def check_manager_limit(
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """API: Проверка лимита на назначение управляющих."""
    try:
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            allowed, message, details = await limits_service.check_manager_assignment_limit(user_id)
        
        return {
            "success": True,
            "allowed": allowed,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        logger.error(f"API Error checking manager limit: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/check/feature/{feature}", response_class=JSONResponse, name="check_feature_access")
async def check_feature_access(
    feature: str,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """API: Проверка доступа к платной функции."""
    try:
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            allowed, message, details = await limits_service.check_feature_access(user_id, feature)
        
        return {
            "success": True,
            "allowed": allowed,
            "message": message,
            "details": details
        }
        
    except Exception as e:
        logger.error(f"API Error checking feature access: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/summary", response_class=JSONResponse, name="limits_summary")
async def limits_summary(
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """API: Полная сводка по лимитам пользователя."""
    try:
        user_id = await _get_user_id_from_current_user(current_user)
        if not user_id:
            raise HTTPException(status_code=400, detail="Не удалось определить пользователя")
        
        async with get_async_session() as session:
            limits_service = LimitsService(session)
            summary = await limits_service.get_user_limits_summary(user_id)
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"API Error getting limits summary: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Административные роуты

@router.get("/admin/overview", response_class=HTMLResponse, name="admin_limits_overview")
async def admin_limits_overview(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Административный обзор лимитов всех пользователей."""
    try:
        async with get_async_session() as session:
            # Получаем всех пользователей с активными подписками
            from sqlalchemy import select
            from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
            
            query = select(UserSubscription).where(
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
            
            result = await session.execute(query)
            active_subscriptions = list(result.scalars().all())
            
            # Получаем сводки по лимитам для каждого пользователя
            limits_service = LimitsService(session)
            user_limits = []
            
            for subscription in active_subscriptions:
                summary = await limits_service.get_user_limits_summary(subscription.user_id)
                if summary.get("has_subscription"):
                    user_limits.append(summary)
        
        return templates.TemplateResponse("admin/limits_overview.html", {
            "request": request,
            "current_user": current_user,
            "title": "Обзор лимитов пользователей",
            "user_limits": user_limits
        })
        
    except Exception as e:
        logger.error(f"Error loading admin limits overview: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки обзора: {str(e)}")


@router.get("/admin/api/overview", response_class=JSONResponse, name="admin_api_limits_overview")
async def admin_api_limits_overview(
    current_user: dict = Depends(require_superadmin)
):
    """API: Административный обзор лимитов."""
    try:
        async with get_async_session() as session:
            # Получаем всех пользователей с активными подписками
            from sqlalchemy import select
            from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
            
            query = select(UserSubscription).where(
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
            
            result = await session.execute(query)
            active_subscriptions = list(result.scalars().all())
            
            # Получаем сводки по лимитам
            limits_service = LimitsService(session)
            user_limits = []
            
            for subscription in active_subscriptions:
                summary = await limits_service.get_user_limits_summary(subscription.user_id)
                if summary.get("has_subscription"):
                    user_limits.append(summary)
        
        return {
            "success": True,
            "data": user_limits
        }
        
    except Exception as e:
        logger.error(f"API Error getting admin limits overview: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def _get_user_id_from_current_user(current_user: dict) -> Optional[int]:
    """Получение внутреннего user_id из current_user."""
    try:
        if isinstance(current_user, dict):
            # current_user - это словарь из JWT payload
            telegram_id = current_user.get("id")
            if not telegram_id:
                return None
            
            async with get_async_session() as session:
                from sqlalchemy import select
                from domain.entities.user import User
                
                user_query = select(User).where(User.telegram_id == telegram_id)
                user_result = await session.execute(user_query)
                user_obj = user_result.scalar_one_or_none()
                return user_obj.id if user_obj else None
        else:
            # current_user - это объект User
            return current_user.id
            
    except Exception as e:
        logger.error(f"Error getting user_id from current_user: {e}")
        return None
