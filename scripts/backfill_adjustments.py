#!/usr/bin/env python3
"""Разовое создание adjustments по всем completed сменам за период."""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import select, and_
from core.database.session import get_async_session
from domain.entities.shift import Shift
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from domain.entities.payroll_adjustment import PayrollAdjustment
from core.logging.logger import logger


async def backfill_adjustments(start_date: date, end_date: date = None):
    """
    Создаёт adjustments для всех completed смен за период.
    
    Args:
        start_date: Начало периода
        end_date: Конец периода (по умолчанию - сегодня)
    """
    if end_date is None:
        end_date = date.today()
    
    print(f"Создание adjustments за период: {start_date} - {end_date}")
    print("=" * 60)
    
    async with get_async_session() as session:
        # Найти все completed смены за период БЕЗ adjustments
        shifts_query = (
            select(Shift)
            .where(
                Shift.status == 'completed',
                Shift.start_time >= datetime.combine(start_date, datetime.min.time()),
                Shift.start_time <= datetime.combine(end_date, datetime.max.time()),
                Shift.end_time.isnot(None)
            )
            .order_by(Shift.start_time)
        )
        
        result = await session.execute(shifts_query)
        shifts = result.scalars().all()
        
        print(f"Найдено {len(shifts)} completed смен за период")
        
        created_count = 0
        skipped_count = 0
        
        for shift in shifts:
            # Проверяем, есть ли уже adjustment для этой смены
            existing_adj_query = select(PayrollAdjustment).where(
                PayrollAdjustment.shift_id == shift.id,
                PayrollAdjustment.adjustment_type == 'shift_base'
            )
            existing_result = await session.execute(existing_adj_query)
            existing_adj = existing_result.scalar_one_or_none()
            
            if existing_adj:
                skipped_count += 1
                continue
            
            # Создаём base adjustment
            adj_service = PayrollAdjustmentService(session)
            
            try:
                await adj_service.create_shift_base_adjustment(
                    shift=shift,
                    employee_id=shift.user_id,
                    object_id=shift.object_id,
                    created_by=shift.user_id,  # Системное создание
                    description=f"Базовая оплата за смену #{shift.id} (backfill)"
                )
                created_count += 1
                
                if created_count % 10 == 0:
                    print(f"  Создано {created_count} adjustments...")
                    
            except Exception as e:
                logger.error(f"Error creating adjustment for shift {shift.id}: {e}")
                continue
        
        # Сохраняем всё
        await session.commit()
        
        print("=" * 60)
        print(f"✅ Создано новых adjustments: {created_count}")
        print(f"⏭️  Пропущено (уже есть): {skipped_count}")
        print(f"📊 Всего обработано: {len(shifts)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        start = date.fromisoformat(sys.argv[1])
    else:
        start = date(2025, 9, 30)
    
    if len(sys.argv) > 2:
        end = date.fromisoformat(sys.argv[2])
    else:
        end = date.today()
    
    asyncio.run(backfill_adjustments(start, end))

