"""Rate Limiter для защиты API от злоупотреблений."""

from typing import Optional
from core.cache.redis_cache import cache
from core.logging.logger import logger


class RateLimiter:
    """Утилита для ограничения частоты запросов через Redis."""
    
    @staticmethod
    async def check_rate_limit(
        key: str, 
        max_requests: int, 
        window_seconds: int
    ) -> bool:
        """Проверка лимита запросов.
        
        Args:
            key: Уникальный ключ для отслеживания (например, IP адрес или user_id)
            max_requests: Максимальное количество запросов
            window_seconds: Временное окно в секундах
            
        Returns:
            True если лимит не превышен, False если превышен
        """
        try:
            # Подключаемся к Redis если не подключен
            if not cache.is_connected:
                await cache.connect()
            
            # Формируем ключ для rate limiting
            rate_key = f"rate_limit:{key}"
            
            # Инкрементируем счетчик
            current = await cache.redis.incr(rate_key)
            
            # Если это первый запрос, устанавливаем TTL
            if current == 1:
                await cache.redis.expire(rate_key, window_seconds)
            
            # Проверяем лимит
            if current > max_requests:
                logger.warning(
                    f"Rate limit exceeded",
                    key=key,
                    current=current,
                    max_requests=max_requests,
                    window_seconds=window_seconds
                )
                return False
            
            logger.debug(
                f"Rate limit check passed",
                key=key,
                current=current,
                max_requests=max_requests
            )
            return True
            
        except Exception as e:
            # При ошибке Redis пропускаем запрос (graceful degradation)
            logger.error(f"Rate limit check failed: {e}")
            return True
    
    @staticmethod
    async def get_remaining_requests(
        key: str,
        max_requests: int
    ) -> int:
        """Получение количества оставшихся запросов.
        
        Args:
            key: Уникальный ключ для отслеживания
            max_requests: Максимальное количество запросов
            
        Returns:
            Количество оставшихся запросов
        """
        try:
            if not cache.is_connected:
                await cache.connect()
            
            rate_key = f"rate_limit:{key}"
            current = await cache.redis.get(rate_key)
            
            if current is None:
                return max_requests
            
            current_count = int(current)
            remaining = max_requests - current_count
            
            return max(0, remaining)
            
        except Exception as e:
            logger.error(f"Failed to get remaining requests: {e}")
            return max_requests
    
    @staticmethod
    async def reset_limit(key: str) -> bool:
        """Сброс лимита для ключа.
        
        Args:
            key: Уникальный ключ для сброса
            
        Returns:
            True если успешно сброшен
        """
        try:
            if not cache.is_connected:
                await cache.connect()
            
            rate_key = f"rate_limit:{key}"
            result = await cache.redis.delete(rate_key)
            
            logger.info(f"Rate limit reset for key {key}")
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False

