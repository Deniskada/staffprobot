"""Отправщики уведомлений."""

from .telegram_sender import TelegramNotificationSender, get_telegram_sender
from .email_sender import EmailNotificationSender, get_email_sender

__all__ = [
    "TelegramNotificationSender",
    "get_telegram_sender",
    "EmailNotificationSender",
    "get_email_sender"
]

