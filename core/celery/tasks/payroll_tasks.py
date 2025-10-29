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
                    PaymentSchedule.is_active == True   # Только активные графики
                )
                schedules_result = await session.execute(schedules_query)
                schedules = schedules_result.scalars().all()
                
                logger.info(f"Found {len(schedules)} active payment schedules to check")
                
                total_entries_created = 0
                total_adjustments_applied = 0
                errors = []
                
                for schedule in schedules:
                    try:
                        # Проверяем, есть ли выплата сегодня для этого графика
                        logger.info(
                            "Schedule check",
                            schedule_id=schedule.id,
                            schedule_name=schedule.name,
                            frequency=schedule.frequency,
                            payment_day=schedule.payment_day,
                            period_cfg=schedule.payment_period,
                            today=today.isoformat()
                        )

                        payment_period = await _get_payment_period_for_date(schedule, today)
                        
                        if not payment_period:
                            logger.info(
                                "Skip schedule: not a payment day",
                                schedule_id=schedule.id
                            )
                            continue
                        
                        period_start = payment_period['period_start']
                        period_end = payment_period['period_end']

                        if period_start > period_end:
                            logger.warning(
                                "Invalid period (start > end)",
                                schedule_id=schedule.id,
                                period_start=period_start.isoformat(),
                                period_end=period_end.isoformat()
                            )
                            continue
                        
                        logger.info(
                            f"Processing schedule {schedule.id}: {schedule.name}",
                            period_start=period_start.isoformat(),
                            period_end=period_end.isoformat()
                        )
                        
                        # 2. Найти все объекты с этим payment_schedule_id
                        # Учитываем как прямую привязку, так и наследование от подразделения
                        
                        # Если у графика указан owner_id, берём ВСЕ активные объекты владельца
                        if schedule.owner_id:
                            objects_query = select(Object).where(
                                Object.is_active == True,
                                Object.owner_id == schedule.owner_id
                            )
                        else:
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
                                # 3. Найти сотрудников (contracts) для этого объекта
                                # Берём активные ИЛИ terminated с settlement_policy='schedule'
                                # Contract.allowed_objects - это JSON массив с ID объектов
                                from sqlalchemy import cast, text
                                from sqlalchemy.dialects.postgresql import JSONB
                                
                                contracts_query = select(Contract).where(
                                    and_(
                                        Contract.allowed_objects.isnot(None),
                                        cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj.id], JSONB)),
                                        or_(
                                            and_(Contract.status == 'active', Contract.is_active == True),
                                            and_(
                                                Contract.status == 'terminated',
                                                Contract.settlement_policy == 'schedule'
                                            )
                                        )
                                    )
                                )
                                contracts_result = await session.execute(contracts_query)
                                contracts = contracts_result.scalars().all()
                                
                                logger.debug(f"Found {len(contracts)} contracts (active + terminated/schedule) for object {obj.id}")
                                
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
                                        
                                        # Рассчитать итоговые суммы и часы
                                        gross_amount = Decimal('0.00')
                                        total_bonuses = Decimal('0.00')
                                        total_deductions = Decimal('0.00')
                                        total_hours = Decimal('0.00')
                                        avg_hourly_rate = Decimal('0.00')
                                        
                                        shift_adjustments = []
                                        for adj in adjustments:
                                            amount_decimal = Decimal(str(adj.amount))
                                            
                                            if adj.adjustment_type == 'shift_base':
                                                gross_amount += amount_decimal
                                                shift_adjustments.append(adj)
                                            elif amount_decimal > 0:
                                                total_bonuses += amount_decimal
                                            else:
                                                total_deductions += abs(amount_decimal)
                                        
                                        # Получить часы и ставку из смен
                                        if shift_adjustments:
                                            from domain.entities.shift import Shift
                                            shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]
                                            if shift_ids:
                                                shifts_result = await session.execute(
                                                    select(Shift).where(Shift.id.in_(shift_ids))
                                                )
                                                shifts = shifts_result.scalars().all()
                                                for shift in shifts:
                                                    if shift.total_hours:
                                                        total_hours += Decimal(str(shift.total_hours))
                                                    if shift.hourly_rate:
                                                        avg_hourly_rate = Decimal(str(shift.hourly_rate))
                                        
                                        # Если нет часов, попытаться рассчитать
                                        if total_hours == 0 and gross_amount > 0 and avg_hourly_rate > 0:
                                            total_hours = gross_amount / avg_hourly_rate
                                        
                                        # Если всё ещё нет ставки, взять из объекта
                                        if avg_hourly_rate == 0:
                                            avg_hourly_rate = Decimal(str(obj.hourly_rate)) if obj.hourly_rate else Decimal('200.00')
                                        
                                        net_amount = gross_amount + total_bonuses - total_deductions
                                        
                                        # Создать PayrollEntry
                                        payroll_entry = PayrollEntry(
                                            employee_id=contract.employee_id,
                                            contract_id=contract.id,
                                            object_id=obj.id,
                                            period_start=period_start,
                                            period_end=period_end,
                                            hours_worked=float(total_hours),
                                            hourly_rate=float(avg_hourly_rate),
                                            gross_amount=float(gross_amount),
                                            total_bonuses=float(total_bonuses),
                                            total_deductions=float(total_deductions),
                                            net_amount=float(net_amount)
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
        period_config = schedule.payment_period
        
        # НОВЫЙ формат: поддержка массива payments (несколько выплат в месяц)
        payments = period_config.get('payments', [])
        
        if payments:
            # Ищем выплату, у которой next_payment_date совпадает с target_date
            matching_payment = None
            for payment in payments:
                next_payment_str = payment.get('next_payment_date')
                if next_payment_str:
                    try:
                        next_payment = date.fromisoformat(next_payment_str)
                        if next_payment == target_date:
                            matching_payment = payment
                            break
                    except (ValueError, TypeError):
                        continue
            
            if not matching_payment:
                # Дата не совпадает ни с одной выплатой
                return None
            
            # Нашли нужную выплату - рассчитываем период
            start_offset = matching_payment.get('start_offset', 0)
            end_offset = matching_payment.get('end_offset', 0)
            
            period_start = target_date + timedelta(days=start_offset)
            period_end = target_date + timedelta(days=end_offset)
            
            # Если is_end_of_month=True, корректируем period_end до последнего дня месяца
            if matching_payment.get('is_end_of_month', False):
                # Вычисляем последний день месяца для period_end
                # Берём первый день следующего месяца и вычитаем 1 день
                if period_end.month == 12:
                    next_month_start = date(period_end.year + 1, 1, 1)
                else:
                    next_month_start = date(period_end.year, period_end.month + 1, 1)
                period_end = next_month_start - timedelta(days=1)
            
            return {
                'period_start': period_start,
                'period_end': period_end
            }
        
        # СТАРЫЙ формат: обратная совместимость (для системных графиков)
        # Проверяем, совпадает ли день месяца с днем выплаты
        if target_date.day != schedule.payment_day:
            return None
        
        # Используем старый формат с прямыми offset'ами
        start_offset = period_config.get('start_offset', -60)  # По умолчанию -60 дней назад
        end_offset = period_config.get('end_offset', -30)  # По умолчанию -30 дней назад
        
        # Рассчитываем период относительно даты выплаты
        period_start = target_date + timedelta(days=start_offset)
        period_end = target_date + timedelta(days=end_offset)
        
        # Проверяем calc_rules для старого формата
        calc_rules = period_config.get('calc_rules', {})
        if calc_rules.get('period') == 'previous_month':
            # Период - весь предыдущий месяц
            prev_month = target_date.month - 1
            prev_year = target_date.year
            if prev_month < 1:
                prev_month = 12
                prev_year -= 1
            
            period_start = date(prev_year, prev_month, 1)
            # Последний день предыдущего месяца
            first_day_current = date(target_date.year, target_date.month, 1)
            period_end = first_day_current - timedelta(days=1)
        
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


@celery_app.task(name="create_final_settlements_by_termination_date")
def create_final_settlements_by_termination_date():
    """
    Создаёт финальные расчёты для сотрудников в дату увольнения.
    
    Запускается ежедневно в 01:05.
    
    Логика:
    1. Находит все договоры с termination_date = сегодня и settlement_policy = 'termination_date'
    2. Для каждого договора:
       - Получает все неприменённые adjustments до даты увольнения (включительно)
       - Создаёт PayrollEntry
       - Проставляет payroll_entry_id и is_applied=TRUE у adjustments
    """
    
    async def process():
        try:
            today = date.today()
            logger.info(f"Starting final settlements for termination_date={today}")
            
            async with get_async_session() as session:
                # 1. Найти все контракты с termination_date=сегодня и settlement_policy='termination_date'
                contracts_query = select(Contract).where(
                    Contract.status == 'terminated',
                    Contract.settlement_policy == 'termination_date',
                    Contract.termination_date == today
                )
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                logger.info(f"Found {len(contracts)} contracts for final settlement")
                
                total_entries_created = 0
                total_adjustments_applied = 0
                errors = []
                
                for contract in contracts:
                    try:
                        # 2. Получить все неприменённые adjustments до даты увольнения
                        adjustment_service = PayrollAdjustmentService(session)
                        adjustments = await adjustment_service.get_unapplied_adjustments_until(
                            employee_id=contract.employee_id,
                            until_date=today
                        )
                        
                        if not adjustments:
                            logger.debug(
                                f"No adjustments for final settlement",
                                employee_id=contract.employee_id,
                                termination_date=today
                            )
                            continue
                        
                        # Рассчитать итоговые суммы и часы
                        gross_amount = Decimal('0.00')
                        total_bonuses = Decimal('0.00')
                        total_deductions = Decimal('0.00')
                        total_hours = Decimal('0.00')
                        avg_hourly_rate = Decimal('0.00')
                        
                        shift_adjustments = []
                        for adj in adjustments:
                            amount_decimal = Decimal(str(adj.amount))
                            
                            if adj.adjustment_type == 'shift_base':
                                gross_amount += amount_decimal
                                shift_adjustments.append(adj)
                            elif amount_decimal > 0:
                                total_bonuses += amount_decimal
                            else:
                                total_deductions += abs(amount_decimal)
                        
                        # Получить часы и ставку из смен
                        if shift_adjustments:
                            from domain.entities.shift import Shift
                            shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]
                            if shift_ids:
                                shifts_result = await session.execute(
                                    select(Shift).where(Shift.id.in_(shift_ids))
                                )
                                shifts = shifts_result.scalars().all()
                                for shift in shifts:
                                    if shift.total_hours:
                                        total_hours += Decimal(str(shift.total_hours))
                                    if shift.hourly_rate:
                                        avg_hourly_rate = Decimal(str(shift.hourly_rate))
                        
                        # Если нет часов, попытаться рассчитать
                        if total_hours == 0 and gross_amount > 0 and avg_hourly_rate > 0:
                            total_hours = gross_amount / avg_hourly_rate
                        
                        # Получить object_id из первого adjustment с object_id
                        object_id = next((adj.object_id for adj in adjustments if adj.object_id), None)
                        
                        # Если всё ещё нет ставки, взять из объекта
                        if avg_hourly_rate == 0 and object_id:
                            obj_result = await session.execute(
                                select(Object).where(Object.id == object_id)
                            )
                            obj = obj_result.scalar_one_or_none()
                            if obj and obj.hourly_rate:
                                avg_hourly_rate = Decimal(str(obj.hourly_rate))
                        
                        net_amount = gross_amount + total_bonuses - total_deductions
                        
                        # Создать PayrollEntry
                        payroll_entry = PayrollEntry(
                            employee_id=contract.employee_id,
                            contract_id=contract.id,
                            object_id=object_id,
                            period_start=None,  # Для финрасчёта период не указываем
                            period_end=today,
                            hours_worked=float(total_hours),
                            hourly_rate=float(avg_hourly_rate) if avg_hourly_rate else 0.0,
                            gross_amount=float(gross_amount),
                            total_bonuses=float(total_bonuses),
                            total_deductions=float(total_deductions),
                            net_amount=float(net_amount)
                        )
                        
                        session.add(payroll_entry)
                        await session.flush()
                        
                        # Отметить adjustments как применённые
                        adjustment_ids = [adj.id for adj in adjustments]
                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                            adjustment_ids=adjustment_ids,
                            payroll_entry_id=payroll_entry.id
                        )
                        
                        total_entries_created += 1
                        total_adjustments_applied += applied_count
                        
                        logger.info(
                            f"Created final settlement entry",
                            payroll_entry_id=payroll_entry.id,
                            employee_id=contract.employee_id,
                            termination_date=today,
                            gross_amount=float(gross_amount),
                            net_amount=float(net_amount),
                            adjustments_count=applied_count
                        )
                        
                    except Exception as e:
                        error_msg = f"Error creating final settlement for contract {contract.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Сохраняем все изменения
                await session.commit()
                
                logger.info(
                    f"Final settlements completed",
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
            logger.error(f"Critical error in final settlements task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())
