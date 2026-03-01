"""Авто-логин через токены в ссылках бота.

Токен живёт TOKEN_TTL (10 мин) и может использоваться многократно
в пределах этого окна — Telegram делает prefetch ссылок для превью,
что «съедает» одноразовые токены до клика пользователя.
"""

import uuid
from datetime import timedelta
from typing import Optional

from core.cache.redis_cache import cache
from core.logging.logger import logger

TOKEN_PREFIX = "auto_login"
TOKEN_TTL = timedelta(minutes=10)


async def generate_auto_login_token(telegram_id: int) -> str:
    """Генерирует токен для авто-логина и сохраняет в Redis (TTL 10 мин)."""
    token = uuid.uuid4().hex
    key = f"{TOKEN_PREFIX}:{token}"
    await cache.set(key, {"telegram_id": telegram_id}, ttl=TOKEN_TTL)
    return token


async def validate_auto_login_token(token: str) -> Optional[int]:
    """Проверяет токен, возвращает telegram_id. Токен не удаляется — истекает по TTL."""
    key = f"{TOKEN_PREFIX}:{token}"
    data = await cache.get(key)
    if not data:
        return None
    return data.get("telegram_id")


async def build_auto_login_url(
    telegram_id: int, path: str, base_url: str
) -> str:
    """Создаёт URL с авто-логин токеном для вставки в сообщения бота."""
    token = await generate_auto_login_token(telegram_id)
    separator = "&" if "?" in path else "?"
    return f"{base_url}/auth/auto?t={token}&next={path}"
