"""Сервис для управления справочником товаров (расходные материалы)."""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.product import Product


class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_products(self, owner_id: int, include_inactive: bool = False) -> List[Product]:
        """Список товаров владельца."""
        query = select(Product).where(Product.owner_id == owner_id)
        if not include_inactive:
            query = query.where(Product.is_active == True)
        query = query.order_by(Product.name)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_product(self, product_id: int) -> Optional[Product]:
        return await self.session.get(Product, product_id)

    async def create_product(
        self, owner_id: int, name: str, unit: str = "шт.", price: float = 0
    ) -> Product:
        from decimal import Decimal
        product = Product(
            owner_id=owner_id,
            name=name.strip(),
            unit=unit.strip(),
            price=Decimal(str(price)),
        )
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def update_product(
        self,
        product_id: int,
        name: Optional[str] = None,
        unit: Optional[str] = None,
        price: Optional[float] = None,
    ) -> Optional[Product]:
        from decimal import Decimal
        product = await self.session.get(Product, product_id)
        if not product:
            return None
        if name is not None:
            product.name = name.strip()
        if unit is not None:
            product.unit = unit.strip()
        if price is not None:
            product.price = Decimal(str(price))
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def deactivate_product(self, product_id: int) -> bool:
        product = await self.session.get(Product, product_id)
        if not product:
            return False
        product.is_active = False
        await self.session.commit()
        return True

    async def activate_product(self, product_id: int) -> bool:
        product = await self.session.get(Product, product_id)
        if not product:
            return False
        product.is_active = True
        await self.session.commit()
        return True
