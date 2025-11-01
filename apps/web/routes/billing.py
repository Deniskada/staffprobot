"""Роуты для системы биллинга."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from core.database.session import get_async_session, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from apps.web.middleware.auth_middleware import require_superadmin, require_owner_or_superadmin
from apps.web.services.billing_service import BillingService
from domain.entities.billing_transaction import TransactionType, TransactionStatus, PaymentMethod
from domain.entities.payment_notification import NotificationType, NotificationChannel
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse, name="billing_dashboard")
async def billing_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Дашборд биллинга."""
    try:
        from sqlalchemy import select, func
        from domain.entities.billing_transaction import BillingTransaction, TransactionStatus
        from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
        
        billing_service = BillingService(session)
        
        # Статистика транзакций
        total_transactions_result = await session.execute(
            select(func.count(BillingTransaction.id))
        )
        total_transactions = total_transactions_result.scalar() or 0
        
        # Общая выручка (сумма COMPLETED транзакций)
        total_revenue_result = await session.execute(
            select(func.sum(BillingTransaction.amount)).where(
                BillingTransaction.status == TransactionStatus.COMPLETED
            )
        )
        total_revenue = float(total_revenue_result.scalar() or 0)
        
        # Количество активных подписок
        active_subscriptions_result = await session.execute(
            select(func.count(UserSubscription.id)).where(
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        active_subscriptions = active_subscriptions_result.scalar() or 0
        
        # Количество ожидающих платежей (PENDING)
        pending_payments_result = await session.execute(
            select(func.count(BillingTransaction.id)).where(
                BillingTransaction.status == TransactionStatus.PENDING
            )
        )
        pending_payments = pending_payments_result.scalar() or 0
        
        statistics = {
            "total_transactions": total_transactions,
            "total_revenue": total_revenue,
            "active_subscriptions": active_subscriptions,
            "pending_payments": pending_payments
        }
        
        return templates.TemplateResponse("admin/billing_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Система биллинга",
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"Error loading billing dashboard: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/transactions", response_class=HTMLResponse, name="billing_transactions")
async def billing_transactions(
    request: Request,
    user_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Список транзакций с сортировкой и фильтрацией."""
    try:
        from sqlalchemy import select, desc, asc, and_, func
        from domain.entities.billing_transaction import BillingTransaction, TransactionStatus, TransactionType
        from sqlalchemy.orm import selectinload
        
        # Базовый запрос
        query = select(BillingTransaction)
        
        # Фильтры
        filters = []
        if user_id:
            filters.append(BillingTransaction.user_id == user_id)
        if status:
            try:
                filters.append(BillingTransaction.status == TransactionStatus(status))
            except ValueError:
                pass
        if transaction_type:
            try:
                filters.append(BillingTransaction.transaction_type == TransactionType(transaction_type))
            except ValueError:
                pass
        
        if filters:
            query = query.where(and_(*filters))
        
        # Сортировка
        sort_column = getattr(BillingTransaction, sort_by, BillingTransaction.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Подсчет общего количества
        count_query = select(func.count(BillingTransaction.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Пагинация
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Выполняем запрос
        result = await session.execute(query)
        transactions = list(result.scalars().all())
        
        # Подсчет страниц
        total_pages = (total_count + per_page - 1) // per_page
        
        return templates.TemplateResponse("admin/billing_transactions.html", {
            "request": request,
            "current_user": current_user,
            "title": "Транзакции",
            "transactions": transactions,
            "selected_user_id": user_id,
            "selected_status": status,
            "selected_transaction_type": transaction_type,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages,
            "now": datetime.now(timezone.utc)
        })
        
    except Exception as e:
        logger.error(f"Error loading transactions: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки транзакций: {str(e)}")


@router.get("/usage", response_class=HTMLResponse, name="usage_metrics")
async def usage_metrics(
    request: Request,
    user_id: Optional[int] = None,
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Метрики использования лимитов."""
    try:
        from sqlalchemy.orm import selectinload
        
        billing_service = BillingService(session)
        
        if user_id:
            limits_info = await billing_service.check_usage_limits(user_id)
            user_limits = [limits_info] if limits_info["has_subscription"] else []
        else:
            # Получаем метрики всех пользователей с активными подписками
            from sqlalchemy import select
            from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
            
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
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Обновление статуса транзакции."""
    try:
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


@router.post("/transactions/{transaction_id}/check", response_class=JSONResponse, name="check_transaction_payment")
async def check_transaction_payment(
    transaction_id: int,
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Проверка статуса платежа через API YooKassa и обновление транзакции."""
    try:
        from sqlalchemy import select
        from domain.entities.billing_transaction import BillingTransaction
        
        # Получаем транзакцию
        result = await session.execute(
            select(BillingTransaction).where(BillingTransaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()
        
        if not transaction:
            return JSONResponse({
                "success": False,
                "error": "Транзакция не найдена"
            }, status_code=404)
        
        if not transaction.external_id:
            return JSONResponse({
                "success": False,
                "error": "У транзакции нет внешнего ID платежа"
            })
        
        # Проверяем статус через YooKassa API
        from apps.web.services.payment_gateway.yookassa_service import YooKassaService
        yookassa_service = YooKassaService()
        
        try:
            payment_status = await yookassa_service.get_payment_status(transaction.external_id)
            
            logger.info(
                "Payment status checked via API",
                transaction_id=transaction_id,
                payment_id=transaction.external_id,
                status=payment_status.get("status") if payment_status else None
            )
            
            # Если платеж успешен - обрабатываем его
            if payment_status and payment_status.get("status") == "succeeded" and payment_status.get("paid"):
                billing_service = BillingService(session)
                await billing_service.process_payment_success(transaction_id, transaction.external_id)
                
                return JSONResponse({
                    "success": True,
                    "message": "Платеж успешно обработан",
                    "payment_status": payment_status
                })
            elif payment_status and payment_status.get("status") == "canceled":
                billing_service = BillingService(session)
                await billing_service.update_transaction_status(
                    transaction_id,
                    TransactionStatus.CANCELLED
                )
                
                return JSONResponse({
                    "success": True,
                    "message": "Платеж отменен",
                    "payment_status": payment_status
                })
            else:
                return JSONResponse({
                    "success": True,
                    "message": f"Статус платежа: {payment_status.get('status') if payment_status else 'неизвестен'}",
                    "payment_status": payment_status,
                    "transaction_status": transaction.status.value
                })
                
        except Exception as e:
            logger.error(f"Error checking payment status: {e}", error=str(e), exc_info=True)
            return JSONResponse({
                "success": False,
                "error": f"Ошибка проверки статуса платежа: {str(e)}"
            })
        
    except Exception as e:
        logger.error(f"Error checking transaction payment: {e}", error=str(e), exc_info=True)
        return JSONResponse({
            "success": False,
            "error": f"Ошибка проверки транзакции: {str(e)}"
        })


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
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """API: Список уведомлений о платежах."""
    try:
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


@router.get("/api/tariff-distribution", response_class=JSONResponse, name="api_tariff_distribution")
async def api_tariff_distribution(
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """API: Распределение подписок по тарифам."""
    try:
        from sqlalchemy import select, func
        from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
        from domain.entities.tariff_plan import TariffPlan
        from sqlalchemy.orm import selectinload
        
        # Получаем активные подписки с тарифами
        query = select(UserSubscription).where(
            UserSubscription.status == SubscriptionStatus.ACTIVE
        ).options(selectinload(UserSubscription.tariff_plan))
        
        result = await session.execute(query)
        subscriptions = list(result.scalars().all())
        
        # Подсчитываем распределение
        distribution = {}
        for subscription in subscriptions:
            tariff_name = subscription.tariff_plan.name if subscription.tariff_plan else "Неизвестный тариф"
            distribution[tariff_name] = distribution.get(tariff_name, 0) + 1
        
        return {
            "success": True,
            "distribution": distribution,
            "total": len(subscriptions)
        }
        
    except Exception as e:
        logger.error(f"API Error loading tariff distribution: {e}")
        return {
            "success": False,
            "error": str(e)
        }
