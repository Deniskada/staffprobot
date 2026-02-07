"""Позиция обращения (товар в инциденте типа 'request')."""

from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class IncidentItem(Base):
    __tablename__ = "incident_items"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)

    # Снимки на момент добавления (не зависят от изменений справочника)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    price = Column(Numeric(10, 2), nullable=False, default=0)

    added_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    modified_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    incident = relationship("Incident", backref="items")
    product = relationship("Product", foreign_keys=[product_id])
    adder = relationship("User", foreign_keys=[added_by])
    modifier = relationship("User", foreign_keys=[modified_by])

    @property
    def total(self) -> float:
        """Итого по позиции = quantity * price."""
        return float((self.quantity or 0) * (self.price or 0))

    def __repr__(self) -> str:
        return f"<IncidentItem id={self.id} product={self.product_name} qty={self.quantity}>"
