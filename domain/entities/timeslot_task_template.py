"""Модель шаблона задачи для тайм-слота."""

from sqlalchemy import Column, Integer, ForeignKey, Numeric, DateTime, Text, Boolean
from sqlalchemy.sql import func
from domain.entities.base import Base


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
    
    def __repr__(self) -> str:
        return f"<TimeslotTaskTemplate(id={self.id}, timeslot_id={self.timeslot_id}, task_text='{self.task_text}')>"

