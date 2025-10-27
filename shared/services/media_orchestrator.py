"""Единый оркестратор для работы с медиа (фото/видео/документы) в боте и вебе."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import json
import redis.asyncio as redis
from core.config.settings import get_settings
from core.logging.logger import logger


settings = get_settings()


@dataclass
class MediaFlowConfig:
    """Конфигурация медиа-потока для пользователя."""
    user_id: int
    context_type: str  # cancellation_doc | task_proof | incident_evidence | shift_photo
    context_id: int
    require_text: bool = False
    require_photo: bool = False
    max_photos: int = 1
    allow_skip: bool = True
    collected_text: Optional[str] = None
    collected_photos: List[str] = None  # List of file_ids or paths
    
    def __post_init__(self):
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
    
    async def begin_flow(self, cfg: MediaFlowConfig) -> None:
        """Начать новый медиа-поток для пользователя."""
        key = self._make_key(cfg.user_id)
        data = asdict(cfg)
        await self.redis.setex(key, self._ttl, json.dumps(data))
        logger.info(f"Media flow started: user={cfg.user_id}, type={cfg.context_type}, context={cfg.context_id}")
    
    async def get_flow(self, user_id: int) -> Optional[MediaFlowConfig]:
        """Получить текущий медиа-поток пользователя."""
        key = self._make_key(user_id)
        data = await self.redis.get(key)
        if not data:
            return None
        cfg_dict = json.loads(data)
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
    
    async def is_flow_complete(self, user_id: int) -> bool:
        """Проверить, завершён ли поток (все требования выполнены)."""
        cfg = await self.get_flow(user_id)
        if not cfg:
            return False
        
        text_ok = not cfg.require_text or cfg.collected_text
        photos_ok = not cfg.require_photo or len(cfg.collected_photos) > 0
        
        return text_ok and photos_ok
    
    async def finish(self, user_id: int) -> Optional[MediaFlowConfig]:
        """Завершить поток и вернуть финальную конфигурацию."""
        cfg = await self.get_flow(user_id)
        if cfg:
            key = self._make_key(user_id)
            await self.redis.delete(key)
            logger.info(f"Media flow finished: user={user_id}, type={cfg.context_type}")
        return cfg
    
    async def cancel(self, user_id: int) -> None:
        """Отменить поток."""
        key = self._make_key(user_id)
        await self.redis.delete(key)
        logger.info(f"Media flow cancelled: user={user_id}")
    
    async def close(self):
        """Закрыть соединение с Redis."""
        await self.redis.close()


