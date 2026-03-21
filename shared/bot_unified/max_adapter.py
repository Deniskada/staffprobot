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
            sender = msg.get("sender") or {}
            chat_id = str(
                recipient.get("chat_id") or recipient.get("user_id") or sender.get("user_id") or ""
            )
            text = (body.get("text") or "").strip()
            location = None
            photo_url = None
            photo_token = None
            for att in body.get("attachments") or []:
                att_type = att.get("type")
                payload = att.get("payload") or att
                if att_type in ("location", "geo", "geolocation") and location is None:
                    lat = payload.get("latitude") or payload.get("lat")
                    lon = payload.get("longitude") or payload.get("lon") or payload.get("lng")
                    if lat is not None and lon is not None:
                        location = {"latitude": float(lat), "longitude": float(lon)}
                if att_type == "image" and photo_url is None and photo_token is None:
                    photo_url = payload.get("url") or payload.get("preview_url")
                    photo_token = payload.get("token")
            return NormalizedUpdate(
                type="message",
                chat_id=chat_id,
                text=text,
                messenger="max",
                external_user_id=str(sender.get("user_id", "")) or None,
                from_username=sender.get("username"),
                first_name=sender.get("first_name"),
                last_name=sender.get("last_name"),
                location=location,
                photo_url=photo_url,
                photo_token=photo_token,
                raw=raw,
            )

        if update_type == "message_callback":
            cb = raw.get("callback") or {}
            msg = raw.get("message") or {}
            recipient = msg.get("recipient") or {}
            user = cb.get("user") or {}
            sender_msg = msg.get("sender") or {}
            chat_id = str(
                recipient.get("chat_id")
                or recipient.get("user_id")
                or user.get("user_id")
                or sender_msg.get("user_id")
                or raw.get("chat_id")
                or ""
            )
            callback_id = cb.get("callback_id")
            payload = cb.get("payload") or ""
            uid = user.get("user_id")
            if uid is None or str(uid).strip() == "":
                uid = sender_msg.get("user_id")
            ext_uid = str(uid).strip() if uid is not None and str(uid).strip() != "" else None
            return NormalizedUpdate(
                type="callback",
                chat_id=chat_id,
                text="",
                messenger="max",
                callback_data=payload if isinstance(payload, str) else str(payload),
                callback_id=str(callback_id) if callback_id else None,
                external_user_id=ext_uid,
                raw=raw,
            )

        if update_type == "bot_started":
            chat_id = str(raw.get("chat_id", "") or raw.get("user_id", ""))
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
