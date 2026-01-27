"""Роуты для управления подписками пользователей."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_async_session, get_db_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.tariff_service import TariffService
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse, name="user_subscriptions_list")
async def user_subscriptions_list(
    request: Request,
    user_id: Optional[str] = Query(None, description="ID пользователя"),
    status: Optional[str] = Query(None),
    tariff_id: Optional[str] = Query(None, description="ID тарифа"),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Список подписок пользователей с сортировкой и фильтрацией."""
    try:
        tariff_service = TariffService(session)
        
        # Получаем все подписки с информацией о пользователях и тарифах
        from sqlalchemy import select, desc, asc, and_, func
        from sqlalchemy.orm import selectinload
        from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
        from domain.entities.user import User
        from domain.entities.tariff_plan import TariffPlan
        
        # Базовый запрос
        query = select(UserSubscription).options(
            selectinload(UserSubscription.user),
            selectinload(UserSubscription.tariff_plan)
        )
        
        # Фильтры
        filters = []
        # Обрабатываем пустые строки и None как отсутствие фильтра
        if user_id and user_id.strip():
            try:
                user_id_int = int(user_id.strip())
                filters.append(UserSubscription.user_id == user_id_int)
            except (ValueError, TypeError):
                pass
        if status and status.strip():
            try:
                filters.append(UserSubscription.status == SubscriptionStatus(status.strip()))
            except ValueError:
                pass
        if tariff_id and tariff_id.strip():
            try:
                tariff_id_int = int(tariff_id.strip())
                filters.append(UserSubscription.tariff_plan_id == tariff_id_int)
            except (ValueError, TypeError):
                pass
        
        if filters:
            query = query.where(and_(*filters))
        
        # Сортировка
        sort_column = getattr(UserSubscription, sort_by, UserSubscription.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))
        
        # Подсчет общего количества
        count_query = select(func.count(UserSubscription.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = await session.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Пагинация
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Выполняем запрос
        result = await session.execute(query)
        subscriptions = list(result.scalars().all())
        
        # Подсчет страниц
        total_pages = (total_count + per_page - 1) // per_page
        
        # Статистика
        statistics = await tariff_service.get_tariff_statistics()
        
        # Получаем список тарифов для фильтра
        tariff_plans = await tariff_service.get_all_tariff_plans(active_only=False)
        
        return templates.TemplateResponse("admin/user_subscriptions.html", {
            "request": request,
            "current_user": current_user,
            "title": "Управление подписками пользователей",
            "subscriptions": subscriptions,
            "statistics": statistics,
            "tariff_plans": tariff_plans,
            "selected_user_id": int(user_id.strip()) if user_id and user_id.strip() else None,
            "selected_status": status,
            "selected_tariff_id": int(tariff_id.strip()) if tariff_id and tariff_id.strip() else None,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": total_pages
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
            has_active_subscription = False
            if user_id:
                from sqlalchemy import select
                from domain.entities.user import User
                from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
                
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                selected_user = result.scalar_one_or_none()
                
                # Проверяем наличие активной подписки (для определения, можно ли дать grace period)
                if selected_user:
                    subscription_result = await session.execute(
                        select(UserSubscription).where(
                            UserSubscription.user_id == user_id,
                            UserSubscription.status == SubscriptionStatus.ACTIVE
                        )
                    )
                    has_active_subscription = subscription_result.scalar_one_or_none() is not None
        
        return templates.TemplateResponse("admin/assign_subscription.html", {
            "request": request,
            "current_user": current_user,
            "title": "Назначение подписки пользователю",
            "tariff_plans": tariff_plans,
            "selected_user": selected_user,
            "user_id": user_id,
            "has_active_subscription": has_active_subscription
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
    is_paid: Optional[str] = Form(None),
    grace_period_days: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Назначение подписки пользователю.
    
    Если тариф платный и is_paid=False, создаст транзакцию со статусом PENDING.
    Если тариф платный и is_paid=True, создаст транзакцию со статусом COMPLETED (админ оплатил вручную).
    Если тариф бесплатный, создаст подписку напрямую.
    """
    try:
        from sqlalchemy import select
        from domain.entities.user import User
        from domain.entities.tariff_plan import TariffPlan
        from domain.entities.billing_transaction import BillingTransaction, TransactionType, TransactionStatus, PaymentMethod as BillingPaymentMethod
        from datetime import datetime, timedelta, timezone
        
        # Проверяем, что пользователь существует
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Получаем тарифный план
        tariff_result = await session.execute(
            select(TariffPlan).where(TariffPlan.id == tariff_plan_id)
        )
        tariff_plan = tariff_result.scalar_one_or_none()
        
        if not tariff_plan:
            raise HTTPException(status_code=404, detail="Тарифный план не найден")
        
        tariff_service = TariffService(session)
        
        # Проверяем, есть ли у пользователя активная подписка (для определения, можно ли дать grace period)
        from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
        existing_subscription_result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        has_active_subscription = existing_subscription_result.scalar_one_or_none() is not None
        
        # Если указан grace period и у пользователя нет активной подписки - создаем подписку с grace period
        if grace_period_days and grace_period_days > 0 and not has_active_subscription:
            # Grace period: создаем подписку без требования оплаты на указанное количество дней
            expires_at = datetime.now(timezone.utc) + timedelta(days=grace_period_days)
            
            # Создаем подписку со статусом ACTIVE и expires_at на grace_period_days дней
            subscription = await tariff_service.create_user_subscription(
                user_id=user_id,
                tariff_plan_id=tariff_plan_id,
                payment_method=payment_method,
                notes=(notes or "") + f" | Grace period: {grace_period_days} дней"
            )
            
            # Устанавливаем expires_at на grace_period_days дней
            subscription.expires_at = expires_at
            subscription.status = SubscriptionStatus.ACTIVE
            await session.commit()
            
            logger.info(
                f"Assigned subscription with grace period {subscription.id} to user {user_id} on tariff {tariff_plan_id}",
                subscription_id=subscription.id,
                grace_period_days=grace_period_days,
                expires_at=expires_at
            )
            
            return RedirectResponse(url="/admin/subscriptions/", status_code=status.HTTP_302_FOUND)
        
        # Обычная логика назначения подписки
        # Определяем срок действия подписки
        if tariff_plan.billing_period == "month":
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        elif tariff_plan.billing_period == "year":
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        else:
            expires_at = None
        
        # Если тариф платный
        if tariff_plan.price and float(tariff_plan.price) > 0:
            # Создаем подписку
            subscription = await tariff_service.create_user_subscription(
                user_id=user_id,
                tariff_plan_id=tariff_plan_id,
                payment_method=payment_method,
                notes=notes or "Назначена админом"
            )
            subscription.tariff_plan = tariff_plan

            from apps.web.services.billing_service import BillingService
            billing_service = BillingService(session)
            amount = await billing_service.compute_subscription_amount(
                user_id, subscription, tariff_plan
            )

            # Обрабатываем чекбокс is_paid (может быть строкой "true" или отсутствовать)
            is_paid_bool = is_paid == "true" or is_paid is True

            if is_paid_bool:
                # Админ отметил как оплаченную - создаем транзакцию со статусом COMPLETED
                transaction = await billing_service.create_transaction(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    transaction_type=TransactionType.PAYMENT,
                    amount=amount,
                    currency=tariff_plan.currency or "RUB",
                    payment_method=BillingPaymentMethod.MANUAL,
                    description=f"Оплата подписки на тариф '{tariff_plan.name}' (оплачено админом)",
                    external_id=f"admin_manual_{subscription.id}",
                    expires_at=None
                )
                
                # Обновляем статус на COMPLETED
                await billing_service.update_transaction_status(
                    transaction.id,
                    TransactionStatus.COMPLETED
                )
                
                # Обновляем подписку (продлеваем срок)
                subscription.expires_at = expires_at
                subscription.last_payment_at = datetime.now(timezone.utc)
                await session.commit()
                
                logger.info(
                    f"Assigned paid subscription {subscription.id} to user {user_id} on tariff {tariff_plan_id} (paid by admin)",
                    subscription_id=subscription.id,
                    transaction_id=transaction.id
                )
            else:
                # Админ НЕ отметил как оплаченную - создаем транзакцию со статусом PENDING
                # Владелец должен будет оплатить сам
                transaction = await billing_service.create_transaction(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    transaction_type=TransactionType.PAYMENT,
                    amount=amount,
                    currency=tariff_plan.currency or "RUB",
                    payment_method=BillingPaymentMethod.MANUAL,
                    description=f"Оплата подписки на тариф '{tariff_plan.name}' (требует оплаты)",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7)
                )
                
                # Подписка создается, но expires_at не устанавливается до оплаты
                # Подписка остается ACTIVE, но требует оплаты (expires_at будет установлен после оплаты)
                # Статус подписки остается ACTIVE, статус транзакции PENDING
                await session.commit()
                
                logger.info(
                    f"Assigned pending subscription {subscription.id} to user {user_id} on tariff {tariff_plan_id} (requires payment)",
                    subscription_id=subscription.id,
                    transaction_id=transaction.id
                )
        else:
            # Бесплатный тариф - создаем подписку напрямую
            subscription = await tariff_service.create_user_subscription(
                user_id=user_id,
                tariff_plan_id=tariff_plan_id,
                payment_method=payment_method,
                notes=notes or "Назначена админом (бесплатный тариф)"
            )
            
            # Обновляем expires_at для бесплатного тарифа
            subscription.expires_at = expires_at
            await session.commit()
            
            logger.info(
                f"Assigned free subscription {subscription.id} to user {user_id} on tariff {tariff_plan_id}",
                subscription_id=subscription.id
            )
        
        return RedirectResponse(url="/admin/subscriptions/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning subscription: {e}", error=str(e), exc_info=True)
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


@router.get("/{subscription_id}/logs", response_class=HTMLResponse, name="subscription_logs")
async def subscription_logs(
    request: Request,
    subscription_id: int,
    current_user: dict = Depends(require_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Просмотр логов изменений тарифа и опций подписки."""
    try:
        from sqlalchemy import select, desc
        from sqlalchemy.orm import selectinload
        from domain.entities.user_subscription import UserSubscription
        from domain.entities.subscription_option_log import SubscriptionOptionLog
        from domain.entities.tariff_plan import TariffPlan
        
        # Получаем подписку
        subscription_result = await session.execute(
            select(UserSubscription)
            .options(
                selectinload(UserSubscription.user),
                selectinload(UserSubscription.tariff_plan)
            )
            .where(UserSubscription.id == subscription_id)
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise HTTPException(status_code=404, detail="Подписка не найдена")
        
        # Получаем логи изменений
        logs_result = await session.execute(
            select(SubscriptionOptionLog)
            .where(SubscriptionOptionLog.subscription_id == subscription_id)
            .order_by(desc(SubscriptionOptionLog.changed_at))
        )
        logs = list(logs_result.scalars().all())
        
        # Получаем информацию о тарифах для отображения
        tariff_ids = set()
        for log in logs:
            if log.old_tariff_id:
                tariff_ids.add(log.old_tariff_id)
            if log.new_tariff_id:
                tariff_ids.add(log.new_tariff_id)
        
        tariffs_map = {}
        if tariff_ids:
            tariffs_result = await session.execute(
                select(TariffPlan).where(TariffPlan.id.in_(tariff_ids))
            )
            for tariff in tariffs_result.scalars().all():
                tariffs_map[tariff.id] = tariff
        
        # Получаем маппинг названий опций
        from core.config.features import SYSTEM_FEATURES_REGISTRY
        
        # Формируем данные для шаблона
        logs_data = []
        for log in logs:
            # Преобразуем ключи опций в человекочитаемые названия
            options_enabled_names = []
            for option_key in (log.options_enabled or []):
                feature = SYSTEM_FEATURES_REGISTRY.get(option_key)
                options_enabled_names.append({
                    "key": option_key,
                    "name": feature.get("name", option_key) if feature else option_key
                })
            
            options_disabled_names = []
            for option_key in (log.options_disabled or []):
                feature = SYSTEM_FEATURES_REGISTRY.get(option_key)
                options_disabled_names.append({
                    "key": option_key,
                    "name": feature.get("name", option_key) if feature else option_key
                })
            
            log_data = {
                "id": log.id,
                "changed_at": log.changed_at,
                "old_tariff": tariffs_map.get(log.old_tariff_id) if log.old_tariff_id else None,
                "new_tariff": tariffs_map.get(log.new_tariff_id) if log.new_tariff_id else None,
                "options_enabled": options_enabled_names,
                "options_disabled": options_disabled_names,
            }
            logs_data.append(log_data)
        
        return templates.TemplateResponse("admin/subscription_logs.html", {
            "request": request,
            "current_user": current_user,
            "title": f"Логи подписки #{subscription.id}",
            "subscription": subscription,
            "logs": logs_data,
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading subscription logs: {e}", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки логов: {str(e)}")
