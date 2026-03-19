"""Сервис одноразовых кодов привязки MAX к user_id (Redis)."""

import secrets
from typing import Optional

from core.cache.redis_cache import cache
from core.logging.logger import logger

LINK_KEY_PREFIX = "link:max:"
TTL_SECONDS = 600  # 10 минут


async def generate_max_link_code(user_id: int) -> tuple[str, int]:
    """
    Сгенерировать одноразовый код для привязки MAX.
    Возвращает (code, expires_in_seconds).
    """
    code = secrets.token_hex(3).upper()[:6]
    key = f"{LINK_KEY_PREFIX}{code}"
    try:
        ok = await cache.set(key, str(user_id), ttl=TTL_SECONDS, serialize="json")
        if ok:
            return code, TTL_SECONDS
    except Exception as e:
        logger.error(f"generate_max_link_code: {e}", exc_info=True)
    return "", 0


async def consume_max_link_code(code: str) -> Optional[int]:
    """
    Проверить код и вернуть user_id. Код одноразовый — удаляется после использования.
    """
    if not code or len(code) != 6 or not code.isalnum():
        return None
    key = f"{LINK_KEY_PREFIX}{code.upper()}"
    try:
        val = await cache.get(key, serialize="json")
        await cache.delete(key)
        if val is not None:
            return int(val) if isinstance(val, str) else int(val)
    except Exception as e:
        logger.error(f"consume_max_link_code: {e}", exc_info=True)
    return None
