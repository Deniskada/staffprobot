"""Сервис для генерации административных отчетов."""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
import json

from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.shift import Shift
from domain.entities.user_subscription import UserSubscription, SubscriptionStatus
from domain.entities.billing_transaction import BillingTransaction, TransactionStatus
from domain.entities.usage_metrics import UsageMetrics
from core.logging.logger import logger


class ReportsService:
    """Сервис для генерации административных отчетов."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # === Отчеты по пользователям ===
    
    async def get_users_report(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        role_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Отчет по пользователям."""
        try:
            # Базовый запрос
            query = select(User)
            
            # Фильтры по дате
            if start_date:
                query = query.where(User.created_at >= start_date)
            if end_date:
                query = query.where(User.created_at <= end_date)
            
            # Фильтр по роли
            if role_filter:
                query = query.where(User.role == role_filter)
            
            result = await self.session.execute(query)
            users = list(result.scalars().all())
            
            # Статистика
            total_users = len(users)
            active_users = len([u for u in users if u.is_active])
            
            # Группировка по ролям
            roles_count = {}
            for user in users:
                role = user.role
                roles_count[role] = roles_count.get(role, 0) + 1
            
            # Группировка по месяцам регистрации
            monthly_registrations = {}
            for user in users:
                month_key = user.created_at.strftime('%Y-%m') if user.created_at else 'Unknown'
                monthly_registrations[month_key] = monthly_registrations.get(month_key, 0) + 1
            
            return {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "inactive_users": total_users - active_users
                },
                "roles_distribution": roles_count,
                "monthly_registrations": monthly_registrations,
                "users": [self._user_to_dict(user) for user in users]
            }
            
        except Exception as e:
            logger.error(f"Error generating users report: {e}")
            return {"error": str(e)}
    
    # === Отчеты по владельцам ===
    
    async def get_owners_report(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Отчет по владельцам объектов."""
        try:
            # Получаем владельцев
            owners_query = select(User).where(User.role == "owner")
            
            if start_date:
                owners_query = owners_query.where(User.created_at >= start_date)
            if end_date:
                owners_query = owners_query.where(User.created_at <= end_date)
            
            owners_result = await self.session.execute(owners_query)
            owners = list(owners_result.scalars().all())
            
            owners_data = []
            total_objects = 0
            total_employees = 0
            
            for owner in owners:
                # Количество объектов владельца
                objects_count_result = await self.session.execute(
                    select(func.count(Object.id)).where(
                        Object.owner_id == owner.id,
                        Object.is_active == True
                    )
                )
                objects_count = objects_count_result.scalar() or 0
                
                # Количество сотрудников владельца
                employees_count_result = await self.session.execute(
                    select(func.count(Contract.id.distinct())).join(Object).where(
                        Object.owner_id == owner.id
                    )
                )
                employees_count = employees_count_result.scalar() or 0
                
                # Активная подписка
                subscription_result = await self.session.execute(
                    select(UserSubscription).where(
                        UserSubscription.user_id == owner.id,
                        UserSubscription.status == SubscriptionStatus.ACTIVE
                    ).options(selectinload(UserSubscription.tariff_plan))
                )
                subscription = subscription_result.scalar_one_or_none()
                
                owner_data = {
                    "id": owner.id,
                    "telegram_id": owner.telegram_id,
                    "username": owner.username,
                    "first_name": owner.first_name,
                    "last_name": owner.last_name,
                    "email": owner.email,
                    "created_at": owner.created_at.isoformat() if owner.created_at else None,
                    "is_active": owner.is_active,
                    "objects_count": objects_count,
                    "employees_count": employees_count,
                    "subscription": {
                        "name": subscription.tariff_plan.name if subscription else None,
                        "status": subscription.status.value if subscription else None,
                        "expires_at": subscription.expires_at.isoformat() if subscription and subscription.expires_at else None
                    } if subscription else None
                }
                
                owners_data.append(owner_data)
                total_objects += objects_count
                total_employees += employees_count
            
            # Сортировка по количеству объектов
            owners_data.sort(key=lambda x: x["objects_count"], reverse=True)
            
            return {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "summary": {
                    "total_owners": len(owners_data),
                    "active_owners": len([o for o in owners_data if o["is_active"]]),
                    "total_objects": total_objects,
                    "total_employees": total_employees,
                    "avg_objects_per_owner": round(total_objects / len(owners_data), 2) if owners_data else 0,
                    "avg_employees_per_owner": round(total_employees / len(owners_data), 2) if owners_data else 0
                },
                "owners": owners_data
            }
            
        except Exception as e:
            logger.error(f"Error generating owners report: {e}")
            return {"error": str(e)}
    
    # === Финансовые отчеты ===
    
    async def get_financial_report(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Финансовый отчет (доходы по тарифам, оплаты)."""
        try:
            # Базовый запрос транзакций
            query = select(BillingTransaction)
            
            if start_date:
                query = query.where(BillingTransaction.created_at >= start_date)
            if end_date:
                query = query.where(BillingTransaction.created_at <= end_date)
            
            result = await self.session.execute(query)
            transactions = list(result.scalars().all())
            
            # Статистика по транзакциям
            total_revenue = 0
            total_transactions = len(transactions)
            completed_transactions = 0
            failed_transactions = 0
            
            # Группировка по типам транзакций
            transaction_types = {}
            payment_methods = {}
            monthly_revenue = {}
            
            for transaction in transactions:
                amount = float(transaction.amount)
                
                # Общая выручка
                if transaction.status == TransactionStatus.COMPLETED:
                    total_revenue += amount
                    completed_transactions += 1
                elif transaction.status == TransactionStatus.FAILED:
                    failed_transactions += 1
                
                # Группировка по типам
                t_type = transaction.transaction_type.value
                transaction_types[t_type] = transaction_types.get(t_type, 0) + 1
                
                # Группировка по способам оплаты
                if transaction.payment_method:
                    method = transaction.payment_method.value
                    payment_methods[method] = payment_methods.get(method, 0) + 1
                
                # Месячная выручка
                if transaction.status == TransactionStatus.COMPLETED:
                    month_key = transaction.created_at.strftime('%Y-%m')
                    monthly_revenue[month_key] = monthly_revenue.get(month_key, 0) + amount
            
            # Статистика по подпискам
            subscriptions_query = select(UserSubscription).where(
                UserSubscription.status == SubscriptionStatus.ACTIVE
            ).options(selectinload(UserSubscription.tariff_plan))
            
            subscriptions_result = await self.session.execute(subscriptions_query)
            active_subscriptions = list(subscriptions_result.scalars().all())
            
            # Группировка по тарифам
            tariff_distribution = {}
            total_monthly_revenue = 0
            
            for subscription in active_subscriptions:
                tariff_name = subscription.tariff_plan.name
                tariff_distribution[tariff_name] = tariff_distribution.get(tariff_name, 0) + 1
                
                # Подсчет потенциального месячного дохода
                if subscription.tariff_plan.price > 0:
                    total_monthly_revenue += float(subscription.tariff_plan.price)
            
            return {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "revenue": {
                    "total_revenue": total_revenue,
                    "monthly_potential": total_monthly_revenue,
                    "avg_transaction": round(total_revenue / completed_transactions, 2) if completed_transactions > 0 else 0
                },
                "transactions": {
                    "total": total_transactions,
                    "completed": completed_transactions,
                    "failed": failed_transactions,
                    "success_rate": round((completed_transactions / total_transactions) * 100, 2) if total_transactions > 0 else 0
                },
                "transaction_types": transaction_types,
                "payment_methods": payment_methods,
                "monthly_revenue": monthly_revenue,
                "tariff_distribution": tariff_distribution,
                "active_subscriptions": len(active_subscriptions)
            }
            
        except Exception as e:
            logger.error(f"Error generating financial report: {e}")
            return {"error": str(e)}
    
    # === Системная аналитика ===
    
    async def get_system_analytics_report(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Отчет по системной аналитике."""
        try:
            # Общая статистика пользователей
            total_users_result = await self.session.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0
            
            active_users_result = await self.session.execute(
                select(func.count(User.id)).where(User.is_active == True)
            )
            active_users = active_users_result.scalar() or 0
            
            # Статистика по объектам
            total_objects_result = await self.session.execute(select(func.count(Object.id)))
            total_objects = total_objects_result.scalar() or 0
            
            active_objects_result = await self.session.execute(
                select(func.count(Object.id)).where(Object.is_active == True)
            )
            active_objects = active_objects_result.scalar() or 0
            
            # Статистика по сменам
            shifts_query = select(Shift)
            if start_date:
                shifts_query = shifts_query.where(Shift.start_time >= start_date)
            if end_date:
                shifts_query = shifts_query.where(Shift.start_time <= end_date)
            
            shifts_result = await self.session.execute(shifts_query)
            shifts = list(shifts_result.scalars().all())
            
            total_shifts = len(shifts)
            completed_shifts = len([s for s in shifts if s.status == "completed"])
            
            # Статистика по подпискам
            active_subscriptions_result = await self.session.execute(
                select(func.count(UserSubscription.id)).where(
                    UserSubscription.status == SubscriptionStatus.ACTIVE
                )
            )
            active_subscriptions = active_subscriptions_result.scalar() or 0
            
            # Статистика по лимитам (метрики использования)
            usage_metrics_result = await self.session.execute(
                select(UsageMetrics).order_by(desc(UsageMetrics.created_at))
            )
            recent_metrics = list(usage_metrics_result.scalars().all())
            
            # Анализ превышений лимитов
            over_limit_users = 0
            for metrics in recent_metrics:
                if (metrics.current_objects >= metrics.max_objects and metrics.max_objects != -1) or \
                   (metrics.current_employees >= metrics.max_employees and metrics.max_employees != -1):
                    over_limit_users += 1
            
            # Активность пользователей по дням
            daily_activity = {}
            for shift in shifts:
                if shift.start_time:
                    day_key = shift.start_time.strftime('%Y-%m-%d')
                    daily_activity[day_key] = daily_activity.get(day_key, 0) + 1
            
            return {
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "inactive": total_users - active_users,
                    "active_percentage": round((active_users / total_users) * 100, 2) if total_users > 0 else 0
                },
                "objects": {
                    "total": total_objects,
                    "active": active_objects,
                    "inactive": total_objects - active_objects,
                    "active_percentage": round((active_objects / total_objects) * 100, 2) if total_objects > 0 else 0
                },
                "shifts": {
                    "total": total_shifts,
                    "completed": completed_shifts,
                    "completion_rate": round((completed_shifts / total_shifts) * 100, 2) if total_shifts > 0 else 0
                },
                "subscriptions": {
                    "active": active_subscriptions,
                    "conversion_rate": round((active_subscriptions / total_users) * 100, 2) if total_users > 0 else 0
                },
                "limits": {
                    "users_over_limit": over_limit_users,
                    "total_metrics_tracked": len(recent_metrics)
                },
                "activity": {
                    "daily_activity": daily_activity,
                    "most_active_day": max(daily_activity.items(), key=lambda x: x[1]) if daily_activity else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating system analytics report: {e}")
            return {"error": str(e)}
    
    # === Экспорт отчетов ===
    
    async def export_report_to_csv(self, report_data: Dict[str, Any], report_type: str) -> str:
        """Экспорт отчета в CSV формат."""
        try:
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            if report_type == "users":
                # Заголовки
                writer.writerow([
                    "ID", "Telegram ID", "Username", "First Name", "Last Name", 
                    "Email", "Role", "Is Active", "Created At"
                ])
                
                # Данные
                for user in report_data.get("users", []):
                    writer.writerow([
                        user.get("id"),
                        user.get("telegram_id"),
                        user.get("username"),
                        user.get("first_name"),
                        user.get("last_name"),
                        user.get("email"),
                        user.get("role"),
                        user.get("is_active"),
                        user.get("created_at")
                    ])
            
            elif report_type == "owners":
                # Заголовки
                writer.writerow([
                    "ID", "Telegram ID", "Username", "First Name", "Last Name",
                    "Email", "Objects Count", "Employees Count", "Subscription Name",
                    "Subscription Status", "Created At"
                ])
                
                # Данные
                for owner in report_data.get("owners", []):
                    subscription = owner.get("subscription", {})
                    writer.writerow([
                        owner.get("id"),
                        owner.get("telegram_id"),
                        owner.get("username"),
                        owner.get("first_name"),
                        owner.get("last_name"),
                        owner.get("email"),
                        owner.get("objects_count"),
                        owner.get("employees_count"),
                        subscription.get("name"),
                        subscription.get("status"),
                        owner.get("created_at")
                    ])
            
            elif report_type == "financial":
                # Для финансового отчета экспортируем сводку
                writer.writerow(["Metric", "Value"])
                writer.writerow(["Total Revenue", report_data.get("revenue", {}).get("total_revenue", 0)])
                writer.writerow(["Monthly Potential", report_data.get("revenue", {}).get("monthly_potential", 0)])
                writer.writerow(["Total Transactions", report_data.get("transactions", {}).get("total", 0)])
                writer.writerow(["Completed Transactions", report_data.get("transactions", {}).get("completed", 0)])
                writer.writerow(["Success Rate", report_data.get("transactions", {}).get("success_rate", 0)])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {e}")
            return f"Error: {str(e)}"
    
    def _user_to_dict(self, user: User) -> Dict[str, Any]:
        """Преобразование пользователя в словарь."""
        return {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
