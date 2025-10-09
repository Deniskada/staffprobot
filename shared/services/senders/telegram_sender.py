"""Telegram отправщик уведомлений для StaffProBot."""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from telegram import Bot
from telegram.error import TelegramError, BadRequest, Forbidden, NetworkError
from telegram.constants import ParseMode

from core.logging.logger import logger
from core.config.settings import settings
from domain.entities.notification import (
    Notification,
    NotificationType,
    NotificationStatus,
    NotificationPriority
)
from shared.templates.notifications import NotificationTemplateManager


class TelegramNotificationSender:
    """Отправщик уведомлений через Telegram."""
    
    # Эмодзи для разных типов уведомлений
    EMOJI_MAP = {
        # Смены
        NotificationType.SHIFT_REMINDER: "⏰",
        NotificationType.SHIFT_CONFIRMED: "✅",
        NotificationType.SHIFT_CANCELLED: "❌",
        NotificationType.SHIFT_STARTED: "🚀",
        NotificationType.SHIFT_COMPLETED: "🏁",
        
        # Договоры
        NotificationType.CONTRACT_SIGNED: "📝",
        NotificationType.CONTRACT_TERMINATED: "🔚",
        NotificationType.CONTRACT_EXPIRING: "⚠️",
        NotificationType.CONTRACT_UPDATED: "✏️",
        
        # Отзывы
        NotificationType.REVIEW_RECEIVED: "⭐",
        NotificationType.REVIEW_MODERATED: "✓",
        NotificationType.APPEAL_SUBMITTED: "⚖️",
        NotificationType.APPEAL_DECISION: "🔨",
        
        # Платежи
        NotificationType.PAYMENT_DUE: "💳",
        NotificationType.PAYMENT_SUCCESS: "💰",
        NotificationType.PAYMENT_FAILED: "⚠️",
        NotificationType.SUBSCRIPTION_EXPIRING: "⏳",
        NotificationType.SUBSCRIPTION_EXPIRED: "⏰",
        NotificationType.USAGE_LIMIT_WARNING: "📊",
        NotificationType.USAGE_LIMIT_EXCEEDED: "🚫",
        
        # Системные
        NotificationType.WELCOME: "👋",
        NotificationType.PASSWORD_RESET: "🔐",
        NotificationType.ACCOUNT_SUSPENDED: "⛔",
        NotificationType.ACCOUNT_ACTIVATED: "✅",
        NotificationType.SYSTEM_MAINTENANCE: "🔧",
        NotificationType.FEATURE_ANNOUNCEMENT: "🎉"
    }
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Инициализация отправщика.
        
        Args:
            bot_token: Токен бота (опционально, по умолчанию из settings)
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        if not self.bot_token:
            raise ValueError("Telegram bot token is not configured")
        
        self.bot = Bot(token=self.bot_token)
        self.max_retries = 3
        self.retry_delay = 2  # секунды
    
    async def send_notification(
        self,
        notification: Notification,
        telegram_id: int,
        variables: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Отправка уведомления в Telegram.
        
        Args:
            notification: Объект уведомления
            telegram_id: Telegram ID получателя
            variables: Переменные для шаблона (опционально, можно взять из notification.data)
            
        Returns:
            True если отправлено успешно
        """
        try:
            # Подготавливаем переменные для шаблона
            template_vars = variables or notification.data or {}
            
            # Рендерим шаблон
            rendered = NotificationTemplateManager.render(
                notification_type=notification.type,
                channel=notification.channel,
                variables=template_vars
            )
            
            # Форматируем сообщение для Telegram
            message = self._format_message(
                notification=notification,
                title=rendered["title"],
                message=rendered["message"]
            )
            
            # Определяем parse_mode (используем HTML для Telegram)
            parse_mode = ParseMode.HTML
            
            # Отправляем с повторными попытками
            success = await self._send_with_retry(
                telegram_id=telegram_id,
                message=message,
                parse_mode=parse_mode,
                notification=notification
            )
            
            if success:
                logger.info(
                    f"Telegram notification sent successfully",
                    notification_id=notification.id,
                    telegram_id=telegram_id,
                    type=notification.type.value
                )
            else:
                logger.error(
                    f"Failed to send Telegram notification",
                    notification_id=notification.id,
                    telegram_id=telegram_id,
                    type=notification.type.value
                )
            
            return success
            
        except Exception as e:
            logger.error(
                f"Error sending Telegram notification: {e}",
                notification_id=notification.id,
                telegram_id=telegram_id,
                error=str(e)
            )
            return False
    
    async def _send_with_retry(
        self,
        telegram_id: int,
        message: str,
        parse_mode: str,
        notification: Notification
    ) -> bool:
        """
        Отправка сообщения с повторными попытками.
        
        Args:
            telegram_id: Telegram ID получателя
            message: Текст сообщения
            parse_mode: Режим парсинга (HTML/Markdown)
            notification: Объект уведомления для обновления статуса
            
        Returns:
            True если отправлено успешно
        """
        import asyncio
        
        for attempt in range(self.max_retries):
            try:
                # Отправляем сообщение
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=message,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True
                )
                
                return True
                
            except Forbidden as e:
                # Пользователь заблокировал бота - не повторяем
                logger.warning(
                    f"User blocked the bot",
                    telegram_id=telegram_id,
                    notification_id=notification.id,
                    error=str(e)
                )
                return False
                
            except BadRequest as e:
                # Неверный запрос (например, неверный chat_id) - не повторяем
                logger.warning(
                    f"Bad request to Telegram API",
                    telegram_id=telegram_id,
                    notification_id=notification.id,
                    error=str(e)
                )
                return False
                
            except NetworkError as e:
                # Сетевая ошибка - повторяем
                logger.warning(
                    f"Network error, attempt {attempt + 1}/{self.max_retries}",
                    telegram_id=telegram_id,
                    notification_id=notification.id,
                    error=str(e)
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return False
                    
            except TelegramError as e:
                # Другая ошибка Telegram API - повторяем
                logger.warning(
                    f"Telegram API error, attempt {attempt + 1}/{self.max_retries}",
                    telegram_id=telegram_id,
                    notification_id=notification.id,
                    error=str(e)
                )
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return False
                    
            except Exception as e:
                # Неожиданная ошибка
                logger.error(
                    f"Unexpected error sending Telegram message",
                    telegram_id=telegram_id,
                    notification_id=notification.id,
                    error=str(e)
                )
                return False
        
        return False
    
    def _format_message(
        self,
        notification: Notification,
        title: str,
        message: str
    ) -> str:
        """
        Форматирование сообщения для Telegram.
        
        Args:
            notification: Объект уведомления
            title: Заголовок
            message: Текст сообщения
            
        Returns:
            Отформатированное сообщение
        """
        # Получаем эмодзи для типа уведомления
        emoji = self.EMOJI_MAP.get(notification.type, "📢")
        
        # Добавляем маркер приоритета для срочных уведомлений
        priority_marker = ""
        if notification.priority == NotificationPriority.URGENT:
            priority_marker = "🚨 <b>СРОЧНО!</b>\n\n"
        elif notification.priority == NotificationPriority.HIGH:
            priority_marker = "⚡ <b>Важно!</b>\n\n"
        
        # Конвертируем переносы строк для HTML
        formatted_message = message.replace('\n', '\n')
        
        # Собираем финальное сообщение
        final_message = (
            f"{priority_marker}"
            f"{emoji} <b>{title}</b>\n\n"
            f"{formatted_message}"
        )
        
        # Добавляем timestamp для срочных уведомлений
        if notification.priority in [NotificationPriority.URGENT, NotificationPriority.HIGH]:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
            final_message += f"\n\n<i>Отправлено: {timestamp} UTC</i>"
        
        return final_message
    
    async def send_bulk_notifications(
        self,
        notifications: list[tuple[Notification, int, Optional[Dict[str, Any]]]]
    ) -> Dict[str, Any]:
        """
        Массовая отправка уведомлений.
        
        Args:
            notifications: Список кортежей (notification, telegram_id, variables)
            
        Returns:
            Статистика отправки: {sent: int, failed: int, errors: list}
        """
        results = {
            "sent": 0,
            "failed": 0,
            "errors": []
        }
        
        for notification, telegram_id, variables in notifications:
            try:
                success = await self.send_notification(
                    notification=notification,
                    telegram_id=telegram_id,
                    variables=variables
                )
                
                if success:
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "notification_id": notification.id,
                        "telegram_id": telegram_id,
                        "reason": "Send failed"
                    })
                    
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "notification_id": notification.id,
                    "telegram_id": telegram_id,
                    "reason": str(e)
                })
                
                logger.error(
                    f"Error in bulk notification send",
                    notification_id=notification.id,
                    telegram_id=telegram_id,
                    error=str(e)
                )
        
        logger.info(
            f"Bulk notification send completed",
            sent=results["sent"],
            failed=results["failed"],
            total=len(notifications)
        )
        
        return results
    
    async def test_connection(self) -> bool:
        """
        Проверка подключения к Telegram API.
        
        Returns:
            True если подключение работает
        """
        try:
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot connected: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Telegram API: {e}", error=str(e))
            return False


# Глобальный экземпляр отправщика
_telegram_sender: Optional[TelegramNotificationSender] = None


def get_telegram_sender() -> TelegramNotificationSender:
    """
    Получение глобального экземпляра Telegram отправщика.
    
    Returns:
        Экземпляр TelegramNotificationSender
    """
    global _telegram_sender
    
    if _telegram_sender is None:
        _telegram_sender = TelegramNotificationSender()
    
    return _telegram_sender

