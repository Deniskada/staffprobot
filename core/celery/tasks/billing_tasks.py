"""Celery задачи для биллинга и автоматического продления подписок."""

from datetime import datetime, timedelta, timezone, date
from typing import List, Optional
from sqlalchemy import select, and_, cast, String
from sqlalchemy.orm import selectinload

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.billing_transaction import BillingTransaction, TransactionStatus
from domain.entities.notification import Notification, NotificationType, NotificationChannel
from apps.web.services.billing_service import BillingService
from apps.web.services.payment_gateway.yookassa_service import YooKassaService
from core.logging.logger import logger
from core.utils.url_helper import URLHelper


@celery_app.task(name="check-expiring-subscriptions")
def check_expiring_subscriptions():
    """
    Проверка подписок, истекающих в ближайшее время.
    Запускается ежедневно в 09:00 UTC.
    
    Выполняет:
    1. Находит подписки, истекающие через 7 и 1 день
    2. Создает уведомления SUBSCRIPTION_EXPIRING
    3. Для подписок с auto_renewal=True создает транзакцию и платеж через YooKassa
    """
    async def _check_expiring_subscriptions_async():
        async with get_async_session() as session:
            billing_service = BillingService(session)
            
            # Получаем сегодняшнюю дату
            today = date.today()
            
            # Даты истечения: через 7 дней и через 1 день
            expires_7_days = datetime.combine(today + timedelta(days=7), datetime.min.time())
            expires_1_day = datetime.combine(today + timedelta(days=1), datetime.min.time())
            
            # Ищем подписки, истекающие через 7 дней
            query_7_days = select(UserSubscription).where(
                and_(
                    UserSubscription.status == SubscriptionStatus.ACTIVE,
                    UserSubscription.expires_at.isnot(None),
                    UserSubscription.expires_at >= expires_7_days.replace(tzinfo=timezone.utc),
                    UserSubscription.expires_at < (expires_7_days + timedelta(days=1)).replace(tzinfo=timezone.utc)
                )
            ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
            
            result_7_days = await session.execute(query_7_days)
            subscriptions_7_days = result_7_days.scalars().all()
            
            # Ищем подписки, истекающие через 1 день
            query_1_day = select(UserSubscription).where(
                and_(
                    UserSubscription.status == SubscriptionStatus.ACTIVE,
                    UserSubscription.expires_at.isnot(None),
                    UserSubscription.expires_at >= expires_1_day.replace(tzinfo=timezone.utc),
                    UserSubscription.expires_at < (expires_1_day + timedelta(days=1)).replace(tzinfo=timezone.utc)
                )
            ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
            
            result_1_day = await session.execute(query_1_day)
            subscriptions_1_day = result_1_day.scalars().all()
            
            notifications_created = 0
            payments_created = 0
            
            # Обрабатываем подписки, истекающие через 7 дней
            for subscription in subscriptions_7_days:
                try:
                    # Проверяем, было ли уже уведомление
                    existing_notification = await session.execute(
                        select(Notification).where(
                            and_(
                                Notification.user_id == subscription.user_id,
                                Notification.type == NotificationType.SUBSCRIPTION_EXPIRING,
                                cast(Notification.data['subscription_id'], String) == str(subscription.id)
                            )
                        ).limit(1)
                    )
                    if existing_notification.scalar_one_or_none():
                        continue
                    
                    # Создаем уведомление
                    notification = Notification(
                        user_id=subscription.user_id,
                        type=NotificationType.SUBSCRIPTION_EXPIRING,
                        channel=NotificationChannel.TELEGRAM,
                        status="pending",
                        title="Подписка скоро истекает",
                        message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' истекает через 7 дней. Продлите подписку, чтобы не потерять доступ к функциям.",
                        data={"subscription_id": subscription.id, "days_left": 7}
                    )
                    session.add(notification)
                    notifications_created += 1
                    
                    # Если включено автопродление и тариф платный, создаем платеж
                    if subscription.auto_renewal and subscription.tariff_plan.price and float(subscription.tariff_plan.price) > 0:
                        try:
                            return_url = await URLHelper.build_url("/owner/subscription/payment_success")
                            result = await billing_service.process_auto_renewal(
                                subscription.user_id,
                                return_url=return_url
                            )
                            
                            if result and len(result) == 2:
                                transaction, payment_url = result
                                if transaction:
                                    payments_created += 1
                                    logger.info(
                                        f"Created auto renewal payment for subscription {subscription.id}",
                                        subscription_id=subscription.id,
                                        transaction_id=transaction.id,
                                        payment_url=payment_url
                                    )
                        except Exception as e:
                            logger.error(
                                f"Error creating auto renewal payment for subscription {subscription.id}: {e}",
                                error=str(e),
                                subscription_id=subscription.id
                            )
                    
                except Exception as e:
                    logger.error(
                        f"Error processing subscription {subscription.id}: {e}",
                        error=str(e),
                        subscription_id=subscription.id
                    )
            
            # Обрабатываем подписки, истекающие через 1 день
            for subscription in subscriptions_1_day:
                try:
                    # Проверяем, было ли уже уведомление
                    existing_notification = await session.execute(
                        select(Notification).where(
                            and_(
                                Notification.user_id == subscription.user_id,
                                Notification.type == NotificationType.SUBSCRIPTION_EXPIRING,
                                cast(Notification.data['subscription_id'], String) == str(subscription.id)
                            )
                        ).limit(1)
                    )
                    if existing_notification.scalar_one_or_none():
                        continue
                    
                    # Создаем уведомление
                    notification = Notification(
                        user_id=subscription.user_id,
                        type=NotificationType.SUBSCRIPTION_EXPIRING,
                        channel=NotificationChannel.TELEGRAM,
                        status="pending",
                        title="Подписка истекает завтра",
                        message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' истекает завтра! Срочно продлите подписку.",
                        data={"subscription_id": subscription.id, "days_left": 1}
                    )
                    session.add(notification)
                    notifications_created += 1
                    
                    # Если включено автопродление и тариф платный, создаем платеж
                    if subscription.auto_renewal and subscription.tariff_plan.price and float(subscription.tariff_plan.price) > 0:
                        try:
                            return_url = await URLHelper.build_url("/owner/subscription/payment_success")
                            transaction, payment_url = await billing_service.process_auto_renewal(
                                subscription.user_id,
                                return_url=return_url
                            )
                            
                            if transaction and payment_url:
                                payments_created += 1
                                logger.info(
                                    f"Created urgent auto renewal payment for subscription {subscription.id}",
                                    subscription_id=subscription.id,
                                    transaction_id=transaction.id
                                )
                        except Exception as e:
                            logger.error(
                                f"Error creating urgent auto renewal payment for subscription {subscription.id}: {e}",
                                error=str(e),
                                subscription_id=subscription.id
                            )
                    
                except Exception as e:
                    logger.error(
                        f"Error processing subscription {subscription.id}: {e}",
                        error=str(e),
                        subscription_id=subscription.id
                    )
            
            await session.commit()
            
            logger.info(
                f"Checked expiring subscriptions",
                notifications_created=notifications_created,
                payments_created=payments_created
            )
            
            return {
                "notifications_created": notifications_created,
                "payments_created": payments_created
            }
    
    # Запускаем асинхронную функцию
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_check_expiring_subscriptions_async())


@celery_app.task(name="check-expired-subscriptions")
def check_expired_subscriptions():
    """
    Проверка истёкших подписок.
    Запускается ежедневно в 00:05 UTC.
    
    Выполняет:
    1. Находит истёкшие подписки
    2. Обновляет статус на EXPIRED
    3. Создает уведомление SUBSCRIPTION_EXPIRED
    """
    async def _check_expired_subscriptions_async():
        async with get_async_session() as session:
            # Получаем текущее время в UTC
            now = datetime.now(timezone.utc)
            
            # Ищем активные подписки, у которых истёк срок
            query = select(UserSubscription).where(
                and_(
                    UserSubscription.status == SubscriptionStatus.ACTIVE,
                    UserSubscription.expires_at.isnot(None),
                    UserSubscription.expires_at < now
                )
            ).options(selectinload(UserSubscription.user), selectinload(UserSubscription.tariff_plan))
            
            result = await session.execute(query)
            expired_subscriptions = result.scalars().all()
            
            expired_count = 0
            notifications_created = 0
            
            for subscription in expired_subscriptions:
                try:
                    # Обновляем статус подписки
                    subscription.status = SubscriptionStatus.EXPIRED
                    expired_count += 1
                    
                    # Создаем уведомление
                    notification = Notification(
                        user_id=subscription.user_id,
                        type=NotificationType.SUBSCRIPTION_EXPIRED,
                        channel=NotificationChannel.TELEGRAM,
                        status="pending",
                        title="Подписка истекла",
                        message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' истекла. Продлите подписку, чтобы восстановить доступ к функциям.",
                        data={"subscription_id": subscription.id}
                    )
                    session.add(notification)
                    notifications_created += 1
                    
                    logger.info(
                        f"Expired subscription {subscription.id}",
                        subscription_id=subscription.id,
                        user_id=subscription.user_id
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error processing expired subscription {subscription.id}: {e}",
                        error=str(e),
                        subscription_id=subscription.id
                    )
            
            await session.commit()
            
            logger.info(
                f"Checked expired subscriptions",
                expired_count=expired_count,
                notifications_created=notifications_created
            )
            
            return {
                "expired_count": expired_count,
                "notifications_created": notifications_created
            }
    
    # Запускаем асинхронную функцию
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_check_expired_subscriptions_async())


@celery_app.task(name="activate-scheduled-subscriptions")
def activate_scheduled_subscriptions():
    """Активация подписок с отложенным стартом (когда наступает их started_at)."""
    async def _activate_scheduled_subscriptions_async():
        async with get_async_session() as session:
            try:
                now = datetime.now(timezone.utc)
                
                # Находим подписки со статусом SUSPENDED, которые должны активироваться сейчас
                result = await session.execute(
                    select(UserSubscription).where(
                        UserSubscription.status == SubscriptionStatus.SUSPENDED,
                        UserSubscription.started_at <= now
                    ).options(
                        selectinload(UserSubscription.tariff_plan)
                    )
                )
                subscriptions = result.scalars().all()
                
                activated_count = 0
                for subscription in subscriptions:
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.updated_at = now
                    
                    await session.commit()
                    
                    logger.info(
                        f"Activated scheduled subscription",
                        subscription_id=subscription.id,
                        user_id=subscription.user_id,
                        started_at=subscription.started_at,
                        expires_at=subscription.expires_at
                    )
                    
                    activated_count += 1
                
                if activated_count > 0:
                    logger.info(
                        f"Activated scheduled subscriptions",
                        count=activated_count
                    )
                
                return {"activated": activated_count, "processed": len(subscriptions)}
                
            except Exception as e:
                logger.error(
                    f"Error activating scheduled subscriptions: {e}",
                    error=str(e)
                )
                await session.rollback()
                raise
    
    # Запускаем асинхронную функцию
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(_activate_scheduled_subscriptions_async())

