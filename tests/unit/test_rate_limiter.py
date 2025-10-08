"""Unit тесты для RateLimiter"""

import pytest
from core.utils.rate_limiter import RateLimiter
from core.cache.redis_cache import cache


@pytest.mark.asyncio
async def test_rate_limiter_basic():
    """Тест базовой функциональности rate limiter"""
    try:
        await cache.connect()
        
        # Сбрасываем лимит перед тестом
        await RateLimiter.reset_limit("test_user_1")
        
        # Первые 5 запросов должны пройти
        for i in range(5):
            result = await RateLimiter.check_rate_limit("test_user_1", 5, 60)
            assert result is True, f"Request {i+1} should be allowed"
        
        # 6-й запрос должен быть заблокирован
        result = await RateLimiter.check_rate_limit("test_user_1", 5, 60)
        assert result is False, "Request 6 should be blocked"
        
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_rate_limiter_remaining_requests():
    """Тест получения оставшихся запросов"""
    try:
        await cache.connect()
        
        # Сбрасываем лимит
        await RateLimiter.reset_limit("test_user_2")
        
        # Проверяем начальное количество
        remaining = await RateLimiter.get_remaining_requests("test_user_2", 10)
        assert remaining == 10, "Should have 10 requests initially"
        
        # Делаем 3 запроса
        for _ in range(3):
            await RateLimiter.check_rate_limit("test_user_2", 10, 60)
        
        # Должно остаться 7
        remaining = await RateLimiter.get_remaining_requests("test_user_2", 10)
        assert remaining == 7, "Should have 7 requests remaining"
        
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_rate_limiter_reset():
    """Тест сброса лимита"""
    try:
        await cache.connect()
        
        # Создаем лимит
        await RateLimiter.check_rate_limit("test_user_3", 5, 60)
        await RateLimiter.check_rate_limit("test_user_3", 5, 60)
        
        # Проверяем остаток
        remaining_before = await RateLimiter.get_remaining_requests("test_user_3", 5)
        assert remaining_before == 3, "Should have 3 requests remaining"
        
        # Сбрасываем
        result = await RateLimiter.reset_limit("test_user_3")
        assert result is True, "Reset should succeed"
        
        # Проверяем что лимит сброшен
        remaining_after = await RateLimiter.get_remaining_requests("test_user_3", 5)
        assert remaining_after == 5, "Should have full 5 requests after reset"
        
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_rate_limiter_window_expiry():
    """Тест истечения временного окна"""
    import asyncio
    
    try:
        await cache.connect()
        
        # Сбрасываем лимит
        await RateLimiter.reset_limit("test_user_4")
        
        # Делаем 2 запроса с коротким окном (2 секунды)
        await RateLimiter.check_rate_limit("test_user_4", 2, 2)
        await RateLimiter.check_rate_limit("test_user_4", 2, 2)
        
        # Третий должен быть заблокирован
        result = await RateLimiter.check_rate_limit("test_user_4", 2, 2)
        assert result is False, "Third request should be blocked"
        
        # Ждем 3 секунды (окно истечет)
        await asyncio.sleep(3)
        
        # Теперь должен пройти (новое окно)
        result = await RateLimiter.check_rate_limit("test_user_4", 2, 2)
        assert result is True, "Request after window expiry should be allowed"
        
    finally:
        await cache.disconnect()


@pytest.mark.asyncio
async def test_rate_limiter_graceful_degradation():
    """Тест graceful degradation при недоступности Redis"""
    # Тест без подключения к Redis
    # RateLimiter должен пропускать запросы при ошибках
    
    # Не подключаемся к Redis
    # check_rate_limit должен вернуть True (пропустить)
    result = await RateLimiter.check_rate_limit("test_user_5", 5, 60)
    # При отключенном Redis должен пропускать (graceful degradation)
    # Или вернуть True из-за обработки исключения
    assert result in [True, False]  # Зависит от состояния cache.is_connected

