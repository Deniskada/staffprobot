"""Middleware для ограничения частоты запросов."""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from core.utils.rate_limiter import RateLimiter
from core.logging.logger import logger


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения частоты запросов к API."""
    
    # Лимиты по ролям (запросов в минуту)
    ROLE_LIMITS = {
        "owner": 200,
        "manager": 150,
        "employee": 100,
        "superadmin": 300,
        "moderator": 200,
        "guest": 50  # Неавторизованные пользователи
    }
    
    # Временное окно (секунды)
    WINDOW_SECONDS = 60
    
    # Пути, которые не ограничиваются
    EXCLUDED_PATHS = [
        "/health",
        "/metrics",
        "/static/",
        "/favicon.ico"
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Обработка запроса с проверкой rate limit."""
        
        # Пропускаем исключенные пути
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # Определяем ключ для rate limiting
        # Приоритет: user_id > telegram_id > IP
        rate_key = await self._get_rate_key(request)
        
        # Определяем лимит для пользователя
        max_requests = await self._get_max_requests(request)
        
        # Проверяем лимит
        allowed = await RateLimiter.check_rate_limit(
            key=rate_key,
            max_requests=max_requests,
            window_seconds=self.WINDOW_SECONDS
        )
        
        if not allowed:
            # Получаем оставшееся время до сброса
            remaining = await RateLimiter.get_remaining_requests(rate_key, max_requests)
            
            logger.warning(
                f"Rate limit exceeded for {rate_key}",
                path=path,
                max_requests=max_requests
            )
            
            raise HTTPException(
                status_code=429,
                detail=f"Превышен лимит запросов. Максимум {max_requests} запросов в минуту. Попробуйте через минуту."
            )
        
        # Добавляем заголовки с информацией о лимитах
        response = await call_next(request)
        
        remaining = await RateLimiter.get_remaining_requests(rate_key, max_requests)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(self.WINDOW_SECONDS)
        
        return response
    
    async def _get_rate_key(self, request: Request) -> str:
        """Получение ключа для rate limiting."""
        # Пытаемся получить user из состояния (установлен auth middleware)
        user = getattr(request.state, "user", None)
        
        if user:
            # Используем user_id или telegram_id
            user_id = user.get("id") or user.get("telegram_id")
            if user_id:
                return f"user:{user_id}"
        
        # Используем IP адрес как fallback
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    async def _get_max_requests(self, request: Request) -> int:
        """Получение максимального количества запросов для пользователя."""
        # Пытаемся получить роль пользователя
        user = getattr(request.state, "user", None)
        
        if user:
            role = user.get("role", "employee")
            return self.ROLE_LIMITS.get(role, self.ROLE_LIMITS["employee"])
        
        # Для неавторизованных - минимальный лимит
        return self.ROLE_LIMITS["guest"]

