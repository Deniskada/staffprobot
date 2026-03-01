"""Авто-логин через одноразовые токены в ссылках бота."""

import uuid
from datetime import timedelta
from typing import Optional

from core.cache.redis_cache import cache
from core.logging.logger import logger

TOKEN_PREFIX = "auto_login"
TOKEN_TTL = timedelta(minutes=10)


async def generate_auto_login_token(telegram_id: int) -> str:
    """Генерирует одноразовый токен для авто-логина и сохраняет в Redis."""
    token = uuid.uuid4().hex
    key = f"{TOKEN_PREFIX}:{token}"
    await cache.set(key, {"telegram_id": telegram_id}, ttl=TOKEN_TTL)
    return token


async def validate_auto_login_token(token: str) -> Optional[int]:
    """Проверяет токен, возвращает telegram_id и удаляет токен (одноразовый)."""
    key = f"{TOKEN_PREFIX}:{token}"
    data = await cache.get(key)
    if not data:
        return None
    await cache.delete(key)
    return data.get("telegram_id")


async def build_auto_login_url(
    telegram_id: int, path: str, base_url: str
) -> str:
    """Создаёт URL с авто-логин токеном для вставки в сообщения бота."""
    token = await generate_auto_login_token(telegram_id)
    separator = "&" if "?" in path else "?"
    return f"{base_url}/auth/auto?t={token}&next={path}"
