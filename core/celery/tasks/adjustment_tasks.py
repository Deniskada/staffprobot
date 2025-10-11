"""Celery задача для создания корректировок начислений из закрытых смен."""

from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from domain.entities.shift import Shift
from domain.entities.object import Object
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.late_penalty_calculator import LatePenaltyCalculator


@celery_app.task(name="process_closed_shifts_adjustments")
def process_closed_shifts_adjustments():
    """
    Обрабатывает недавно закрытые смены и создает для них корректировки начислений.
    
    Запускается каждые 10 минут.
    
    Логика:
    1. Находит все смены, закрытые за последние 15 минут
    2. Для каждой смены проверяет, созданы ли adjustments
    3. Если нет - создает:
       - shift_base (базовая оплата)
       - late_start (штраф за опоздание, если есть)
       - task_bonus/task_penalty (за задачи из object.shift_tasks JSONB)
    """
    
    async def process():
        try:
            logger.info("Starting closed shifts adjustments processing")
            
            # Время последней обработки - 15 минут назад
            cutoff_time = datetime.now() - timedelta(minutes=15)
            
            async with get_async_session() as session:
                # Найти смены, закрытые за последние 15 минут
                shifts_query = select(Shift).options(
                    selectinload(Shift.object).selectinload(Object.org_unit),
                    selectinload(Shift.time_slot)
                ).where(
                    and_(
                        Shift.status == 'completed',
                        Shift.end_time >= cutoff_time,
                        Shift.end_time.isnot(None)
                    )
                ).order_by(Shift.end_time.desc())
                
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                logger.info(f"Found {len(shifts)} closed shifts for processing")
                
                if not shifts:
                    return {
                        'success': True,
                        'shifts_processed': 0,
                        'adjustments_created': 0
                    }
                
                total_processed = 0
                total_adjustments = 0
                errors = []
                
                for shift in shifts:
                    try:
                        # Проверить, уже созданы ли adjustments для этой смены
                        from domain.entities.payroll_adjustment import PayrollAdjustment
                        
                        existing_query = select(PayrollAdjustment).where(
                            PayrollAdjustment.shift_id == shift.id
                        )
                        existing_result = await session.execute(existing_query)
                        existing = existing_result.scalar_one_or_none()
                        
                        if existing:
                            logger.debug(f"Adjustments already exist for shift {shift.id}, skipping")
                            continue
                        
                        # 1. Создать базовую оплату за смену (напрямую без сервиса)
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
                        total_adjustments += 1
                        
                        # 2. Проверить и создать штраф за опоздание (если есть planned_start)
                        if shift.object and hasattr(shift, 'planned_start') and shift.planned_start and shift.start_time:
                            # Получить настройки штрафов (inline логика)
                            obj = shift.object
                            threshold_minutes = None
                            penalty_per_minute = None
                            
                            if not obj.inherit_late_settings and obj.late_threshold_minutes is not None and obj.late_penalty_per_minute is not None:
                                threshold_minutes = obj.late_threshold_minutes
                                penalty_per_minute = obj.late_penalty_per_minute
                            elif obj.org_unit:
                                # Получить от org_unit
                                org_unit = obj.org_unit
                                if not org_unit.inherit_late_settings and org_unit.late_threshold_minutes is not None:
                                    threshold_minutes = org_unit.late_threshold_minutes
                                    penalty_per_minute = org_unit.late_penalty_per_minute
                            
                            if threshold_minutes is not None and penalty_per_minute is not None:
                                # Рассчитать опоздание
                                delta = shift.start_time - shift.planned_start
                                late_minutes = int(delta.total_seconds() / 60)
                                
                                if late_minutes > threshold_minutes:
                                    penalized_minutes = late_minutes - threshold_minutes
                                    penalty_amount = Decimal(str(penalized_minutes)) * Decimal(str(penalty_per_minute))
                                    
                                    late_adjustment = PayrollAdjustment(
                                        shift_id=shift.id,
                                        employee_id=shift.user_id,
                                        object_id=shift.object_id,
                                        adjustment_type='late_start',
                                        amount=-abs(penalty_amount),
                                        description=f'Штраф за опоздание на {late_minutes} мин',
                                        details={
                                            'shift_id': shift.id,
                                            'late_minutes': late_minutes,
                                            'penalty_per_minute': float(penalty_per_minute)
                                        },
                                        created_by=shift.user_id,
                                        is_applied=False
                                    )
                                    session.add(late_adjustment)
                                    total_adjustments += 1
                        
                        # 3. Обработать задачи смены (из объекта И тайм-слота)
                        shift_tasks = []
                        
                        # Задачи из объекта
                        if shift.object and shift.object.shift_tasks:
                            for task in shift.object.shift_tasks:
                                task_copy = dict(task)
                                task_copy['source'] = 'object'
                                shift_tasks.append(task_copy)
                        
                        # Задачи из тайм-слота (если смена запланированная)
                        if shift.time_slot_id and shift.time_slot:
                            from domain.entities.timeslot_task_template import TimeslotTaskTemplate
                            
                            timeslot_tasks_query = select(TimeslotTaskTemplate).where(
                                TimeslotTaskTemplate.timeslot_id == shift.time_slot_id
                            )
                            timeslot_tasks_result = await session.execute(timeslot_tasks_query)
                            timeslot_tasks = timeslot_tasks_result.scalars().all()
                            
                            for task_template in timeslot_tasks:
                                media_types_list = task_template.media_types.split(',') if task_template.media_types else ['photo', 'video']
                                shift_tasks.append({
                                    'text': task_template.task_text,
                                    'is_mandatory': task_template.is_mandatory,
                                    'deduction_amount': float(task_template.deduction_amount) if task_template.deduction_amount else 0,
                                    'requires_media': task_template.requires_media,
                                    'media_types': media_types_list,
                                    'source': 'timeslot',
                                    'timeslot_task_id': task_template.id
                                })
                        
                        if shift_tasks:
                            import json
                            import re
                            
                            # Получаем информацию о выполненных задачах и медиа из shift.notes
                            completed_task_indices = []
                            task_media = {}
                            if shift.notes:
                                # Ищем [TASKS]{...} в notes
                                match = re.search(r'\[TASKS\]({.*?})', shift.notes)
                                if match:
                                    try:
                                        tasks_data = json.loads(match.group(1))
                                        completed_task_indices = tasks_data.get('completed_tasks', [])
                                        task_media = tasks_data.get('task_media', {})
                                    except json.JSONDecodeError:
                                        logger.warning(f"Failed to parse completed_tasks for shift {shift.id}")
                            
                            # Обрабатываем каждую задачу
                            for idx, task in enumerate(shift_tasks):
                                task_text = task.get('text') or task.get('task_text', 'Задача')
                                is_mandatory = task.get('is_mandatory', True)
                                deduction_amount = task.get('deduction_amount') or task.get('bonus_amount', 0)
                                requires_media = task.get('requires_media', False)
                                source = task.get('source', 'object')
                                
                                if not deduction_amount or float(deduction_amount) == 0:
                                    continue  # Пропускаем задачи без стоимости
                                
                                # Проверяем выполнение
                                is_completed = idx in completed_task_indices
                                
                                # Проверяем обязательность медиа
                                if requires_media and is_completed:
                                    media_info = task_media.get(str(idx))
                                    if not media_info:
                                        logger.warning(
                                            f"Task marked complete but missing media",
                                            shift_id=shift.id,
                                            task_idx=idx,
                                            task_text=task_text,
                                            source=source
                                        )
                                        continue  # Не начисляем, если нет медиа
                                
                                # Применяем премию/штраф в зависимости от выполнения
                                amount = Decimal(str(deduction_amount))
                                
                                # Формируем details с медиа и источником
                                details = {
                                    'task_text': task_text,
                                    'is_mandatory': is_mandatory,
                                    'completed': is_completed,
                                    'source': source
                                }
                                
                                # Добавляем медиа в details
                                if is_completed and str(idx) in task_media:
                                    media_info = task_media[str(idx)]
                                    details['media_url'] = media_info.get('media_url')
                                    details['media_type'] = media_info.get('media_type')
                                
                                if amount > 0:
                                    # Положительная сумма - премия за выполнение
                                    if is_completed:
                                        adjustment_type = 'task_bonus'
                                        task_adj = PayrollAdjustment(
                                            shift_id=shift.id,
                                            employee_id=shift.user_id,
                                            object_id=shift.object_id,
                                            adjustment_type=adjustment_type,
                                            amount=amount,
                                            description=f"Премия за задачу: {task_text}",
                                            details=details,
                                            created_by=shift.user_id,
                                            is_applied=False
                                        )
                                        session.add(task_adj)
                                        total_adjustments += 1
                                else:
                                    # Отрицательная сумма - штраф за невыполнение
                                    if not is_completed:
                                        adjustment_type = 'task_penalty'
                                        task_adj = PayrollAdjustment(
                                            shift_id=shift.id,
                                            employee_id=shift.user_id,
                                            object_id=shift.object_id,
                                            adjustment_type=adjustment_type,
                                            amount=amount,  # уже отрицательное
                                            description=f"Штраф за невыполнение задачи: {task_text}",
                                            details=details,
                                            created_by=shift.user_id,
                                            is_applied=False
                                        )
                                        session.add(task_adj)
                                        total_adjustments += 1
                        
                        total_processed += 1
                        
                        logger.info(
                            f"Adjustments created for shift",
                            shift_id=shift.id,
                            employee_id=shift.user_id
                        )
                        
                    except Exception as e:
                        error_msg = f"Error processing shift {shift.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Сохраняем все изменения
                await session.commit()
                
                logger.info(
                    f"Closed shifts processing completed",
                    shifts_processed=total_processed,
                    adjustments_created=total_adjustments,
                    errors_count=len(errors)
                )
                
                return {
                    'success': True,
                    'shifts_processed': total_processed,
                    'adjustments_created': total_adjustments,
                    'errors': errors
                }
                
        except Exception as e:
            logger.error(f"Critical error in adjustments task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())

