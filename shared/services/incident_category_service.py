from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.incident_category import IncidentCategory


class IncidentCategoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_categories(self, owner_id: int) -> List[IncidentCategory]:
        res = await self.session.execute(
            select(IncidentCategory).where(
                and_(IncidentCategory.owner_id == owner_id, IncidentCategory.is_active == True)
            ).order_by(IncidentCategory.name)
        )
        return list(res.scalars().all())

    async def create_or_update(self, owner_id: int, name: str, category_id: Optional[int] = None) -> IncidentCategory:
        if category_id:
            cat = await self.session.get(IncidentCategory, category_id)
            if not cat:
                raise ValueError("Категория не найдена")
            cat.name = name
        else:
            cat = IncidentCategory(owner_id=owner_id, name=name)
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


