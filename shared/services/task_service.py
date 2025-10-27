"""Shared-сервис для управления задачами (все роли)."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from decimal import Decimal

from domain.entities.task_template import TaskTemplateV2
from domain.entities.task_plan import TaskPlanV2
from domain.entities.task_entry import TaskEntryV2
from domain.entities.object import Object
from domain.entities.contract import Contract
from core.logging.logger import logger


class TaskService:
    """Универсальный сервис для задач (owner/manager/employee)."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_templates_for_role(
        self,
        user_id: int,
        role: str,
        owner_id: Optional[int] = None,
        object_id: Optional[int] = None,
        active_only: Optional[bool] = None,
        for_selection: bool = False
    ) -> List[TaskTemplateV2]:
        """
        Получить шаблоны задач с учётом роли.
        
        Args:
            user_id: ID пользователя
            role: Роль (owner/manager/employee)
            owner_id: ID владельца (для manager/employee)
            object_id: Фильтр по объекту
            active_only: Явная фильтрация по активности (None = авто-режим)
            for_selection: Для форм выбора (всегда только активные)
        """
        query = select(TaskTemplateV2)
        
        # Для форм выбора (создание задачи/плана) - ВСЕГДА только активные
        if for_selection:
            active_only = True
        
        # Авто-режим: owner видит все, остальные - только активные по умолчанию
        if active_only is None:
            active_only = (role != "owner")
        
        if role == "owner":
            query = query.where(TaskTemplateV2.owner_id == user_id)
        elif role == "manager":
            # Manager видит только задачи на объектах, где он управляющий
            if not owner_id:
                return []
            # Получаем объекты, где manager имеет доступ
            contract_query = select(Contract.allowed_objects).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.owner_id == owner_id,
                    Contract.role == "manager",
                    Contract.is_active == True
                )
            )
            contract_result = await self.session.execute(contract_query)
            contract = contract_result.scalar_one_or_none()
            if not contract or not contract.allowed_objects:
                return []
            allowed_obj_ids = contract.allowed_objects
            query = query.where(
                and_(
                    TaskTemplateV2.owner_id == owner_id,
                    or_(
                        TaskTemplateV2.object_id.in_(allowed_obj_ids),
                        TaskTemplateV2.object_id.is_(None)  # Глобальные шаблоны
                    )
                )
            )
        elif role == "employee":
            # Employee видит только шаблоны задач на своих объектах (через contracts)
            if not owner_id:
                return []
            contract_query = select(Contract.allowed_objects).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.owner_id == owner_id,
                    Contract.is_active == True
                )
            )
            contract_result = await self.session.execute(contract_query)
            contracts = contract_result.scalars().all()
            if not contracts:
                return []
            # Собираем все allowed_objects
            allowed_obj_ids = set()
            for c in contracts:
                if c.allowed_objects:
                    allowed_obj_ids.update(c.allowed_objects)
            if not allowed_obj_ids:
                return []
            query = query.where(
                and_(
                    TaskTemplateV2.owner_id == owner_id,
                    TaskTemplateV2.object_id.in_(list(allowed_obj_ids))
                )
            )
        else:
            return []
        
        if object_id:
            query = query.where(
                or_(
                    TaskTemplateV2.object_id == object_id,
                    TaskTemplateV2.object_id.is_(None)
                )
            )
        
        # Фильтр по активности (только для manager/employee по умолчанию)
        if active_only:
            query = query.where(TaskTemplateV2.is_active == True)
        
        query = query.order_by(TaskTemplateV2.title)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_template_by_id(self, template_id: int) -> Optional[TaskTemplateV2]:
        """Получить шаблон по ID."""
        result = await self.session.execute(
            select(TaskTemplateV2).where(TaskTemplateV2.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def create_template(
        self,
        owner_id: int,
        code: str,
        title: str,
        description: Optional[str] = None,
        is_mandatory: bool = False,
        requires_media: bool = False,
        default_amount: Optional[Decimal] = None,
        object_id: Optional[int] = None,
        org_unit_id: Optional[int] = None
    ) -> TaskTemplateV2:
        """Создать шаблон задачи."""
        template = TaskTemplateV2(
            owner_id=owner_id,
            code=code,
            title=title,
            description=description,
            is_mandatory=is_mandatory,
            requires_media=requires_media,
            default_bonus_amount=default_amount,
            object_id=object_id,
            org_unit_id=org_unit_id,
            is_active=True
        )
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        logger.info(f"Created TaskTemplateV2: {template.id}, owner={owner_id}, code={code}")
        return template
    
    async def get_entries_for_role(
        self,
        user_id: int,
        role: str,
        owner_id: Optional[int] = None,
        limit: int = 100
    ) -> List[TaskEntryV2]:
        """Получить записи выполнения задач с учётом роли."""
        query = select(TaskEntryV2)
        
        if role == "owner":
            # Owner видит все entries для своих шаблонов
            query = query.join(TaskPlanV2).join(TaskTemplateV2).where(
                TaskTemplateV2.owner_id == user_id
            )
        elif role == "manager":
            # Manager видит entries на своих объектах
            if not owner_id:
                return []
            contract_query = select(Contract.allowed_objects).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.owner_id == owner_id,
                    Contract.role == "manager",
                    Contract.is_active == True
                )
            )
            contract_result = await self.session.execute(contract_query)
            contract = contract_result.scalar_one_or_none()
            if not contract or not contract.allowed_objects:
                return []
            allowed_obj_ids = contract.allowed_objects
            query = query.join(TaskPlanV2).where(
                TaskPlanV2.object_id.in_(allowed_obj_ids)
            )
        elif role == "employee":
            # Employee видит только свои entries
            query = query.where(TaskEntryV2.employee_id == user_id)
        else:
            return []
        
        query = query.order_by(TaskEntryV2.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_entries_for_shift_schedule(
        self,
        shift_schedule_id: int
    ) -> List[TaskEntryV2]:
        """
        Получить все задачи для конкретной смены (ShiftSchedule).
        Используется в боте для показа задач во время смены.
        """
        from sqlalchemy.orm import selectinload
        
        query = select(TaskEntryV2).where(
            TaskEntryV2.shift_schedule_id == shift_schedule_id
        ).options(
            selectinload(TaskEntryV2.template),
            selectinload(TaskEntryV2.plan)
        ).order_by(TaskEntryV2.created_at)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def mark_entry_completed(
        self,
        entry_id: int,
        completion_notes: Optional[str] = None,
        completion_media: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Отметить задачу как выполненную.
        
        Args:
            entry_id: ID записи задачи
            completion_notes: Текстовые комментарии
            completion_media: Список медиафайлов [{"url": "...", "type": "photo"}]
            
        Returns:
            True если успешно
        """
        from datetime import datetime
        
        entry = await self.session.get(TaskEntryV2, entry_id)
        if not entry:
            return False
        
        entry.is_completed = True
        entry.completed_at = datetime.utcnow()
        entry.completion_notes = completion_notes
        entry.completion_media = completion_media or []
        
        await self.session.commit()
        logger.info(f"Marked TaskEntryV2 {entry_id} as completed")
        return True

