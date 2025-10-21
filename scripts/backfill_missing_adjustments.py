"""Создание adjustments для смен, которые не были обработаны задачей."""

import asyncio
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.org_structure import OrgStructureUnit
from domain.entities.payroll_adjustment import PayrollAdjustment


async def get_effective_late_settings_for_object(session, obj: Object) -> dict:
    """Получить эффективные настройки штрафов с учетом иерархии."""
    if not obj.inherit_late_settings and obj.late_threshold_minutes is not None and obj.late_penalty_per_minute is not None:
        return {
            'threshold_minutes': obj.late_threshold_minutes,
            'penalty_per_minute': obj.late_penalty_per_minute,
            'source': 'object'
        }
    
    if obj.org_unit_id:
        current_unit_id = obj.org_unit_id
        
        while current_unit_id:
            unit_query = select(OrgStructureUnit).where(OrgStructureUnit.id == current_unit_id)
            unit_result = await session.execute(unit_query)
            unit = unit_result.scalar_one_or_none()
            
            if not unit:
                break
            
            if not unit.inherit_late_settings and unit.late_threshold_minutes is not None and unit.late_penalty_per_minute is not None:
                return {
                    'threshold_minutes': unit.late_threshold_minutes,
                    'penalty_per_minute': unit.late_penalty_per_minute,
                    'source': f'org_unit:{unit.name}'
                }
            
            current_unit_id = unit.parent_id
    
    return {
        'threshold_minutes': None,
        'penalty_per_minute': None,
        'source': 'none'
    }


async def backfill_missing_adjustments():
    """Создать adjustments для completed смен без adjustments."""
    
    async with get_async_session() as session:
        # Найти completed смены без adjustments
        shifts_query = select(Shift).options(
            selectinload(Shift.object).selectinload(Object.org_unit),
            selectinload(Shift.time_slot)
        ).where(
            Shift.status == 'completed',
            Shift.end_time.isnot(None)
        ).order_by(Shift.id)
        
        shifts_result = await session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"Проверка {len(shifts)} completed смен")
        print(f"{'='*80}\n")
        
        shifts_without_adjustments = []
        
        for shift in shifts:
            # Проверяем есть ли adjustments
            adj_query = select(PayrollAdjustment).where(
                PayrollAdjustment.shift_id == shift.id
            )
            adj_result = await session.execute(adj_query)
            existing_adjustments = adj_result.scalars().all()
            
            if not existing_adjustments:
                shifts_without_adjustments.append(shift)
                print(f"❌ Смена {shift.id}: нет adjustments (закрыта {shift.end_time})")
        
        print(f"\n{'='*80}")
        print(f"Смен без adjustments: {len(shifts_without_adjustments)}")
        print(f"{'='*80}\n")
        
        if not shifts_without_adjustments:
            print("✅ Все смены имеют adjustments!")
            return
        
        response = input(f"\nСоздать adjustments для {len(shifts_without_adjustments)} смен? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Создание отменено")
            return
        
        created_count = 0
        for shift in shifts_without_adjustments:
            # 1. Создать shift_base
            shift_base = PayrollAdjustment(
                shift_id=shift.id,
                employee_id=shift.user_id,
                object_id=shift.object_id,
                adjustment_type='shift_base',
                amount=shift.total_payment or Decimal('0.00'),
                description=f'Базовая оплата за смену #{shift.id}',
                details={
                    'shift_id': shift.id,
                    'hours': float(shift.total_hours or 0),
                    'hourly_rate': float(shift.hourly_rate or 0)
                },
                created_by=shift.user_id,
                is_applied=False
            )
            session.add(shift_base)
            created_count += 1
            
            # 2. Проверить штраф за опоздание
            if shift.planned_start and shift.actual_start and shift.actual_start > shift.planned_start:
                late_seconds = (shift.actual_start - shift.planned_start).total_seconds()
                late_minutes = int(late_seconds / 60)
                
                late_settings = await get_effective_late_settings_for_object(session, shift.object)
                penalty_per_minute = late_settings.get('penalty_per_minute')
                threshold_minutes = late_settings.get('threshold_minutes', 0)
                
                if penalty_per_minute and late_minutes > threshold_minutes:
                    penalized_minutes = late_minutes - threshold_minutes
                    penalty_amount = Decimal(str(penalized_minutes)) * Decimal(str(penalty_per_minute))
                    
                    late_adjustment = PayrollAdjustment(
                        shift_id=shift.id,
                        employee_id=shift.user_id,
                        object_id=shift.object_id,
                        adjustment_type='late_start',
                        amount=-abs(penalty_amount),
                        description=f'Штраф за опоздание: {late_minutes} мин (порог {threshold_minutes} мин)',
                        details={
                            'shift_id': shift.id,
                            'late_minutes': late_minutes,
                            'threshold_minutes': threshold_minutes,
                            'penalized_minutes': penalized_minutes,
                            'penalty_per_minute': float(penalty_per_minute),
                            'planned_start': shift.planned_start.isoformat(),
                            'actual_start': shift.actual_start.isoformat()
                        },
                        created_by=shift.user_id,
                        is_applied=False
                    )
                    session.add(late_adjustment)
                    created_count += 1
                    
                    print(f"  ⚠️  Смена {shift.id}: штраф {penalty_amount}₽ за {late_minutes} мин (порог {threshold_minutes}, источник: {late_settings.get('source')})")
        
        await session.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ Создано adjustments: {created_count}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(backfill_missing_adjustments())

