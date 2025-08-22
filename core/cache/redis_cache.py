"""Redis кэширование для StaffProBot."""

import json
import pickle
from datetime import timedelta
from typing import Any, Dict, List, Optional, Union
from core.config.settings import settings
from core.logging.logger import logger

# Импорт Redis - обязательная зависимость
import redis.asyncio as redis


class RedisCache:
    """Асинхронный Redis кэш с поддержкой JSON и Pickle сериализации."""
    
    def __init__(self, redis_url: str = None, db: int = None):
        """Инициализация Redis клиента."""
        self.redis_url = redis_url or settings.redis_url
        self.db = db or settings.redis_db
        self.redis: Optional[redis.Redis] = None
        self.is_connected = False
    
    async def connect(self) -> None:
        """Подключение к Redis."""
        try:
            self.redis = redis.from_url(
                self.redis_url,
                db=self.db,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Проверка подключения
            await self.redis.ping()
            self.is_connected = True
            logger.info("Redis cache connected successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self) -> None:
        """Отключение от Redis."""
        if self.redis:
            await self.redis.close()
            self.is_connected = False
            logger.info("Redis cache disconnected")
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[Union[int, timedelta]] = None,
        serialize: str = "json"
    ) -> bool:
        """Сохранение значения в кэш.
        
        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
            ttl: Время жизни в секундах или timedelta
            serialize: Тип сериализации ('json' или 'pickle')
        """
        if not self.is_connected:
            logger.warning("Redis not connected, skipping cache set", key=key)
            return False
        
        try:
            # Сериализация значения
            if serialize == "json":
                serialized_value = json.dumps(value, ensure_ascii=False, default=str)
            elif serialize == "pickle":
                serialized_value = pickle.dumps(value)
            else:
                raise ValueError(f"Unsupported serialization type: {serialize}")
            
            # Конвертация TTL
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
            
            # Сохранение в Redis
            success = await self.redis.set(key, serialized_value, ex=ttl_seconds)
            
            if success:
                logger.debug("Cache set successful", key=key, ttl=ttl_seconds, serialize=serialize)
            
            return bool(success)
            
        except Exception as e:
            logger.error(f"Failed to set cache: {e}", key=key, error=str(e))
            return False
    
    async def get(self, key: str, serialize: str = "json") -> Optional[Any]:
        """Получение значения из кэша.
        
        Args:
            key: Ключ для получения
            serialize: Тип десериализации ('json' или 'pickle')
        """
        if not self.is_connected:
            logger.warning("Redis not connected, skipping cache get", key=key)
            return None
        
        try:
            serialized_value = await self.redis.get(key)
            
            if serialized_value is None:
                logger.debug("Cache miss", key=key)
                return None
            
            # Десериализация значения
            if serialize == "json":
                value = json.loads(serialized_value.decode('utf-8'))
            elif serialize == "pickle":
                value = pickle.loads(serialized_value)
            else:
                raise ValueError(f"Unsupported serialization type: {serialize}")
            
            logger.debug("Cache hit", key=key, serialize=serialize)
            return value
            
        except Exception as e:
            logger.error(f"Failed to get cache: {e}", key=key, error=str(e))
            return None
    
    async def delete(self, key: str) -> bool:
        """Удаление значения из кэша."""
        if not self.is_connected:
            logger.warning("Redis not connected, skipping cache delete", key=key)
            return False
        
        try:
            result = await self.redis.delete(key)
            logger.debug("Cache delete", key=key, deleted=bool(result))
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to delete cache: {e}", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа в кэше."""
        if not self.is_connected:
            return False
        
        try:
            result = await self.redis.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check cache existence: {e}", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """Установка TTL для существующего ключа."""
        if not self.is_connected:
            return False
        
        try:
            if isinstance(ttl, timedelta):
                ttl_seconds = int(ttl.total_seconds())
            else:
                ttl_seconds = ttl
            
            result = await self.redis.expire(key, ttl_seconds)
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to set cache expiration: {e}", key=key, error=str(e))
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Получение списка ключей по паттерну."""
        if not self.is_connected:
            return []
        
        try:
            keys = await self.redis.keys(pattern)
            return [key.decode('utf-8') for key in keys]
        except Exception as e:
            logger.error(f"Failed to get cache keys: {e}", pattern=pattern, error=str(e))
            return []
    
    async def clear_pattern(self, pattern: str) -> int:
        """Удаление всех ключей по паттерну."""
        if not self.is_connected:
            return 0
        
        try:
            keys = await self.keys(pattern)
            if keys:
                result = await self.redis.delete(*keys)
                logger.info(f"Cleared {result} cache keys", pattern=pattern)
                return result
            return 0
        except Exception as e:
            logger.error(f"Failed to clear cache pattern: {e}", pattern=pattern, error=str(e))
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики Redis."""
        if not self.is_connected:
            return {}
        
        try:
            info = await self.redis.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                )
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            return {}
    
    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """Расчет hit rate кэша."""
        total = hits + misses
        if total == 0:
            return 0.0
        return round((hits / total) * 100, 2)


# Глобальный экземпляр кэша
cache = RedisCache()


# Декораторы для кэширования
def cached(
    ttl: Union[int, timedelta] = 300,
    key_prefix: str = "",
    serialize: str = "json"
):
    """Декоратор для кэширования результатов функций."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Генерация ключа кэша
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Попытка получить из кэша
            cached_result = await cache.get(cache_key, serialize=serialize)
            if cached_result is not None:
                logger.debug("Cache hit for function", function=func.__name__, key=cache_key)
                return cached_result
            
            # Выполнение функции
            result = await func(*args, **kwargs)
            
            # Сохранение в кэш
            await cache.set(cache_key, result, ttl=ttl, serialize=serialize)
            logger.debug("Cache set for function", function=func.__name__, key=cache_key)
            
            return result
        return wrapper
    return decorator


async def init_cache() -> None:
    """Инициализация кэша при запуске приложения."""
    await cache.connect()


async def close_cache() -> None:
    """Закрытие кэша при остановке приложения."""
    await cache.disconnect()
