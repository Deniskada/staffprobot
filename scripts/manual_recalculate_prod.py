"""Скрипт для ручного запуска пересчёта начислений на проде."""

import asyncio
from datetime import date
from sqlalchemy import select

from core.database.session import get_async_session
from domain.entities.payment_schedule import PaymentSchedule
from shared.services.user_service import get_user_id_from_telegram_id


async def manual_recalculate(target_date_str: str, owner_telegram_id: int):
    """
    Вручную запустить пересчёт начислений.
    
    Args:
        target_date_str: Дата в формате YYYY-MM-DD
        owner_telegram_id: Telegram ID владельца
    """
    target_date_obj = date.fromisoformat(target_date_str)
    
    async with get_async_session() as session:
        # Получить user_id владельца
        owner_id = await get_user_id_from_telegram_id(owner_telegram_id, session)
        if not owner_id:
            print(f"❌ Владелец с telegram_id={owner_telegram_id} не найден")
            return
        
        print(f"✅ Owner ID: {owner_id}, target_date: {target_date_obj}")
        
        # Импорт логики из payroll.py
        from apps.web.routes.payroll import owner_payroll_manual_recalculate
        from core.config.settings import settings
        from fastapi import Request
        from starlette.datastructures import FormData
        
        # Эмулируем Request
        class FakeRequest:
            pass
        
        request = FakeRequest()
        
        # Вызываем функцию напрямую
        from core.celery.tasks.payroll_tasks import _get_payment_period_for_date
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        from domain.entities.object import Object
        from domain.entities.contract import Contract
        from domain.entities.payroll_entry import PayrollEntry
        from domain.entities.payroll_adjustment import PayrollAdjustment
        from sqlalchemy import and_, or_, cast
        from sqlalchemy.dialects.postgresql import JSONB
        from decimal import Decimal
        from core.logging.logger import logger
        
        # Найти активные payment_schedules владельца
        schedules_query = select(PaymentSchedule).where(
            PaymentSchedule.owner_id == owner_id,
            PaymentSchedule.is_active == True
        )
        schedules_result = await session.execute(schedules_query)
        schedules = schedules_result.scalars().all()
        
        print(f"📋 Found {len(schedules)} active schedules")
        
        total_entries = 0
        total_adjustments = 0
        
        for schedule in schedules:
            # Проверка дня выплаты
            payment_period = await _get_payment_period_for_date(schedule, target_date_obj)
            
            if not payment_period:
                print(f"⏭️  Schedule {schedule.id} ({schedule.name}): not a payment day")
                continue
            
            period_start = payment_period['period_start']
            period_end = payment_period['period_end']
            
            print(f"✅ Schedule {schedule.id} ({schedule.name}): period {period_start} → {period_end}")
            
            # Найти объекты владельца
            objects_query = select(Object).where(
                Object.is_active == True,
                Object.owner_id == owner_id
            )
            objects_result = await session.execute(objects_query)
            objects = objects_result.scalars().all()
            
            print(f"   📦 Found {len(objects)} objects")
            
            for obj in objects:
                # Найти контракты (включая terminated + settlement_policy='schedule')
                contracts_query = select(Contract).where(
                    and_(
                        Contract.allowed_objects.isnot(None),
                        cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj.id], JSONB)),
                        or_(
                            Contract.status == 'active',  # ВСЕ активные
                            and_(
                                Contract.status == 'terminated',
                                Contract.settlement_policy == 'schedule'
                            )
                        )
                    )
                )
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                if not contracts:
                    continue
                
                print(f"      👥 Object {obj.id} ({obj.name}): {len(contracts)} contracts")
                
                for contract in contracts:
                    adjustment_service = PayrollAdjustmentService(session)
                    
                    # Получить неприменённые adjustments за период
                    adjustments = await adjustment_service.get_unapplied_adjustments(
                        employee_id=contract.employee_id,
                        period_start=period_start,
                        period_end=period_end
                    )
                    
                    if not adjustments:
                        print(f"         ⚪ Employee {contract.employee_id}: no adjustments")
                        continue
                    
                    print(f"         ✅ Employee {contract.employee_id}: {len(adjustments)} adjustments → creating entry")
                    
                    # Проверить, существует ли начисление
                    existing_entry_query = select(PayrollEntry).where(
                        PayrollEntry.employee_id == contract.employee_id,
                        PayrollEntry.period_start == period_start,
                        PayrollEntry.period_end == period_end,
                        PayrollEntry.object_id == obj.id
                    )
                    existing_entry_result = await session.execute(existing_entry_query)
                    existing_entry = existing_entry_result.scalar_one_or_none()
                    
                    # Рассчитать суммы
                    gross = Decimal('0')
                    bonuses = Decimal('0')
                    deductions = Decimal('0')
                    
                    for adj in adjustments:
                        amount = Decimal(str(adj.amount))
                        if adj.adjustment_type == 'shift_base':
                            gross += amount
                        elif amount > 0:
                            bonuses += amount
                        else:
                            deductions += abs(amount)
                    
                    net = gross + bonuses - deductions
                    
                    if existing_entry:
                        print(f"            ♻️  Updating existing entry {existing_entry.id}")
                        existing_entry.gross_amount = float(gross)
                        existing_entry.total_bonuses = float(bonuses)
                        existing_entry.total_deductions = float(deductions)
                        existing_entry.net_amount = float(net)
                    else:
                        print(f"            ➕ Creating new entry")
                        entry = PayrollEntry(
                            employee_id=contract.employee_id,
                            contract_id=contract.id,
                            object_id=obj.id,
                            period_start=period_start,
                            period_end=period_end,
                            gross_amount=float(gross),
                            total_bonuses=float(bonuses),
                            total_deductions=float(deductions),
                            net_amount=float(net),
                            hours_worked=0.0,  # Рассчитается позже
                            hourly_rate=float(obj.hourly_rate) if obj.hourly_rate else 200.0
                        )
                        session.add(entry)
                        await session.flush()
                        existing_entry = entry
                        total_entries += 1
                    
                    # Отметить корректировки как применённые
                    for adj in adjustments:
                        adj.payroll_entry_id = existing_entry.id
                        adj.is_applied = True
                        total_adjustments += 1
        
        await session.commit()
        print(f"\n✅ ИТОГО: {total_entries} начислений, {total_adjustments} корректировок")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python manual_recalculate_prod.py <date> <owner_telegram_id>")
        print("Example: python manual_recalculate_prod.py 2025-10-25 1170536174")
        sys.exit(1)
    
    target_date = sys.argv[1]
    owner_tg_id = int(sys.argv[2])
    
    asyncio.run(manual_recalculate(target_date, owner_tg_id))

