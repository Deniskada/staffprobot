"""Celery задачи для автоматического создания начислений по графику выплат."""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any
import asyncio

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from domain.entities.payment_schedule import PaymentSchedule
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.org_structure import OrgStructureUnit
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
                        # Учитываем как прямую привязку, так и наследование от подразделения
                        
                        # Сначала найдем ID подразделений с этим графиком
                        units_query = select(OrgStructureUnit.id).where(
                            OrgStructureUnit.payment_schedule_id == schedule.id,
                            OrgStructureUnit.is_active == True
                        )
                        units_result = await session.execute(units_query)
                        unit_ids = [row[0] for row in units_result.all()]
                        
                        # Теперь найдем объекты:
                        # - с прямой привязкой к графику ИЛИ
                        # - принадлежащие подразделению с этим графиком
                        objects_query = select(Object).where(
                            Object.is_active == True,
                            or_(
                                Object.payment_schedule_id == schedule.id,
                                Object.org_unit_id.in_(unit_ids) if unit_ids else False
                            )
                        )
                        objects_result = await session.execute(objects_query)
                        objects = objects_result.scalars().all()
                        
                        logger.info(f"Found {len(objects)} objects for schedule {schedule.id}")
                        
                        for obj in objects:
                            try:
                                # 3. Найти активных сотрудников (contracts) для этого объекта
                                # Contract.allowed_objects - это JSON массив с ID объектов
                                from sqlalchemy import cast, text
                                from sqlalchemy.dialects.postgresql import JSONB
                                
                                contracts_query = select(Contract).where(
                                    and_(
                                        Contract.status == 'active',
                                        Contract.is_active == True,
                                        Contract.allowed_objects.isnot(None),
                                        cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj.id], JSONB))
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
    if not schedule.payment_period:
        return None
    
    # Обработка еженедельных графиков
    if schedule.frequency == 'weekly':
        # payment_day: 1 = понедельник, 2 = вторник, ... 7 = воскресенье
        # weekday(): 0 = понедельник, 1 = вторник, ... 6 = воскресенье
        target_weekday = target_date.weekday() + 1  # Конвертируем в 1-7
        
        if target_weekday != schedule.payment_day:
            # Сегодня не день выплаты
            return None
        
        # Получаем настройки периода из payment_period
        period_config = schedule.payment_period
        start_offset = period_config.get('start_offset', -22)  # По умолчанию -22 дня
        end_offset = period_config.get('end_offset', -16)  # По умолчанию -16 дней
        
        # Рассчитываем период относительно даты выплаты
        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)
        
        return {
            'period_start': period_start,
            'period_end': period_end
        }
    
    # Обработка двухнедельных графиков (аналогично weekly)
    elif schedule.frequency == 'biweekly':
        target_weekday = target_date.weekday() + 1
        
        if target_weekday != schedule.payment_day:
            return None
        
        period_config = schedule.payment_period
        start_offset = period_config.get('start_offset', -28)  # По умолчанию -28 дней
        end_offset = period_config.get('end_offset', -14)  # По умолчанию -14 дней
        
        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)
        
        return {
            'period_start': period_start,
            'period_end': period_end
        }
    
    # Обработка месячных графиков
    elif schedule.frequency == 'monthly':
        # Проверяем, совпадает ли сегодняшний день месяца с днем выплаты
        if target_date.day != schedule.payment_day:
            return None
        
        # Получаем настройки периода из payment_period
        period_config = schedule.payment_period
        start_offset = period_config.get('start_offset', -60)  # По умолчанию -60 дней назад
        end_offset = period_config.get('end_offset', -30)  # По умолчанию -30 дней назад
        
        # Рассчитываем период относительно даты выплаты
        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)
        
        return {
            'period_start': period_start,
            'period_end': period_end
        }
    
    # Обработка ежедневных графиков (выплата каждый день)
    elif schedule.frequency == 'daily':
        period_config = schedule.payment_period
        start_offset = period_config.get('start_offset', -1)  # По умолчанию -1 день
        end_offset = period_config.get('end_offset', -1)  # По умолчанию -1 день
        
        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)
        
        return {
            'period_start': period_start,
            'period_end': period_end
        }
    
    return None
