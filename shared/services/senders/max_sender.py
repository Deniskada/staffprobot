"""Отправка персональных уведомлений в MAX (platform-api)."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from core.config.settings import settings
from core.logging.logger import logger
from domain.entities.notification import Notification, NotificationPriority, NotificationType
from shared.bot_unified.max_client import MaxClient
from shared.templates.notifications import NotificationTemplateManager


class MaxNotificationSender:
    """Отправщик уведомлений в личный чат MAX по external_user_id (user_id в API)."""

    EMOJI_MAP = {
        NotificationType.SHIFT_REMINDER: "⏰",
        NotificationType.SHIFT_CONFIRMED: "✅",
        NotificationType.SHIFT_CANCELLED: "❌",
        NotificationType.SHIFT_STARTED: "🚀",
        NotificationType.SHIFT_COMPLETED: "🏁",
        NotificationType.CONTRACT_SIGNED: "📝",
        NotificationType.CONTRACT_TERMINATED: "🔚",
        NotificationType.CONTRACT_EXPIRING: "⚠️",
        NotificationType.CONTRACT_UPDATED: "✏️",
        NotificationType.OFFER_SENT: "📄",
        NotificationType.OFFER_ACCEPTED: "✅",
        NotificationType.OFFER_REJECTED: "❌",
        NotificationType.WELCOME: "👋",
        NotificationType.PASSWORD_RESET: "🔐",
    }

    def __init__(self, client: Optional[MaxClient] = None):
        self._client = client or MaxClient()

    async def send_notification(
        self,
        notification: Notification,
        max_user_id: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        max_user_id — MessengerAccount.external_user_id (MAX user_id для ?user_id=).
        """
        if not settings.max_bot_token:
            logger.warning("MAX_BOT_TOKEN not set, skip MAX notification")
            return False
        if not settings.max_features_enabled:
            logger.debug("MAX_FEATURES_ENABLED=false, skip MAX notification")
            return False
        if not max_user_id:
            return False
        try:
            template_vars = variables or notification.data or {}
            if notification.message:
                title_to_use = notification.title or "Уведомление"
                message_to_use = notification.message
            else:
                rendered = NotificationTemplateManager.render(
                    notification_type=notification.type_enum,
                    channel=notification.channel_enum,
                    variables=template_vars,
                )
                title_to_use = rendered["title"]
                message_to_use = rendered["message"]

            text = self._format_message(notification, title_to_use, message_to_use)
            text = self._markdownish_to_html(text)
            await self._client.send_to_user(max_user_id, text, format="html")
            logger.info(
                "MAX notification sent",
                notification_id=notification.id,
                max_user_id=max_user_id[:8] + "...",
                type=notification.type,
            )
            return True
        except Exception as e:
            logger.error(
                f"MAX notification failed (notification_id={notification.id}): {e}",
                exc_info=True,
            )
            return False

    def _format_message(
        self,
        notification: Notification,
        title: str,
        message: str,
    ) -> str:
        emoji = self.EMOJI_MAP.get(notification.type_enum, "📢")
        priority_marker = ""
        if notification.priority_enum == NotificationPriority.URGENT:
            priority_marker = "🚨 <b>СРОЧНО!</b>\n\n"
        elif notification.priority_enum == NotificationPriority.HIGH:
            priority_marker = "⚡ <b>Важно!</b>\n\n"
        return f"{priority_marker}{emoji} <b>{title}</b>\n\n{message}"

    @staticmethod
    def _markdownish_to_html(message: str) -> str:
        message = re.sub(r"\*([^*]+)\*", r"<b>\1</b>", message)
        message = re.sub(r"_([^_]+)_", r"<i>\1</i>", message)
        return message


def get_max_sender() -> MaxNotificationSender:
    return MaxNotificationSender()
