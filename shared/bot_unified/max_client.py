"""MAX API client: отправка сообщений в platform-api.max.ru."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from core.config.settings import settings
from core.logging.logger import logger

from .messenger import MessengerFeatures


class MaxClient:
    """HTTP-клиент для MAX platform-api."""

    BASE_URL = "https://platform-api.max.ru"

    def __init__(self, token: Optional[str] = None):
        self._token = token or settings.max_bot_token

    def _url(self, path: str) -> str:
        sep = "&" if "?" in path else "?"
        return f"{self.BASE_URL}{path}{sep}access_token={self._token}"

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = None,
    ) -> None:
        """POST /messages — отправка текста."""
        if not self._token:
            logger.warning("MaxClient: MAX_BOT_TOKEN not set, skip send")
            return
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if keyboard:
            payload["keyboard"] = keyboard
        async with httpx.AsyncClient() as client:
            r = await client.post(self._url("/messages"), json=payload)
            r.raise_for_status()

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        """POST /answers — подтверждение callback."""
        if not self._token:
            return
        payload = {"callback_id": callback_id, "text": text or "ok"}
        async with httpx.AsyncClient() as client:
            r = await client.post(self._url("/answers"), json=payload)
            r.raise_for_status()


class MaxMessenger:
    """Messenger-реализация для MAX."""

    name = "max"
    features = MessengerFeatures(supports_contact_request=False, supports_webapp=False)

    def __init__(self, client: Optional[MaxClient] = None):
        self._client = client or MaxClient()

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = None,
    ) -> None:
        await self._client.send_text(chat_id, text, keyboard, parse_mode)

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
    ) -> None:
        # TODO: MAX upload flow (POST /uploads?type=image)
        if caption:
            await self._client.send_text(chat_id, f"{photo}\n{caption}", keyboard)
        else:
            await self._client.send_text(chat_id, photo, keyboard)

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        await self._client.answer_callback(callback_id, text)
