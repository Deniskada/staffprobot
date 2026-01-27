"""Фабрика провайдеров медиа-хранилища."""

from __future__ import annotations

from typing import Any, Optional

from core.config.settings import settings
from core.logging.logger import logger

from .base import MediaStorageClient
from .s3_client import S3MediaStorageClient
from .telegram_client import TelegramMediaStorageClient


def get_media_storage_client(
    bot: Optional[Any] = None,
    provider_override: Optional[str] = None,
) -> MediaStorageClient:
    """
    Возвращает клиент хранилища.

    provider_override: "telegram" | "minio" | "s3" — использовать вместо настроек.
    Иначе берётся MEDIA_STORAGE_PROVIDER из settings.
    s3 — любой S3-совместимый провайдер (reg.ru, Cloud.ru, AWS и т.д.).
    """
    base = (settings.media_storage_provider or "telegram").strip().lower()
    provider = (provider_override or base).strip().lower()
    logger.debug(f"Media storage provider: {provider}")

    if provider == "telegram":
        return TelegramMediaStorageClient(bot=bot)
    if provider == "minio":
        return S3MediaStorageClient(provider="minio")
    if provider == "s3":
        return S3MediaStorageClient(provider="s3")

    raise ValueError(f"Unknown media storage provider: {provider}")
