"""Единый оркестратор для работы с медиа (фото/видео/документы) в боте и вебе."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import json
import redis.asyncio as redis
from core.config.settings import settings
from core.logging.logger import logger
from shared.services.media_storage.base import MediaFile


def _folder_for_context(context_type: str, context_id: int) -> str:
    if context_type == "cancellation_doc":
        return f"cancellations/{context_id}"
    if context_type in ("task_proof", "task_v2_proof"):
        return f"tasks/{context_id}"
    if context_type == "incident_evidence":
        return f"incidents/{context_id}"
    return f"misc/{context_id}"


@dataclass
class MediaFlowConfig:
    """Конфигурация медиа-потока для пользователя."""
    user_id: int
    context_type: str  # cancellation_doc | task_proof | incident_evidence | shift_photo | task_v2_proof
    context_id: int
    require_text: bool = False
    require_photo: bool = False
    max_photos: int = 1
    allow_skip: bool = True
    collected_text: Optional[str] = None
    collected_photos: List[str] = field(default_factory=list)  # file_ids
    uploaded_media: Optional[List[Any]] = None  # List[MediaFile] после finish; не хранится в Redis

    def __post_init__(self) -> None:
        if self.collected_photos is None:
            self.collected_photos = []


class MediaOrchestrator:
    """
    Единый оркестратор для управления потоками медиа.
    Хранит состояние в Redis, поддерживает бот и веб.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self._key_prefix = "media_flow:"
        self._ttl = 3600  # 1 час
    
    def _make_key(self, user_id: int) -> str:
        return f"{self._key_prefix}{user_id}"
    
    def _to_redis_dict(self, cfg: MediaFlowConfig) -> Dict[str, Any]:
        d = asdict(cfg)
        d.pop("uploaded_media", None)
        return d

    async def begin_flow(self, cfg: MediaFlowConfig) -> None:
        """Начать новый медиа-поток для пользователя."""
        key = self._make_key(cfg.user_id)
        data = self._to_redis_dict(cfg)
        await self.redis.setex(key, self._ttl, json.dumps(data))
        logger.info(
            f"Media flow started: user={cfg.user_id}, type={cfg.context_type}, context={cfg.context_id}"
        )
    
    async def get_flow(self, user_id: int) -> Optional[MediaFlowConfig]:
        """Получить текущий медиа-поток пользователя."""
        key = self._make_key(user_id)
        data = await self.redis.get(key)
        if not data:
            return None
        cfg_dict = json.loads(data)
        cfg_dict.pop("uploaded_media", None)
        return MediaFlowConfig(**cfg_dict)
    
    async def update_flow(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Обновить медиа-поток."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return False
        
        for key, value in updates.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        
        await self.begin_flow(cfg)  # Re-save with updated TTL
        return True
    
    async def add_text(self, user_id: int, text: str) -> bool:
        """Добавить текст в поток."""
        return await self.update_flow(user_id, {"collected_text": text})
    
    async def add_photo(self, user_id: int, file_id: str) -> bool:
        """Добавить фото в поток."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return False
        
        if len(cfg.collected_photos) >= cfg.max_photos:
            logger.warning(f"Max photos reached for user {user_id}")
            return False
        
        cfg.collected_photos.append(file_id)
        await self.begin_flow(cfg)
        return True
    
    async def get_collected_count(self, user_id: int) -> int:
        """Получить количество собранных файлов."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return 0
        return len(cfg.collected_photos) if cfg.collected_photos else 0
    
    async def can_add_more(self, user_id: int) -> bool:
        """Проверить, можно ли добавить еще файлов."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return False
        current_count = len(cfg.collected_photos) if cfg.collected_photos else 0
        return current_count < cfg.max_photos
    
    async def is_flow_complete(self, user_id: int) -> bool:
        """Проверить, завершён ли поток (все требования выполнены)."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return False
        text_ok = not cfg.require_text or bool(cfg.collected_text)
        photos_ok = not cfg.require_photo or (len(cfg.collected_photos or []) > 0)
        result: bool = bool(text_ok and photos_ok)
        return result
    
    async def finish(
        self,
        user_id: int,
        bot: Any = None,
        media_types: Optional[Dict[str, str]] = None,
        storage_mode: Optional[str] = None,
    ) -> Optional[MediaFlowConfig]:
        """
        Завершить поток и вернуть финальную конфигурацию.
        Если передан bot и есть collected_photos, загружает медиа в хранилище.
        storage_mode: "telegram" | "storage" | "both" — из настроек владельца; иначе глобальный провайдер.
        """
        cfg = await self.get_flow(user_id)
        if not cfg:
            return None
        key = self._make_key(user_id)
        await self.redis.delete(key)
        logger.info(f"Media flow finished: user={user_id}, type={cfg.context_type}")

        if bot and cfg.collected_photos:
            logger.info(
                "Starting media upload in finish",
                user_id=user_id,
                context_type=cfg.context_type,
                context_id=cfg.context_id,
                photos_count=len(cfg.collected_photos),
                storage_mode=storage_mode,
            )
            try:
                from core.config.settings import settings
                from shared.services.media_storage import get_media_storage_client
                override = None
                uploaded: List[Any] = []
                folder = _folder_for_context(cfg.context_type, cfg.context_id)
                types_map = media_types or {}
                
                if storage_mode == "both":
                    # Загружаем в оба хранилища: сначала в S3, затем сохраняем telegram file_id
                    p = (settings.media_storage_provider or "minio").strip().lower()
                    s3_override = p if p in ("minio", "selectel") else "minio"
                    
                    logger.info(
                        "Getting S3 storage client for 'both' mode",
                        user_id=user_id,
                        provider_override=s3_override,
                    )
                    
                    s3_storage = get_media_storage_client(bot=bot, provider_override=s3_override)
                    telegram_storage = get_media_storage_client(bot=bot, provider_override="telegram")
                    
                    for idx, fid in enumerate(cfg.collected_photos):
                        ftype = types_map.get(fid, "photo")
                        logger.info(
                            "Uploading to S3 (both mode)",
                            user_id=user_id,
                            file_index=idx + 1,
                            total=len(cfg.collected_photos),
                            folder=folder,
                            file_type=ftype,
                        )
                        # Загружаем в S3
                        s3_media = await s3_storage.store_telegram_file(fid, folder, ftype, bot)
                        # Получаем telegram file_id
                        tg_media = await telegram_storage.store_telegram_file(fid, folder, ftype, bot)
                        
                        # Создаем MediaFile с информацией о обоих хранилищах
                        # Используем S3 key как основной, но сохраняем telegram_file_id в metadata
                        m = MediaFile(
                            key=s3_media.key,
                            url=s3_media.url,
                            type=ftype,
                            size=s3_media.size,
                            mime_type=s3_media.mime_type,
                            uploaded_at=s3_media.uploaded_at,
                            metadata={
                                **(s3_media.metadata or {}),
                                "telegram_file_id": tg_media.key,  # Сохраняем telegram file_id в metadata
                            },
                        )
                        uploaded.append(m)
                        logger.info(
                            "File uploaded to both storages",
                            user_id=user_id,
                            file_index=idx + 1,
                            s3_key=s3_media.key,
                            telegram_file_id=tg_media.key,
                        )
                elif storage_mode == "telegram":
                    override = "telegram"
                    logger.info(
                        "Getting Telegram storage client",
                        user_id=user_id,
                        storage_mode=storage_mode,
                    )
                    storage = get_media_storage_client(bot=bot, provider_override=override)
                    for idx, fid in enumerate(cfg.collected_photos):
                        ftype = types_map.get(fid, "photo")
                        logger.info(
                            "Uploading telegram file",
                            user_id=user_id,
                            file_index=idx + 1,
                            total=len(cfg.collected_photos),
                            folder=folder,
                            file_type=ftype,
                        )
                        m = await storage.store_telegram_file(fid, folder, ftype, bot)
                        uploaded.append(m)
                        logger.info(
                            "File uploaded successfully",
                            user_id=user_id,
                            file_index=idx + 1,
                            key=m.key,
                            url=m.url,
                        )
                elif storage_mode == "storage":
                    p = (settings.media_storage_provider or "minio").strip().lower()
                    override = p if p in ("minio", "selectel") else "minio"
                    logger.info(
                        "Getting S3 storage client",
                        user_id=user_id,
                        storage_mode=storage_mode,
                        provider_override=override,
                    )
                    storage = get_media_storage_client(bot=bot, provider_override=override)
                    for idx, fid in enumerate(cfg.collected_photos):
                        ftype = types_map.get(fid, "photo")
                        logger.info(
                            "Uploading to S3",
                            user_id=user_id,
                            file_index=idx + 1,
                            total=len(cfg.collected_photos),
                            folder=folder,
                            file_type=ftype,
                        )
                        m = await storage.store_telegram_file(fid, folder, ftype, bot)
                        uploaded.append(m)
                        logger.info(
                            "File uploaded successfully",
                            user_id=user_id,
                            file_index=idx + 1,
                            key=m.key,
                            url=m.url,
                        )
                
                cfg.uploaded_media = uploaded
                logger.info(
                    "All media uploaded successfully",
                    user_id=user_id,
                    uploaded_count=len(uploaded),
                )
            except Exception as e:
                logger.exception(
                    "Media storage upload failed, continuing without uploaded_media",
                    user_id=user_id,
                    context_type=cfg.context_type,
                    context_id=cfg.context_id,
                    error=str(e),
                )
        elif not bot:
            logger.warning("No bot provided for media upload", user_id=user_id)
        elif not cfg.collected_photos:
            logger.warning("No collected photos to upload", user_id=user_id)

        return cfg
    
    async def cancel(self, user_id: int) -> None:
        """Отменить поток."""
        key = self._make_key(user_id)
        await self.redis.delete(key)
        logger.info(f"Media flow cancelled: user={user_id}")
    
    async def close(self):
        """Закрыть соединение с Redis."""
        await self.redis.close()


