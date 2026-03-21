"""Обогащение переменных уведомления ссылкой авто-логина (TG и MAX)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.logging.logger import logger
from domain.entities.notification import Notification
from domain.entities.user import User


async def enrich_variables_with_action_link(
    notification: Notification,
    user: User,
    variables: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Добавляет link_url (и accept_url при необходимости) через internal user_id.
    Используется NotificationDispatcher и Celery-отправка.
    """
    out = dict(variables or {})
    try:
        from core.auth.auto_login import build_auto_login_url
        from core.utils.url_helper import URLHelper
        from shared.services.notification_action_service import NotificationActionService

        base_url = await URLHelper.get_web_url()
        user_role = user.role or "employee"
        action_service = NotificationActionService()
        action_path = action_service.get_action_url(notification, user_role)
        if action_path:
            auto_url = await build_auto_login_url(user.id, action_path, base_url)
            out["link_url"] = auto_url
            if "accept_url" in out:
                out["accept_url"] = auto_url
        if "link_url" not in out:
            out["link_url"] = ""
    except Exception as e:
        logger.warning(f"enrich_variables_with_action_link failed: {e}")
        out.setdefault("link_url", "")

    return out
