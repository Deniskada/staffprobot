"""Исправление смен с двойным смещением часового пояса."""

import asyncio
from datetime import datetime, time as dt_time
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import pytz

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object


async def find_and_fix_timezone_shifts():
    """Найти и исправить смены с неправильным смещением часового пояса."""
    
    async with get_async_session() as session:
        # Получаем все shift_schedules с привязкой к тайм-слотам
        query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.time_slot),
            selectinload(ShiftSchedule.object)
        ).where(
            ShiftSchedule.time_slot_id.isnot(None),
            ShiftSchedule.status.in_(['planned', 'confirmed'])
        ).order_by(ShiftSchedule.id)
        
        result = await session.execute(query)
        shifts = result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"Проверка {len(shifts)} запланированных смен на корректность timezone")
        print(f"{'='*80}\n")
        
        problematic_shifts = []
        
        for shift in shifts:
            if not shift.time_slot or not shift.object:
                continue
            
            timeslot = shift.time_slot
            obj = shift.object
            
            # Получаем timezone объекта
            object_timezone = obj.timezone if obj.timezone else 'Europe/Moscow'
            tz = pytz.timezone(object_timezone)
            
            # Правильное UTC время = локальное время тайм-слота локализованное и конвертированное в UTC
            correct_start_naive = datetime.combine(timeslot.slot_date, timeslot.start_time)
            correct_end_naive = datetime.combine(timeslot.slot_date, timeslot.end_time)
            
            correct_start_utc = tz.localize(correct_start_naive).astimezone(pytz.UTC).replace(tzinfo=None)
            correct_end_utc = tz.localize(correct_end_naive).astimezone(pytz.UTC).replace(tzinfo=None)
            
            # Приводим сохранённое время к naive для сравнения
            current_start = shift.planned_start.replace(tzinfo=None) if shift.planned_start.tzinfo else shift.planned_start
            current_end = shift.planned_end.replace(tzinfo=None) if shift.planned_end.tzinfo else shift.planned_end
            
            # Сравниваем с сохранённым временем
            if current_start != correct_start_utc or current_end != correct_end_utc:
                problematic_shifts.append({
                    'shift_id': shift.id,
                    'object_id': obj.id,
                    'object_name': obj.name,
                    'timezone': object_timezone,
                    'slot_date': timeslot.slot_date,
                    'timeslot_local': f"{timeslot.start_time} - {timeslot.end_time}",
                    'current_planned': f"{shift.planned_start} - {shift.planned_end}",
                    'correct_planned': f"{correct_start_utc} - {correct_end_utc}",
                    'shift': shift,
                    'correct_start': correct_start_utc,
                    'correct_end': correct_end_utc
                })
                
                print(f"❌ Смена {shift.id}:")
                print(f"   Объект: {obj.name} (timezone: {object_timezone})")
                print(f"   Дата: {timeslot.slot_date}")
                print(f"   Тайм-слот (локально): {timeslot.start_time} - {timeslot.end_time}")
                print(f"   Сохранено (UTC):      {current_start} - {current_end}")
                print(f"   Должно быть (UTC):    {correct_start_utc} - {correct_end_utc}")
                print(f"   Разница: {(current_start - correct_start_utc).total_seconds() / 3600:.1f} часов\n")
        
        print(f"{'='*80}")
        print(f"Найдено проблемных смен: {len(problematic_shifts)}")
        print(f"{'='*80}\n")
        
        if not problematic_shifts:
            print("✅ Все смены имеют корректное время!")
            return
        
        # Запрашиваем подтверждение на исправление
        response = input(f"\nИсправить {len(problematic_shifts)} проблемных смен? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Исправление отменено")
            return
        
        # Исправляем смены
        fixed_count = 0
        for item in problematic_shifts:
            shift = item['shift']
            shift.planned_start = item['correct_start']
            shift.planned_end = item['correct_end']
            fixed_count += 1
        
        await session.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ Исправлено смен: {fixed_count}")
        print(f"{'='*80}\n")
        
        # Показываем примеры исправлений
        print("\nПримеры исправлений:")
        for item in problematic_shifts[:5]:
            print(f"  Смена {item['shift_id']}: {item['object_name']}")
            print(f"    Было:    {item['current_planned']}")
            print(f"    Стало:   {item['correct_planned']}")
            print()


if __name__ == "__main__":
    asyncio.run(find_and_fix_timezone_shifts())

