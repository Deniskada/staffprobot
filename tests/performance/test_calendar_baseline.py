"""Baseline тесты производительности календаря (ДО оптимизации)"""

import asyncio
import time
from datetime import date, timedelta
from shared.services.calendar_filter_service import CalendarFilterService
from core.database.session import get_async_session
from core.cache.redis_cache import cache


async def test_calendar_performance_baseline():
    """Измерение производительности календаря ДО кэширования"""
    
    print('='*80)
    print('BASELINE: Производительность календаря ДО оптимизации')
    print('='*80)
    
    # Очищаем кэш перед тестами
    await cache.connect()
    await cache.clear_pattern("*")
    await cache.disconnect()
    
    # Тестовые данные
    owner_telegram_id = 795156846
    user_role = "owner"
    
    # Период: текущий месяц
    today = date.today()
    start_date = date(today.year, today.month, 1)
    # Последний день месяца
    if today.month == 12:
        end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    print(f'\nПериод: {start_date} - {end_date} ({(end_date - start_date).days + 1} дней)')
    
    async with get_async_session() as session:
        service = CalendarFilterService(session)
        
        # Тест 1: Календарь для 1 объекта
        print('\n--- Тест 1: 1 объект ---')
        start_time = time.time()
        calendar_1 = await service.get_calendar_data(
            user_telegram_id=owner_telegram_id,
            user_role=user_role,
            date_range_start=start_date,
            date_range_end=end_date,
            object_filter=None  # Все доступные
        )
        time_1_obj = (time.time() - start_time) * 1000
        
        print(f'Время: {time_1_obj:.2f} мс')
        print(f'Объектов доступно: {len(calendar_1.accessible_objects)}')
        print(f'Тайм-слотов: {calendar_1.total_timeslots}')
        print(f'Смен: {calendar_1.total_shifts}')
        
        # Тест 2: Повторный запрос (проверим есть ли какое-то кэширование)
        print('\n--- Тест 2: Повторный запрос ---')
        start_time = time.time()
        calendar_2 = await service.get_calendar_data(
            user_telegram_id=owner_telegram_id,
            user_role=user_role,
            date_range_start=start_date,
            date_range_end=end_date,
            object_filter=None
        )
        time_2_req = (time.time() - start_time) * 1000
        
        print(f'Время: {time_2_req:.2f} мс')
        
        # Есть ли ускорение?
        if time_2_req < time_1_obj:
            speedup = ((time_1_obj - time_2_req) / time_1_obj) * 100
            print(f'Ускорение: {speedup:.1f}% (какое-то кэширование есть)')
        else:
            print('Ускорения нет (кэширование не работает)')
        
        # Тест 3: Следующий месяц (новые данные)
        print('\n--- Тест 3: Следующий месяц ---')
        next_month_start = end_date + timedelta(days=1)
        next_month_end = next_month_start + timedelta(days=30)
        
        start_time = time.time()
        calendar_3 = await service.get_calendar_data(
            user_telegram_id=owner_telegram_id,
            user_role=user_role,
            date_range_start=next_month_start,
            date_range_end=next_month_end,
            object_filter=None
        )
        time_next_month = (time.time() - start_time) * 1000
        
        print(f'Время: {time_next_month:.2f} мс')
        print(f'Тайм-слотов: {calendar_3.total_timeslots}')
        
    print('\n' + '='*80)
    print('ИТОГОВЫЕ РЕЗУЛЬТАТЫ BASELINE:')
    print('='*80)
    print(f'Первая загрузка (текущий месяц): {time_1_obj:.2f} мс')
    print(f'Повторная загрузка: {time_2_req:.2f} мс')
    print(f'Следующий месяц: {time_next_month:.2f} мс')
    print(f'Среднее время: {(time_1_obj + time_2_req + time_next_month) / 3:.2f} мс')
    print('='*80)
    
    # Сохраняем результаты для сравнения
    results = {
        'first_load': time_1_obj,
        'second_load': time_2_req,
        'next_month': time_next_month,
        'average': (time_1_obj + time_2_req + time_next_month) / 3,
        'accessible_objects': len(calendar_1.accessible_objects),
        'total_timeslots': calendar_1.total_timeslots,
        'total_shifts': calendar_1.total_shifts
    }
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_calendar_performance_baseline())
    
    print('\n📊 Целевые метрики для оптимизации:')
    print(f'  - Ускорение: >80%')
    print(f'  - Целевое время: <{results["average"] * 0.2:.2f} мс')
    print(f'  - Текущее среднее: {results["average"]:.2f} мс')

