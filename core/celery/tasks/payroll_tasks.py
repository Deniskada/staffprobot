"""Celery задачи для автоматического создания начислений по графику выплат."""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any
import asyncio

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from domain.entities.payment_schedule import PaymentSchedule
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_adjustment import PayrollAdjustment
from shared.services.payroll_adjustment_service import PayrollAdjustmentService


@celery_app.task(name="create_payroll_entries_by_schedule")
def create_payroll_entries_by_schedule():
    """
    Автоматически создает начисления (payroll_entries) по графикам выплат.
    
    Запускается ежедневно в 01:00.
    
    Логика:
    1. Находит все payment_schedules, у которых дата выплаты = сегодня
    2. Для каждого графика находит все объекты с этим payment_schedule_id
    3. Для каждого объекта находит активных сотрудников (contracts)
    4. Для каждого сотрудника:
       - Определяет период выплаты из schedule (period_start, period_end)
       - Получает все is_applied=FALSE adjustments за период
       - Создает PayrollEntry
       - Проставляет payroll_entry_id и is_applied=TRUE у adjustments
    """
    
    async def process():
        try:
            today = date.today()
            logger.info(f"Starting payroll entries creation for {today}")
            
            async with get_async_session() as session:
                # 1. Найти все schedules с датой выплаты сегодня
                schedules_query = select(PaymentSchedule).where(
                    PaymentSchedule.is_custom == True  # Только пользовательские графики
                )
                schedules_result = await session.execute(schedules_query)
                schedules = schedules_result.scalars().all()
                
                logger.info(f"Found {len(schedules)} payment schedules to check")
                
                total_entries_created = 0
                total_adjustments_applied = 0
                errors = []
                
                for schedule in schedules:
                    try:
                        # Проверяем, есть ли выплата сегодня для этого графика
                        payment_period = await _get_payment_period_for_date(schedule, today)
                        
                        if not payment_period:
                            # Сегодня не день выплаты для этого графика
                            continue
                        
                        period_start = payment_period['period_start']
                        period_end = payment_period['period_end']
                        
                        logger.info(
                            f"Processing schedule {schedule.id}: {schedule.name}",
                            period_start=period_start.isoformat(),
                            period_end=period_end.isoformat()
                        )
                        
                        # 2. Найти все объекты с этим payment_schedule_id
                        objects_query = select(Object).where(
                            Object.payment_schedule_id == schedule.id,
                            Object.is_active == True
                        )
                        objects_result = await session.execute(objects_query)
                        objects = objects_result.scalars().all()
                        
                        logger.info(f"Found {len(objects)} objects for schedule {schedule.id}")
                        
                        for obj in objects:
                            try:
                                # 3. Найти активных сотрудников (contracts) для этого объекта
                                contracts_query = select(Contract).where(
                                    and_(
                                        Contract.object_id == obj.id,
                                        Contract.status == 'active',
                                        Contract.is_active == True
                                    )
                                )
                                contracts_result = await session.execute(contracts_query)
                                contracts = contracts_result.scalars().all()
                                
                                logger.debug(f"Found {len(contracts)} active contracts for object {obj.id}")
                                
                                for contract in contracts:
                                    try:
                                        # 4. Создать payroll_entry для сотрудника
                                        adjustment_service = PayrollAdjustmentService(session)
                                        
                                        # Получить неприменённые adjustments за период
                                        adjustments = await adjustment_service.get_unapplied_adjustments(
                                            employee_id=contract.employee_id,
                                            period_start=period_start,
                                            period_end=period_end
                                        )
                                        
                                        if not adjustments:
                                            logger.debug(
                                                f"No adjustments for employee",
                                                employee_id=contract.employee_id,
                                                period_start=period_start,
                                                period_end=period_end
                                            )
                                            continue
                                        
                                        # Рассчитать итоговые суммы
                                        gross_amount = Decimal('0.00')
                                        total_bonuses = Decimal('0.00')
                                        total_deductions = Decimal('0.00')
                                        
                                        for adj in adjustments:
                                            amount_decimal = Decimal(str(adj.amount))
                                            
                                            if adj.adjustment_type == 'shift_base':
                                                gross_amount += amount_decimal
                                            elif amount_decimal > 0:
                                                total_bonuses += amount_decimal
                                            else:
                                                total_deductions += abs(amount_decimal)
                                        
                                        net_amount = gross_amount + total_bonuses - total_deductions
                                        
                                        # Создать PayrollEntry
                                        payroll_entry = PayrollEntry(
                                            employee_id=contract.employee_id,
                                            contract_id=contract.id,
                                            object_id=obj.id,
                                            period_start=period_start,
                                            period_end=period_end,
                                            gross_amount=float(gross_amount),
                                            total_bonuses=float(total_bonuses),
                                            total_deductions=float(total_deductions),
                                            net_amount=float(net_amount),
                                            status='pending',
                                            payment_schedule_id=schedule.id
                                        )
                                        
                                        session.add(payroll_entry)
                                        await session.flush()
                                        
                                        # Отметить adjustments как примененные
                                        adjustment_ids = [adj.id for adj in adjustments]
                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                            adjustment_ids=adjustment_ids,
                                            payroll_entry_id=payroll_entry.id
                                        )
                                        
                                        total_entries_created += 1
                                        total_adjustments_applied += applied_count
                                        
                                        logger.info(
                                            f"Created payroll entry",
                                            payroll_entry_id=payroll_entry.id,
                                            employee_id=contract.employee_id,
                                            object_id=obj.id,
                                            gross_amount=float(gross_amount),
                                            net_amount=float(net_amount),
                                            adjustments_count=applied_count
                                        )
                                        
                                    except Exception as e:
                                        error_msg = f"Error creating payroll entry for contract {contract.id}: {e}"
                                        logger.error(error_msg)
                                        errors.append(error_msg)
                                        continue
                                
                            except Exception as e:
                                error_msg = f"Error processing object {obj.id}: {e}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                continue
                        
                    except Exception as e:
                        error_msg = f"Error processing schedule {schedule.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Сохраняем все изменения
                await session.commit()
                
                logger.info(
                    f"Payroll entries creation completed",
                    entries_created=total_entries_created,
                    adjustments_applied=total_adjustments_applied,
                    errors_count=len(errors)
                )
                
                return {
                    'success': True,
                    'date': today.isoformat(),
                    'entries_created': total_entries_created,
                    'adjustments_applied': total_adjustments_applied,
                    'errors': errors
                }
                
        except Exception as e:
            logger.error(f"Critical error in payroll entries task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())


async def _get_payment_period_for_date(
    schedule: PaymentSchedule,
    target_date: date
) -> Dict[str, date]:
    """
    Определяет период выплаты для заданной даты по графику.
    
    Args:
        schedule: График выплат
        target_date: Дата, для которой проверяем
        
    Returns:
        dict: {'period_start': date, 'period_end': date} или None если сегодня не день выплаты
    """
    if not schedule.periods:
        return None
    
    # Проверяем каждый период в графике
    for period in schedule.periods:
        # Формат периода: {'start_day': int, 'end_day': int, 'offset_days': int, ...}
        payment_day = period.get('payment_day')  # День месяца для выплаты
        
        if not payment_day:
            continue
        
        # Проверяем, совпадает ли сегодняшний день с днем выплаты
        if target_date.day == payment_day:
            # Определяем период
            start_day = period.get('start_day', 1)
            end_day = period.get('end_day', 31)
            
            # Месяц периода - предыдущий месяц от даты выплаты
            # (т.к. выплата за прошедший период)
            if target_date.month == 1:
                period_month = 12
                period_year = target_date.year - 1
            else:
                period_month = target_date.month - 1
                period_year = target_date.year
            
            # Формируем даты начала и конца периода
            from calendar import monthrange
            last_day_of_period = monthrange(period_year, period_month)[1]
            
            period_start = date(period_year, period_month, min(start_day, last_day_of_period))
            period_end = date(period_year, period_month, min(end_day, last_day_of_period))
            
            return {
                'period_start': period_start,
                'period_end': period_end
            }
    
    return None
