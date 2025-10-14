"""Модель корректировки начислений."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional


class PayrollAdjustment(Base):
    """
    Корректировка начислений (единая таблица для всех типов).
    
    Типы корректировок:
    - shift_base: базовая оплата за смену
    - late_start: штраф за опоздание
    - task_bonus: премия за выполнение задачи
    - task_penalty: штраф за невыполнение задачи
    - manual_bonus: ручная премия
    - manual_deduction: ручной штраф
    """
    
    __tablename__ = "payroll_adjustments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Контекст
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Тип и сумма корректировки
    adjustment_type = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)  # может быть положительным или отрицательным
    
    # Описание и детали
    description = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)  # дополнительные данные (минуты опоздания, название задачи и т.д.)
    
    # Привязка к выплате (заполняется Celery)
    payroll_entry_id = Column(Integer, ForeignKey("payroll_entries.id", ondelete="SET NULL"), nullable=True, index=True)
    is_applied = Column(Boolean, default=False, nullable=False, index=True)  # применено к payroll_entry
    
    # История изменений
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    edit_history = Column(JSONB, nullable=True)  # [{timestamp, user_id, field, old_value, new_value}]
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    shift = relationship("Shift", backref="adjustments")
    employee = relationship("User", foreign_keys=[employee_id], backref="payroll_adjustments")
    object = relationship("Object", backref="adjustments")
    payroll_entry = relationship("PayrollEntry", backref="adjustments")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    
    def __repr__(self) -> str:
        return f"<PayrollAdjustment(id={self.id}, type='{self.adjustment_type}', amount={self.amount}, employee_id={self.employee_id})>"
    
    def get_type_label(self) -> str:
        """Получить человекочитаемое название типа корректировки."""
        type_labels = {
            'shift_base': 'Базовая оплата за смену',
            'late_start': 'Штраф за опоздание',
            'task_bonus': 'Премия за задачу',
            'task_penalty': 'Штраф за невыполнение задачи',
            'manual_bonus': 'Ручная премия',
            'manual_deduction': 'Ручной штраф',
            'cancellation_fine': 'Штраф за отмену смены',
            'cancellation_fine_short_notice': 'Штраф за отмену смены',
            'cancellation_fine_invalid_reason': 'Штраф за отмену смены'
        }
        return type_labels.get(self.adjustment_type, self.adjustment_type)
    
    def is_positive(self) -> bool:
        """Проверить, является ли корректировка положительной (увеличивает выплату)."""
        return float(self.amount) > 0
    
    def is_negative(self) -> bool:
        """Проверить, является ли корректировка отрицательной (уменьшает выплату)."""
        return float(self.amount) < 0

