#!/usr/bin/env python3
"""
Скрипт для принудительного закрытия активных смен через SQL.
Использование: python scripts/close_open_objects.py
"""

import asyncio
import pytz
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from core.database.session import get_async_session
from core.logging.logger import logger


async def close_active_shifts():
    """Принудительно закрывает все активные смены через SQL."""
    async with get_async_session() as session:
        now_utc = datetime.now(pytz.UTC)
        
        # Получаем активные смены через SQL
        active_shifts_query = text("""
            SELECT 
                s.id, s.object_id, s.user_id, s.start_time, s.end_time,
                s.hourly_rate, s.is_planned, s.time_slot_id,
                o.name as object_name, o.closing_time, o.timezone
            FROM shifts s
            JOIN objects o ON s.object_id = o.id
            WHERE s.status = 'active'
            ORDER BY s.start_time
        """)
        
        active_shifts_result = await session.execute(active_shifts_query)
        active_shifts = active_shifts_result.fetchall()
        
        logger.info(f"Found {len(active_shifts)} active shifts")
        
        closed_count = 0
        closed_object_ids = set()
        
        for row in active_shifts:
            try:
                shift_id = row.id
                object_id = row.object_id
                start_time = row.start_time
                hourly_rate = row.hourly_rate
                is_planned = row.is_planned
                time_slot_id = row.time_slot_id
                object_name = row.object_name
                closing_time = row.closing_time
                tz_name = row.timezone or 'Europe/Moscow'
                
                obj_tz = pytz.timezone(tz_name)
                
                # Определяем время закрытия
                end_time_utc = None
                
                # Для запланированных смен используем время из тайм-слота
                if is_planned and time_slot_id:
                    timeslot_query = text("SELECT end_time FROM time_slots WHERE id = :ts_id")
                    ts_result = await session.execute(timeslot_query, {"ts_id": time_slot_id})
                    ts_row = ts_result.fetchone()
                    
                    if ts_row and ts_row.end_time:
                        start_local = start_time.astimezone(obj_tz) if start_time.tzinfo else obj_tz.localize(start_time)
                        end_local = datetime.combine(start_local.date(), ts_row.end_time)
                        end_local = obj_tz.localize(end_local)
                        end_time_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Fallback: closing_time объекта
                if end_time_utc is None and closing_time:
                    start_local = start_time.astimezone(obj_tz) if start_time.tzinfo else obj_tz.localize(start_time)
                    end_local = datetime.combine(start_local.date(), closing_time)
                    end_local = obj_tz.localize(end_local)
                    end_time_utc = end_local.astimezone(pytz.UTC).replace(tzinfo=None)
                
                # Fallback: текущее время если прошло > 12 часов
                if end_time_utc is None:
                    if (now_utc.replace(tzinfo=None) - start_time).total_seconds() > 12 * 3600:
                        end_time_utc = now_utc.replace(tzinfo=None)
                
                if end_time_utc:
                    # Вычисляем продолжительность
                    duration = end_time_utc - start_time
                    total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                    total_hours = total_hours.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    total_payment = None
                    if hourly_rate:
                        rate_decimal = Decimal(str(hourly_rate))
                        total_payment = (total_hours * rate_decimal).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    # Обновляем смену через SQL
                    update_query = text("""
                        UPDATE shifts 
                        SET status = 'completed',
                            end_time = :end_time,
                            total_hours = :total_hours,
                            total_payment = :total_payment
                        WHERE id = :shift_id
                    """)
                    
                    await session.execute(update_query, {
                        "shift_id": shift_id,
                        "end_time": end_time_utc,
                        "total_hours": float(total_hours),
                        "total_payment": float(total_payment) if total_payment else None
                    })
                    
                    closed_count += 1
                    closed_object_ids.add(object_id)
                    logger.info(f"Closed shift {shift_id} (object {object_name}): {total_hours}h, {total_payment}₽")
                    
            except Exception as e:
                logger.error(f"Error closing shift {row.id}: {e}")
        
        if closed_count > 0:
            await session.commit()
            logger.info(f"✅ Closed {closed_count} shifts")
        
        # Закрываем ObjectOpening для объектов без активных смен
        closed_openings_count = 0
        try:
            # Получаем ВСЕ открытые ObjectOpening (не только из закрытых смен)
            open_openings_query = text("""
                SELECT id, object_id 
                FROM object_openings 
                WHERE closed_at IS NULL
            """)
            openings_result = await session.execute(open_openings_query)
            open_openings = openings_result.fetchall()
            
            logger.info(f"Checking {len(open_openings)} open ObjectOpenings for active shifts")
            
            # Для каждого открытого объекта проверяем активные смены
            for opening_row in open_openings:
                object_id = opening_row.object_id
                opening_id = opening_row.id
                # Проверяем количество активных смен
                active_count_query = text("""
                    SELECT COUNT(*) FROM shifts 
                    WHERE object_id = :obj_id AND status = 'active'
                """)
                count_result = await session.execute(active_count_query, {"obj_id": object_id})
                active_count = count_result.scalar()
                
                if active_count == 0:
                    # Закрываем ObjectOpening через SQL
                    close_opening_query = text("""
                        UPDATE object_openings 
                        SET closed_at = :closed_at,
                            closed_by = NULL
                        WHERE id = :opening_id
                    """)
                    
                    await session.execute(close_opening_query, {
                        "opening_id": opening_id,
                        "closed_at": now_utc.replace(tzinfo=None)
                    })
                    
                    closed_openings_count += 1
                    logger.info(f"Closed ObjectOpening {opening_id} for object {object_id}")
            
            if closed_openings_count > 0:
                await session.commit()
                logger.info(f"✅ Closed {closed_openings_count} ObjectOpenings")
                
        except Exception as e:
            logger.error(f"Error closing ObjectOpenings: {e}")
        
        return {
            "closed_shifts": closed_count,
            "closed_openings": closed_openings_count
        }


if __name__ == "__main__":
    print("🔄 Принудительное закрытие активных смен и открытых объектов...")
    result = asyncio.run(close_active_shifts())
    print(f"✅ Завершено: закрыто смен={result['closed_shifts']}, закрыто объектов={result['closed_openings']}")

