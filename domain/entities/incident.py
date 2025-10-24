from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, index=True)
    shift_schedule_id = Column(Integer, ForeignKey("shift_schedules.id"), nullable=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    category = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="new")
    reason_code = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    evidence_media_ids = Column(Text, nullable=True)  # comma-separated IDs (простое хранение)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


