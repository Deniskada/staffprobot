"""Модель выплаты сотруднику."""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, Date, DateTime, Text, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class EmployeePayment(Base):
    """Выплата сотруднику (факт перевода денег)."""
    
    __tablename__ = "employee_payments"
    
    id = Column(Integer, primary_key=True, index=True)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Сумма выплаты
    amount = Column(Numeric(10, 2), nullable=False)
    
    # Дата и способ выплаты
    payment_date = Column(Date, nullable=False, index=True)
    payment_method = Column(String(50), nullable=False)  # 'cash', 'bank_transfer', 'card', 'other'
    
    # Статус
    status = Column(String(50), default='pending', nullable=False, index=True)  # 'pending', 'completed', 'failed'
    
    # Подтверждение
    confirmation_code = Column(String(255), nullable=True)  # Номер транзакции, подтверждение
    payment_details = Column(JSONB, nullable=True)  # Банковские данные, реквизиты
    
    # Комментарий
    notes = Column(Text, nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    payroll_entry = relationship("PayrollEntry", backref="payments")
    employee = relationship("User", foreign_keys=[employee_id], backref="received_payments")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self) -> str:
        return f"<EmployeePayment(id={self.id}, employee_id={self.employee_id}, amount={self.amount}, status='{self.status}')>"
    
    def mark_completed(self) -> None:
        """Отметить выплату как завершенную."""
        self.status = 'completed'
        self.completed_at = func.now()
    
    def mark_failed(self) -> None:
        """Отметить выплату как неудачную."""
        self.status = 'failed'

