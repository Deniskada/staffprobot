"""Тесты graceful degradation при недоступности Redis"""

import asyncio
from apps.web.services.contract_service import ContractService
from apps.web.services.object_service import ObjectService
from core.database.session import get_async_session
from core.cache.redis_cache import cache


async def test_graceful_degradation_contract_service():
    """Тест работы ContractService при недоступности Redis"""
    
    print('=== Тест Graceful Degradation: ContractService ===')
    
    # Отключаем Redis
    print('\n1. Отключаем Redis...')
    if cache.is_connected:
        await cache.disconnect()
    print(f'   Redis подключен: {cache.is_connected}')
    
    # Пытаемся получить данные
    print('\n2. Запрос при отключенном Redis...')
    service = ContractService()
    
    try:
        result = await service.get_contract_employees_by_telegram_id(795156846)
        print(f'   ✅ Успешно! Получено сотрудников: {len(result)}')
        print(f'   Приложение работает без Redis')
    except Exception as e:
        print(f'   ❌ Ошибка: {e}')
        print(f'   Graceful degradation не работает!')
    
    print('\n3. Подключаем Redis обратно...')
    await cache.connect()
    print(f'   Redis подключен: {cache.is_connected}')
    
    await cache.disconnect()
    print('\n✅ Тест graceful degradation завершен')


async def test_graceful_degradation_object_service():
    """Тест работы ObjectService при недоступности Redis"""
    
    print('\n=== Тест Graceful Degradation: ObjectService ===')
    
    # Отключаем Redis
    print('\n1. Отключаем Redis...')
    if cache.is_connected:
        await cache.disconnect()
    
    # Пытаемся получить данные
    print('\n2. Запрос при отключенном Redis...')
    
    try:
        async with get_async_session() as session:
            service = ObjectService(session)
            result = await service.get_objects_by_owner(795156846)
            print(f'   ✅ Успешно! Получено объектов: {len(result)}')
            print(f'   Приложение работает без Redis')
    except Exception as e:
        print(f'   ❌ Ошибка: {e}')
        print(f'   Graceful degradation не работает!')
    
    print('\n3. Подключаем Redis обратно...')
    await cache.connect()
    print(f'   Redis подключен: {cache.is_connected}')
    
    await cache.disconnect()
    print('\n✅ Тест graceful degradation завершен')


if __name__ == "__main__":
    print('='*60)
    asyncio.run(test_graceful_degradation_contract_service())
    print('='*60)
    asyncio.run(test_graceful_degradation_object_service())
    print('='*60)

