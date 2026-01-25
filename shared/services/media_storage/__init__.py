"""Единое медиа-хранилище (restruct1 Фаза 1). Провайдеры: telegram, minio, selectel."""

from shared.services.media_storage.factory import get_media_storage_client

__all__ = ["get_media_storage_client"]
