#!/usr/bin/env python3
"""
Скрипт для принудительного закрытия активных смен.
Использование: python scripts/close_open_objects.py
"""

import asyncio
import pytz
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from core.logging.logger import logger


async def close_active_shifts():
    """Принудительно закрывает все активные смены."""
    async with get_async_session() as session:
        now_utc = datetime.now(pytz.UTC)
        
        # Находим все активные смены
        active_shifts_query = (
            select(Shift)
            .options(selectinload(Shift.object))
            .where(Shift.status == 'active')
        )
        
        active_shifts_result = await session.execute(active_shifts_query)
        active_shifts = active_shifts_result.scalars().all()
        
        logger.info(f"Found {len(active_shifts)} active shifts")
        
        closed_count = 0
        
        for shift in active_shifts:
            try:
                obj = shift.object
                if not obj:
                    logger.warning(f"Shift {shift.id} has no object, skipping")
                    continue
                
                tz_name = getattr(obj, 'timezone', None) or 'Europe/Moscow'
                obj_tz = pytz.timezone(tz_name)
                
                # Определяем время закрытия
                end_time_utc = None
                
                # Для запланированных смен используем время из тайм-слота
                if shift.is_planned and shift.time_slot_id:
                    timeslot_query = select(TimeSlot).where(TimeSlot.id == shift.time_slot_id)
                    timeslot_result = await session.execute(timeslot_query)
                    timeslot = timeslot_result.scalar_one_or_none()
                    
                    if timeslot and timeslot.end_time:
                        start_local = shift.start_time.astimezone(obj_tz) if shift.start_time.tzinfo else obj_tz.localize(shift.start_time)
                        end_local = datetime.combine(start_local.date(), timeslot.end_time)
                        end_local = obj_tz.localize(end_local)
                        end_time_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Fallback: closing_time объекта
                if end_time_utc is None and obj.closing_time:
                    start_local = shift.start_time.astimezone(obj_tz) if shift.start_time.tzinfo else obj_tz.localize(shift.start_time)
                    end_local = datetime.combine(start_local.date(), obj.closing_time)
                    end_local = obj_tz.localize(end_local)
                    end_time_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Fallback: текущее время если прошло > 12 часов
                if end_time_utc is None:
                    if (now_utc.replace(tzinfo=None) - shift.start_time).total_seconds() > 12 * 3600:
                        end_time_utc = now_utc.replace(tzinfo=None)
                
                if end_time_utc:
                    # Вычисляем продолжительность
                    duration = end_time_utc - shift.start_time
                    total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                    total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    total_payment = None
                    if shift.hourly_rate:
                        rate_decimal = Decimal(shift.hourly_rate)
                        total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    shift.end_time = end_time_utc
                    shift.status = 'completed'
                    shift.total_hours = float(total_hours)
                    shift.total_payment = float(total_payment) if total_payment else None
                    
                    closed_count += 1
                    logger.info(f"Closed shift {shift.id} (object {obj.name}): {shift.total_hours}h, {shift.total_payment}₽")
                    
            except Exception as e:
                logger.error(f"Error closing shift {shift.id}: {e}")
        
        if closed_count > 0:
            await session.commit()
            logger.info(f"✅ Closed {closed_count} shifts")
        
        return closed_count


if __name__ == "__main__":
    print("🔄 Принудительное закрытие активных смен...")
    closed = asyncio.run(close_active_shifts())
    print(f"✅ Завершено: закрыто смен={closed}")

