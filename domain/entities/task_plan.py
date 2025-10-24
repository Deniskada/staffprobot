from __future__ import annotations

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskPlan(Base):
    __tablename__ = "task_plans"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, index=True)
    time_slot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=True, index=True)

    planned_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    template = relationship("TaskTemplate")


