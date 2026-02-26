"""Celery задача для автоматического назначения задач на смены."""

from __future__ import annotations

from datetime import datetime, timedelta, time
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import select, and_, or_, cast, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.dialects.postgresql import JSONB

from core.celery.celery_app import celery_app
from core.database.session import get_celery_session
from core.logging.logger import logger
from domain.entities.task_plan import TaskPlanV2
from domain.entities.task_entry import TaskEntryV2
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
from domain.entities.shift import Shift


async def create_task_entries_for_date(session: AsyncSession, target_date: datetime.date) -> int:
    """
    Создать TaskEntryV2 для всех активных планов на заданную дату.
    
    Args:
        session: Асинхронная сессия БД
        target_date: Дата для создания задач
        
    Returns:
        Количество созданных TaskEntryV2
    """
    created_count = 0
    
    # Получаем все активные планы
    plans_query = select(TaskPlanV2).where(
        TaskPlanV2.is_active == True
    ).options(
        selectinload(TaskPlanV2.template),
        selectinload(TaskPlanV2.object)
    )
    plans_result = await session.execute(plans_query)
    plans = plans_result.scalars().all()
    
    for plan in plans:
        # Проверяем, подходит ли план для данной даты
        if not should_create_entry_for_date(plan, target_date):
            continue
        
        # Получаем смены для этого плана
        shift_schedules = await get_relevant_shift_schedules(session, plan, target_date)
        
        for shift in shift_schedules:
            # Проверяем, не существует ли уже TaskEntry
            existing_query = select(TaskEntryV2).where(
                and_(
                    TaskEntryV2.plan_id == plan.id,
                    TaskEntryV2.shift_schedule_id == shift.id
                )
            )
            existing_result = await session.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue  # Уже существует
            
            # Создаём TaskEntryV2
            entry = TaskEntryV2(
                template_id=plan.template_id,
                plan_id=plan.id,
                shift_schedule_id=shift.id,
                employee_id=shift.user_id,  # В ShiftSchedule поле называется user_id
                is_completed=False,
                created_at=datetime.utcnow()
            )
            session.add(entry)
            created_count += 1
            logger.debug(
                f"Created TaskEntryV2 for plan {plan.id}, shift {shift.id}, employee {shift.user_id}"
            )
    
    await session.commit()
    return created_count


def should_create_entry_for_date(plan: TaskPlanV2, target_date: datetime.date) -> bool:
    """
    Проверяет, нужно ли создавать TaskEntry для плана на данную дату.
    
    Args:
        plan: План задачи
        target_date: Проверяемая дата
        
    Returns:
        True если нужно создать, False иначе
    """
    # Если указана конкретная дата - проверяем совпадение
    if plan.planned_date:
        return plan.planned_date.date() == target_date
    
    # Если есть дата окончания периодичности - проверяем
    if plan.recurrence_end_date and target_date > plan.recurrence_end_date:
        return False
    
    # Проверяем периодичность
    if not plan.recurrence_type:
        # Постоянный план без периодичности - создаём для каждой даты
        return True
    
    if plan.recurrence_type == "weekdays":
        # Проверяем день недели (ISO: 1=Пн, 7=Вс)
        weekdays = plan.recurrence_config.get("weekdays", [])
        return target_date.isoweekday() in weekdays
    
    if plan.recurrence_type == "day_interval":
        # Проверяем интервал от даты создания плана
        if not plan.created_at:
            return False
        interval = plan.recurrence_config.get("interval", 1)
        days_diff = (target_date - plan.created_at.date()).days
        return days_diff % interval == 0
    
    return False


async def get_relevant_shift_schedules(
    session: AsyncSession, 
    plan: TaskPlanV2, 
    target_date: datetime.date
) -> List[ShiftSchedule]:
    """
    Получить смены, на которые нужно назначить задачу.
    
    Args:
        session: Асинхронная сессия БД
        plan: План задачи
        target_date: Дата смен
        
    Returns:
        Список смен
    """
    # Базовый запрос - активные смены на заданную дату
    query = select(ShiftSchedule).where(
        and_(
            ShiftSchedule.status.in_(["confirmed", "planned"]),
            ShiftSchedule.planned_start >= datetime.combine(target_date, time.min),
            ShiftSchedule.planned_start < datetime.combine(target_date + timedelta(days=1), time.min)
        )
    ).options(
        selectinload(ShiftSchedule.time_slot)
    )
    
    # Фильтр по объектам (если указаны в плане)
    if plan.object_ids:
        query = query.where(ShiftSchedule.object_id.in_(plan.object_ids))
    elif plan.object_id:  # Для обратной совместимости
        query = query.where(ShiftSchedule.object_id == plan.object_id)
    
    # Фильтр по времени начала (если указано в плане)
    if plan.planned_time_start:
        # Ищем смены, время начала которых попадает в окно ±30 минут
        time_start = datetime.combine(target_date, plan.planned_time_start)
        time_end = time_start + timedelta(minutes=30)
        query = query.where(
            and_(
                ShiftSchedule.planned_start >= time_start - timedelta(minutes=30),
                ShiftSchedule.planned_start <= time_end
            )
        )
    
    result = await session.execute(query)
    return result.scalars().all()


async def create_task_entries_for_active_shifts(session: AsyncSession, plan: TaskPlanV2) -> int:
    """
    Создать TaskEntryV2 для уже активных смен по новому плану.
    Вызывается сразу после создания плана в веб-интерфейсе.
    
    Args:
        session: Асинхронная сессия БД
        plan: Новый план задачи
        
    Returns:
        Количество созданных TaskEntryV2
    """
    created_count = 0
    today = datetime.utcnow().date()
    
    # Получаем активные смены (сегодня и будущие)
    query = select(ShiftSchedule).where(
        and_(
            ShiftSchedule.status.in_(["confirmed", "planned"]),
            ShiftSchedule.planned_start >= datetime.combine(today, time.min)
        )
    ).options(
        selectinload(ShiftSchedule.time_slot)
    )
    
    # Фильтр по объектам (если указаны в плане)
    if plan.object_ids:
        query = query.where(ShiftSchedule.object_id.in_(plan.object_ids))
    elif plan.object_id:  # Для обратной совместимости
        query = query.where(ShiftSchedule.object_id == plan.object_id)
    
    result = await session.execute(query)
    shifts = result.scalars().all()
    
    for shift in shifts:
        # Проверяем, подходит ли смена для этого плана
        shift_date = shift.planned_start.date()
        
        # Проверяем соответствие дате/периодичности
        if not should_create_entry_for_date(plan, shift_date):
            continue
        
        # Проверяем время начала
        if plan.planned_time_start:
            shift_time = shift.planned_start.time()
            plan_time_seconds = (
                plan.planned_time_start.hour * 3600 + 
                plan.planned_time_start.minute * 60
            )
            shift_time_seconds = (
                shift_time.hour * 3600 + 
                shift_time.minute * 60
            )
            # Разница не более 30 минут
            if abs(plan_time_seconds - shift_time_seconds) > 1800:
                continue
        
        # Проверяем, не существует ли уже TaskEntry
        existing_query = select(TaskEntryV2).where(
            and_(
                TaskEntryV2.plan_id == plan.id,
                TaskEntryV2.shift_schedule_id == shift.id
            )
        )
        existing_result = await session.execute(existing_query)
        if existing_result.scalar_one_or_none():
            continue
        
        # Создаём TaskEntryV2
        entry = TaskEntryV2(
            template_id=plan.template_id,
            plan_id=plan.id,
            shift_schedule_id=shift.id,
            employee_id=shift.user_id,  # В ShiftSchedule поле называется user_id
            is_completed=False,
            created_at=datetime.utcnow()
        )
        session.add(entry)
        created_count += 1
        logger.debug(
            f"Created TaskEntryV2 for plan {plan.id}, shift {shift.id}, employee {shift.user_id}"
        )
    
    return created_count


@celery_app.task(name="auto_assign_tasks")
def auto_assign_tasks_celery():
    """
    Celery задача: автоматическое назначение задач на смены.
    Запускается ежедневно в 4:00 МСК.
    """
    import asyncio
    
    async def _run():
        async with get_celery_session() as session:
            # Создаём задачи на сегодня и завтра
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            
            count_today = await create_task_entries_for_date(session, today)
            count_tomorrow = await create_task_entries_for_date(session, tomorrow)
            
            logger.info(
                f"Auto-assigned tasks: {count_today} for today, {count_tomorrow} for tomorrow"
            )
            
            return count_today + count_tomorrow
    
    return asyncio.run(_run())


async def create_task_entries_for_shift(session: AsyncSession, shift: Shift) -> int:
    """
    Создать TaskEntryV2 для одной открытой смены (запланированной или спонтанной).
    Вызывается сразу после открытия смены через бот.
    
    Args:
        session: Асинхронная сессия БД
        shift: Открытая смена
        
    Returns:
        Количество созданных TaskEntryV2
    """
    created_count = 0
    shift_date = shift.start_time.date()
    
    # Получаем все активные планы для этого объекта С eager loading шаблонов
    query = select(TaskPlanV2).where(
        TaskPlanV2.is_active == True
    ).options(
        selectinload(TaskPlanV2.template)  # КРИТИЧНО: загружаем шаблоны заранее!
    )
    
    # Фильтр по объекту смены (работает для всех типов смен)
    # Используем JSONB оператор @> для проверки содержания элемента в массиве
    query = query.where(
        or_(
            TaskPlanV2.object_id == shift.object_id,
            cast(TaskPlanV2.object_ids, JSONB).op('@>')(cast([shift.object_id], JSONB)),
            # Общие планы (без привязки к объектам)
            and_(
                TaskPlanV2.object_ids.is_(None),
                TaskPlanV2.object_id.is_(None)
            )
        )
    )
    
    result = await session.execute(query)
    plans = result.scalars().all()
    
    logger.info(f"Found {len(plans)} active TaskPlanV2 for shift {shift.id} (object={shift.object_id})")
    
    for plan in plans:
        # Проверяем, подходит ли план для даты смены
        if not should_create_entry_for_date(plan, shift_date):
            logger.debug(f"Plan {plan.id} skipped: date mismatch")
            continue
        
        # Проверяем время начала (если указано в плане)
        if plan.planned_time_start and shift.schedule_id:
            # Для запланированных смен проверяем время
            from domain.entities.shift_schedule import ShiftSchedule
            schedule_query = select(ShiftSchedule).where(ShiftSchedule.id == shift.schedule_id)
            schedule_result = await session.execute(schedule_query)
            schedule = schedule_result.scalar_one_or_none()
            
            if schedule:
                shift_time = schedule.planned_start.time()
                plan_time_seconds = (
                    plan.planned_time_start.hour * 3600 + 
                    plan.planned_time_start.minute * 60
                )
                shift_time_seconds = (
                    shift_time.hour * 3600 + 
                    shift_time.minute * 60
                )
                # Разница не более 30 минут
                if abs(plan_time_seconds - shift_time_seconds) > 1800:
                    logger.debug(f"Plan {plan.id} skipped: time mismatch")
                    continue
        
        # Проверяем, не существует ли уже TaskEntry для ЭТОЙ СМЕНЫ (по shift_id - универсально!)
        existing_query = select(TaskEntryV2).where(
            and_(
                TaskEntryV2.plan_id == plan.id,
                TaskEntryV2.shift_id == shift.id  # Используем shift_id вместо shift_schedule_id!
            )
        )
        existing_result = await session.execute(existing_query)
        if existing_result.scalar_one_or_none():
            logger.debug(f"TaskEntry for plan {plan.id} and shift {shift.id} already exists")
            continue
        
        # Создаём TaskEntryV2 (теперь безопасно обращаться к plan.template!)
        if not plan.template:
            logger.warning(f"Plan {plan.id} has no template, skipping")
            continue
            
        entry = TaskEntryV2(
            template_id=plan.template_id,
            plan_id=plan.id,
            shift_id=shift.id,  # Основная привязка - работает для всех типов смен!
            shift_schedule_id=shift.schedule_id if shift.schedule_id else None,  # Для аналитики
            employee_id=shift.user_id,
            is_completed=False,
            requires_media=plan.template.requires_media,  # Теперь безопасно!
            created_at=datetime.utcnow()
        )
        session.add(entry)
        created_count += 1
        logger.info(
            f"Created TaskEntryV2 for shift {shift.id} (planned={bool(shift.schedule_id)}), "
            f"plan {plan.id}, template={plan.template.title}"
        )
    
    return created_count

