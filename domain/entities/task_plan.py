from __future__ import annotations

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, String, Date, Time, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskPlanV2(Base):
    __tablename__ = "task_plans_v2"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates_v2.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, index=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=True, index=True)

    planned_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Поля для периодичности и времени
    recurrence_type = Column(String(20), nullable=True)  # None, 'weekdays', 'day_interval'
    recurrence_config = Column(JSON, nullable=True)  # {"weekdays": [1,2,3]} или {"interval": 3}
    planned_time_start = Column(Time, nullable=True)  # Время начала задачи
    recurrence_end_date = Column(Date, nullable=True)  # Дата окончания периодичности

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("TaskTemplateV2", foreign_keys=[template_id])
    owner = relationship("User", foreign_keys=[owner_id])
    object = relationship("Object", foreign_keys=[object_id])
    time_slot = relationship("TimeSlot", foreign_keys=[time_slot_id])


