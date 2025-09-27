"""Сервис для контроля лимитов и платных функций."""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.usage_metrics import UsageMetrics
from domain.entities.billing_transaction import BillingTransaction, TransactionStatus
from core.logging.logger import logger


class LimitsService:
    """Сервис для контроля лимитов и платных функций."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def check_object_creation_limit(self, user_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Проверка лимита на создание объектов."""
        try:
            # Получаем активную подписку
            subscription = await self._get_active_subscription(user_id)
            if not subscription:
                return False, "Нет активной подписки", {}
            
            # Получаем текущее количество объектов
            objects_count_result = await self.session.execute(
                select(func.count(Object.id)).where(
                    Object.owner_id == user_id,
                    Object.is_active == True
                )
            )
            current_objects = objects_count_result.scalar() or 0
            
            # Проверяем лимит
            max_objects = subscription.tariff_plan.max_objects
            if max_objects == -1:  # Безлимит
                return True, "Лимит не ограничен", {
                    "current": current_objects,
                    "max": -1,
                    "remaining": -1
                }
            
            if current_objects >= max_objects:
                return False, f"Превышен лимит объектов ({current_objects}/{max_objects})", {
                    "current": current_objects,
                    "max": max_objects,
                    "remaining": 0
                }
            
            return True, "Лимит не превышен", {
                "current": current_objects,
                "max": max_objects,
                "remaining": max_objects - current_objects
            }
            
        except Exception as e:
            logger.error(f"Error checking object creation limit for user {user_id}: {e}")
            return False, "Ошибка проверки лимита", {}
    
    async def check_employee_creation_limit(self, user_id: int, object_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Проверка лимита на добавление сотрудников к объекту."""
        try:
            # Получаем активную подписку
            subscription = await self._get_active_subscription(user_id)
            if not subscription:
                return False, "Нет активной подписки", {}
            
            # Получаем текущее количество сотрудников по всем объектам пользователя
            employees_count_result = await self.session.execute(
                select(func.count(Contract.id.distinct())).join(Object).where(
                    Object.owner_id == user_id,
                    Object.is_active == True
                )
            )
            current_employees = employees_count_result.scalar() or 0
            
            # Проверяем лимит
            max_employees = subscription.tariff_plan.max_employees
            if max_employees == -1:  # Безлимит
                return True, "Лимит не ограничен", {
                    "current": current_employees,
                    "max": -1,
                    "remaining": -1
                }
            
            if current_employees >= max_employees:
                return False, f"Превышен лимит сотрудников ({current_employees}/{max_employees})", {
                    "current": current_employees,
                    "max": max_employees,
                    "remaining": 0
                }
            
            return True, "Лимит не превышен", {
                "current": current_employees,
                "max": max_employees,
                "remaining": max_employees - current_employees
            }
            
        except Exception as e:
            logger.error(f"Error checking employee creation limit for user {user_id}: {e}")
            return False, "Ошибка проверки лимита", {}
    
    async def check_manager_assignment_limit(self, user_id: int) -> Tuple[bool, str, Dict[str, Any]]:
        """Проверка лимита на назначение управляющих."""
        try:
            # Получаем активную подписку
            subscription = await self._get_active_subscription(user_id)
            if not subscription:
                return False, "Нет активной подписки", {}
            
            # Получаем количество управляющих
            # TODO: Реализовать подсчет управляющих когда будет модель ManagerObjectPermission
            current_managers = 0  # Временно
            
            # Проверяем лимит
            max_managers = subscription.tariff_plan.max_managers
            if max_managers == -1:  # Безлимит
                return True, "Лимит не ограничен", {
                    "current": current_managers,
                    "max": -1,
                    "remaining": -1
                }
            
            if current_managers >= max_managers:
                return False, f"Превышен лимит управляющих ({current_managers}/{max_managers})", {
                    "current": current_managers,
                    "max": max_managers,
                    "remaining": 0
                }
            
            return True, "Лимит не превышен", {
                "current": current_managers,
                "max": max_managers,
                "remaining": max_managers - current_managers
            }
            
        except Exception as e:
            logger.error(f"Error checking manager assignment limit for user {user_id}: {e}")
            return False, "Ошибка проверки лимита", {}
    
    async def check_feature_access(self, user_id: int, feature: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Проверка доступа к платной функции."""
        try:
            # Получаем активную подписку
            subscription = await self._get_active_subscription(user_id)
            if not subscription:
                return False, "Нет активной подписки", {
                    "feature": feature,
                    "available": False
                }
            
            # Проверяем, есть ли функция в тарифе
            tariff_features = subscription.tariff_plan.features or []
            has_feature = feature in tariff_features
            
            if not has_feature:
                return False, f"Функция '{feature}' недоступна в текущем тарифе", {
                    "feature": feature,
                    "available": False,
                    "tariff": subscription.tariff_plan.name
                }
            
            return True, "Функция доступна", {
                "feature": feature,
                "available": True,
                "tariff": subscription.tariff_plan.name
            }
            
        except Exception as e:
            logger.error(f"Error checking feature access for user {user_id}, feature {feature}: {e}")
            return False, "Ошибка проверки доступа к функции", {
                "feature": feature,
                "available": False
            }
    
    async def get_user_limits_summary(self, user_id: int) -> Dict[str, Any]:
        """Получение сводки по всем лимитам пользователя."""
        try:
            # Получаем активную подписку
            subscription = await self._get_active_subscription(user_id)
            if not subscription:
                return {
                    "has_subscription": False,
                    "message": "Нет активной подписки"
                }
            
            # Проверяем все лимиты
            object_limit = await self.check_object_creation_limit(user_id)
            employee_limit = await self.check_employee_creation_limit(user_id, 0)
            manager_limit = await self.check_manager_assignment_limit(user_id)
            
            # Получаем доступные функции
            available_features = subscription.tariff_plan.features or []
            
            # Проверяем статус платежей
            payment_status = await self._check_payment_status(user_id)
            
            return {
                "has_subscription": True,
                "subscription": {
                    "id": subscription.id,
                    "tariff_name": subscription.tariff_plan.name,
                    "status": subscription.status.value,
                    "expires_at": subscription.expires_at.isoformat() if subscription.expires_at else None
                },
                "limits": {
                    "objects": {
                        "allowed": object_limit[0],
                        "message": object_limit[1],
                        "details": object_limit[2]
                    },
                    "employees": {
                        "allowed": employee_limit[0],
                        "message": employee_limit[1],
                        "details": employee_limit[2]
                    },
                    "managers": {
                        "allowed": manager_limit[0],
                        "message": manager_limit[1],
                        "details": manager_limit[2]
                    }
                },
                "features": {
                    "available": available_features,
                    "count": len(available_features)
                },
                "payment_status": payment_status,
                "warnings": await self._get_limits_warnings(user_id, subscription)
            }
            
        except Exception as e:
            logger.error(f"Error getting user limits summary for user {user_id}: {e}")
            return {
                "has_subscription": False,
                "error": str(e)
            }
    
    async def enforce_limits_middleware(self, user_id: int, action: str, **kwargs) -> Tuple[bool, str]:
        """Middleware для принудительной проверки лимитов перед действиями."""
        try:
            if action == "create_object":
                allowed, message, _ = await self.check_object_creation_limit(user_id)
                return allowed, message
            
            elif action == "add_employee":
                object_id = kwargs.get('object_id', 0)
                allowed, message, _ = await self.check_employee_creation_limit(user_id, object_id)
                return allowed, message
            
            elif action == "assign_manager":
                allowed, message, _ = await self.check_manager_assignment_limit(user_id)
                return allowed, message
            
            elif action == "use_feature":
                feature = kwargs.get('feature', '')
                allowed, message, _ = await self.check_feature_access(user_id, feature)
                return allowed, message
            
            else:
                return True, "Неизвестное действие"
                
        except Exception as e:
            logger.error(f"Error in limits middleware for user {user_id}, action {action}: {e}")
            return False, "Ошибка проверки лимитов"
    
    async def _get_active_subscription(self, user_id: int) -> Optional[UserSubscription]:
        """Получение активной подписки пользователя."""
        result = await self.session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(
                selectinload(UserSubscription.tariff_plan)
            )
        )
        return result.scalar_one_or_none()
    
    async def _check_payment_status(self, user_id: int) -> Dict[str, Any]:
        """Проверка статуса платежей."""
        try:
            # Проверяем последние транзакции
            result = await self.session.execute(
                select(BillingTransaction).where(
                    BillingTransaction.user_id == user_id
                ).order_by(BillingTransaction.created_at.desc()).limit(5)
            )
            recent_transactions = list(result.scalars().all())
            
            if not recent_transactions:
                return {
                    "status": "no_payments",
                    "message": "Нет истории платежей"
                }
            
            # Проверяем статус последней транзакции
            last_transaction = recent_transactions[0]
            
            if last_transaction.status == TransactionStatus.COMPLETED:
                return {
                    "status": "paid",
                    "message": "Платежи в порядке",
                    "last_payment": last_transaction.created_at.isoformat()
                }
            elif last_transaction.status == TransactionStatus.FAILED:
                return {
                    "status": "payment_failed",
                    "message": "Последний платеж не прошел",
                    "last_payment_attempt": last_transaction.created_at.isoformat()
                }
            elif last_transaction.status == TransactionStatus.PENDING:
                return {
                    "status": "pending",
                    "message": "Ожидается обработка платежа",
                    "pending_since": last_transaction.created_at.isoformat()
                }
            else:
                return {
                    "status": "unknown",
                    "message": "Неопределенный статус платежей"
                }
                
        except Exception as e:
            logger.error(f"Error checking payment status for user {user_id}: {e}")
            return {
                "status": "error",
                "message": "Ошибка проверки платежей"
            }
    
    async def _get_limits_warnings(self, user_id: int, subscription: UserSubscription) -> List[str]:
        """Получение предупреждений о лимитах."""
        warnings = []
        
        try:
            # Проверяем срок подписки
            if subscription.expires_at:
                days_until_expiry = subscription.days_until_expiry()
                if days_until_expiry <= 7:
                    warnings.append(f"Подписка истекает через {days_until_expiry} дней")
                elif days_until_expiry <= 0:
                    warnings.append("Подписка истекла")
            
            # Проверяем приближение к лимитам
            object_limit = await self.check_object_creation_limit(user_id)
            if object_limit[0] and object_limit[2].get('remaining', -1) <= 2:
                warnings.append("Осталось мало объектов")
            
            employee_limit = await self.check_employee_creation_limit(user_id, 0)
            if employee_limit[0] and employee_limit[2].get('remaining', -1) <= 2:
                warnings.append("Осталось мало сотрудников")
            
            manager_limit = await self.check_manager_assignment_limit(user_id)
            if manager_limit[0] and manager_limit[2].get('remaining', -1) <= 2:
                warnings.append("Осталось мало управляющих")
            
        except Exception as e:
            logger.error(f"Error getting limits warnings for user {user_id}: {e}")
            warnings.append("Ошибка получения предупреждений")
        
        return warnings
