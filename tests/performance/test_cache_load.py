"""Нагрузочные тесты Redis кэша с большим количеством данных"""

import asyncio
import time
from apps.web.services.contract_service import ContractService
from core.cache.redis_cache import cache


async def test_high_load_caching():
    """Тест поведения кэша при высокой нагрузке"""
    
    print('=== Нагрузочный тест Redis кэша ===')
    
    await cache.connect()
    
    # Очищаем кэш
    await cache.clear_pattern("*")
    
    service = ContractService()
    
    # Симулируем множественные запросы от разных пользователей
    print('\n1. Симуляция 50 параллельных запросов...')
    
    async def make_request(user_id):
        """Одиночный запрос"""
        start = time.time()
        result = await service.get_contract_employees_by_telegram_id(user_id)
        elapsed = (time.time() - start) * 1000
        return elapsed, len(result)
    
    # Генерируем разные telegram_id
    user_ids = [795156846 + i for i in range(50)]
    
    # Первая волна - cache miss для всех
    start_total = time.time()
    tasks = [make_request(uid) for uid in user_ids]
    results = await asyncio.gather(*tasks)
    total_time_miss = (time.time() - start_total) * 1000
    
    avg_time_miss = sum(r[0] for r in results) / len(results)
    print(f'   Cache Miss:')
    print(f'   - Общее время: {total_time_miss:.2f} мс')
    print(f'   - Среднее на запрос: {avg_time_miss:.2f} мс')
    
    # Проверяем количество ключей в Redis
    all_keys = await cache.keys("*")
    print(f'   - Ключей в Redis: {len(all_keys)}')
    
    # Вторая волна - cache hit для всех
    print('\n2. Повторные 50 запросов (из кэша)...')
    start_total = time.time()
    tasks = [make_request(uid) for uid in user_ids]
    results_cached = await asyncio.gather(*tasks)
    total_time_hit = (time.time() - start_total) * 1000
    
    avg_time_hit = sum(r[0] for r in results_cached) / len(results_cached)
    print(f'   Cache Hit:')
    print(f'   - Общее время: {total_time_hit:.2f} мс')
    print(f'   - Среднее на запрос: {avg_time_hit:.2f} мс')
    
    # Расчет ускорения
    speedup = ((total_time_miss - total_time_hit) / total_time_miss) * 100
    print(f'\n📊 Результаты:')
    print(f'   - Ускорение общего времени: {speedup:.1f}%')
    print(f'   - Ускорение среднего запроса: {((avg_time_miss - avg_time_hit) / avg_time_miss * 100):.1f}%')
    
    if speedup >= 50:
        print('   ✅ Отличный результат! Ускорение >50%')
    elif speedup >= 20:
        print('   ✅ Хороший результат! Ускорение >20%')
    else:
        print(f'   ⚠️ Ускорение недостаточное ({speedup:.1f}%)')
    
    # Проверка статистики Redis
    print('\n3. Статистика Redis после нагрузки...')
    stats = await cache.get_stats()
    print(f'   - Hits: {stats.get("keyspace_hits")}')
    print(f'   - Misses: {stats.get("keyspace_misses")}')
    print(f'   - Hit Rate: {stats.get("hit_rate")}%')
    print(f'   - Memory: {stats.get("used_memory_human")}')
    
    await cache.disconnect()
    print('\n✅ Нагрузочный тест завершен')


if __name__ == "__main__":
    print('='*60)
    asyncio.run(test_high_load_caching())
    print('='*60)

