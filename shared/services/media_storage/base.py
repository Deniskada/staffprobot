"""Интерфейс и типы медиа-хранилища (restruct1 Фаза 1.3)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# Бот из python-telegram-bot (типизация без импорта в рантайме)
BotType = Any


@dataclass
class MediaFile:
    """Метаданные медиа-файла."""

    key: str
    url: str
    type: str  # "photo" | "video" | "document"
    size: int
    mime_type: str
    uploaded_at: datetime
    metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


class MediaStorageClient(ABC):
    """Абстрактный интерфейс для работы с хранилищем медиа."""

    @abstractmethod
    async def upload(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MediaFile:
        """Загрузить файл в хранилище."""
        ...

    @abstractmethod
    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Получить URL для доступа к файлу (presigned или публичный)."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Удалить файл из хранилища."""
        ...

    @abstractmethod
    async def list_files(
        self, folder: str, prefix: Optional[str] = None
    ) -> List[MediaFile]:
        """Получить список файлов в папке."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Проверить существование файла."""
        ...

    async def store_telegram_file(
        self,
        file_id: str,
        folder: str,
        file_type: str,
        bot: BotType,
    ) -> MediaFile:
        """
        Сохранить файл из Telegram (file_id) в хранилище.
        TG-клиент: регистрирует file_id, возвращает MediaFile.
        S3-клиент: скачивает через bot, загружает в хранилище.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}.store_telegram_file not implemented"
        )
