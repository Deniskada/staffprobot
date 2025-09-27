"""Сервис для работы с тарифными планами."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, timezone

from domain.entities.tariff_plan import TariffPlan
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.user import User
from domain.entities.contract import Contract
from core.logging.logger import logger


class TariffService:
    """Сервис для работы с тарифными планами."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_all_tariff_plans(self, active_only: bool = True) -> List[TariffPlan]:
        """Получение всех тарифных планов."""
        query = select(TariffPlan)
        
        if active_only:
            query = query.where(TariffPlan.is_active == True)
        
        query = query.order_by(TariffPlan.price)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_tariff_plan_by_id(self, tariff_id: int) -> Optional[TariffPlan]:
        """Получение тарифного плана по ID."""
        query = select(TariffPlan).where(TariffPlan.id == tariff_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_tariff_plan(self, data: Dict[str, Any]) -> TariffPlan:
        """Создание нового тарифного плана."""
        tariff_plan = TariffPlan(
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            currency=data.get("currency", "RUB"),
            billing_period=data.get("billing_period", "month"),
            max_objects=data.get("max_objects", 2),
            max_employees=data.get("max_employees", 5),
            max_managers=data.get("max_managers", 0),
            features=data.get("features", []),
            is_active=data.get("is_active", True),
            is_popular=data.get("is_popular", False)
        )
        
        self.session.add(tariff_plan)
        await self.session.commit()
        await self.session.refresh(tariff_plan)
        
        logger.info(f"Created tariff plan: {tariff_plan.name}")
        return tariff_plan
    
    async def update_tariff_plan(self, tariff_id: int, data: Dict[str, Any]) -> Optional[TariffPlan]:
        """Обновление тарифного плана."""
        tariff_plan = await self.get_tariff_plan_by_id(tariff_id)
        if not tariff_plan:
            return None
        
        for key, value in data.items():
            if hasattr(tariff_plan, key):
                setattr(tariff_plan, key, value)
        
        tariff_plan.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(tariff_plan)
        
        logger.info(f"Updated tariff plan: {tariff_plan.name}")
        return tariff_plan
    
    async def delete_tariff_plan(self, tariff_id: int) -> bool:
        """Удаление тарифного плана."""
        tariff_plan = await self.get_tariff_plan_by_id(tariff_id)
        if not tariff_plan:
            return False
        
        # Проверяем, есть ли активные подписки
        active_subscriptions = await self.get_active_subscriptions_by_tariff(tariff_id)
        if active_subscriptions:
            logger.warning(f"Cannot delete tariff plan {tariff_id}: has active subscriptions")
            return False
        
        await self.session.delete(tariff_plan)
        await self.session.commit()
        
        logger.info(f"Deleted tariff plan: {tariff_plan.name}")
        return True
    
    async def get_user_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Получение активной подписки пользователя."""
        query = select(UserSubscription).where(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        ).options(selectinload(UserSubscription.tariff_plan))
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_user_subscription(
        self, 
        user_id: int, 
        tariff_plan_id: int, 
        payment_method: str = None,
        notes: str = None
    ) -> UserSubscription:
        """Создание подписки пользователя."""
        # Деактивируем старые подписки
        await self.deactivate_user_subscriptions(user_id)
        
        tariff_plan = await self.get_tariff_plan_by_id(tariff_plan_id)
        if not tariff_plan:
            raise ValueError(f"Tariff plan {tariff_plan_id} not found")
        
        # Определяем срок действия
        expires_at = None
        if tariff_plan.price > 0:  # Платный тариф
            if tariff_plan.billing_period == "month":
                expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            elif tariff_plan.billing_period == "year":
                expires_at = datetime.now(timezone.utc) + timedelta(days=365)
        
        subscription = UserSubscription(
            user_id=user_id,
            tariff_plan_id=tariff_plan_id,
            status=SubscriptionStatus.ACTIVE,
            expires_at=expires_at,
            payment_method=payment_method,
            notes=notes
        )
        
        self.session.add(subscription)
        await self.session.commit()
        await self.session.refresh(subscription)
        
        logger.info(f"Created subscription for user {user_id} on tariff {tariff_plan.name}")
        return subscription
    
    async def deactivate_user_subscriptions(self, user_id: int) -> None:
        """Деактивация всех подписок пользователя."""
        query = select(UserSubscription).where(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        
        result = await self.session.execute(query)
        subscriptions = result.scalars().all()
        
        for subscription in subscriptions:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.updated_at = datetime.now(timezone.utc)
        
        await self.session.commit()
        
        if subscriptions:
            logger.info(f"Deactivated {len(subscriptions)} subscriptions for user {user_id}")
    
    async def get_active_subscriptions_by_tariff(self, tariff_id: int) -> List[UserSubscription]:
        """Получение активных подписок по тарифу."""
        query = select(UserSubscription).where(
            and_(
                UserSubscription.tariff_plan_id == tariff_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def check_user_limits(self, user_id: int) -> Dict[str, Any]:
        """Проверка лимитов пользователя."""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            # Если нет подписки, возвращаем базовые лимиты
            return {
                "max_objects": 2,
                "max_employees": 5,
                "max_managers": 0,
                "features": ["basic_reports", "telegram_bot", "basic_support"],
                "is_unlimited": False
            }
        
        tariff_plan = subscription.tariff_plan
        
        return {
            "max_objects": tariff_plan.max_objects,
            "max_employees": tariff_plan.max_employees,
            "max_managers": tariff_plan.max_managers,
            "features": tariff_plan.features or [],
            "is_unlimited": tariff_plan.max_objects == -1,
            "subscription": subscription.to_dict(),
            "tariff_plan": tariff_plan.to_dict()
        }
    
    async def can_user_create_object(self, user_id: int) -> bool:
        """Проверка, может ли пользователь создать объект."""
        limits = await self.check_user_limits(user_id)
        
        if limits["is_unlimited"]:
            return True
        
        # Подсчитываем количество объектов пользователя
        query = select(func.count()).select_from(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user_objects_count = result.scalar() or 0
        
        return user_objects_count < limits["max_objects"]
    
    async def can_user_hire_employee(self, user_id: int) -> bool:
        """Проверка, может ли пользователь нанять сотрудника."""
        limits = await self.check_user_limits(user_id)
        
        if limits["is_unlimited"]:
            return True
        
        # Подсчитываем количество сотрудников пользователя
        query = select(func.count()).select_from(Contract).where(
            and_(
                Contract.owner_id == user_id,
                Contract.status == "active"
            )
        )
        result = await self.session.execute(query)
        employees_count = result.scalar() or 0
        
        return employees_count < limits["max_employees"]
    
    async def get_tariff_statistics(self) -> Dict[str, Any]:
        """Получение статистики по тарифам."""
        # Общее количество подписок
        total_subscriptions_result = await self.session.execute(
            select(func.count(UserSubscription.id))
        )
        total_subscriptions = total_subscriptions_result.scalar()
        
        # Активные подписки
        active_subscriptions_result = await self.session.execute(
            select(func.count(UserSubscription.id)).where(
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        )
        active_subscriptions = active_subscriptions_result.scalar()
        
        # Подписки по тарифам
        tariff_stats_result = await self.session.execute(
            select(
                TariffPlan.name,
                func.count(UserSubscription.id).label('subscriptions_count')
            )
            .select_from(TariffPlan)
            .join(UserSubscription, TariffPlan.id == UserSubscription.tariff_plan_id)
            .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
            .group_by(TariffPlan.id, TariffPlan.name)
        )
        
        return {
            "total_subscriptions": total_subscriptions or 0,
            "active_subscriptions": active_subscriptions or 0,
            "tariff_breakdown": [
                {"name": row.name, "count": row.subscriptions_count}
                for row in tariff_stats_result
            ]
        }
