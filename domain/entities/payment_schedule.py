"""Модель графика выплат."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional, Dict, Any


class PaymentSchedule(Base):
    """График выплат сотрудникам."""
    
    __tablename__ = "payment_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String(50), nullable=False, index=True)  # weekly, biweekly, monthly
    payment_period = Column(JSONB, nullable=False)  # Детали периода расчета
    payment_day = Column(Integer, nullable=False)  # 1-7 для weekly, 1-31 для monthly
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships (будут добавлены после связывания)
    # contracts = relationship("Contract", back_populates="payment_schedule")
    # objects = relationship("Object", back_populates="payment_schedule")
    
    def __repr__(self) -> str:
        return f"<PaymentSchedule(id={self.id}, name='{self.name}', frequency='{self.frequency}')>"
    
    @property
    def is_weekly(self) -> bool:
        """Проверка, является ли график еженедельным."""
        return self.frequency == 'weekly'
    
    @property
    def is_monthly(self) -> bool:
        """Проверка, является ли график ежемесячным."""
        return self.frequency == 'monthly'
    
    def get_payment_period_description(self) -> str:
        """
        Получить читаемое описание периода расчета.
        
        Returns:
            Описание периода (например: "За предыдущую неделю (пн-вс)")
        """
        if self.payment_period and isinstance(self.payment_period, dict):
            return self.payment_period.get('description', 'Не указано')
        return 'Не указано'

