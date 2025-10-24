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
        object_id: Optional[int] = None
    ) -> List[TaskTemplateV2]:
        """Получить шаблоны задач с учётом роли."""
        query = select(TaskTemplateV2)
        
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
        
        query = query.where(TaskTemplateV2.is_active == True).order_by(TaskTemplateV2.title)
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
            default_amount=default_amount,
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

