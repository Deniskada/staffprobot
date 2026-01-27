"""Единое медиа-хранилище (restruct1 Фаза 1). Провайдеры: telegram, minio, s3 (reg.ru, Cloud.ru, AWS и т.д.)."""

from shared.services.media_storage.base import MediaFile, MediaStorageClient
from shared.services.media_storage.factory import get_media_storage_client

__all__ = ["MediaFile", "MediaStorageClient", "get_media_storage_client"]
