"""Интерфейс транспорта для отправки сообщений (TG/MAX)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass(frozen=True, slots=True)
class MessengerFeatures:
    supports_contact_request: bool = False
    supports_webapp: bool = False


class Messenger(Protocol):
    """Транспортный интерфейс. Бизнес-логика работает только через него."""

    name: str
    features: MessengerFeatures

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = None,
    ) -> None: ...

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
    ) -> Optional[str]: ...

    async def answer_callback(self, callback_id: str, text: str = "") -> None: ...
