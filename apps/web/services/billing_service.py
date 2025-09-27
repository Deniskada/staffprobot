"""Сервис для работы с биллингом и платежами."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
import json

from domain.entities.billing_transaction import BillingTransaction, TransactionType, TransactionStatus, PaymentMethod
from domain.entities.usage_metrics import UsageMetrics
from domain.entities.payment_notification import PaymentNotification, NotificationType, NotificationStatus, NotificationChannel
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from core.logging.logger import logger


class BillingService:
    """Сервис для работы с биллингом."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # === Транзакции ===
    
    async def create_transaction(
        self,
        user_id: int,
        transaction_type: TransactionType,
        amount: float,
        currency: str = "RUB",
        subscription_id: Optional[int] = None,
        payment_method: Optional[PaymentMethod] = None,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> BillingTransaction:
        """Создание новой транзакции."""
        transaction = BillingTransaction(
            user_id=user_id,
            subscription_id=subscription_id,
            transaction_type=transaction_type,
            status=TransactionStatus.PENDING,
            amount=amount,
            currency=currency,
            payment_method=payment_method,
            description=description,
            external_id=external_id,
            expires_at=expires_at
        )
        
        self.session.add(transaction)
        await self.session.commit()
        await self.session.refresh(transaction)
        
        logger.info(f"Created transaction {transaction.id} for user {user_id}: {amount} {currency}")
        return transaction
    
    async def update_transaction_status(
        self,
        transaction_id: int,
        status: TransactionStatus,
        gateway_response: Optional[str] = None
    ) -> Optional[BillingTransaction]:
        """Обновление статуса транзакции."""
        transaction = await self.session.get(BillingTransaction, transaction_id)
        if not transaction:
            return None
        
        transaction.status = status
        if gateway_response:
            transaction.gateway_response = gateway_response
        
        if status in [TransactionStatus.COMPLETED, TransactionStatus.FAILED, TransactionStatus.CANCELLED]:
            transaction.processed_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(transaction)
        
        logger.info(f"Updated transaction {transaction_id} status to {status.value}")
        return transaction
    
    async def get_user_transactions(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[BillingTransaction]:
        """Получение транзакций пользователя."""
        query = select(BillingTransaction).where(
            BillingTransaction.user_id == user_id
        ).order_by(desc(BillingTransaction.created_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # === Метрики использования ===
    
    async def update_usage_metrics(self, user_id: int, subscription_id: int) -> UsageMetrics:
        """Обновление метрик использования для пользователя."""
        # Получаем текущую подписку
        subscription_result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.id == subscription_id,
                UserSubscription.user_id == user_id
            ).options(selectinload(UserSubscription.tariff_plan))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found for user {user_id}")
        
        # Считаем текущее использование
        objects_count_result = await self.session.execute(
            select(func.count(Object.id)).where(Object.owner_id == user_id)
        )
        objects_count = objects_count_result.scalar() or 0
        
        employees_count_result = await self.session.execute(
            select(func.count(Contract.id.distinct())).join(Object).where(Object.owner_id == user_id)
        )
        employees_count = employees_count_result.scalar() or 0
        
        # Получаем или создаем метрики
        metrics_result = await self.session.execute(
            select(UsageMetrics).where(
                UsageMetrics.user_id == user_id,
                UsageMetrics.subscription_id == subscription_id
            ).order_by(desc(UsageMetrics.created_at))
        )
        metrics = metrics_result.scalar_one_or_none()
        
        if not metrics:
            # Создаем новые метрики
            period_start = subscription.started_at or datetime.now(timezone.utc)
            period_end = subscription.expires_at or (datetime.now(timezone.utc) + timedelta(days=30))
            
            metrics = UsageMetrics(
                user_id=user_id,
                subscription_id=subscription_id,
                max_objects=subscription.tariff_plan.max_objects,
                max_employees=subscription.tariff_plan.max_employees,
                max_managers=subscription.tariff_plan.max_managers,
                current_objects=objects_count,
                current_employees=employees_count,
                current_managers=0,  # TODO: Реализовать подсчет управляющих
                period_start=period_start,
                period_end=period_end
            )
            self.session.add(metrics)
        else:
            # Обновляем существующие метрики
            metrics.current_objects = objects_count
            metrics.current_employees = employees_count
            metrics.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        await self.session.refresh(metrics)
        
        logger.info(f"Updated usage metrics for user {user_id}: {objects_count}/{metrics.max_objects} objects, {employees_count}/{metrics.max_employees} employees")
        return metrics
    
    async def check_usage_limits(self, user_id: int) -> Dict[str, Any]:
        """Проверка лимитов использования пользователя."""
        # Получаем активную подписку
        subscription_result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(selectinload(UserSubscription.tariff_plan))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            return {
                "has_subscription": False,
                "limits": {},
                "usage": {},
                "warnings": []
            }
        
        # Получаем последние метрики
        metrics_result = await self.session.execute(
            select(UsageMetrics).where(
                UsageMetrics.user_id == user_id,
                UsageMetrics.subscription_id == subscription.id
            ).order_by(desc(UsageMetrics.created_at))
        )
        metrics = metrics_result.scalar_one_or_none()
        
        if not metrics:
            # Обновляем метрики
            metrics = await self.update_usage_metrics(user_id, subscription.id)
        
        warnings = []
        
        # Проверяем превышения лимитов
        if metrics.is_limit_exceeded("objects"):
            warnings.append(f"Превышен лимит объектов: {metrics.current_objects}/{metrics.max_objects}")
        
        if metrics.is_limit_exceeded("employees"):
            warnings.append(f"Превышен лимит сотрудников: {metrics.current_employees}/{metrics.max_employees}")
        
        if metrics.is_limit_exceeded("managers"):
            warnings.append(f"Превышен лимит управляющих: {metrics.current_managers}/{metrics.max_managers}")
        
        return {
            "has_subscription": True,
            "subscription": subscription.to_dict(),
            "limits": {
                "objects": metrics.max_objects,
                "employees": metrics.max_employees,
                "managers": metrics.max_managers
            },
            "usage": {
                "objects": metrics.current_objects,
                "employees": metrics.current_employees,
                "managers": metrics.current_managers
            },
            "percentages": {
                "objects": metrics.get_usage_percentage("objects"),
                "employees": metrics.get_usage_percentage("employees"),
                "managers": metrics.get_usage_percentage("managers")
            },
            "remaining": {
                "objects": metrics.get_remaining_limit("objects"),
                "employees": metrics.get_remaining_limit("employees"),
                "managers": metrics.get_remaining_limit("managers")
            },
            "warnings": warnings
        }
    
    # === Уведомления ===
    
    async def create_payment_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.TELEGRAM,
        subscription_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        scheduled_at: Optional[datetime] = None,
        notification_data: Optional[Dict[str, Any]] = None
    ) -> PaymentNotification:
        """Создание уведомления о платеже."""
        notification = PaymentNotification(
            user_id=user_id,
            subscription_id=subscription_id,
            transaction_id=transaction_id,
            notification_type=notification_type,
            status=NotificationStatus.PENDING,
            channel=channel,
            title=title,
            message=message,
            scheduled_at=scheduled_at,
            notification_data=json.dumps(notification_data) if notification_data else None
        )
        
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        
        logger.info(f"Created payment notification {notification.id} for user {user_id}: {notification_type.value}")
        return notification
    
    async def schedule_subscription_renewal_notifications(self, user_id: int) -> List[PaymentNotification]:
        """Планирование уведомлений о продлении подписки."""
        notifications = []
        
        # Получаем активную подписку
        subscription_result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(selectinload(UserSubscription.tariff_plan))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription or not subscription.expires_at:
            return notifications
        
        # За 7 дней до истечения
        warning_date = subscription.expires_at - timedelta(days=7)
        if warning_date > datetime.now(timezone.utc):
            notification = await self.create_payment_notification(
                user_id=user_id,
                subscription_id=subscription.id,
                notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
                title="Подписка скоро истекает",
                message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' истекает через 7 дней. Продлите подписку, чтобы не потерять доступ к функциям.",
                scheduled_at=warning_date
            )
            notifications.append(notification)
        
        # За 1 день до истечения
        urgent_date = subscription.expires_at - timedelta(days=1)
        if urgent_date > datetime.now(timezone.utc):
            notification = await self.create_payment_notification(
                user_id=user_id,
                subscription_id=subscription.id,
                notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
                title="Подписка истекает завтра",
                message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' истекает завтра! Срочно продлите подписку.",
                scheduled_at=urgent_date
            )
            notifications.append(notification)
        
        return notifications
    
    # === Автоматическое продление ===
    
    async def process_auto_renewal(self, user_id: int) -> Optional[BillingTransaction]:
        """Обработка автоматического продления подписки."""
        # Получаем активную подписку с автопродлением
        subscription_result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE,
                UserSubscription.auto_renewal == True
            ).options(selectinload(UserSubscription.tariff_plan))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription or subscription.tariff_plan.price == 0:
            return None
        
        # Создаем транзакцию для автопродления
        transaction = await self.create_transaction(
            user_id=user_id,
            subscription_id=subscription.id,
            transaction_type=TransactionType.PAYMENT,
            amount=float(subscription.tariff_plan.price),
            currency=subscription.tariff_plan.currency,
            payment_method=PaymentMethod.MANUAL,  # TODO: Получить из настроек пользователя
            description=f"Автоматическое продление подписки на тариф '{subscription.tariff_plan.name}'",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # TODO: Здесь должна быть интеграция с платежной системой
        # Пока что помечаем как завершенную
        await self.update_transaction_status(transaction.id, TransactionStatus.COMPLETED)
        
        # Продлеваем подписку
        if subscription.tariff_plan.billing_period == "month":
            new_expires_at = subscription.expires_at + timedelta(days=30) if subscription.expires_at else datetime.now(timezone.utc) + timedelta(days=30)
        elif subscription.tariff_plan.billing_period == "year":
            new_expires_at = subscription.expires_at + timedelta(days=365) if subscription.expires_at else datetime.now(timezone.utc) + timedelta(days=365)
        else:
            new_expires_at = subscription.expires_at
        
        subscription.expires_at = new_expires_at
        subscription.last_payment_at = datetime.now(timezone.utc)
        await self.session.commit()
        
        # Планируем уведомления о следующем продлении
        await self.schedule_subscription_renewal_notifications(user_id)
        
        logger.info(f"Processed auto renewal for user {user_id}, subscription extended to {new_expires_at}")
        return transaction
