"""Модель истории изменений договоров."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional
import enum


class ContractChangeType(str, enum.Enum):
    """Тип изменения договора."""
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"


class ContractHistory(Base):
    """История изменений договора."""
    
    __tablename__ = "contract_history"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Метаданные изменения
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    changed_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    change_type = Column(String(50), nullable=False)  # Храним как строку, проверяем через Python enum
    
    # Детали изменения
    field_name = Column(String(100), nullable=False, index=True)  # Название измененного поля
    old_value = Column(JSONB, nullable=True)  # Старое значение
    new_value = Column(JSONB, nullable=True)  # Новое значение
    change_reason = Column(Text, nullable=True)  # Причина изменения (опционально)
    
    # Дата начала действия (для будущих изменений)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительные данные (IP, user agent, etc.)
    change_metadata = Column(JSONB, nullable=True)
    
    # Отношения
    contract = relationship("Contract", backref="history")
    changed_by_user = relationship("User", foreign_keys=[changed_by], backref="contract_changes")
    
    def __repr__(self) -> str:
        return f"<ContractHistory(id={self.id}, contract_id={self.contract_id}, field={self.field_name}, type={self.change_type})>"
