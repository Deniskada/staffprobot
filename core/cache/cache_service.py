"""Сервис кэширования для бизнес-объектов StaffProBot."""

from datetime import timedelta
from typing import List, Optional, Dict, Any
from core.cache.redis_cache import cache, cached
from core.logging.logger import logger


class CacheService:
    """Сервис для кэширования бизнес-объектов."""
    
    # Префиксы ключей
    USER_PREFIX = "user"
    OBJECT_PREFIX = "object"
    SHIFT_PREFIX = "shift"
    ACTIVE_SHIFTS_PREFIX = "active_shifts"
    USER_OBJECTS_PREFIX = "user_objects"
    ANALYTICS_PREFIX = "analytics"
    
    # TTL по умолчанию
    DEFAULT_TTL = timedelta(minutes=15)
    SHORT_TTL = timedelta(minutes=5)
    LONG_TTL = timedelta(hours=1)
    
    @classmethod
    async def get_user(cls, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя из кэша."""
        key = f"{cls.USER_PREFIX}:{user_id}"
        return await cache.get(key)
    
    @classmethod
    async def set_user(cls, user_id: int, user_data: Dict[str, Any], ttl: timedelta = None) -> bool:
        """Сохранение пользователя в кэш."""
        key = f"{cls.USER_PREFIX}:{user_id}"
        return await cache.set(key, user_data, ttl=ttl or cls.DEFAULT_TTL)
    
    @classmethod
    async def delete_user(cls, user_id: int) -> bool:
        """Удаление пользователя из кэша."""
        key = f"{cls.USER_PREFIX}:{user_id}"
        return await cache.delete(key)
    
    @classmethod
    async def get_object(cls, object_id: int) -> Optional[Dict[str, Any]]:
        """Получение объекта из кэша."""
        key = f"{cls.OBJECT_PREFIX}:{object_id}"
        return await cache.get(key)
    
    @classmethod
    async def set_object(cls, object_id: int, object_data: Dict[str, Any], ttl: timedelta = None) -> bool:
        """Сохранение объекта в кэш."""
        key = f"{cls.OBJECT_PREFIX}:{object_id}"
        return await cache.set(key, object_data, ttl=ttl or cls.DEFAULT_TTL)
    
    @classmethod
    async def delete_object(cls, object_id: int) -> bool:
        """Удаление объекта из кэша."""
        key = f"{cls.OBJECT_PREFIX}:{object_id}"
        return await cache.delete(key)
    
    @classmethod
    async def get_shift(cls, shift_id: int) -> Optional[Dict[str, Any]]:
        """Получение смены из кэша."""
        key = f"{cls.SHIFT_PREFIX}:{shift_id}"
        return await cache.get(key)
    
    @classmethod
    async def set_shift(cls, shift_id: int, shift_data: Dict[str, Any], ttl: timedelta = None) -> bool:
        """Сохранение смены в кэш."""
        key = f"{cls.SHIFT_PREFIX}:{shift_id}"
        return await cache.set(key, shift_data, ttl=ttl or cls.SHORT_TTL)
    
    @classmethod
    async def delete_shift(cls, shift_id: int) -> bool:
        """Удаление смены из кэша."""
        key = f"{cls.SHIFT_PREFIX}:{shift_id}"
        return await cache.delete(key)
    
    @classmethod
    async def get_user_active_shifts(cls, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """Получение активных смен пользователя из кэша."""
        key = f"{cls.ACTIVE_SHIFTS_PREFIX}:{user_id}"
        return await cache.get(key)
    
    @classmethod
    async def set_user_active_shifts(cls, user_id: int, shifts: List[Dict[str, Any]], ttl: timedelta = None) -> bool:
        """Сохранение активных смен пользователя в кэш."""
        key = f"{cls.ACTIVE_SHIFTS_PREFIX}:{user_id}"
        return await cache.set(key, shifts, ttl=ttl or cls.SHORT_TTL)
    
    @classmethod
    async def delete_user_active_shifts(cls, user_id: int) -> bool:
        """Удаление активных смен пользователя из кэша."""
        key = f"{cls.ACTIVE_SHIFTS_PREFIX}:{user_id}"
        return await cache.delete(key)
    
    @classmethod
    async def get_user_objects(cls, user_id: int) -> Optional[List[Dict[str, Any]]]:
        """Получение объектов пользователя из кэша."""
        key = f"{cls.USER_OBJECTS_PREFIX}:{user_id}"
        return await cache.get(key)
    
    @classmethod
    async def set_user_objects(cls, user_id: int, objects: List[Dict[str, Any]], ttl: timedelta = None) -> bool:
        """Сохранение объектов пользователя в кэш."""
        key = f"{cls.USER_OBJECTS_PREFIX}:{user_id}"
        return await cache.set(key, objects, ttl=ttl or cls.DEFAULT_TTL)
    
    @classmethod
    async def delete_user_objects(cls, user_id: int) -> bool:
        """Удаление объектов пользователя из кэша."""
        key = f"{cls.USER_OBJECTS_PREFIX}:{user_id}"
        return await cache.delete(key)
    
    @classmethod
    async def get_analytics_data(cls, cache_key: str) -> Optional[Dict[str, Any]]:
        """Получение аналитических данных из кэша."""
        key = f"{cls.ANALYTICS_PREFIX}:{cache_key}"
        return await cache.get(key)
    
    @classmethod
    async def set_analytics_data(cls, cache_key: str, data: Dict[str, Any], ttl: timedelta = None) -> bool:
        """Сохранение аналитических данных в кэш."""
        key = f"{cls.ANALYTICS_PREFIX}:{cache_key}"
        return await cache.set(key, data, ttl=ttl or cls.LONG_TTL)
    
    @classmethod
    async def invalidate_user_cache(cls, user_id: int) -> None:
        """Инвалидация всего кэша пользователя."""
        await cls.delete_user(user_id)
        await cls.delete_user_active_shifts(user_id)
        await cls.delete_user_objects(user_id)
        logger.info("User cache invalidated", user_id=user_id)
    
    @classmethod
    async def invalidate_object_cache(cls, object_id: int) -> None:
        """Инвалидация кэша объекта."""
        await cls.delete_object(object_id)
        # Инвалидируем кэш пользователей, связанных с объектом
        pattern = f"{cls.USER_OBJECTS_PREFIX}:*"
        await cache.clear_pattern(pattern)
        logger.info("Object cache invalidated", object_id=object_id)
    
    @classmethod
    async def invalidate_shift_cache(cls, shift_id: int, user_id: int = None) -> None:
        """Инвалидация кэша смены."""
        await cls.delete_shift(shift_id)
        if user_id:
            await cls.delete_user_active_shifts(user_id)
        logger.info("Shift cache invalidated", shift_id=shift_id, user_id=user_id)
    
    @classmethod
    async def clear_analytics_cache(cls) -> None:
        """Очистка кэша аналитики."""
        pattern = f"{cls.ANALYTICS_PREFIX}:*"
        cleared_count = await cache.clear_pattern(pattern)
        logger.info("Analytics cache cleared", cleared_keys=cleared_count)
    
    @classmethod
    async def get_cache_stats(cls) -> Dict[str, Any]:
        """Получение статистики кэша."""
        redis_stats = await cache.get_stats()
        
        # Подсчет ключей по типам
        user_keys = await cache.keys(f"{cls.USER_PREFIX}:*")
        object_keys = await cache.keys(f"{cls.OBJECT_PREFIX}:*")
        shift_keys = await cache.keys(f"{cls.SHIFT_PREFIX}:*")
        active_shift_keys = await cache.keys(f"{cls.ACTIVE_SHIFTS_PREFIX}:*")
        analytics_keys = await cache.keys(f"{cls.ANALYTICS_PREFIX}:*")
        
        return {
            'redis_stats': redis_stats,
            'key_counts': {
                'users': len(user_keys),
                'objects': len(object_keys),
                'shifts': len(shift_keys),
                'active_shifts': len(active_shift_keys),
                'analytics': len(analytics_keys),
                'total': len(user_keys) + len(object_keys) + len(shift_keys) + 
                        len(active_shift_keys) + len(analytics_keys)
            }
        }


# Декораторы для кэширования методов сервисов
def cache_user_data(ttl: timedelta = CacheService.DEFAULT_TTL):
    """Декоратор для кэширования данных пользователя."""
    return cached(ttl=ttl, key_prefix=CacheService.USER_PREFIX)


def cache_object_data(ttl: timedelta = CacheService.DEFAULT_TTL):
    """Декоратор для кэширования данных объекта."""
    return cached(ttl=ttl, key_prefix=CacheService.OBJECT_PREFIX)


def cache_shift_data(ttl: timedelta = CacheService.SHORT_TTL):
    """Декоратор для кэширования данных смены."""
    return cached(ttl=ttl, key_prefix=CacheService.SHIFT_PREFIX)


def cache_analytics_data(ttl: timedelta = CacheService.LONG_TTL):
    """Декоратор для кэширования аналитических данных."""
    return cached(ttl=ttl, key_prefix=CacheService.ANALYTICS_PREFIX)
