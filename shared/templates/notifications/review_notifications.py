"""
Шаблоны уведомлений для системы отзывов и обжалований.
"""

from typing import Dict, Any, Optional
from datetime import datetime


class ReviewNotificationTemplates:
    """Шаблоны уведомлений для отзывов и обжалований."""
    
    # Уведомления о статусе отзыва
    REVIEW_SUBMITTED = {
        "title": "Отзыв отправлен на модерацию",
        "message": "Ваш отзыв о {target_type} #{target_id} отправлен на модерацию. Рассмотрение займет до 48 часов.",
        "type": "info",
        "channels": ["web", "telegram"]
    }
    
    REVIEW_APPROVED = {
        "title": "Отзыв одобрен",
        "message": "Ваш отзыв о {target_type} #{target_id} одобрен и опубликован.",
        "type": "success",
        "channels": ["web", "telegram"]
    }
    
    REVIEW_REJECTED = {
        "title": "Отзыв отклонен",
        "message": "Ваш отзыв о {target_type} #{target_id} отклонен. Причина: {rejection_reason}. Вы можете подать обжалование.",
        "type": "warning",
        "channels": ["web", "telegram"]
    }
    
    # Уведомления о статусе обжалования
    APPEAL_SUBMITTED = {
        "title": "Обжалование подано",
        "message": "Ваше обжалование по отзыву #{review_id} подано на рассмотрение. Рассмотрение займет до 72 часов.",
        "type": "info",
        "channels": ["web", "telegram"]
    }
    
    APPEAL_APPROVED = {
        "title": "Обжалование одобрено",
        "message": "Ваше обжалование по отзыву #{review_id} одобрено. Отзыв возвращен на модерацию.",
        "type": "success",
        "channels": ["web", "telegram"]
    }
    
    APPEAL_REJECTED = {
        "title": "Обжалование отклонено",
        "message": "Ваше обжалование по отзыву #{review_id} отклонено. Решение модерации окончательное.",
        "type": "error",
        "channels": ["web", "telegram"]
    }
    
    # Уведомления для модераторов
    MODERATION_REQUIRED = {
        "title": "Требуется модерация",
        "message": "Новый отзыв #{review_id} ожидает модерации. Время на рассмотрение: 48 часов.",
        "type": "warning",
        "channels": ["web", "telegram"],
        "target_roles": ["moderator", "superadmin"]
    }
    
    APPEAL_REQUIRED = {
        "title": "Требуется рассмотрение обжалования",
        "message": "Новое обжалование #{appeal_id} ожидает рассмотрения. Время на рассмотрение: 72 часа.",
        "type": "warning",
        "channels": ["web", "telegram"],
        "target_roles": ["moderator", "superadmin"]
    }
    
    MODERATION_OVERDUE = {
        "title": "Просрочена модерация",
        "message": "Отзыв #{review_id} просрочен на модерации. Требуется срочное рассмотрение.",
        "type": "error",
        "channels": ["web", "telegram"],
        "target_roles": ["moderator", "superadmin"]
    }
    
    APPEAL_OVERDUE = {
        "title": "Просрочено рассмотрение обжалования",
        "message": "Обжалование #{appeal_id} просрочено на рассмотрении. Требуется срочное рассмотрение.",
        "type": "error",
        "channels": ["web", "telegram"],
        "target_roles": ["moderator", "superadmin"]
    }
    
    # Уведомления для владельцев объектов/сотрудников
    NEW_REVIEW_ABOUT_OBJECT = {
        "title": "Новый отзыв об объекте",
        "message": "Оставлен новый отзыв об объекте #{object_id}. Рейтинг: {rating}/5. {title}",
        "type": "info",
        "channels": ["web", "telegram"],
        "target_roles": ["owner", "manager"]
    }
    
    NEW_REVIEW_ABOUT_EMPLOYEE = {
        "title": "Новый отзыв о сотруднике",
        "message": "Оставлен новый отзыв о сотруднике #{employee_id}. Рейтинг: {rating}/5. {title}",
        "type": "info",
        "channels": ["web", "telegram"],
        "target_roles": ["owner", "manager"]
    }
    
    RATING_UPDATED = {
        "title": "Обновлен рейтинг",
        "message": "Рейтинг {target_type} #{target_id} обновлен: {new_rating}/5 (было {old_rating}/5).",
        "type": "info",
        "channels": ["web", "telegram"],
        "target_roles": ["owner", "manager"]
    }
    
    @classmethod
    def get_template(cls, template_name: str) -> Optional[Dict[str, Any]]:
        """Получение шаблона уведомления по имени."""
        return getattr(cls, template_name.upper(), None)
    
    @classmethod
    def format_message(cls, template_name: str, **kwargs) -> Optional[str]:
        """Форматирование сообщения уведомления."""
        template = cls.get_template(template_name)
        if not template:
            return None
        
        try:
            return template["message"].format(**kwargs)
        except KeyError as e:
            # Если не хватает параметров, возвращаем базовое сообщение
            return template["message"]
    
    @classmethod
    def get_notification_data(cls, template_name: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Получение полных данных уведомления."""
        template = cls.get_template(template_name)
        if not template:
            return None
        
        return {
            "title": template["title"],
            "message": cls.format_message(template_name, **kwargs),
            "type": template["type"],
            "channels": template.get("channels", ["web"]),
            "target_roles": template.get("target_roles", []),
            "created_at": datetime.utcnow().isoformat(),
            "data": kwargs
        }


class ReviewNotificationService:
    """Сервис для отправки уведомлений о отзывах и обжалованиях."""
    
    def __init__(self, session):
        self.session = session
        self.templates = ReviewNotificationTemplates()
    
    async def send_review_submitted_notification(self, user_id: int, review_data: Dict[str, Any]) -> bool:
        """Отправка уведомления о подаче отзыва."""
        try:
            notification_data = self.templates.get_notification_data(
                "review_submitted",
                target_type=review_data.get("target_type", "объекте"),
                target_id=review_data.get("target_id", "N/A")
            )
            
            if notification_data:
                # TODO: Интеграция с реальной системой уведомлений
                print(f"Notification for user {user_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending review submitted notification: {e}")
            return False
    
    async def send_review_status_notification(self, user_id: int, review_data: Dict[str, Any], status: str) -> bool:
        """Отправка уведомления об изменении статуса отзыва."""
        try:
            template_name = f"review_{status}"
            notification_data = self.templates.get_notification_data(
                template_name,
                target_type=review_data.get("target_type", "объекте"),
                target_id=review_data.get("target_id", "N/A"),
                rejection_reason=review_data.get("rejection_reason", "Не указана")
            )
            
            if notification_data:
                # TODO: Интеграция с реальной системой уведомлений
                print(f"Notification for user {user_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending review status notification: {e}")
            return False
    
    async def send_appeal_submitted_notification(self, user_id: int, appeal_data: Dict[str, Any]) -> bool:
        """Отправка уведомления о подаче обжалования."""
        try:
            notification_data = self.templates.get_notification_data(
                "appeal_submitted",
                review_id=appeal_data.get("review_id", "N/A")
            )
            
            if notification_data:
                # TODO: Интеграция с реальной системой уведомлений
                print(f"Notification for user {user_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending appeal submitted notification: {e}")
            return False
    
    async def send_appeal_status_notification(self, user_id: int, appeal_data: Dict[str, Any], status: str) -> bool:
        """Отправка уведомления об изменении статуса обжалования."""
        try:
            template_name = f"appeal_{status}"
            notification_data = self.templates.get_notification_data(
                template_name,
                review_id=appeal_data.get("review_id", "N/A")
            )
            
            if notification_data:
                # TODO: Интеграция с реальной системой уведомлений
                print(f"Notification for user {user_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending appeal status notification: {e}")
            return False
    
    async def send_moderation_required_notification(self, review_id: int, review_data: Dict[str, Any]) -> bool:
        """Отправка уведомления модераторам о необходимости модерации."""
        try:
            notification_data = self.templates.get_notification_data(
                "moderation_required",
                review_id=review_id
            )
            
            if notification_data:
                # TODO: Отправка всем модераторам и суперадминам
                print(f"Moderation notification: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending moderation required notification: {e}")
            return False
    
    async def send_appeal_required_notification(self, appeal_id: int, appeal_data: Dict[str, Any]) -> bool:
        """Отправка уведомления модераторам о необходимости рассмотрения обжалования."""
        try:
            notification_data = self.templates.get_notification_data(
                "appeal_required",
                appeal_id=appeal_id
            )
            
            if notification_data:
                # TODO: Отправка всем модераторам и суперадминам
                print(f"Appeal notification: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending appeal required notification: {e}")
            return False
    
    async def send_new_review_notification(self, target_owner_id: int, review_data: Dict[str, Any]) -> bool:
        """Отправка уведомления владельцу о новом отзыве."""
        try:
            target_type = review_data.get("target_type", "object")
            template_name = f"new_review_about_{target_type}"
            
            notification_data = self.templates.get_notification_data(
                template_name,
                **{f"{target_type}_id": review_data.get("target_id", "N/A")},
                rating=review_data.get("rating", "N/A"),
                title=review_data.get("title", "Без заголовка")
            )
            
            if notification_data:
                # TODO: Отправка владельцу объекта/сотрудника
                print(f"New review notification for owner {target_owner_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending new review notification: {e}")
            return False
    
    async def send_rating_updated_notification(self, target_owner_id: int, rating_data: Dict[str, Any]) -> bool:
        """Отправка уведомления об обновлении рейтинга."""
        try:
            notification_data = self.templates.get_notification_data(
                "rating_updated",
                target_type=rating_data.get("target_type", "объекте"),
                target_id=rating_data.get("target_id", "N/A"),
                new_rating=rating_data.get("new_rating", "N/A"),
                old_rating=rating_data.get("old_rating", "N/A")
            )
            
            if notification_data:
                # TODO: Отправка владельцу объекта/сотрудника
                print(f"Rating updated notification for owner {target_owner_id}: {notification_data['title']}")
                return True
            
            return False
        except Exception as e:
            print(f"Error sending rating updated notification: {e}")
            return False
