"""Модель удержания из зарплаты."""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, Text, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class PayrollDeduction(Base):
    """Удержание из зарплаты."""
    
    __tablename__ = "payroll_deductions"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Тип удержания
    deduction_type = Column(String(50), nullable=False, index=True)  # 'late_start', 'missed_task', 'manual', 'tax', 'other'
    
    # Автоматическое или ручное
    is_automatic = Column(Boolean, default=False, nullable=False, index=True)
    
    # Сумма
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Описание и детали
    description = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)  # Дополнительные данные (shift_id, task_id, late_minutes и т.д.)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", backref="deductions")
    created_by = relationship("User")
    
    def __repr__(self) -> str:
        return f"<PayrollDeduction(id={self.id}, type='{self.deduction_type}', amount={self.amount})>"

