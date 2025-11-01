"""Роуты для управления подписками владельцев."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.billing_service import BillingService
from apps.web.services.tariff_service import TariffService
from apps.web.services.limits_service import LimitsService
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.billing_transaction import BillingTransaction
from domain.entities.tariff_plan import TariffPlan
from core.logging.logger import logger
from apps.web.routes.owner import get_user_id_from_current_user

router = APIRouter()
from apps.web.jinja import templates


@router.get("/subscription", response_class=HTMLResponse, name="owner_subscription")
async def owner_subscription(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Текущая подписка владельца."""
    try:
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем текущую подписку
        limits_service = LimitsService(db)
        limits_summary = await limits_service.get_user_limits_summary(user_id)
        
        # Получаем последние транзакции
        billing_service = BillingService(db)
        transactions = await billing_service.get_user_transactions(user_id, limit=5)
        
        return templates.TemplateResponse("owner/subscription.html", {
            "request": request,
            "current_user": current_user,
            "title": "Моя подписка",
            "limits_summary": limits_summary,
            "transactions": transactions
        })
        
    except Exception as e:
        logger.error(f"Error loading owner subscription: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки подписки: {str(e)}")


@router.get("/tariffs", response_class=HTMLResponse, name="owner_tariffs")
async def owner_tariffs(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список доступных тарифов для выбора."""
    try:
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем доступные тарифы
        tariff_service = TariffService(db)
        tariff_plans = await tariff_service.get_all_tariff_plans(active_only=True)
        
        # Получаем текущую подписку
        limits_service = LimitsService(db)
        limits_summary = await limits_service.get_user_limits_summary(user_id)
        
        # Загружаем системные функции для отображения названий
        from shared.services.system_features_service import SystemFeaturesService
        features_service = SystemFeaturesService()
        all_features = await features_service.get_all_features(db)
        feature_names_map = {f.key: f.name for f in all_features}
        
        return templates.TemplateResponse("owner/tariffs.html", {
            "request": request,
            "current_user": current_user,
            "title": "Выбор тарифа",
            "tariff_plans": tariff_plans,
            "limits_summary": limits_summary,
            "feature_names": feature_names_map
        })
        
    except Exception as e:
        logger.error(f"Error loading owner tariffs: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки тарифов: {str(e)}")


@router.get("/billing/transactions", response_class=HTMLResponse, name="owner_billing_transactions")
async def owner_billing_transactions(
    request: Request,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """История транзакций владельца."""
    try:
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем транзакции
        billing_service = BillingService(db)
        
        # Применяем фильтр по статусу если указан
        transactions = await billing_service.get_user_transactions(user_id, limit=100)
        
        if status_filter:
            from domain.entities.billing_transaction import TransactionStatus
            try:
                filter_status = TransactionStatus(status_filter)
                transactions = [t for t in transactions if t.status == filter_status]
            except ValueError:
                pass  # Неверный статус, показываем все
        
        return templates.TemplateResponse("owner/billing/transactions.html", {
            "request": request,
            "current_user": current_user,
            "title": "История платежей",
            "transactions": transactions,
            "status_filter": status_filter
        })
        
    except Exception as e:
        logger.error(f"Error loading owner billing transactions: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки транзакций: {str(e)}")


@router.get("/billing/transactions/{transaction_id}", response_class=JSONResponse, name="owner_billing_transaction_detail")
async def owner_billing_transaction_detail(
    transaction_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали транзакции владельца."""
    try:
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем транзакцию
        transaction_result = await db.execute(
            select(BillingTransaction).where(
                BillingTransaction.id == transaction_id,
                BillingTransaction.user_id == user_id
            )
        )
        transaction = transaction_result.scalar_one_or_none()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Транзакция не найдена")
        
        return {
            "success": True,
            "data": transaction.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading transaction detail: {e}", error=str(e), exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/subscription/payment_success", response_class=HTMLResponse, name="owner_payment_success")
async def owner_payment_success(
    request: Request,
    payment_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница после успешной оплаты."""
    try:
        logger.info(
            "Payment success page accessed",
            payment_id=payment_id,
            user_id=current_user.get("id"),
            query_params=dict(request.query_params)
        )
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Проверяем статус платежа если передан payment_id
        payment_status = None
        if payment_id:
            from apps.web.services.payment_gateway.yookassa_service import YooKassaService
            yookassa_service = YooKassaService()
            try:
                payment_status = await yookassa_service.get_payment_status(payment_id)
                logger.info(
                    "Payment status retrieved",
                    payment_id=payment_id,
                    status=payment_status.get("status") if payment_status else None
                )
            except Exception as e:
                logger.error(f"Error getting payment status: {e}", error=str(e), exc_info=True)
        
        # Если payment_id не передан, но есть в query, пытаемся его получить
        if not payment_id:
            payment_id = request.query_params.get("payment_id")
            logger.info(f"Payment ID from query params: {payment_id}")
        
        # Если payment_id все еще нет, пытаемся найти последнюю транзакцию пользователя
        if not payment_id:
            from domain.entities.billing_transaction import BillingTransaction, TransactionStatus
            from sqlalchemy import select, desc
            result = await db.execute(
                select(BillingTransaction)
                .where(
                    BillingTransaction.user_id == user_id,
                    BillingTransaction.status.in_([TransactionStatus.PROCESSING, TransactionStatus.PENDING])
                )
                .order_by(desc(BillingTransaction.created_at))
                .limit(1)
            )
            transaction = result.scalar_one_or_none()
            if transaction and transaction.external_id:
                payment_id = transaction.external_id
                logger.info(f"Found pending transaction with payment_id: {payment_id}")
                
                # Проверяем статус платежа через API YooKassa
                from apps.web.services.payment_gateway.yookassa_service import YooKassaService
                yookassa_service = YooKassaService()
                try:
                    payment_status = await yookassa_service.get_payment_status(payment_id)
                    logger.info(
                        "Payment status retrieved from API",
                        payment_id=payment_id,
                        status=payment_status.get("status") if payment_status else None
                    )
                    
                    # Если платеж успешен, обрабатываем его
                    if payment_status and payment_status.get("status") == "succeeded" and payment_status.get("paid"):
                        billing_service = BillingService(db)
                        await billing_service.process_payment_success(transaction.id, payment_id)
                        logger.info(f"Payment {payment_id} processed successfully via API check")
                except Exception as e:
                    logger.error(f"Error checking payment status via API: {e}", error=str(e), exc_info=True)
        
        return templates.TemplateResponse("owner/payment_success.html", {
            "request": request,
            "current_user": current_user,
            "title": "Оплата завершена",
            "payment_id": payment_id,
            "payment_status": payment_status
        })
        
    except Exception as e:
        logger.error(f"Error loading payment success page: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки страницы: {str(e)}")

