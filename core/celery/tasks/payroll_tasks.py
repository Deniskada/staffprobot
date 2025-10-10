"""Celery задачи для обработки начислений и автоудержаний."""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_

from domain.entities.shift import Shift
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.contract import Contract
from apps.web.services.auto_deduction_service import AutoDeductionService
from apps.web.services.payroll_service import PayrollService


@celery_app.task(name="process_automatic_deductions")
def process_automatic_deductions():
    """
    Обрабатывает автоматические удержания для закрытых смен.
    
    Запускается раз в день в 00:00.
    Находит все смены, закрытые за последние сутки,
    рассчитывает для них автоудержания и добавляет к начислениям.
    """
    import asyncio
    
    async def process():
        try:
            logger.info("Starting automatic deductions processing")
            
            async with get_async_session() as session:
                # Найти смены, закрытые за последние 24 часа
                yesterday = datetime.now() - timedelta(days=1)
                
                shifts_query = select(Shift).where(
                    and_(
                        Shift.status == 'completed',  # Статус для закрытых смен
                        Shift.end_time >= yesterday
                    )
                )
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                logger.info(f"Found {len(shifts)} closed shifts for processing")
                
                deduction_service = AutoDeductionService(session)
                payroll_service = PayrollService(session)
                
                total_processed = 0
                total_deductions = 0
                
                for shift in shifts:
                    try:
                        # Получить смену с объектом и подразделением для определения системы оплаты
                        from sqlalchemy.orm import selectinload
                        from domain.entities.object import Object
                        
                        shift_query = select(Shift).options(
                            selectinload(Shift.object).selectinload(Object.org_unit)
                        ).where(Shift.id == shift.id)
                        shift_result = await session.execute(shift_query)
                        shift_with_obj = shift_result.scalar_one()
                        
                        # Получить активный контракт
                        contract_query = select(Contract).where(
                            and_(
                                Contract.employee_id == shift.user_id,
                                Contract.status == 'active',
                                Contract.is_active == True
                            )
                        ).order_by(Contract.created_at.desc())
                        contract_result = await session.execute(contract_query)
                        contract = contract_result.scalars().first()
                        
                        if not contract:
                            logger.debug(
                                "Skipping shift - no active contract",
                                shift_id=shift.id
                            )
                            continue
                        
                        # Определить эффективную систему оплаты с учетом приоритетов
                        # 1. Если use_contract_payment_system=True → берем из договора
                        # 2. Иначе → берем из объекта (с учетом наследования от подразделения)
                        object_payment_system = shift_with_obj.object.get_effective_payment_system_id()
                        effective_payment_system = contract.get_effective_payment_system_id(object_payment_system)
                        
                        # Премии/штрафы применяются только для "Повременно-премиальной" системы (id=3)
                        if effective_payment_system != 3:
                            logger.debug(
                                "Skipping shift - payment system is not hourly_bonus",
                                shift_id=shift.id,
                                effective_payment_system=effective_payment_system,
                                source="contract" if contract.use_contract_payment_system else "object/org_unit"
                            )
                            continue
                        
                        # Рассчитать автоудержания
                        auto_deductions = await deduction_service.calculate_deductions_for_shift(shift.id)
                        
                        if not auto_deductions:
                            continue
                        
                        # Найти или создать payroll_entry для смены
                        # Ищем существующее начисление за период смены
                        shift_date = shift.end_time.date()
                        
                        payroll_query = select(PayrollEntry).where(
                            and_(
                                PayrollEntry.employee_id == shift.user_id,
                                PayrollEntry.period_start <= shift_date,
                                PayrollEntry.period_end >= shift_date
                            )
                        )
                        payroll_result = await session.execute(payroll_query)
                        payroll_entry = payroll_result.scalars().first()
                        
                        # Если нет начисления - пропускаем (начисление создается вручную)
                        if not payroll_entry:
                            logger.warning(
                                f"No payroll entry found for shift",
                                shift_id=shift.id,
                                employee_id=shift.user_id,
                                shift_date=shift_date.isoformat()
                            )
                            continue
                        
                        # Добавить начисления (удержания/премии) к начислению
                        for adjustment_type, amount, description, details in auto_deductions:
                            # Добавляем shift_id в details
                            details_with_shift = details.copy() if details else {}
                            details_with_shift['shift_id'] = shift.id
                            
                            # Определяем тип начисления по adjustment_type
                            # Штрафы: late_start, task_penalty
                            # Премии: task_bonus
                            if adjustment_type in ('late_start', 'task_penalty') or amount < 0:
                                # Удержание (штраф)
                                await payroll_service.add_deduction(
                                    payroll_entry_id=payroll_entry.id,
                                    deduction_type=adjustment_type,
                                    amount=abs(amount),  # add_deduction ожидает положительное значение
                                    description=description,
                                    is_automatic=True,
                                    created_by_id=shift.user_id,
                                    details=details_with_shift
                                )
                                total_deductions += 1
                            elif adjustment_type == 'task_bonus' or amount > 0:
                                # Премия
                                await payroll_service.add_bonus(
                                    payroll_entry_id=payroll_entry.id,
                                    bonus_type=adjustment_type,
                                    amount=abs(amount),
                                    description=description,
                                    created_by_id=shift.user_id,
                                    details=details_with_shift
                                )
                                total_deductions += 1  # Считаем и премии
                        
                        total_processed += 1
                        
                        logger.info(
                            f"Auto-deductions applied to shift",
                            shift_id=shift.id,
                            payroll_entry_id=payroll_entry.id,
                            deductions_count=len(auto_deductions)
                        )
                        
                    except Exception as e:
                        logger.error(
                            f"Error processing auto-deductions for shift",
                            shift_id=shift.id,
                            error=str(e)
                        )
                        continue
                
                logger.info(
                    f"Automatic deductions processing completed",
                    shifts_processed=total_processed,
                    deductions_added=total_deductions
                )
                
                return {
                    'success': True,
                    'shifts_processed': total_processed,
                    'deductions_added': total_deductions
                }
                
        except Exception as e:
            logger.error(f"Error in automatic deductions task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())

