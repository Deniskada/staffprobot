"""Тест производительности календаря для конкретного пользователя"""

import asyncio
import time
from datetime import date, timedelta
from shared.services.calendar_filter_service import CalendarFilterService
from core.database.session import get_async_session
from core.cache.redis_cache import cache


async def test_calendar_for_user(telegram_id: int = 5577223137):
    """Измерение производительности календаря для конкретного пользователя"""
    
    print('='*80)
    print(f'Тест календаря для пользователя {telegram_id}')
    print('='*80)
    
    # Очищаем кэш
    await cache.connect()
    await cache.clear_pattern("calendar_*")
    
    user_role = "owner"  # Попробуем разные роли
    
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
        
        # Проверяем разные роли
        for role in ["owner", "manager", "employee"]:
            print(f'\n--- Роль: {role} ---')
            
            # Тест 1: Cache Miss
            start_time = time.time()
            try:
                calendar_1 = await service.get_calendar_data(
                    user_telegram_id=telegram_id,
                    user_role=role,
                    date_range_start=start_date,
                    date_range_end=end_date,
                    object_filter=None
                )
                time_miss = (time.time() - start_time) * 1000
                
                print(f'Cache Miss: {time_miss:.2f} мс')
                print(f'Объектов: {len(calendar_1.accessible_objects)}')
                print(f'Тайм-слотов: {calendar_1.total_timeslots}')
                print(f'Смен: {calendar_1.total_shifts}')
                
                if len(calendar_1.accessible_objects) > 0:
                    print(f'Объекты: {[obj["name"] for obj in calendar_1.accessible_objects[:5]]}')
                
                # Тест 2: Cache Hit
                start_time = time.time()
                calendar_2 = await service.get_calendar_data(
                    user_telegram_id=telegram_id,
                    user_role=role,
                    date_range_start=start_date,
                    date_range_end=end_date,
                    object_filter=None
                )
                time_hit = (time.time() - start_time) * 1000
                
                print(f'Cache Hit: {time_hit:.2f} мс')
                
                if time_hit > 0 and time_miss > 0:
                    speedup = ((time_miss - time_hit) / time_miss) * 100
                    print(f'Ускорение: {speedup:.1f}%')
                    
                    if speedup >= 80:
                        print('   ✅ ОТЛИЧНО! Ускорение >80%')
                    elif speedup >= 50:
                        print('   ✅ ХОРОШО! Ускорение >50%')
                    else:
                        print(f'   ⚠️ Ускорение недостаточное ({speedup:.1f}%)')
                
                # Тест 3: Многократные запросы
                times = []
                for i in range(5):
                    start = time.time()
                    await service.get_calendar_data(
                        user_telegram_id=telegram_id,
                        user_role=role,
                        date_range_start=start_date,
                        date_range_end=end_date,
                        object_filter=None
                    )
                    times.append((time.time() - start) * 1000)
                
                avg_time = sum(times) / len(times)
                print(f'Среднее из кэша (5 запросов): {avg_time:.2f} мс')
                
            except Exception as e:
                print(f'Ошибка для роли {role}: {e}')
                import traceback
                traceback.print_exc()
    
    # Статистика Redis
    print('\n--- Статистика Redis ---')
    stats = await cache.get_stats()
    print(f'Hits: {stats.get("keyspace_hits")}')
    print(f'Misses: {stats.get("keyspace_misses")}')
    print(f'Hit Rate: {stats.get("hit_rate")}%')
    
    # Проверяем ключи в кэше
    timeslot_keys = await cache.keys("calendar_timeslots:*")
    shift_keys = await cache.keys("calendar_shifts:*")
    print(f'Ключей timeslots: {len(timeslot_keys)}')
    print(f'Ключей shifts: {len(shift_keys)}')
    
    await cache.disconnect()
    
    print('\n' + '='*80)


if __name__ == "__main__":
    asyncio.run(test_calendar_for_user())

