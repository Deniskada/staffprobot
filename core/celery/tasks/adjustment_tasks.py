"""Celery задача для создания корректировок начислений из закрытых смен."""

from datetime import datetime, timedelta
from decimal import Decimal
import asyncio

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_, func
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
            
            logger.info(f"[ADJUSTMENT_DEBUG] Starting adjustment processing", cutoff_time=cutoff_time, looking_for_status="completed")
            
            async with get_async_session() as session:
                # Найти смены, закрытые за последние 15 минут (по updated_at)
                shifts_query = select(Shift).options(
                    selectinload(Shift.object).selectinload(Object.org_unit),
                    selectinload(Shift.time_slot)
                ).where(
                    and_(
                        Shift.status.in_(['closed', 'completed']),  # Искать оба статуса
                        Shift.updated_at >= cutoff_time,  # Используем updated_at вместо end_time
                        Shift.end_time.isnot(None)
                    )
                ).order_by(Shift.updated_at.desc())
                
                shifts_result = await session.execute(shifts_query)
                shifts = shifts_result.scalars().all()
                
                logger.info(f"[ADJUSTMENT_DEBUG] Found {len(shifts)} shifts with status='completed'", 
                           statuses_searched_for=['completed'], 
                           cutoff_minutes=15)
                
                # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА: проверить все статусы в БД
                all_shifts_query = select(Shift.status, func.count(Shift.id).label('count')).group_by(Shift.status)
                all_shifts_result = await session.execute(all_shifts_query)
                status_counts = all_shifts_result.all()
                
                for status, count in status_counts:
                    logger.info(f"[ADJUSTMENT_DEBUG] Shifts with status='{status}': {count}")
                
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
                        existing = existing_result.scalars().first()
                        
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
                        
                        # 2. Проверить и создать штраф за опоздание (новая логика с planned_start/actual_start)
                        logger.info(
                            f"Checking late penalty for shift",
                            shift_id=shift.id,
                            planned_start=shift.planned_start,
                            actual_start=shift.actual_start,
                            has_both=bool(shift.planned_start and shift.actual_start)
                        )
                        
                        if shift.planned_start and shift.actual_start:
                            # Для запланированных смен - проверяем флаг penalize_late_start
                            should_penalize = True
                            if shift.is_planned and shift.time_slot_id and shift.time_slot:
                                if not shift.time_slot.penalize_late_start:
                                    should_penalize = False
                                    logger.debug(
                                        f"Late penalty disabled by timeslot flag",
                                        shift_id=shift.id,
                                        time_slot_id=shift.time_slot_id
                                    )
                            
                            if should_penalize:
                                # Сравниваем actual_start с planned_start (порог уже учтен при открытии смены)
                                if shift.actual_start > shift.planned_start:
                                    late_seconds = (shift.actual_start - shift.planned_start).total_seconds()
                                    late_minutes = int(late_seconds / 60)
                                    
                                    # Получить настройки штрафа с учетом наследования от org_unit
                                    obj = shift.object
                                    late_settings = obj.get_effective_late_settings()
                                    penalty_per_minute = late_settings.get('penalty_per_minute')
                                    threshold_minutes = late_settings.get('threshold_minutes', 0)
                                    
                                    logger.debug(
                                        f"Late settings for shift {shift.id}",
                                        penalty_per_minute=penalty_per_minute,
                                        threshold_minutes=threshold_minutes,
                                        source=late_settings.get('source')
                                    )
                                    
                                    # Если у объекта не задан штраф - пропускаем
                                    if penalty_per_minute and late_minutes > threshold_minutes:
                                        # Штрафуем только за минуты сверх порога
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
                                        total_adjustments += 1
                                        
                                        logger.info(
                                            f"Late penalty created",
                                            shift_id=shift.id,
                                            late_minutes=late_minutes,
                                            threshold_minutes=threshold_minutes,
                                            penalized_minutes=penalized_minutes,
                                            penalty=float(penalty_amount),
                                            source=late_settings.get('source')
                                        )
                        
                        # 3. Обработать задачи смены (новая логика комбинирования)
                        shift_tasks = []
                        
                        logger.info(f"[ADJUSTMENT_DEBUG] Processing shift {shift.id}, time_slot_id={shift.time_slot_id}")
                        
                        if shift.time_slot_id and shift.time_slot:
                            # 1. Собственные задачи тайм-слота (из таблицы timeslot_task_templates)
                            from domain.entities.timeslot_task_template import TimeslotTaskTemplate
                            from sqlalchemy import select as sql_select
                            
                            template_query = sql_select(TimeslotTaskTemplate).where(
                                TimeslotTaskTemplate.timeslot_id == shift.time_slot_id
                            ).order_by(TimeslotTaskTemplate.display_order)
                            template_result = await session.execute(template_query)
                            templates = template_result.scalars().all()
                            
                            logger.info(f"[ADJUSTMENT_DEBUG] Found {len(templates)} timeslot tasks")
                            for template in templates:
                                shift_tasks.append({
                                    'text': template.task_text,
                                    'is_mandatory': template.is_mandatory if template.is_mandatory is not None else False,
                                    'deduction_amount': float(template.deduction_amount) if template.deduction_amount else 0,
                                    'requires_media': template.requires_media if template.requires_media is not None else False,
                                    'source': 'timeslot'
                                })
                                logger.info(f"[ADJUSTMENT_DEBUG] Timeslot task: {template.task_text}, amount={template.deduction_amount}")
                            
                            # 2. Задачи объекта (если НЕ игнорируются)
                            if not shift.time_slot.ignore_object_tasks and shift.object and shift.object.shift_tasks:
                                logger.info(f"[ADJUSTMENT_DEBUG] Adding {len(shift.object.shift_tasks)} object tasks, ignore_object_tasks={shift.time_slot.ignore_object_tasks}")
                                for task in shift.object.shift_tasks:
                                    task_copy = dict(task)
                                    task_copy['source'] = 'object'
                                    shift_tasks.append(task_copy)
                        else:
                            # Спонтанная смена - всегда задачи объекта
                            if shift.object and shift.object.shift_tasks:
                                for task in shift.object.shift_tasks:
                                    task_copy = dict(task)
                                    task_copy['source'] = 'object'
                                    shift_tasks.append(task_copy)
                        
                        if shift_tasks:
                            import json
                            import re
                            
                            # Получаем информацию о выполненных задачах и медиа из shift.notes
                            completed_task_indices = []
                            task_media = {}
                            if shift.notes:
                                # Ищем [TASKS]{...} в notes
                                # Используем все после [TASKS], т.к. non-greedy {.*?} неправильно парсит вложенный JSON
                                marker = '[TASKS]'
                                marker_pos = shift.notes.find(marker)
                                if marker_pos != -1:
                                    json_str = shift.notes[marker_pos + len(marker):].strip()
                                    try:
                                        tasks_data = json.loads(json_str)
                                        completed_task_indices = tasks_data.get('completed_tasks', [])
                                        task_media = tasks_data.get('task_media', {})
                                        logger.info(
                                            f"Parsed shift tasks data",
                                            shift_id=shift.id,
                                            completed_tasks=completed_task_indices,
                                            media_count=len(task_media)
                                        )
                                    except json.JSONDecodeError as e:
                                        logger.warning(f"Failed to parse completed_tasks for shift {shift.id}: {e}")
                            
                            # Обрабатываем каждую задачу
                            for idx, task in enumerate(shift_tasks):
                                # Поддержка старого и нового формата
                                task_text = task.get('text') or task.get('description') or task.get('task_text', 'Задача')
                                is_mandatory = task.get('is_mandatory', True)
                                
                                # Старый формат: deduction_amount, bonus_amount
                                # Новый формат: amount
                                amount_value = task.get('amount')
                                if amount_value is None:
                                    # Старый формат
                                    deduction = task.get('deduction_amount')
                                    bonus = task.get('bonus_amount')
                                    if deduction is not None:
                                        amount_value = deduction
                                    elif bonus is not None:
                                        amount_value = bonus
                                    else:
                                        amount_value = 0
                                
                                requires_media = task.get('requires_media', False)
                                source = task.get('source', 'object')
                                
                                # Пропускаем НЕобязательные задачи без стоимости
                                if (not amount_value or float(amount_value) == 0) and not is_mandatory:
                                    continue
                                
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
                                # Для обязательных задач без стоимости используем дефолтный штраф -50₽
                                if is_mandatory and (not amount_value or float(amount_value) == 0):
                                    amount_value = -50
                                
                                amount = Decimal(str(amount_value))
                                
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
                                
                                # Для задач с медиа-отчетом создаем запись даже если штраф избежан
                                should_create_media_record = (
                                    requires_media and 
                                    is_completed and 
                                    str(idx) in task_media and 
                                    amount < 0  # Штраф был избежан
                                )
                                
                                if should_create_media_record:
                                    # Создать запись о выполнении задачи с медиа (amount=0, т.к. штраф избежан)
                                    adjustment_type = 'task_completed'
                                    task_adj = PayrollAdjustment(
                                        shift_id=shift.id,
                                        employee_id=shift.user_id,
                                        object_id=shift.object_id,
                                        adjustment_type=adjustment_type,
                                        amount=Decimal('0.00'),
                                        description=f"Выполнено с отчетом: {task_text} (штраф {amount}₽ избежан)",
                                        details=details,
                                        created_by=shift.user_id,
                                        is_applied=False
                                    )
                                    session.add(task_adj)
                                    total_adjustments += 1
                                elif amount > 0:
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
                                    if is_completed:
                                        # ✅ Задача выполнена со штрафом - создаём запись о выполнении (штраф избежан)
                                        adjustment_type = 'task_completed'
                                        task_adj = PayrollAdjustment(
                                            shift_id=shift.id,
                                            employee_id=shift.user_id,
                                            object_id=shift.object_id,
                                            adjustment_type=adjustment_type,
                                            amount=Decimal('0.00'),
                                            description=f"Выполнено: {task_text} (штраф {abs(amount)}₽ избежан)",
                                            details=details,
                                            created_by=shift.user_id,
                                            is_applied=False
                                        )
                                        session.add(task_adj)
                                        total_adjustments += 1
                                    else:
                                        # Задача не выполнена - штраф за невыполнение
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

