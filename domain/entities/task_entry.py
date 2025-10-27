from __future__ import annotations

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskEntryV2(Base):
    __tablename__ = "task_entries_v2"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("task_plans_v2.id"), nullable=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates_v2.id"), nullable=False, index=True)
    shift_schedule_id = Column(Integer, ForeignKey("shift_schedules.id"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    notes = Column(Text, nullable=True)
    requires_media = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    # Результаты выполнения
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completion_notes = Column(Text, nullable=True)  # Текстовый отчёт
    completion_media = Column(JSON, nullable=True)  # [{"url": "...", "type": "photo"}]

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    template = relationship("TaskTemplateV2", foreign_keys=[template_id])
    plan = relationship("TaskPlanV2", foreign_keys=[plan_id])
    shift_schedule = relationship("ShiftSchedule", foreign_keys=[shift_schedule_id])
    employee = relationship("User", foreign_keys=[employee_id])


