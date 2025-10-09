"""Отправщики уведомлений."""

from .telegram_sender import TelegramNotificationSender, get_telegram_sender

__all__ = ["TelegramNotificationSender", "get_telegram_sender"]

