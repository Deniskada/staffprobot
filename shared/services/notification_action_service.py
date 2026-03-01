"""Сервис для определения action URL для уведомлений."""

from typing import Optional
from domain.entities.notification import Notification, NotificationType
from core.logging.logger import logger


class NotificationActionService:
    """Сервис для получения action URL из уведомлений."""
    
    def get_action_url(self, notification: Notification, user_role: str) -> Optional[str]:
        """
        Определяет URL для перехода к связанному объекту уведомления.
        
        Args:
            notification: Объект уведомления
            user_role: Роль пользователя (owner, manager, employee, admin)
        
        Returns:
            URL для перехода или None, если нет связанного объекта
        """
        if not notification.data:
            return None
        
        notif_type = notification.type
        data = notification.data
        
        # Определяем префикс роли для URL
        role_prefix = f"/{user_role}"
        if user_role not in ["owner", "manager", "employee", "admin", "moderator"]:
            role_prefix = "/owner"  # По умолчанию
        
        try:
            # Смены
            if notif_type in [
                NotificationType.SHIFT_REMINDER,
                NotificationType.SHIFT_CONFIRMED,
                NotificationType.SHIFT_CANCELLED,
                NotificationType.SHIFT_STARTED,
                NotificationType.SHIFT_COMPLETED
            ]:
                shift_id = data.get("shift_id") or data.get("schedule_id")
                if shift_id:
                    return f"{role_prefix}/shifts/{shift_id}"
                object_id = data.get("object_id")
                if object_id:
                    return f"{role_prefix}/objects/{object_id}"
            
            # Объекты
            if notif_type in [
                NotificationType.OBJECT_OPENED,
                NotificationType.OBJECT_CLOSED,
                NotificationType.OBJECT_LATE_OPENING,
                NotificationType.OBJECT_NO_SHIFTS_TODAY,
                NotificationType.OBJECT_EARLY_CLOSING
            ]:
                object_id = data.get("object_id")
                if object_id:
                    return f"{role_prefix}/objects/{object_id}"
            
            # Договоры
            if notif_type in [
                NotificationType.CONTRACT_SIGNED,
                NotificationType.CONTRACT_TERMINATED,
                NotificationType.CONTRACT_EXPIRING,
                NotificationType.CONTRACT_UPDATED
            ]:
                contract_id = data.get("contract_id")
                if contract_id:
                    if user_role == "employee":
                        return f"/employee/offers/{contract_id}"
                    elif user_role == "owner":
                        return f"/owner/employees/contract/{contract_id}"
                    elif user_role == "manager":
                        return f"/manager/contracts/{contract_id}"
                employee_id = data.get("employee_id")
                if employee_id:
                    return f"{role_prefix}/employees/{employee_id}"
            
            # Оферты
            if notif_type in [
                NotificationType.OFFER_SENT,
                NotificationType.OFFER_TERMS_CHANGED,
            ]:
                contract_id = data.get("contract_id")
                if contract_id:
                    return f"/employee/offers/{contract_id}"
            
            if notif_type in [
                NotificationType.OFFER_ACCEPTED,
                NotificationType.OFFER_REJECTED,
            ]:
                contract_id = data.get("contract_id")
                if contract_id:
                    return f"/owner/employees/contract/{contract_id}"
            
            # Отзывы
            if notif_type in [
                NotificationType.REVIEW_RECEIVED,
                NotificationType.REVIEW_MODERATED,
                NotificationType.APPEAL_SUBMITTED,
                NotificationType.APPEAL_DECISION
            ]:
                review_id = data.get("review_id")
                if review_id:
                    if user_role == "moderator":
                        return f"/moderator/reviews/{review_id}"
                    return f"{role_prefix}/reviews"
                return f"{role_prefix}/reviews"
            
            # Задачи
            if notif_type in [
                NotificationType.TASK_ASSIGNED,
                NotificationType.TASK_COMPLETED,
                NotificationType.TASK_OVERDUE
            ]:
                task_id = data.get("task_id")
                if task_id:
                    return f"{role_prefix}/tasks/{task_id}"
                return f"{role_prefix}/tasks"
            
            # Платежи
            if notif_type in [
                NotificationType.PAYMENT_DUE,
                NotificationType.PAYMENT_SUCCESS,
                NotificationType.PAYMENT_FAILED,
                NotificationType.SUBSCRIPTION_EXPIRING,
                NotificationType.SUBSCRIPTION_EXPIRED,
                NotificationType.USAGE_LIMIT_WARNING,
                NotificationType.USAGE_LIMIT_EXCEEDED
            ]:
                if user_role == "owner":
                    transaction_id = data.get("transaction_id")
                    if transaction_id:
                        return f"/owner/billing/transactions?id={transaction_id}"
                    return "/owner/subscription"
                elif user_role == "admin":
                    user_id = data.get("user_id")
                    if user_id:
                        return f"/admin/users/{user_id}"
                    return "/admin/billing"
            
            # Системные уведомления
            if notif_type in [
                NotificationType.WELCOME,
                NotificationType.PASSWORD_RESET,
                NotificationType.ACCOUNT_SUSPENDED,
                NotificationType.ACCOUNT_ACTIVATED,
                NotificationType.SYSTEM_MAINTENANCE,
                NotificationType.FEATURE_ANNOUNCEMENT
            ]:
                # Системные уведомления обычно не имеют специфического action
                return None
            
            return None
            
        except Exception as e:
            logger.error(
                f"Error getting action URL for notification {notification.id}: {e}",
                exc_info=True
            )
            return None
    
    def get_action_label(self, notification: Notification) -> str:
        """
        Возвращает текст кнопки действия для уведомления.
        
        Args:
            notification: Объект уведомления
        
        Returns:
            Текст кнопки (например, "Перейти к смене")
        """
        notif_type = notification.type
        
        # Смены
        if notif_type in [
            NotificationType.SHIFT_REMINDER,
            NotificationType.SHIFT_CONFIRMED,
            NotificationType.SHIFT_CANCELLED,
            NotificationType.SHIFT_STARTED,
            NotificationType.SHIFT_COMPLETED
        ]:
            return "Перейти к смене"
        
        # Объекты
        if notif_type in [
            NotificationType.OBJECT_OPENED,
            NotificationType.OBJECT_CLOSED,
            NotificationType.OBJECT_LATE_OPENING,
            NotificationType.OBJECT_NO_SHIFTS_TODAY,
            NotificationType.OBJECT_EARLY_CLOSING
        ]:
            return "Перейти к объекту"
        
        # Договоры
        if notif_type in [
            NotificationType.CONTRACT_SIGNED,
            NotificationType.CONTRACT_TERMINATED,
            NotificationType.CONTRACT_EXPIRING,
            NotificationType.CONTRACT_UPDATED
        ]:
            return "Перейти к договору"
        
        # Отзывы
        if notif_type in [
            NotificationType.REVIEW_RECEIVED,
            NotificationType.REVIEW_MODERATED,
            NotificationType.APPEAL_SUBMITTED,
            NotificationType.APPEAL_DECISION
        ]:
            return "Перейти к отзывам"
        
        # Задачи
        if notif_type in [
            NotificationType.TASK_ASSIGNED,
            NotificationType.TASK_COMPLETED,
            NotificationType.TASK_OVERDUE
        ]:
            return "Перейти к задаче"
        
        # Платежи
        if notif_type in [
            NotificationType.PAYMENT_DUE,
            NotificationType.PAYMENT_SUCCESS,
            NotificationType.PAYMENT_FAILED,
            NotificationType.SUBSCRIPTION_EXPIRING,
            NotificationType.SUBSCRIPTION_EXPIRED,
            NotificationType.USAGE_LIMIT_WARNING,
            NotificationType.USAGE_LIMIT_EXCEEDED
        ]:
            return "Перейти к подписке"
        
        return "Перейти"

