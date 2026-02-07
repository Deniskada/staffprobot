from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.incident_category import IncidentCategory


class IncidentCategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_categories(
        self, owner_id: int, incident_type: Optional[str] = None
    ) -> List[IncidentCategory]:
        """Список активных категорий. Если incident_type указан — фильтр по типу."""
        query = select(IncidentCategory).where(
            and_(IncidentCategory.owner_id == owner_id, IncidentCategory.is_active == True)
        )
        if incident_type:
            query = query.where(IncidentCategory.incident_type == incident_type)
        query = query.order_by(IncidentCategory.name)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def list_all_categories(self, owner_id: int, incident_type: Optional[str] = None) -> List[IncidentCategory]:
        """Все категории (включая неактивные)."""
        query = select(IncidentCategory).where(IncidentCategory.owner_id == owner_id)
        if incident_type:
            query = query.where(IncidentCategory.incident_type == incident_type)
        query = query.order_by(IncidentCategory.name)
        res = await self.session.execute(query)
        return list(res.scalars().all())

    async def create_or_update(
        self,
        owner_id: int,
        name: str,
        category_id: Optional[int] = None,
        incident_type: str = "deduction",
    ) -> IncidentCategory:
        if category_id:
            cat = await self.session.get(IncidentCategory, category_id)
            if not cat:
                raise ValueError("Категория не найдена")
            cat.name = name
            # Тип менять нельзя после создания — только название
        else:
            cat = IncidentCategory(owner_id=owner_id, name=name, incident_type=incident_type)
            self.session.add(cat)
        await self.session.commit()
        await self.session.refresh(cat)
        return cat

    async def deactivate(self, category_id: int) -> bool:
        cat = await self.session.get(IncidentCategory, category_id)
        if not cat:
            return False
        cat.is_active = False
        await self.session.commit()
        return True

    async def activate(self, category_id: int) -> bool:
        cat = await self.session.get(IncidentCategory, category_id)
        if not cat:
            return False
        cat.is_active = True
        await self.session.commit()
        return True


