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
                        Shift.status == 'closed',
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
                            # Отрицательная сумма → удержание (штраф)
                            if amount < 0:
                                # Добавляем shift_id в details
                                details_with_shift = details.copy() if details else {}
                                details_with_shift['shift_id'] = shift.id
                                
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
                            # Положительная сумма → премия
                            elif amount > 0:
                                # Добавляем shift_id в details
                                details_with_shift = details.copy() if details else {}
                                details_with_shift['shift_id'] = shift.id
                                
                                await payroll_service.add_bonus(
                                    payroll_entry_id=payroll_entry.id,
                                    bonus_type=adjustment_type,
                                    amount=amount,
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

