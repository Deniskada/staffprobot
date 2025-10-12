"""Модель записи начисления."""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, DateTime, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional


class PayrollEntry(Base):
    """Запись начисления зарплаты."""
    
    __tablename__ = "payroll_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Период начисления
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    
    # Рабочее время и расчет
    hours_worked = Column(Numeric(10, 2), nullable=False)  # Часов отработано
    hourly_rate = Column(Numeric(10, 2), nullable=False)   # Ставка в рублях
    gross_amount = Column(Numeric(10, 2), nullable=False)  # Начислено до удержаний
    
    # Удержания и доплаты (денормализация для быстрого доступа)
    total_deductions = Column(Numeric(10, 2), default=0, nullable=False)  # Сумма удержаний
    total_bonuses = Column(Numeric(10, 2), default=0, nullable=False)     # Сумма доплат
    net_amount = Column(Numeric(10, 2), nullable=False)                   # К выплате
    
    # Детали расчета (JSON для гибкости)
    calculation_details = Column(JSONB, nullable=True)  # Смены, ставки, корректировки
    
    # Комментарий
    notes = Column(Text, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    employee = relationship("User", foreign_keys=[employee_id], backref="payroll_entries")
    contract = relationship("Contract", backref="payroll_entries")
    object_ = relationship("Object", backref="payroll_entries")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self) -> str:
        return f"<PayrollEntry(id={self.id}, employee_id={self.employee_id}, net_amount={self.net_amount})>"
    
    def calculate_net_amount(self) -> None:
        """Пересчитать итоговую сумму к выплате."""
        self.net_amount = self.gross_amount + self.total_bonuses - self.total_deductions

