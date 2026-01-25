"""Фабрика провайдеров медиа-хранилища."""

from __future__ import annotations

from typing import Any, Optional

from core.config.settings import settings
from core.logging.logger import logger

from .base import MediaStorageClient
from .s3_client import S3MediaStorageClient
from .telegram_client import TelegramMediaStorageClient


def get_media_storage_client(bot: Optional[Any] = None) -> MediaStorageClient:
    """
    Возвращает клиент хранилища по MEDIA_STORAGE_PROVIDER.

    Для provider=telegram при вызове store_telegram_file нужен bot;
    можно передать здесь либо при первом store_telegram_file.
    """
    provider = (settings.media_storage_provider or "telegram").strip().lower()
    logger.debug(f"Media storage provider: {provider}")

    if provider == "telegram":
        return TelegramMediaStorageClient(bot=bot)
    if provider == "minio":
        return S3MediaStorageClient(provider="minio")
    if provider == "selectel":
        return S3MediaStorageClient(provider="selectel")

    raise ValueError(f"Unknown media storage provider: {provider}")
