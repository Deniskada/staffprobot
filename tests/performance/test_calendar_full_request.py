"""Тест полного HTTP-запроса календаря (как в DevTools)"""

import asyncio
import time
from datetime import date, timedelta
from httpx import AsyncClient
from core.cache.redis_cache import cache


async def test_full_calendar_request():
    """Измерение полного времени HTTP-запроса (включая рендеринг)"""
    
    print('='*80)
    print('FULL REQUEST: Полное время HTTP-запроса календаря')
    print('='*80)
    
    # Очищаем кэш
    await cache.connect()
    await cache.clear_pattern("calendar_*")
    
    telegram_id = 5577223137
    
    # Период: текущий месяц
    today = date.today()
    start_date = date(today.year, today.month, 1)
    if today.month == 12:
        end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    
    print(f'\nПериод: {start_date} - {end_date}')
    print(f'User: {telegram_id}')
    
    # Тестируем через HTTP (как в браузере)
    base_url = "http://localhost:8001"
    
    async with AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Сначала нужно авторизоваться (или использовать тестовый токен)
        # Для теста используем прямой API-эндпоинт календаря
        
        # Тест 1: API эндпоинт (JSON)
        print('\n--- Тест 1: API Calendar (JSON) ---')
        api_url = f"/api/calendar?telegram_id={telegram_id}&role=owner&start_date={start_date}&end_date={end_date}"
        
        start_time = time.time()
        try:
            response = await client.get(api_url)
            time_miss = (time.time() - start_time) * 1000
            
            print(f'Status: {response.status_code}')
            print(f'Время (Cache Miss): {time_miss:.2f} мс')
            
            if response.status_code == 200:
                data = response.json()
                print(f'Объектов: {len(data.get("accessible_objects", []))}')
                print(f'Тайм-слотов: {data.get("total_timeslots", 0)}')
                print(f'Смен: {data.get("total_shifts", 0)}')
        except Exception as e:
            print(f'Ошибка: {e}')
            time_miss = 0
        
        # Тест 2: Повторный запрос (Cache Hit)
        print('\n--- Тест 2: API Calendar (Cache Hit) ---')
        start_time = time.time()
        try:
            response = await client.get(api_url)
            time_hit = (time.time() - start_time) * 1000
            
            print(f'Status: {response.status_code}')
            print(f'Время (Cache Hit): {time_hit:.2f} мс')
            
            if time_hit > 0 and time_miss > 0:
                speedup = ((time_miss - time_hit) / time_miss) * 100
                print(f'Ускорение: {speedup:.1f}%')
        except Exception as e:
            print(f'Ошибка: {e}')
            time_hit = 0
        
        # Тест 3: Многократные запросы
        print('\n--- Тест 3: 10 запросов из кэша ---')
        times = []
        for i in range(10):
            start = time.time()
            try:
                await client.get(api_url)
                times.append((time.time() - start) * 1000)
            except:
                pass
        
        if times:
            avg_time = sum(times) / len(times)
            print(f'Среднее: {avg_time:.2f} мс')
            print(f'Мин: {min(times):.2f} мс')
            print(f'Макс: {max(times):.2f} мс')
    
    await cache.disconnect()
    
    print('\n' + '='*80)
    print('ВЫВОДЫ:')
    print('='*80)
    if time_miss > 0 and time_hit > 0:
        print(f'HTTP запрос (JSON API):')
        print(f'  - Cache Miss: {time_miss:.2f} мс')
        print(f'  - Cache Hit: {time_hit:.2f} мс')
        print(f'  - Ускорение: {((time_miss - time_hit) / time_miss * 100):.1f}%')
    print()
    print('Если в DevTools видишь ~500 мс даже при Cache Hit:')
    print('  1. Рендеринг HTML-шаблона занимает время')
    print('  2. Запросы users/contracts/objects не кэшируются')
    print('  3. JavaScript на фронтенде парсит и рисует данные')
    print('  4. Network latency (даже localhost)')
    print()
    print('Решение: кэшировать весь response (HTML или JSON) на уровне роута')
    print('='*80)


if __name__ == "__main__":
    asyncio.run(test_full_calendar_request())

