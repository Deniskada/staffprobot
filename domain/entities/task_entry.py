from __future__ import annotations

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskEntry(Base):
    __tablename__ = "task_entries"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("task_plans.id"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False, index=True)
    shift_schedule_id = Column(Integer, ForeignKey("shift_schedules.id"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    notes = Column(Text, nullable=True)
    requires_media = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    template = relationship("TaskTemplate")
    plan = relationship("TaskPlan")


