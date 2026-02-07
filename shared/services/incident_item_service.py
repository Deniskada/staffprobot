"""Сервис для управления позициями обращений (товары в инциденте)."""

from __future__ import annotations

from typing import List, Optional
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.incident_item import IncidentItem
from domain.entities.incident_history import IncidentHistory
from core.logging.logger import logger


class IncidentItemService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_items(self, incident_id: int) -> List[IncidentItem]:
        """Все позиции инцидента."""
        result = await self.session.execute(
            select(IncidentItem)
            .where(IncidentItem.incident_id == incident_id)
            .options(selectinload(IncidentItem.product))
            .order_by(IncidentItem.created_at)
        )
        return list(result.scalars().all())

    async def add_item(
        self,
        incident_id: int,
        product_id: Optional[int],
        product_name: str,
        quantity: float,
        price: float,
        added_by: int,
    ) -> IncidentItem:
        """Добавить позицию в инцидент."""
        item = IncidentItem(
            incident_id=incident_id,
            product_id=product_id,
            product_name=product_name.strip(),
            quantity=Decimal(str(quantity)),
            price=Decimal(str(price)),
            added_by=added_by,
        )
        self.session.add(item)

        # История
        self._add_history(
            incident_id, added_by, "item_added",
            None, f"{product_name} x{quantity} @ {price}"
        )

        await self.session.commit()
        await self.session.refresh(item)
        logger.info("Добавлена позиция в тикет", incident_id=incident_id, item_id=item.id)
        return item

    async def update_item(
        self,
        item_id: int,
        modified_by: int,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        product_name: Optional[str] = None,
    ) -> Optional[IncidentItem]:
        """Обновить позицию (с записью истории изменений)."""
        item = await self.session.get(IncidentItem, item_id)
        if not item:
            return None

        changes = []
        if quantity is not None and Decimal(str(quantity)) != item.quantity:
            changes.append(f"кол-во: {item.quantity}→{quantity}")
            item.quantity = Decimal(str(quantity))
        if price is not None and Decimal(str(price)) != item.price:
            changes.append(f"цена: {item.price}→{price}")
            item.price = Decimal(str(price))
        if product_name is not None and product_name.strip() != item.product_name:
            changes.append(f"название: {item.product_name}→{product_name.strip()}")
            item.product_name = product_name.strip()

        if changes:
            item.modified_by = modified_by
            self._add_history(
                item.incident_id, modified_by, "item_updated",
                None, f"[{item.product_name}] {'; '.join(changes)}"
            )
            await self.session.commit()
            await self.session.refresh(item)
            logger.info("Позиция тикета обновлена", item_id=item_id, changes=changes)

        return item

    async def remove_item(self, item_id: int, removed_by: int) -> bool:
        """Удалить позицию из инцидента."""
        item = await self.session.get(IncidentItem, item_id)
        if not item:
            return False

        self._add_history(
            item.incident_id, removed_by, "item_removed",
            f"{item.product_name} x{item.quantity} @ {item.price}", None
        )

        await self.session.delete(item)
        await self.session.commit()
        logger.info("Позиция тикета удалена", item_id=item_id)
        return True

    async def calculate_total(self, incident_id: int) -> Decimal:
        """Сумма всех позиций инцидента."""
        items = await self.list_items(incident_id)
        return sum((i.quantity * i.price for i in items), Decimal("0"))

    def _add_history(
        self,
        incident_id: int,
        changed_by: int,
        field: str,
        old_value: Optional[str],
        new_value: Optional[str],
    ) -> None:
        """Записать изменение в историю инцидента."""
        self.session.add(IncidentHistory(
            incident_id=incident_id,
            changed_by=changed_by,
            field=field,
            old_value=old_value,
            new_value=new_value,
        ))
