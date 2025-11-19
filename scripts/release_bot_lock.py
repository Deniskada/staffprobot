#!/usr/bin/env python3
"""Утилита для ручного снятия блокировки bot polling."""

import asyncio
import json
from typing import Optional

from core.cache.redis_cache import cache, init_cache, close_cache

LOCK_KEY = "bot_polling_lock"
HEARTBEAT_KEY = "bot_polling_heartbeat"


async def release_lock() -> None:
    await init_cache()
    try:
        metadata: Optional[str] = None
        if cache.is_connected and cache.redis:
            existing = await cache.redis.get(LOCK_KEY)
            metadata = existing.decode("utf-8") if existing else None
        removed = await cache.delete(LOCK_KEY)
        await cache.delete(HEARTBEAT_KEY)
        message = {
            "lock_removed": bool(removed),
            "previous_value": metadata,
        }
        print(json.dumps(message, ensure_ascii=False, indent=2))
    finally:
        await close_cache()


if __name__ == "__main__":
    asyncio.run(release_lock())

