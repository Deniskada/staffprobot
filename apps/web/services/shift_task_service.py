"""Сервис для работы с задачами на смену."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logging.logger import logger
from domain.entities.shift_task import ShiftTask, TimeslotTaskTemplate
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot


class ShiftTaskService:
    """Сервис для управления задачами на смену."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_tasks_for_shift(
        self,
        shift_id: int,
        object_id: int,
        timeslot_id: Optional[int] = None,
        created_by_id: Optional[int] = None
    ) -> List[ShiftTask]:
        """
        Создать задачи для смены на основе наследования.
        
        Порядок приоритета:
        1. Задачи из объекта (object.shift_tasks)
        2. Задачи из тайм-слота (timeslot.task_templates), если есть
        
        Args:
            shift_id: ID смены
            object_id: ID объекта
            timeslot_id: ID тайм-слота (опционально)
            created_by_id: Кто создал задачи
            
        Returns:
            Список созданных задач
        """
        try:
            tasks = []
            
            # 1. Получить задачи из объекта
            object_query = select(Object).where(Object.id == object_id)
            object_result = await self.db.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            if obj and obj.shift_tasks:
                # object.shift_tasks - это JSON массив объектов {"text": "...", "is_mandatory": true, "deduction_amount": 100}
                for task_data in obj.shift_tasks:
                    # Поддержка старого формата (строки) и нового (объекты)
                    if isinstance(task_data, str):
                        task_text = task_data
                        is_mandatory = True
                        deduction_amount = None
                    elif isinstance(task_data, dict):
                        task_text = task_data.get('text', '')
                        is_mandatory = task_data.get('is_mandatory', True)
                        deduction_amount = task_data.get('deduction_amount')
                    else:
                        continue
                    
                    if task_text and task_text.strip():  # Пропускаем пустые
                        task = ShiftTask(
                            shift_id=shift_id,
                            task_text=task_text.strip(),
                            source='object',
                            source_id=object_id,
                            is_mandatory=is_mandatory,
                            deduction_amount=deduction_amount,
                            created_by_id=created_by_id
                        )
                        self.db.add(task)
                        tasks.append(task)
            
            # 2. Получить задачи из тайм-слота (если есть)
            if timeslot_id:
                timeslot_tasks_query = select(TimeslotTaskTemplate).where(
                    TimeslotTaskTemplate.timeslot_id == timeslot_id
                ).order_by(TimeslotTaskTemplate.display_order)
                
                timeslot_tasks_result = await self.db.execute(timeslot_tasks_query)
                timeslot_tasks = timeslot_tasks_result.scalars().all()
                
                for template in timeslot_tasks:
                    task = ShiftTask(
                        shift_id=shift_id,
                        task_text=template.task_text,
                        source='timeslot',
                        source_id=timeslot_id,
                        is_mandatory=template.is_mandatory,
                        deduction_amount=template.deduction_amount,
                        created_by_id=created_by_id
                    )
                    self.db.add(task)
                    tasks.append(task)
            
            await self.db.commit()
            
            logger.info(
                f"Created {len(tasks)} tasks for shift",
                shift_id=shift_id,
                object_id=object_id,
                timeslot_id=timeslot_id
            )
            
            return tasks
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating tasks for shift: {e}", shift_id=shift_id)
            raise
    
    async def get_shift_tasks(self, shift_id: int) -> List[ShiftTask]:
        """Получить все задачи смены."""
        query = select(ShiftTask).where(ShiftTask.shift_id == shift_id).order_by(ShiftTask.id)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def mark_task_completed(self, task_id: int) -> Optional[ShiftTask]:
        """Отметить задачу как выполненную."""
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if task:
            task.mark_completed()
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Task marked as completed", task_id=task_id, shift_id=task.shift_id)
        
        return task
    
    async def mark_task_incomplete(self, task_id: int) -> Optional[ShiftTask]:
        """Отметить задачу как невыполненную."""
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if task:
            task.mark_incomplete()
            await self.db.commit()
            await self.db.refresh(task)
            
            logger.info(f"Task marked as incomplete", task_id=task_id, shift_id=task.shift_id)
        
        return task
    
    async def add_manual_task(
        self,
        shift_id: int,
        task_text: str,
        created_by_id: int
    ) -> ShiftTask:
        """Добавить ручную задачу к смене."""
        task = ShiftTask(
            shift_id=shift_id,
            task_text=task_text,
            source='manual',
            created_by_id=created_by_id
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(f"Manual task added", task_id=task.id, shift_id=shift_id)
        
        return task
    
    async def get_incomplete_tasks(self, shift_id: int) -> List[ShiftTask]:
        """Получить невыполненные задачи смены."""
        query = select(ShiftTask).where(
            ShiftTask.shift_id == shift_id,
            ShiftTask.is_completed == False
        ).order_by(ShiftTask.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_completed_tasks(self, shift_id: int) -> List[ShiftTask]:
        """Получить выполненные задачи смены."""
        query = select(ShiftTask).where(
            ShiftTask.shift_id == shift_id,
            ShiftTask.is_completed == True
        ).order_by(ShiftTask.completed_at)
        
        result = await self.db.execute(query)
        return result.scalars().all()

