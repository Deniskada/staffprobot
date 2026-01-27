"""Клиент медиа-хранилища через Telegram (file_id)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.logging.logger import logger

from .base import MediaFile, MediaStorageClient

BotType = Any


# MIME по умолчанию для типа
_DEFAULT_MIME: Dict[str, str] = {
    "photo": "image/jpeg",
    "video": "video/mp4",
    "document": "application/octet-stream",
}


class TelegramMediaStorageClient(MediaStorageClient):
    """
    Хранилище через Telegram file_id.
    get_file → file_path; delete/list_files не поддерживаются.
    """

    def __init__(self, bot: Optional[BotType] = None) -> None:
        self._bot = bot

    async def upload(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MediaFile:
        raise NotImplementedError(
            "Telegram storage does not support upload(bytes). "
            "Use store_telegram_file(file_id, folder, file_type, bot) for TG files."
        )

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Возвращает псевдо-URL «telegram:file_id» для использования в боте (resend по file_id)."""
        return f"telegram:{key}"

    async def delete(self, key: str) -> bool:
        return False

    async def list_files(
        self, folder: str, prefix: Optional[str] = None
    ) -> List[MediaFile]:
        return []

    async def exists(self, key: str) -> bool:
        return True

    async def store_telegram_file(
        self,
        file_id: str,
        folder: str,
        file_type: str,
        bot: BotType,
    ) -> MediaFile:
        if not bot:
            raise ValueError("bot required for TelegramMediaStorageClient.store_telegram_file")
        tg_file = await bot.get_file(file_id)
        size = tg_file.file_size or 0
        mime = _DEFAULT_MIME.get(file_type, "application/octet-stream")
        url = f"telegram:{file_id}"
        key = file_id
        now = datetime.now(timezone.utc)
        m = MediaFile(
            key=key,
            url=url,
            type=file_type,
            size=size,
            mime_type=mime,
            uploaded_at=now,
            metadata={"folder": folder, "file_path": tg_file.file_path or ""},
        )
        logger.debug("Telegram media stored", file_id=file_id, folder=folder)
        return m
