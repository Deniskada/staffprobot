"""
Скрипт для исправления времени окончания запланированных смен.

Проблема: запланированные смены закрывались по object.closing_time вместо timeslot.end_time
Решение: пересчитать end_time, total_hours и total_payment для таких смен
"""

import asyncio
from datetime import datetime
from sqlalchemy import select, and_, text
from core.database.session import get_async_session
from domain.entities.shift import Shift
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from core.logging.logger import logger


async def fix_planned_shifts():
    """Исправить запланированные смены, закрытые по времени объекта вместо тайм-слота"""
    
    async with get_async_session() as session:
        # Находим проблемные смены
        query = text("""
            SELECT 
                s.id,
                s.start_time,
                s.end_time,
                s.hourly_rate,
                s.total_hours,
                s.total_payment,
                ts.end_time as ts_end,
                o.closing_time as obj_close,
                o.timezone,
                to_char(s.end_time AT TIME ZONE o.timezone, 'HH24:MI') as end_local_time
            FROM shifts s
            JOIN time_slots ts ON s.time_slot_id = ts.id  
            JOIN objects o ON s.object_id = o.id
            WHERE 
                s.is_planned = true
                AND s.status = 'completed'
                AND s.time_slot_id IS NOT NULL
                AND CAST(s.end_time AT TIME ZONE o.timezone AS TIME) = o.closing_time
                AND ts.end_time < o.closing_time
            ORDER BY s.id;
        """)
        
        result = await session.execute(query)
        problem_shifts = result.fetchall()
        
        print(f'\n{"="*80}')
        print(f'Найдено смен для исправления: {len(problem_shifts)}')
        print(f'{"="*80}\n')
        
        if len(problem_shifts) == 0:
            print('✅ Все смены корректны!')
            return
        
        # Показываем что будем исправлять
        for row in problem_shifts:
            print(f'Смена {row.id}:')
            print(f'  Текущее окончание: {row.end_local_time} (по closing_time объекта)')
            print(f'  Должно быть: {row.ts_end} (по тайм-слоту)')
            print(f'  Текущие часы: {row.total_hours}')
            print(f'  Текущая оплата: {row.total_payment}₽')
            print()
        
        # Подтверждение
        confirm = input(f'\nИсправить {len(problem_shifts)} смен? (yes/no): ')
        if confirm.lower() != 'yes':
            print('Отменено.')
            return
        
        # Исправляем смены
        fixed_count = 0
        for row in problem_shifts:
            try:
                update_query = text("""
                    UPDATE shifts s
                    SET 
                        end_time = (
                            (DATE(s.start_time AT TIME ZONE o.timezone) || ' ' || ts.end_time::text)::timestamp 
                            AT TIME ZONE o.timezone AT TIME ZONE 'UTC'
                        ),
                        total_hours = ROUND(CAST(EXTRACT(EPOCH FROM (
                            (DATE(s.start_time AT TIME ZONE o.timezone) || ' ' || ts.end_time::text)::timestamp 
                            AT TIME ZONE o.timezone AT TIME ZONE 'UTC'
                            - s.start_time
                        ))/3600 AS NUMERIC), 2),
                        total_payment = ROUND(CAST(s.hourly_rate * EXTRACT(EPOCH FROM (
                            (DATE(s.start_time AT TIME ZONE o.timezone) || ' ' || ts.end_time::text)::timestamp 
                            AT TIME ZONE o.timezone AT TIME ZONE 'UTC'
                            - s.start_time
                        ))/3600 AS NUMERIC), 2)
                    FROM time_slots ts, objects o
                    WHERE 
                        s.id = :shift_id
                        AND s.time_slot_id = ts.id
                        AND s.object_id = o.id;
                """)
                
                await session.execute(update_query, {"shift_id": row.id})
                fixed_count += 1
                print(f'✅ Смена {row.id} исправлена')
                
            except Exception as e:
                logger.error(f"Ошибка исправления смены {row.id}: {e}")
                print(f'❌ Смена {row.id}: ошибка - {e}')
        
        await session.commit()
        
        print(f'\n{"="*80}')
        print(f'✅ Исправлено смен: {fixed_count}/{len(problem_shifts)}')
        print(f'{"="*80}\n')
        
        # Показываем результаты
        verify_query = text("""
            SELECT 
                s.id,
                to_char(s.start_time AT TIME ZONE o.timezone, 'HH24:MI') as start_t,
                to_char(s.end_time AT TIME ZONE o.timezone, 'HH24:MI') as end_t,
                ts.end_time as ts_end,
                s.total_hours,
                s.total_payment
            FROM shifts s
            JOIN time_slots ts ON s.time_slot_id = ts.id
            JOIN objects o ON s.object_id = o.id
            WHERE s.id = ANY(:shift_ids)
            ORDER BY s.id;
        """)
        
        shift_ids = [row.id for row in problem_shifts]
        verify_result = await session.execute(verify_query, {"shift_ids": shift_ids})
        
        print('\nИсправленные смены:')
        print(f'{"ID":<6} {"Начало":<8} {"Конец":<8} {"Тайм-слот":<10} {"Часы":<8} {"Оплата"}')
        print('-' * 60)
        for row in verify_result:
            print(f'{row.id:<6} {row.start_t:<8} {row.end_t:<8} {str(row.ts_end):<10} {row.total_hours:<8} {row.total_payment}₽')


if __name__ == "__main__":
    asyncio.run(fix_planned_shifts())

