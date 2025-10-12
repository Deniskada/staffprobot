"""Модель системы оплаты труда."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional


class PaymentSystem(Base):
    """Вид системы оплаты труда."""
    
    __tablename__ = "payment_systems"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    calculation_type = Column(String(50), nullable=False)  # hourly, salary, hourly_bonus
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships (будут добавлены после связывания с Contract и Object)
    # contracts = relationship("Contract", back_populates="payment_system")
    # objects = relationship("Object", back_populates="payment_system")
    
    def __repr__(self) -> str:
        return f"<PaymentSystem(id={self.id}, code='{self.code}', name='{self.name}')>"
    
    @property
    def is_hourly_based(self) -> bool:
        """Проверка, основана ли система на почасовой оплате."""
        return self.calculation_type in ('hourly', 'hourly_bonus')
    
    @property
    def requires_hourly_rate(self) -> bool:
        """Требуется ли почасовая ставка для этой системы."""
        return self.calculation_type in ('hourly', 'hourly_bonus')

