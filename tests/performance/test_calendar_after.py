"""Тесты производительности календаря ПОСЛЕ оптимизации"""

import asyncio
import time
from datetime import date, timedelta
from shared.services.calendar_filter_service import CalendarFilterService
from core.database.session import get_async_session
from core.cache.redis_cache import cache


async def test_calendar_after_optimization():
    """Измерение производительности ПОСЛЕ кэширования"""
    
    print('='*80)
    print('AFTER: Производительность календаря ПОСЛЕ оптимизации')
    print('='*80)
    
    # Очищаем кэш
    await cache.connect()
    await cache.clear_pattern("calendar_*")
    
    owner_telegram_id = 795156846
    user_role = "owner"
    
    # Период: текущий месяц
    today = date.today()
    start_date = date(today.year, today.month, 1)
    if today.month == 12:
        end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    print(f'\nПериод: {start_date} - {end_date}')
    
    async with get_async_session() as session:
        service = CalendarFilterService(session)
        
        # Тест 1: Первая загрузка (Cache Miss)
        print('\n--- Тест 1: Первая загрузка (Cache Miss) ---')
        start_time = time.time()
        calendar_1 = await service.get_calendar_data(
            user_telegram_id=owner_telegram_id,
            user_role=user_role,
            date_range_start=start_date,
            date_range_end=end_date,
            object_filter=None
        )
        time_miss = (time.time() - start_time) * 1000
        
        print(f'Время: {time_miss:.2f} мс')
        print(f'Объектов: {len(calendar_1.accessible_objects)}')
        print(f'Тайм-слотов: {calendar_1.total_timeslots}')
        print(f'Смен: {calendar_1.total_shifts}')
        
        # Проверяем ключи в Redis
        timeslot_keys = await cache.keys("calendar_timeslots:*")
        shift_keys = await cache.keys("calendar_shifts:*")
        print(f'Ключей timeslots в кэше: {len(timeslot_keys)}')
        print(f'Ключей shifts в кэше: {len(shift_keys)}')
        
        # Тест 2: Повторная загрузка (Cache Hit)
        print('\n--- Тест 2: Повторная загрузка (Cache Hit) ---')
        start_time = time.time()
        calendar_2 = await service.get_calendar_data(
            user_telegram_id=owner_telegram_id,
            user_role=user_role,
            date_range_start=start_date,
            date_range_end=end_date,
            object_filter=None
        )
        time_hit = (time.time() - start_time) * 1000
        
        print(f'Время: {time_hit:.2f} мс')
        
        # Расчет ускорения
        if time_hit > 0 and time_miss > 0:
            speedup = ((time_miss - time_hit) / time_miss) * 100
            print(f'Ускорение: {speedup:.1f}%')
            
            if speedup >= 80:
                print('   ✅ ЦЕЛЬ ДОСТИГНУТА! Ускорение >80%')
            elif speedup >= 50:
                print('   ✅ Хороший результат! Ускорение >50%')
            else:
                print(f'   ⚠️ Ускорение недостаточное ({speedup:.1f}%)')
        
        # Тест 3: Многократные запросы
        print('\n--- Тест 3: 10 повторных запросов из кэша ---')
        times = []
        for i in range(10):
            start = time.time()
            await service.get_calendar_data(
                user_telegram_id=owner_telegram_id,
                user_role=user_role,
                date_range_start=start_date,
                date_range_end=end_date,
                object_filter=None
            )
            times.append((time.time() - start) * 1000)
        
        avg_time = sum(times) / len(times)
        print(f'Среднее время: {avg_time:.2f} мс')
        print(f'Мин: {min(times):.2f} мс')
        print(f'Макс: {max(times):.2f} мс')
        
    # Статистика Redis
    print('\n--- Статистика Redis ---')
    stats = await cache.get_stats()
    print(f'Hits: {stats.get("keyspace_hits")}')
    print(f'Misses: {stats.get("keyspace_misses")}')
    print(f'Hit Rate: {stats.get("hit_rate")}%')
    
    await cache.disconnect()
    
    print('\n' + '='*80)
    print('ИТОГОВЫЕ РЕЗУЛЬТАТЫ:')
    print('='*80)
    print(f'Cache Miss: {time_miss:.2f} мс')
    print(f'Cache Hit: {time_hit:.2f} мс')
    print(f'Среднее из кэша (10 запросов): {avg_time:.2f} мс')
    if time_hit > 0 and time_miss > 0:
        print(f'Ускорение: {((time_miss - time_hit) / time_miss * 100):.1f}%')
    print('='*80)


if __name__ == "__main__":
    asyncio.run(test_calendar_after_optimization())

