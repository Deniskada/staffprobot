"""Celery задача для расчёта бонусов/штрафов за выполненные задачи Tasks v2."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List
from decimal import Decimal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.task_entry import TaskEntryV2
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.shift_schedule import ShiftSchedule


async def process_completed_tasks_bonuses(session: AsyncSession) -> int:
    """
    Обработать выполненные задачи и создать корректировки payroll.
    
    Логика:
    - Находим завершённые TaskEntryV2 без связанной корректировки
    - Для каждой создаём PayrollAdjustment на основе default_bonus_amount из шаблона
    - Положительная сумма = бонус, отрицательная = штраф
    
    Returns:
        Количество созданных корректировок
    """
    from sqlalchemy.orm import selectinload
    
    created_count = 0
    
    # Получаем завершённые задачи с шаблонами
    query = select(TaskEntryV2).where(
        and_(
            TaskEntryV2.is_completed == True,
            TaskEntryV2.completed_at.isnot(None)
        )
    ).options(
        selectinload(TaskEntryV2.template),
        selectinload(TaskEntryV2.shift_schedule)
    ).order_by(TaskEntryV2.completed_at.desc()).limit(1000)
    
    result = await session.execute(query)
    completed_entries = result.scalars().all()
    
    for entry in completed_entries:
        template = entry.template
        if not template or not template.default_bonus_amount:
            continue  # Нет шаблона или суммы
        
        # Проверяем, не создана ли уже корректировка для этой задачи
        existing_adj_query = select(PayrollAdjustment).where(
            and_(
                PayrollAdjustment.task_entry_v2_id == entry.id
            )
        )
        existing_adj_result = await session.execute(existing_adj_query)
        if existing_adj_result.scalar_one_or_none():
            continue  # Корректировка уже существует
        
        # Определяем данные для корректировки
        shift_schedule = entry.shift_schedule
        if not shift_schedule:
            logger.warning(f"TaskEntryV2 {entry.id} has no shift_schedule, skipping adjustment")
            continue
        
        amount = template.default_bonus_amount
        adjustment_type = "task_bonus" if amount > 0 else "task_penalty"
        description = f"Задача: {template.title}"
        
        # Создаём корректировку
        adjustment = PayrollAdjustment(
            employee_id=entry.employee_id,
            shift_schedule_id=shift_schedule.id,
            task_entry_v2_id=entry.id,
            adjustment_type=adjustment_type,
            amount=amount,
            description=description,
            details={"task_code": template.code, "task_title": template.title},
            created_by=1,  # Системный пользователь (admin)
            is_applied=False,  # Будет применено Celery задачей
            created_at=datetime.utcnow()
        )
        session.add(adjustment)
        created_count += 1
        
        logger.info(
            f"Created PayrollAdjustment for TaskEntryV2",
            entry_id=entry.id,
            employee_id=entry.employee_id,
            amount=float(amount),
            type=adjustment_type,
            template_code=template.code
        )
    
    await session.commit()
    return created_count


@celery_app.task(name="process_task_bonuses")
def process_task_bonuses_celery():
    """
    Celery задача: обработка бонусов/штрафов за выполненные задачи.
    Запускается каждые 10 минут.
    """
    import asyncio
    
    async def _run():
        async with get_async_session() as session:
            count = await process_completed_tasks_bonuses(session)
            logger.info(f"Processed task bonuses: {count} adjustments created")
            return count
    
    return asyncio.run(_run())

