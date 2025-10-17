"""Сервис журнала задач смен (ShiftTask)."""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from domain.entities.shift_task import ShiftTask
from domain.entities.timeslot_task_template import TimeslotTaskTemplate
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from core.logging.logger import logger


class ShiftTaskJournal:
    """Сервис для работы с журналом задач смен."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def sync_from_config(
        self,
        shift_id: int,
        time_slot_id: Optional[int],
        object_id: int,
        created_by_id: Optional[int] = None
    ) -> List[ShiftTask]:
        """
        Синхронизировать журнал задач из конфигурации (idempotent).
        
        Если задачи для смены уже существуют - ничего не делаем.
        Если нет - создаем снимок из timeslot_task_templates и object.shift_tasks.
        
        Args:
            shift_id: ID смены
            time_slot_id: ID тайм-слота (если есть)
            object_id: ID объекта
            created_by_id: Кто создал задачи
            
        Returns:
            List[ShiftTask]: Список задач (существующие или только что созданные)
        """
        # Проверить, есть ли уже задачи для этой смены
        existing_query = select(ShiftTask).where(ShiftTask.shift_id == shift_id)
        existing_result = await self.db.execute(existing_query)
        existing_tasks = existing_result.scalars().all()
        
        if existing_tasks:
            # Уже синхронизировано
            return existing_tasks
        
        tasks = []
        
        # 1. Получить задачи из объекта
        object_query = select(Object).where(Object.id == object_id)
        object_result = await self.db.execute(object_query)
        obj = object_result.scalar_one_or_none()
        
        # 2. Проверить, нужно ли игнорировать задачи объекта
        ignore_object_tasks = False
        if time_slot_id:
            timeslot_query = select(TimeSlot).where(TimeSlot.id == time_slot_id)
            timeslot_result = await self.db.execute(timeslot_query)
            timeslot = timeslot_result.scalar_one_or_none()
            if timeslot:
                ignore_object_tasks = timeslot.ignore_object_tasks
        
        # 3. Добавить задачи из объекта (если не игнорируются)
        if not ignore_object_tasks and obj and obj.shift_tasks:
            for task_data in obj.shift_tasks:
                if isinstance(task_data, str):
                    task_text = task_data
                    is_mandatory = True
                    deduction_amount = None
                    requires_media = False
                elif isinstance(task_data, dict):
                    task_text = task_data.get('text', '')
                    is_mandatory = task_data.get('is_mandatory', True)
                    deduction_amount = task_data.get('deduction_amount')
                    requires_media = task_data.get('requires_media', False)
                else:
                    continue
                
                if task_text and task_text.strip():
                    task = ShiftTask(
                        shift_id=shift_id,
                        task_text=task_text.strip(),
                        source='object',
                        source_id=object_id,
                        is_mandatory=is_mandatory,
                        requires_media=requires_media,
                        deduction_amount=deduction_amount,
                        created_by_id=created_by_id
                    )
                    self.db.add(task)
                    tasks.append(task)
        
        # 4. Добавить задачи из тайм-слота (если есть)
        if time_slot_id:
            timeslot_tasks_query = select(TimeslotTaskTemplate).where(
                TimeslotTaskTemplate.timeslot_id == time_slot_id
            ).order_by(TimeslotTaskTemplate.display_order)
            
            timeslot_tasks_result = await self.db.execute(timeslot_tasks_query)
            timeslot_tasks = timeslot_tasks_result.scalars().all()
            
            for template in timeslot_tasks:
                task = ShiftTask(
                    shift_id=shift_id,
                    task_text=template.task_text,
                    source='timeslot',
                    source_id=time_slot_id,
                    is_mandatory=template.is_mandatory,
                    requires_media=template.requires_media,
                    deduction_amount=template.deduction_amount,
                    created_by_id=created_by_id
                )
                self.db.add(task)
                tasks.append(task)
        
        if tasks:
            await self.db.commit()
            logger.info(
                "Shift tasks journal synced",
                shift_id=shift_id,
                tasks_count=len(tasks),
                from_object=sum(1 for t in tasks if t.source == 'object'),
                from_timeslot=sum(1 for t in tasks if t.source == 'timeslot')
            )
        
        return tasks
    
    async def get_by_shift(self, shift_id: int) -> List[ShiftTask]:
        """
        Получить все задачи смены из журнала.
        
        Args:
            shift_id: ID смены
            
        Returns:
            List[ShiftTask]: Список задач (может быть пустым)
        """
        query = select(ShiftTask).where(
            ShiftTask.shift_id == shift_id
        ).order_by(ShiftTask.source, ShiftTask.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def toggle_completed(
        self,
        task_id: int,
        user_id: Optional[int] = None
    ) -> Optional[ShiftTask]:
        """
        Переключить статус выполнения задачи.
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя (для логирования)
            
        Returns:
            Optional[ShiftTask]: Обновленная задача или None
        """
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.is_completed:
            task.mark_incomplete()
        else:
            task.mark_completed(user_id)
        
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(
            "Task toggled",
            task_id=task_id,
            shift_id=task.shift_id,
            is_completed=task.is_completed,
            user_id=user_id
        )
        
        return task
    
    async def attach_media(
        self,
        task_id: int,
        media_meta: Dict[str, Any]
    ) -> Optional[ShiftTask]:
        """
        Прикрепить медиа к задаче.
        
        Args:
            task_id: ID задачи
            media_meta: Метаданные медиа (тип, URL, и т.д.)
            
        Returns:
            Optional[ShiftTask]: Обновленная задача или None
        """
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        # Добавить медиа в список
        current_refs = task.media_refs or []
        if not isinstance(current_refs, list):
            current_refs = []
        
        current_refs.append(media_meta)
        task.media_refs = current_refs
        
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(
            "Media attached to task",
            task_id=task_id,
            media_count=len(current_refs)
        )
        
        return task
    
    async def mark_completed(
        self,
        task_id: int,
        user_id: Optional[int] = None,
        media_meta: Optional[Dict[str, Any]] = None
    ) -> Optional[ShiftTask]:
        """
        Отметить задачу как выполненную (с медиа, если есть).
        
        Args:
            task_id: ID задачи
            user_id: ID пользователя
            media_meta: Метаданные медиа (опционально)
            
        Returns:
            Optional[ShiftTask]: Обновленная задача или None
        """
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        task.mark_completed(user_id)
        
        if media_meta:
            current_refs = task.media_refs or []
            if not isinstance(current_refs, list):
                current_refs = []
            current_refs.append(media_meta)
            task.media_refs = current_refs
        
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(
            "Task marked completed",
            task_id=task_id,
            shift_id=task.shift_id,
            user_id=user_id,
            has_media=bool(media_meta)
        )
        
        return task
    
    async def add_manual_task(
        self,
        shift_id: int,
        task_text: str,
        created_by_id: int,
        is_mandatory: bool = False,
        deduction_amount: Optional[Decimal] = None
    ) -> ShiftTask:
        """
        Добавить ручную задачу к смене.
        
        Args:
            shift_id: ID смены
            task_text: Текст задачи
            created_by_id: Кто создал
            is_mandatory: Обязательная задача
            deduction_amount: Штраф/премия
            
        Returns:
            ShiftTask: Созданная задача
        """
        task = ShiftTask(
            shift_id=shift_id,
            task_text=task_text,
            source='manual',
            is_mandatory=is_mandatory,
            deduction_amount=deduction_amount,
            created_by_id=created_by_id
        )
        
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(
            "Manual task added",
            task_id=task.id,
            shift_id=shift_id,
            created_by_id=created_by_id
        )
        
        return task
    
    async def link_correction(
        self,
        task_id: int,
        correction_id: int,
        cost: Optional[Decimal] = None
    ) -> Optional[ShiftTask]:
        """
        Связать задачу с корректировкой начисления.
        
        Args:
            task_id: ID задачи
            correction_id: ID корректировки
            cost: Фактическая стоимость
            
        Returns:
            Optional[ShiftTask]: Обновленная задача или None
        """
        query = select(ShiftTask).where(ShiftTask.id == task_id)
        result = await self.db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        task.correction_ref = correction_id
        if cost is not None:
            task.cost = cost
        
        await self.db.commit()
        await self.db.refresh(task)
        
        logger.info(
            "Correction linked to task",
            task_id=task_id,
            correction_id=correction_id,
            cost=float(cost) if cost else None
        )
        
        return task

