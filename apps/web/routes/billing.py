"""Роуты для системы биллинга."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_superadmin, require_owner_or_superadmin
from apps.web.services.billing_service import BillingService
from domain.entities.billing_transaction import TransactionType, TransactionStatus, PaymentMethod
from domain.entities.payment_notification import NotificationType, NotificationChannel
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse, name="billing_dashboard")
async def billing_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Дашборд биллинга."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            # Получаем статистику транзакций
            # TODO: Добавить агрегированные запросы для статистики
        
        return templates.TemplateResponse("admin/billing_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Система биллинга"
        })
        
    except Exception as e:
        logger.error(f"Error loading billing dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/transactions", response_class=HTMLResponse, name="billing_transactions")
async def billing_transactions(
    request: Request,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_superadmin)
):
    """Список транзакций."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            if user_id:
                transactions = await billing_service.get_user_transactions(user_id, limit=100)
            else:
                # Получаем все транзакции для суперадмина
                from sqlalchemy import select, desc
                from domain.entities.billing_transaction import BillingTransaction
                
                query = select(BillingTransaction).order_by(desc(BillingTransaction.created_at)).limit(100)
                result = await session.execute(query)
                transactions = list(result.scalars().all())
        
        return templates.TemplateResponse("admin/billing_transactions.html", {
            "request": request,
            "current_user": current_user,
            "title": "Транзакции",
            "transactions": transactions,
            "selected_user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Error loading transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки транзакций: {str(e)}")


@router.get("/usage", response_class=HTMLResponse, name="usage_metrics")
async def usage_metrics(
    request: Request,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_superadmin)
):
    """Метрики использования лимитов."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            if user_id:
                limits_info = await billing_service.check_usage_limits(user_id)
                user_limits = [limits_info] if limits_info["has_subscription"] else []
            else:
                # Получаем метрики всех пользователей с активными подписками
                from sqlalchemy import select
                from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
                from domain.entities.usage_metrics import UsageMetrics
                
                query = select(UserSubscription).where(
                    UserSubscription.status == SubscriptionStatus.ACTIVE
                ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
                
                result = await session.execute(query)
                active_subscriptions = list(result.scalars().all())
                
                user_limits = []
                for subscription in active_subscriptions:
                    limits_info = await billing_service.check_usage_limits(subscription.user_id)
                    if limits_info["has_subscription"]:
                        user_limits.append(limits_info)
        
        return templates.TemplateResponse("admin/usage_metrics.html", {
            "request": request,
            "current_user": current_user,
            "title": "Метрики использования",
            "user_limits": user_limits,
            "selected_user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"Error loading usage metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки метрик: {str(e)}")


@router.post("/transactions/{transaction_id}/status", name="update_transaction_status")
async def update_transaction_status(
    request: Request,
    transaction_id: int,
    status: str = Form(...),
    current_user: dict = Depends(require_superadmin)
):
    """Обновление статуса транзакции."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            # Конвертируем строку в enum
            try:
                transaction_status = TransactionStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Неверный статус: {status}")
            
            transaction = await billing_service.update_transaction_status(transaction_id, transaction_status)
            
            if not transaction:
                raise HTTPException(status_code=404, detail="Транзакция не найдена")
        
        return RedirectResponse(url="/admin/billing/transactions", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating transaction status: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления статуса: {str(e)}")


@router.post("/auto-renewal/{user_id}", name="process_auto_renewal")
async def process_auto_renewal(
    request: Request,
    user_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """Обработка автоматического продления подписки."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            transaction = await billing_service.process_auto_renewal(user_id)
            
            if not transaction:
                return JSONResponse({
                    "success": False,
                    "message": "Нет активной подписки с автопродлением или бесплатный тариф"
                })
        
        return JSONResponse({
            "success": True,
            "message": f"Автопродление обработано. Создана транзакция {transaction.id}"
        })
        
    except Exception as e:
        logger.error(f"Error processing auto renewal: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка автопродления: {str(e)}")


# API endpoints для AJAX запросов

@router.get("/api/transactions", response_class=JSONResponse, name="api_transactions")
async def api_transactions(
    user_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_superadmin)
):
    """API: Список транзакций."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            if user_id:
                transactions = await billing_service.get_user_transactions(user_id, limit, offset)
            else:
                from sqlalchemy import select, desc
                from domain.entities.billing_transaction import BillingTransaction
                
                query = select(BillingTransaction).order_by(desc(BillingTransaction.created_at)).limit(limit).offset(offset)
                result = await session.execute(query)
                transactions = list(result.scalars().all())
        
        return {
            "success": True,
            "data": [transaction.to_dict() for transaction in transactions]
        }
        
    except Exception as e:
        logger.error(f"API Error loading transactions: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/usage/{user_id}", response_class=JSONResponse, name="api_user_usage")
async def api_user_usage(
    user_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """API: Метрики использования пользователя."""
    try:
        async with get_async_session() as session:
            billing_service = BillingService(session)
            limits_info = await billing_service.check_usage_limits(user_id)
        
        return {
            "success": True,
            "data": limits_info
        }
        
    except Exception as e:
        logger.error(f"API Error loading user usage: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/notifications", response_class=JSONResponse, name="api_notifications")
async def api_notifications(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(require_superadmin)
):
    """API: Список уведомлений о платежах."""
    try:
        async with get_async_session() as session:
            from sqlalchemy import select, desc
            from domain.entities.payment_notification import PaymentNotification, NotificationStatus
            
            query = select(PaymentNotification).order_by(desc(PaymentNotification.created_at))
            
            if user_id:
                query = query.where(PaymentNotification.user_id == user_id)
            
            if status:
                try:
                    notification_status = NotificationStatus(status)
                    query = query.where(PaymentNotification.status == notification_status)
                except ValueError:
                    pass
            
            query = query.limit(100)
            result = await session.execute(query)
            notifications = list(result.scalars().all())
        
        return {
            "success": True,
            "data": [notification.to_dict() for notification in notifications]
        }
        
    except Exception as e:
        logger.error(f"API Error loading notifications: {e}")
        return {
            "success": False,
            "error": str(e)
        }
