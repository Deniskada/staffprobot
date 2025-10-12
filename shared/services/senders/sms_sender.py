"""SMS отправщик уведомлений для StaffProBot (заглушка)."""

from typing import Optional, Dict, Any

from core.logging.logger import logger
from domain.entities.notification import Notification


class SMSNotificationSender:
    """
    Отправщик уведомлений через SMS.
    
    ВНИМАНИЕ: Это заглушка для будущей реализации.
    SMS отправка не реализована и требует интеграции с SMS провайдером.
    
    Возможные провайдеры для будущей реализации:
    - Twilio
    - AWS SNS
    - MessageBird
    - Vonage (Nexmo)
    - СМСЦ (для России)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        sender_name: str = "StaffProBot"
    ):
        """
        Инициализация отправщика.
        
        Args:
            api_key: API ключ SMS провайдера
            api_secret: API secret SMS провайдера
            sender_name: Имя отправителя (если поддерживается провайдером)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.sender_name = sender_name
        
        logger.warning("SMSNotificationSender is a stub - SMS sending is not implemented")
    
    async def send_notification(
        self,
        notification: Notification,
        phone_number: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка уведомления по SMS.
        
        Args:
            notification: Объект уведомления
            phone_number: Номер телефона получателя
            variables: Переменные для шаблона (опционально)
            
        Returns:
            False - SMS отправка не реализована
        """
        logger.warning(
            "SMS sending is not implemented - notification not sent",
            notification_id=notification.id,
            phone_number=phone_number,
            notification_type=notification.type.value
        )
        
        # TODO: Реализовать отправку SMS через выбранный провайдер
        # Пример интеграции с Twilio:
        # from twilio.rest import Client
        # client = Client(account_sid, auth_token)
        # message = client.messages.create(
        #     body=message_text,
        #     from_='+1234567890',
        #     to=phone_number
        # )
        
        return False
    
    async def test_connection(self) -> bool:
        """
        Проверка подключения к SMS API.
        
        Returns:
            False - SMS не сконфигурирован
        """
        logger.warning("SMS sender is not configured - test connection failed")
        return False
    
    def is_configured(self) -> bool:
        """
        Проверка наличия конфигурации.
        
        Returns:
            False - SMS не сконфигурирован
        """
        return False


# Глобальный экземпляр отправщика
_sms_sender: Optional[SMSNotificationSender] = None


def get_sms_sender() -> SMSNotificationSender:
    """
    Получение глобального экземпляра SMS отправщика.
    
    Returns:
        Экземпляр SMSNotificationSender (заглушка)
    """
    global _sms_sender
    
    if _sms_sender is None:
        _sms_sender = SMSNotificationSender()
    
    return _sms_sender

