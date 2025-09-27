"""Общий сервис уведомлений (web + Telegram)."""

# ВРЕМЕННО ОТКЛЮЧЕНО - система уведомлений будет восстановлена позже
from core.logging.logger import logger

logger.warning("NotificationService временно отключен")

class NotificationService:
    """Временно отключенный сервис уведомлений."""
    
    def __init__(self, session):
        self.session = session
        logger.warning("NotificationService временно отключен")
    
    async def create_notification(self, *args, **kwargs):
        logger.warning("NotificationService.create_notification временно отключен")
        return None
    
    async def get_unread_notifications(self, *args, **kwargs):
        logger.warning("NotificationService.get_unread_notifications временно отключен")
        return []
    
    async def mark_notification_as_read(self, *args, **kwargs):
        logger.warning("NotificationService.mark_notification_as_read временно отключен")
        return False
    
    def create(self, *args, **kwargs):
        logger.warning("NotificationService.create временно отключен")
        return None
    
    def create_shift_confirmation_notification(self, *args, **kwargs):
        logger.warning("NotificationService.create_shift_confirmation_notification временно отключен")
        return {}
    
    def process_pending_reminders(self, *args, **kwargs):
        logger.warning("NotificationService.process_pending_reminders временно отключен")
        return {"processed": 0, "errors": []}