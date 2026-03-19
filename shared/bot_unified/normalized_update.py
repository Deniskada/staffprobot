"""Unified DTO для TG/MAX входящих апдейтов."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class NormalizedUpdate:
    """
    Унифицированный вход для TG/MAX.
    """

    type: str  # "message" | "callback"
    chat_id: str
    text: str = ""
    messenger: str = "telegram"  # "telegram" | "max" — источник апдейта

    callback_data: Optional[str] = None
    callback_id: Optional[str] = None

    external_user_id: Optional[str] = None  # TG user.id / MAX user_id для резолва
    from_username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    contact_phone: Optional[str] = None

    photo_file_id: Optional[str] = None
    photo_url: Optional[str] = None

    location: Optional[dict[str, float]] = None
    raw: Optional[dict[str, Any]] = None

    def is_message(self) -> bool:
        return self.type == "message"

    def is_callback(self) -> bool:
        return self.type == "callback"
