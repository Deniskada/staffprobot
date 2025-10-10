"""Модель задачи на смену."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional


class ShiftTask(Base):
    """Задача, которую нужно выполнить на смене."""
    
    __tablename__ = "shift_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Текст задачи
    task_text = Column(Text, nullable=False)
    
    # Статус выполнения
    is_completed = Column(Boolean, default=False, nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Источник задачи
    source = Column(String(50), nullable=False, index=True)  # 'object', 'timeslot', 'manual'
    source_id = Column(Integer, nullable=True)  # ID объекта/тайм-слота, если применимо
    
    # Обязательность и удержания
    is_mandatory = Column(Boolean, default=True, nullable=False, index=True)  # Обязательная задача
    deduction_amount = Column(Numeric(10, 2), nullable=True)  # Сумма удержания за невыполнение (в рублях)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    shift = relationship("Shift", backref="tasks")
    created_by = relationship("User")
    
    def __repr__(self) -> str:
        return f"<ShiftTask(id={self.id}, shift_id={self.shift_id}, completed={self.is_completed})>"
    
    def mark_completed(self) -> None:
        """Отметить задачу как выполненную."""
        self.is_completed = True
        self.completed_at = func.now()
    
    def mark_incomplete(self) -> None:
        """Отметить задачу как невыполненную."""
        self.is_completed = False
        self.completed_at = None


class TimeslotTaskTemplate(Base):
    """Шаблон задачи для тайм-слота."""
    
    __tablename__ = "timeslot_task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    timeslot_id = Column(Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Текст задачи
    task_text = Column(Text, nullable=False)
    
    # Обязательность и удержания
    is_mandatory = Column(Boolean, default=True, nullable=False)  # Обязательная задача
    deduction_amount = Column(Numeric(10, 2), nullable=True)  # Сумма удержания за невыполнение (в рублях)
    
    # Порядок отображения
    display_order = Column(Integer, default=0, nullable=False)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    timeslot = relationship("TimeSlot", backref="task_templates")
    created_by = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TimeslotTaskTemplate(id={self.id}, timeslot_id={self.timeslot_id})>"

