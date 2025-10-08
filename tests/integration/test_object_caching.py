"""Интеграционные тесты для кэширования ObjectService"""

import asyncio
from core.cache.redis_cache import cache
from core.cache.cache_service import CacheService


async def test_object_service_caching():
    """Тест кэширования ObjectService.get_objects_by_owner()"""
    
    await cache.connect()
    
    print('=== Тест ObjectService кэширование ===')
    
    # Очищаем кэш перед тестом
    await cache.clear_pattern("objects_by_owner:*")
    
    # Для теста используем реальный telegram_id владельца
    owner_telegram_id = 795156846
    
    # Импортируем ObjectService
    from apps.web.services.object_service import ObjectService
    from core.database.session import get_async_session
    
    async with get_async_session() as session:
        service = ObjectService(session)
        
        print('\n1. Первый запрос (ожидается Cache Miss)...')
        objects1 = await service.get_objects_by_owner(owner_telegram_id)
        print(f'   Объектов: {len(objects1)}')
        
        # Проверяем ключи
        keys1 = await cache.keys('objects_by_owner:*')
        print(f'   Ключей в Redis: {len(keys1)}')
        if keys1:
            print(f'   Ключ: {keys1[0]}')
            
            # Проверяем TTL
            from core.cache.redis_cache import RedisCache
            redis_cache = RedisCache()
            await redis_cache.connect()
            ttl = await redis_cache.redis.ttl(keys1[0])
            print(f'   TTL: {ttl} сек (~{ttl/60:.1f} мин)')
            await redis_cache.disconnect()
        
        print('\n2. Второй запрос (ожидается Cache Hit)...')
        objects2 = await service.get_objects_by_owner(owner_telegram_id)
        print(f'   Объектов: {len(objects2)}')
        
        # Ключи должны быть те же
        keys2 = await cache.keys('objects_by_owner:*')
        print(f'   Ключей в Redis: {len(keys2)}')
        print(f'   Ключи стабильные: {keys1 == keys2}')
        
        print('\n3. Третий запрос (ожидается Cache Hit)...')
        objects3 = await service.get_objects_by_owner(owner_telegram_id)
        print(f'   Объектов: {len(objects3)}')
    
    # Проверяем статистику
    print('\n=== Статистика Redis ===')
    stats = await cache.get_stats()
    print(f'Hits: {stats.get("keyspace_hits")}')
    print(f'Misses: {stats.get("keyspace_misses")}')
    print(f'Hit Rate: {stats.get("hit_rate")}%')
    
    print('\n✅ Тест ObjectService завершен')
    
    await cache.disconnect()


async def test_object_invalidation():
    """Тест инвалидации кэша при операциях с объектами"""
    
    await cache.connect()
    
    print('\n=== Тест инвалидации ObjectService ===')
    
    owner_telegram_id = 795156846
    
    from apps.web.services.object_service import ObjectService
    from core.database.session import get_async_session
    
    async with get_async_session() as session:
        service = ObjectService(session)
        
        # Создаем кэш
        print('\n1. Создаем кэш objects_by_owner...')
        objects1 = await service.get_objects_by_owner(owner_telegram_id)
        keys_before = await cache.keys('objects_by_owner:*')
        print(f'   Ключей: {len(keys_before)}')
        
        # Вызываем инвалидацию для любого объекта
        if objects1:
            print(f'\n2. Инвалидируем кэш для object_id={objects1[0].id}...')
            await CacheService.invalidate_object_cache(objects1[0].id)
            
            keys_after = await cache.keys('objects_by_owner:*')
            print(f'   Ключей после инвалидации: {len(keys_after)}')
            
            # Следующий запрос должен создать новый кэш
            print('\n3. Повторный запрос (ожидается Cache Miss)...')
            objects2 = await service.get_objects_by_owner(owner_telegram_id)
            print(f'   Объектов: {len(objects2)}')
            
            keys_final = await cache.keys('objects_by_owner:*')
            print(f'   Ключей после повторного запроса: {len(keys_final)}')
            
            if len(keys_after) == 0:
                print('\n✅ Инвалидация работает корректно!')
            else:
                print('\n❌ Инвалидация не удалила ключи!')
        else:
            print('   Нет объектов для теста')
    
    await cache.disconnect()


if __name__ == "__main__":
    print('='*60)
    asyncio.run(test_object_service_caching())
    print('='*60)
    asyncio.run(test_object_invalidation())
    print('='*60)

