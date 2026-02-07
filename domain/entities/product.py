"""Справочник товаров (расходные материалы)."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False)
    unit = Column(String(50), nullable=False, default="шт.")  # единица измерения
    price = Column(Numeric(10, 2), nullable=False, default=0)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_id])

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name} price={self.price}>"
