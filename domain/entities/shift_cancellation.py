"""Модель отмены запланированной смены."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional


class ShiftCancellation(Base):
    """Модель учета отмены запланированных смен."""
    
    __tablename__ = "shift_cancellations"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_schedule_id = Column(Integer, ForeignKey("shift_schedules.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    
    # Кто и как отменил
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cancelled_by_type = Column(String(20), nullable=False, index=True)  # employee, owner, manager, system
    
    # Причина отмены
    cancellation_reason = Column(String(50), nullable=False, index=True)
    # short_notice, no_reason, medical_cert, emergency_cert, police_cert, 
    # owner_decision, contract_termination, other
    reason_notes = Column(Text, nullable=True)  # Дополнительное описание
    
    # Временные метки
    hours_before_shift = Column(Numeric(10, 2), nullable=True)  # За сколько часов до смены отменено
    
    # Документы (справки)
    document_description = Column(Text, nullable=True)  # Описание справки (номер, дата)
    document_verified = Column(Boolean, default=False, nullable=False)  # Проверена ли справка
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Штрафы
    fine_amount = Column(Numeric(10, 2), nullable=True)  # Сумма штрафа
    fine_reason = Column(String(50), nullable=True)  # short_notice, invalid_reason
    fine_applied = Column(Boolean, default=False, nullable=False, index=True)  # Применен ли штраф
    payroll_adjustment_id = Column(Integer, ForeignKey("payroll_adjustments.id"), nullable=True, index=True)
    
    # Контекст
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)  # Договор на момент отмены
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    shift_schedule = relationship("ShiftSchedule", backref="cancellation")
    employee = relationship("User", foreign_keys=[employee_id], backref="my_shift_cancellations")
    object = relationship("Object", backref="shift_cancellations")
    cancelled_by = relationship("User", foreign_keys=[cancelled_by_id], backref="cancelled_shifts")
    verified_by = relationship("User", foreign_keys=[verified_by_id], backref="verified_cancellations")
    payroll_adjustment = relationship("PayrollAdjustment", backref="shift_cancellation")
    contract = relationship("Contract", backref="related_cancellations")
    
    def __repr__(self) -> str:
        return f"<ShiftCancellation(id={self.id}, shift_schedule_id={self.shift_schedule_id}, reason='{self.cancellation_reason}')>"
    
    @property
    def is_valid_reason(self) -> bool:
        """Проверка, является ли причина уважительной."""
        return self.cancellation_reason in ['medical_cert', 'emergency_cert', 'police_cert']
    
    @property
    def needs_verification(self) -> bool:
        """Требует ли причина верификации."""
        return self.is_valid_reason and not self.document_verified
    
    @property
    def cancellation_reason_label(self) -> str:
        """Человекочитаемое название причины."""
        labels = {
            'short_notice': 'Отмена в короткий срок',
            'no_reason': 'Без причины',
            'medical_cert': 'Медицинская справка',
            'emergency_cert': 'Справка от МЧС',
            'police_cert': 'Справка от полиции',
            'owner_decision': 'Решение владельца',
            'contract_termination': 'Расторжение договора',
            'other': 'Другая причина'
        }
        return labels.get(self.cancellation_reason, self.cancellation_reason)
    
    @property
    def cancelled_by_type_label(self) -> str:
        """Человекочитаемое название типа отменившего."""
        labels = {
            'employee': 'Сотрудник',
            'owner': 'Владелец',
            'manager': 'Управляющий',
            'system': 'Система (автоматически)'
        }
        return labels.get(self.cancelled_by_type, self.cancelled_by_type)

