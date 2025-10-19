"""Модель для отслеживания расторжений договоров."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class ContractTermination(Base):
    """История расторжений договоров для аналитики."""
    
    __tablename__ = "contract_terminations"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    terminated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    terminated_by_type = Column(String(32), nullable=False)  # 'owner', 'manager', 'system'
    
    # Причина расторжения
    reason_category = Column(String(64), nullable=False, index=True)  # 'owner_decision', 'performance', etc.
    reason = Column(Text, nullable=False)  # Подробное описание
    
    # Параметры увольнения
    termination_date = Column(Date, nullable=True)  # Дата увольнения
    settlement_policy = Column(String(32), nullable=False)  # 'schedule' | 'termination_date'
    
    # Метаданные
    terminated_at = Column(DateTime(timezone=True), nullable=False)  # Когда был расторгнут
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Отношения
    contract = relationship("Contract", backref="termination_records")
    employee = relationship("User", foreign_keys=[employee_id], backref="contract_terminations_as_employee")
    owner = relationship("User", foreign_keys=[owner_id], backref="contract_terminations_as_owner")
    terminated_by = relationship("User", foreign_keys=[terminated_by_id], backref="contract_terminations_performed")
    
    def __repr__(self) -> str:
        return f"<ContractTermination(id={self.id}, contract_id={self.contract_id}, reason_category='{self.reason_category}')>"

