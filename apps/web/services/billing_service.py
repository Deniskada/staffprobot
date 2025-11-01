"""Сервис для работы с биллингом и платежами."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta, date
import json
import re
from decimal import Decimal


def json_serializer(obj):
    """Кастомный сериализатор для JSON, обрабатывает Decimal, datetime и другие типы."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        # Объект с атрибутами - конвертируем в словарь
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

from domain.entities.billing_transaction import BillingTransaction, TransactionType, TransactionStatus, PaymentMethod
from domain.entities.usage_metrics import UsageMetrics
from domain.entities.payment_notification import PaymentNotification, NotificationType, NotificationStatus, NotificationChannel
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from apps.web.services.payment_gateway.yookassa_service import YooKassaService
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
    
    async def create_payment_transaction(
        self,
        user_id: int,
        subscription_id: int,
        amount: float,
        currency: str,
        description: str,
        return_url: str
    ) -> tuple[BillingTransaction, str]:
        """
        Создание транзакции и платежа в YooKassa.
        
        Args:
            user_id: ID пользователя
            subscription_id: ID подписки
            amount: Сумма платежа
            currency: Валюта (RUB)
            description: Описание платежа
            return_url: URL для возврата после оплаты
            
        Returns:
            tuple: (transaction, payment_url)
        """
        # Получаем подписку для метаданных
        subscription_result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.id == subscription_id,
                UserSubscription.user_id == user_id
            ).options(selectinload(UserSubscription.tariff_plan))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if not subscription:
            raise ValueError(f"Subscription {subscription_id} not found for user {user_id}")
        
        # Создаем транзакцию со статусом PENDING
        transaction = await self.create_transaction(
            user_id=user_id,
            subscription_id=subscription_id,
            transaction_type=TransactionType.PAYMENT,
            amount=amount,
            currency=currency,
            payment_method=PaymentMethod.YOOKASSA,
            description=description,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        # Создаем платеж в YooKassa
        yookassa_service = YooKassaService()
        metadata = {
            "transaction_id": str(transaction.id),
            "user_id": str(user_id),
            "subscription_id": str(subscription_id),
            "tariff_plan_id": str(subscription.tariff_plan_id)
        }
        
        logger.info(
            f"Creating YooKassa payment",
            transaction_id=transaction.id,
            amount=amount,
            currency=currency,
            return_url=return_url,
            metadata=metadata
        )
        
        try:
            payment_data = await yookassa_service.create_payment(
                amount=amount,
                currency=currency,
                description=description,
                return_url=return_url,
                metadata=metadata
            )
            
            logger.info(
                f"YooKassa payment created",
                transaction_id=transaction.id,
                payment_id=payment_data.get("id"),
                confirmation_url=payment_data.get("confirmation_url")
            )
            
            # Обновляем транзакцию с external_id и gateway_response
            transaction.external_id = payment_data["id"]
            transaction.gateway_response = json.dumps(payment_data, default=json_serializer)
            transaction.status = TransactionStatus.PROCESSING
            await self.session.commit()
            await self.session.refresh(transaction)
            
            logger.info(
                f"Created payment transaction {transaction.id} with YooKassa payment {payment_data['id']}",
                transaction_id=transaction.id,
                payment_id=payment_data["id"],
                amount=amount
            )
            
            payment_url = payment_data.get("confirmation_url")
            if not payment_url:
                raise ValueError("YooKassa payment confirmation_url not found")
            
            return transaction, payment_url
            
        except Exception as e:
            # В случае ошибки обновляем статус транзакции на FAILED
            logger.error(
                f"Error creating YooKassa payment for transaction {transaction.id}: {e}",
                transaction_id=transaction.id,
                error=str(e)
            )
            transaction.status = TransactionStatus.FAILED
            transaction.gateway_response = json.dumps({"error": str(e)}, default=json_serializer)
            await self.session.commit()
            raise
    
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
        
        # Считаем количество уникальных сотрудников (employee_id) по активным контрактам владельца
        # Contract связан с владельцем напрямую через owner_id
        employees_count_result = await self.session.execute(
            select(func.count(func.distinct(Contract.employee_id)))
            .where(
                Contract.owner_id == user_id,
                Contract.status == "active"
            )
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
        
        # Получаем информацию о тарифе
        subscription_dict = subscription.to_dict()
        if subscription.tariff_plan:
            subscription_dict["tariff_plan"] = {
                "id": subscription.tariff_plan.id,
                "name": subscription.tariff_plan.name,
                "price": float(subscription.tariff_plan.price) if subscription.tariff_plan.price else 0,
                "currency": subscription.tariff_plan.currency,
                "billing_period": subscription.tariff_plan.billing_period
            }
        
        return {
            "has_subscription": True,
            "subscription": subscription_dict,
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
            notification_data=json.dumps(notification_data, default=json_serializer) if notification_data else None
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
    
    async def process_payment_success(
        self,
        transaction_id: int,
        payment_id: str
    ) -> None:
        """
        Обработка успешной оплаты.
        
        Args:
            transaction_id: ID транзакции в БД
            payment_id: ID платежа в YooKassa
        """
        # Получаем транзакцию
        transaction = await self.session.get(BillingTransaction, transaction_id)
        if not transaction:
            logger.error(f"Transaction {transaction_id} not found")
            return
        
        # Обновляем статус транзакции на COMPLETED
        transaction.status = TransactionStatus.COMPLETED
        transaction.processed_at = datetime.now(timezone.utc)
        if payment_id:
            transaction.external_id = payment_id
        
        # Получаем подписку
        if transaction.subscription_id:
            subscription_result = await self.session.execute(
                select(UserSubscription).where(
                    UserSubscription.id == transaction.subscription_id
                ).options(selectinload(UserSubscription.tariff_plan))
            )
            subscription = subscription_result.scalar_one_or_none()
            
            if subscription:
                # Активируем подписку (из SUSPENDED в ACTIVE) после оплаты
                # expires_at уже установлен правильно при создании подписки (начинается после окончания предыдущей)
                # НЕ изменяем expires_at - он уже вычислен правильно
                
                subscription.last_payment_at = datetime.now(timezone.utc)
                
                # Если подписка была SUSPENDED (ожидала оплаты), активируем её
                # Если она должна начаться в будущем - оставляем SUSPENDED до даты начала
                # Если дата начала уже наступила - активируем
                if subscription.status == SubscriptionStatus.SUSPENDED:
                    if subscription.started_at and subscription.started_at <= datetime.now(timezone.utc):
                        subscription.status = SubscriptionStatus.ACTIVE
                        logger.info(
                            f"Activated subscription after payment",
                            subscription_id=subscription.id,
                            started_at=subscription.started_at,
                            expires_at=subscription.expires_at
                        )
                    else:
                        # Подписка оплачена, но начнется в будущем - оставляем SUSPENDED
                        logger.info(
                            f"Subscription paid, will activate at scheduled date",
                            subscription_id=subscription.id,
                            started_at=subscription.started_at,
                            expires_at=subscription.expires_at
                        )
                elif subscription.status == SubscriptionStatus.EXPIRED:
                    # Если подписка истекла - активируем её снова (но expires_at уже установлен)
                    subscription.status = SubscriptionStatus.ACTIVE
                    logger.info(
                        f"Reactivated expired subscription after payment",
                        subscription_id=subscription.id,
                        expires_at=subscription.expires_at
                    )
                
                await self.session.commit()
                
                # Получаем expires_at для уведомления (используем из подписки, а не undefined переменную)
                expires_at_display = subscription.expires_at.strftime('%d.%m.%Y') if subscription.expires_at else "бессрочно"
                
                # Планируем уведомления о следующем продлении
                await self.schedule_subscription_renewal_notifications(transaction.user_id)
                
                # Создаем уведомление владельцу
                await self.create_payment_notification(
                    user_id=transaction.user_id,
                    subscription_id=subscription.id,
                    transaction_id=transaction.id,
                    notification_type=NotificationType.PAYMENT_SUCCESS,
                    title="Оплата успешно завершена",
                    message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' успешно оплачена и продлена до {expires_at_display}.",
                    channel=NotificationChannel.TELEGRAM
                )
                
                logger.info(
                    f"Processed payment success for transaction {transaction_id}, subscription expires at {expires_at_display}",
                    transaction_id=transaction_id,
                    payment_id=payment_id,
                    subscription_id=subscription.id,
                    expires_at=subscription.expires_at.isoformat() if subscription.expires_at else None
                )
        
        await self.session.commit()
    
    # === Автоматическое продление ===
    
    async def process_auto_renewal(self, user_id: int, return_url: Optional[str] = None) -> tuple[Optional[BillingTransaction], Optional[str]]:
        """
        Обработка автоматического продления подписки.
        
        Args:
            user_id: ID пользователя
            return_url: URL для возврата после оплаты (для создания платежа)
            
        Returns:
            tuple: (transaction, payment_url) или (transaction, None) если бесплатный тариф
        """
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
            return None, None
        
        # Если return_url передан, создаем платеж через YooKassa
        if return_url:
            try:
                transaction, payment_url = await self.create_payment_transaction(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    amount=float(subscription.tariff_plan.price),
                    currency=subscription.tariff_plan.currency,
                    description=f"Автоматическое продление подписки на тариф '{subscription.tariff_plan.name}'",
                    return_url=return_url
                )
                
                # Создаем уведомление владельцу о необходимости оплаты
                await self.create_payment_notification(
                    user_id=user_id,
                    subscription_id=subscription.id,
                    transaction_id=transaction.id,
                    notification_type=NotificationType.SUBSCRIPTION_EXPIRING,
                    title="Требуется оплата для автопродления",
                    message=f"Ваша подписка на тариф '{subscription.tariff_plan.name}' будет автоматически продлена после оплаты.",
                    channel=NotificationChannel.TELEGRAM
                )
                
                logger.info(
                    f"Created auto renewal payment for user {user_id}",
                    transaction_id=transaction.id,
                    payment_url=payment_url
                )
                
                return transaction, payment_url
                
            except Exception as e:
                logger.error(
                    f"Error creating auto renewal payment for user {user_id}: {e}",
                    error=str(e),
                    user_id=user_id
                )
                return None, None
        
        # Если return_url не передан, создаем транзакцию без платежа (для ручной обработки админом)
        transaction = await self.create_transaction(
            user_id=user_id,
            subscription_id=subscription.id,
            transaction_type=TransactionType.PAYMENT,
            amount=float(subscription.tariff_plan.price),
            currency=subscription.tariff_plan.currency,
            payment_method=PaymentMethod.MANUAL,
            description=f"Автоматическое продление подписки на тариф '{subscription.tariff_plan.name}' (требует обработки)",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7)
        )
        
        logger.info(f"Created auto renewal transaction {transaction.id} for user {user_id} (requires manual processing)")
        return transaction, None
