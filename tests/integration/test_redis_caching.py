"""Интеграционные тесты для Redis кэширования"""

import pytest
from core.cache.cache_service import CacheService
from datetime import timedelta


@pytest.mark.asyncio
async def test_cache_basic_operations():
    """Тест базовых операций кэша"""
    # Тест set/get
    test_key = "test:basic"
    test_value = {"data": "test_value", "number": 123}
    
    # Сохраняем в кэш
    await CacheService.set(test_key, test_value, ttl=timedelta(minutes=1))
    
    # Получаем из кэша
    cached_value = await CacheService.get(test_key)
    assert cached_value is not None
    assert cached_value["data"] == "test_value"
    assert cached_value["number"] == 123
    
    # Удаляем из кэша
    await CacheService.delete(test_key)
    
    # Проверяем удаление
    deleted_value = await CacheService.get(test_key)
    assert deleted_value is None


@pytest.mark.asyncio
async def test_cache_user_operations():
    """Тест кэширования пользователей"""
    user_id = 999999
    user_data = {
        "id": user_id,
        "telegram_id": 123456789,
        "first_name": "Test",
        "last_name": "User"
    }
    
    # Сохраняем пользователя в кэш
    await CacheService.set_user(user_id, user_data)
    
    # Получаем из кэша
    cached_user = await CacheService.get_user(user_id)
    assert cached_user is not None
    assert cached_user["telegram_id"] == 123456789
    assert cached_user["first_name"] == "Test"
    
    # Инвалидируем
    await CacheService.invalidate_user_cache(user_id)
    
    # Проверяем инвалидацию
    invalidated_user = await CacheService.get_user(user_id)
    assert invalidated_user is None


@pytest.mark.asyncio
async def test_cache_object_operations():
    """Тест кэширования объектов"""
    object_id = 888888
    object_data = {
        "id": object_id,
        "name": "Test Object",
        "address": "Test Address"
    }
    
    # Сохраняем объект в кэш
    await CacheService.set_object(object_id, object_data)
    
    # Получаем из кэша
    cached_object = await CacheService.get_object(object_id)
    assert cached_object is not None
    assert cached_object["name"] == "Test Object"
    
    # Инвалидируем
    await CacheService.invalidate_object_cache(object_id)
    
    # Проверяем инвалидацию
    invalidated_object = await CacheService.get_object(object_id)
    assert invalidated_object is None


@pytest.mark.asyncio
async def test_cache_ttl():
    """Тест TTL кэша"""
    import asyncio
    
    test_key = "test:ttl"
    test_value = {"data": "expiring"}
    
    # Сохраняем с TTL 1 секунда
    await CacheService.set(test_key, test_value, ttl=timedelta(seconds=1))
    
    # Сразу должен быть доступен
    cached = await CacheService.get(test_key)
    assert cached is not None
    
    # Ждем 2 секунды
    await asyncio.sleep(2)
    
    # Должен исчезнуть
    expired = await CacheService.get(test_key)
    assert expired is None
