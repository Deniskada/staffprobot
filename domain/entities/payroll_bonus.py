"""Модель доплаты к зарплате."""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class PayrollBonus(Base):
    """Доплата к зарплате."""
    
    __tablename__ = "payroll_bonuses"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Тип доплаты
    bonus_type = Column(String(50), nullable=False, index=True)  # 'performance', 'overtime', 'manual', 'other'
    
    # Сумма
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Описание и детали
    description = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)  # Дополнительные данные
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", backref="bonuses")
    created_by = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PayrollBonus(id={self.id}, type='{self.bonus_type}', amount={self.amount})>"

