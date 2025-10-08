"""Тесты производительности Redis кэширования"""

import asyncio
import time
from apps.web.services.contract_service import ContractService
from apps.web.services.object_service import ObjectService
from core.database.session import get_async_session
from core.cache.redis_cache import cache


async def test_contract_service_performance():
    """Тест производительности кэширования ContractService"""
    
    print('=== Тест производительности: ContractService ===')
    
    await cache.connect()
    
    # Очищаем кэш
    await cache.clear_pattern("contract_employees:*")
    
    service = ContractService()
    owner_telegram_id = 795156846
    
    # Замер без кэша (cache miss)
    print('\n1. Запрос БЕЗ кэша (Cache Miss)...')
    start_time = time.time()
    result1 = await service.get_contract_employees_by_telegram_id(owner_telegram_id)
    time_without_cache = (time.time() - start_time) * 1000  # мс
    print(f'   Время: {time_without_cache:.2f} мс')
    print(f'   Сотрудников: {len(result1)}')
    
    # Замер с кэшем (cache hit)
    print('\n2. Запрос С кэшем (Cache Hit)...')
    start_time = time.time()
    result2 = await service.get_contract_employees_by_telegram_id(owner_telegram_id)
    time_with_cache = (time.time() - start_time) * 1000  # мс
    print(f'   Время: {time_with_cache:.2f} мс')
    print(f'   Сотрудников: {len(result2)}')
    
    # Расчет ускорения
    if time_with_cache > 0:
        speedup = ((time_without_cache - time_with_cache) / time_without_cache) * 100
        print(f'\n📊 Ускорение: {speedup:.1f}%')
        
        if speedup >= 20:
            print('   ✅ Целевое ускорение достигнуто (>20%)')
        else:
            print(f'   ⚠️ Ускорение меньше целевого 20% (получено {speedup:.1f}%)')
    
    # Средний запрос с кэшем (10 раз)
    print('\n3. Среднее время с кэшем (10 запросов)...')
    times = []
    for i in range(10):
        start = time.time()
        await service.get_contract_employees_by_telegram_id(owner_telegram_id)
        times.append((time.time() - start) * 1000)
    
    avg_time = sum(times) / len(times)
    print(f'   Среднее время: {avg_time:.2f} мс')
    print(f'   Мин: {min(times):.2f} мс')
    print(f'   Макс: {max(times):.2f} мс')
    
    await cache.disconnect()
    print('\n✅ Тест производительности ContractService завершен')


async def test_object_service_performance():
    """Тест производительности кэширования ObjectService"""
    
    print('\n=== Тест производительности: ObjectService ===')
    
    await cache.connect()
    
    # Очищаем кэш
    await cache.clear_pattern("objects_by_owner:*")
    
    owner_telegram_id = 795156846
    
    async with get_async_session() as session:
        service = ObjectService(session)
        
        # Замер без кэша
        print('\n1. Запрос БЕЗ кэша (Cache Miss)...')
        start_time = time.time()
        result1 = await service.get_objects_by_owner(owner_telegram_id)
        time_without_cache = (time.time() - start_time) * 1000
        print(f'   Время: {time_without_cache:.2f} мс')
        print(f'   Объектов: {len(result1)}')
        
        # Замер с кэшем
        print('\n2. Запрос С кэшем (Cache Hit)...')
        start_time = time.time()
        result2 = await service.get_objects_by_owner(owner_telegram_id)
        time_with_cache = (time.time() - start_time) * 1000
        print(f'   Время: {time_with_cache:.2f} мс')
        print(f'   Объектов: {len(result2)}')
        
        # Расчет ускорения
        if time_with_cache > 0:
            speedup = ((time_without_cache - time_with_cache) / time_without_cache) * 100
            print(f'\n📊 Ускорение: {speedup:.1f}%')
            
            if speedup >= 20:
                print('   ✅ Целевое ускорение достигнуто (>20%)')
            else:
                print(f'   ⚠️ Ускорение меньше целевого (получено {speedup:.1f}%)')
    
    await cache.disconnect()
    print('\n✅ Тест производительности ObjectService завершен')


if __name__ == "__main__":
    print('='*60)
    asyncio.run(test_contract_service_performance())
    print('='*60)
    asyncio.run(test_object_service_performance())
    print('='*60)

