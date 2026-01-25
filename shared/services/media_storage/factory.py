"""Фабрика провайдеров медиа-хранилища."""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.config.settings import settings
from core.logging.logger import logger

if TYPE_CHECKING:
    pass  # MediaStorageClient — в Фазе 1.3


def get_media_storage_client():
    """
    Возвращает клиент хранилища по конфигу MEDIA_STORAGE_PROVIDER.

    Реализации (TelegramMediaStorageClient, S3MediaStorageClient) — Фаза 1.3.
    До этого вызов поднимает NotImplementedError.
    """
    provider = (settings.media_storage_provider or "telegram").strip().lower()
    logger.debug(f"Media storage provider: {provider}")

    if provider == "telegram":
        # В 1.3: from .telegram_client import TelegramMediaStorageClient; return TelegramMediaStorageClient()
        raise NotImplementedError(
            "MediaStorageClient not implemented yet (Phase 1.3). "
            "Use MediaOrchestrator with Telegram file_id until then."
        )
    if provider in ("minio", "selectel"):
        # В 1.3: from .s3_client import S3MediaStorageClient; return S3MediaStorageClient(...)
        raise NotImplementedError(
            f"MediaStorageClient for '{provider}' not implemented yet (Phase 1.3). "
            "Set MEDIA_STORAGE_PROVIDER=telegram for current behaviour."
        )

    raise ValueError(f"Unknown media storage provider: {provider}")
