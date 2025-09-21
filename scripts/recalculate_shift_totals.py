#!/usr/bin/env python3
"""Скрипт для пересчета total_hours и total_payment для завершенных смен."""

import asyncio
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.session import get_async_session
from sqlalchemy import select, update
from domain.entities.shift import Shift
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def recalculate_shift_totals():
    """Пересчитывает total_hours и total_payment для завершенных смен."""
    try:
        async with get_async_session() as session:
            # Получаем все завершенные смены без total_hours или total_payment
            shifts_query = select(Shift).where(
                Shift.status == 'completed',
                Shift.end_time.isnot(None),
                (Shift.total_hours.is_(None) | (Shift.total_hours == 0))
            )
            
            shifts_result = await session.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            
            logger.info(f"Найдено {len(shifts)} смен для пересчета")
            
            updated_count = 0
            
            for shift in shifts:
                try:
                    # Вычисляем общее время
                    duration = shift.end_time - shift.start_time
                    total_hours = round(duration.total_seconds() / 3600, 2)
                    
                    # Вычисляем общую оплату
                    hourly_rate = float(shift.hourly_rate) if shift.hourly_rate else 0.0
                    total_payment = round(total_hours * hourly_rate, 2) if hourly_rate > 0 else 0.0
                    
                    # Обновляем смену
                    update_query = update(Shift).where(Shift.id == shift.id).values(
                        total_hours=total_hours,
                        total_payment=total_payment
                    )
                    await session.execute(update_query)
                    
                    updated_count += 1
                    logger.info(f"Обновлена смена {shift.id}: {total_hours} часов, {total_payment} рублей")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обновлении смены {shift.id}: {e}")
                    continue
            
            # Сохраняем изменения
            await session.commit()
            
            logger.info(f"Успешно обновлено {updated_count} смен")
            return updated_count
            
    except Exception as e:
        logger.error(f"Ошибка при пересчете: {e}")
        return 0


async def main():
    """Основная функция."""
    logger.info("Начинаем пересчет total_hours и total_payment для завершенных смен...")
    
    updated_count = await recalculate_shift_totals()
    
    if updated_count > 0:
        logger.info(f"✅ Пересчет завершен! Обновлено {updated_count} смен")
    else:
        logger.info("ℹ️ Нет смен для пересчета")


if __name__ == "__main__":
    asyncio.run(main())
