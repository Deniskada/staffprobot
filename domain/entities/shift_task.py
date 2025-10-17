"""Модель задачи на смену (журнал выполнения)."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime


class ShiftTask(Base):
    """Задача на смену (журнал выполнения)."""
    
    __tablename__ = "shift_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Текст и источник задачи
    task_text = Column(Text, nullable=False)
    source = Column(String(50), nullable=False, index=True)  # object, timeslot, manual
    source_id = Column(Integer, nullable=True)  # ID объекта или тайм-слота
    
    # Параметры задачи
    is_mandatory = Column(Boolean, default=True, nullable=False, index=True)
    requires_media = Column(Boolean, default=False, nullable=False)
    deduction_amount = Column(Numeric(10, 2), nullable=True)  # Штраф/премия
    
    # Статус выполнения
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Дополнительная информация
    media_refs = Column(JSON, nullable=True)  # Ссылки на медиа-файлы
    correction_ref = Column(Integer, nullable=True)  # ID корректировки начисления
    cost = Column(Numeric(10, 2), nullable=True)  # Фактическая премия/штраф
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Отношения
    shift = relationship("Shift", backref="tasks")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def mark_completed(self, user_id: Optional[int] = None) -> None:
        """Отметить задачу как выполненную."""
        self.is_completed = True
        self.completed_at = datetime.utcnow()
    
    def mark_incomplete(self) -> None:
        """Снять отметку выполнения."""
        self.is_completed = False
        self.completed_at = None
    
    def __repr__(self) -> str:
        return f"<ShiftTask(id={self.id}, shift_id={self.shift_id}, text='{self.task_text[:30]}...', completed={self.is_completed})>"

