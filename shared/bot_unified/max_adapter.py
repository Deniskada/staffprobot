"""MAX webhook JSON → NormalizedUpdate."""

from __future__ import annotations

from typing import Any, Optional

from .normalized_update import NormalizedUpdate


class MaxAdapter:
    """Парсинг MAX webhook payload → NormalizedUpdate."""

    @staticmethod
    def parse(raw: dict[str, Any]) -> Optional[NormalizedUpdate]:
        """JSON webhook → NormalizedUpdate. None если тип не поддерживается."""
        update_type = raw.get("update_type")
        if not update_type:
            return None

        if update_type == "message_created":
            msg = raw.get("message") or {}
            recipient = msg.get("recipient") or {}
            body = msg.get("body") or {}
            chat_id = str(recipient.get("chat_id", ""))
            text = (body.get("text") or "").strip()
            sender = msg.get("sender") or {}
            return NormalizedUpdate(
                type="message",
                chat_id=chat_id,
                text=text,
                messenger="max",
                external_user_id=str(sender.get("user_id", "")) or None,
                from_username=sender.get("username"),
                first_name=sender.get("first_name"),
                last_name=sender.get("last_name"),
                raw=raw,
            )

        if update_type == "message_callback":
            cb = raw.get("callback") or {}
            msg = raw.get("message") or {}
            recipient = msg.get("recipient") or {}
            chat_id = str(recipient.get("chat_id", ""))
            callback_id = cb.get("callback_id")
            payload = cb.get("payload") or ""
            return NormalizedUpdate(
                type="callback",
                chat_id=chat_id,
                text="",
                messenger="max",
                callback_data=payload if isinstance(payload, str) else str(payload),
                callback_id=str(callback_id) if callback_id else None,
                raw=raw,
            )

        if update_type == "bot_started":
            chat_id = str(raw.get("chat_id", ""))
            payload = raw.get("payload") or ""
            # Конвертируем в /start для переиспользования логики
            text = f"/start {payload}".strip()
            return NormalizedUpdate(
                type="message",
                chat_id=chat_id,
                text=text,
                messenger="max",
                external_user_id=str(raw.get("user_id", "")) or None,
                raw=raw,
            )

        return None
