from __future__ import annotations

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Date, Numeric
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

    category = Column(String(100), nullable=False)  # e.g., 'late_arrival', 'task_non_completion', 'damage', 'violation'
    severity = Column(String(50), nullable=True)  # e.g., 'low', 'medium', 'high', 'critical'
    status = Column(String(50), nullable=False, default="new")  # 'new', 'in_review', 'resolved', 'rejected'
    reason_code = Column(String(100), nullable=True)  # Link to predefined reason
    notes = Column(Text, nullable=True)
    evidence_media_ids = Column(Text, nullable=True)  # JSON list of media IDs
    suggested_adjustments = Column(Text, nullable=True)  # JSON list of suggested payroll adjustments

    # Пользовательские реквизиты
    custom_number = Column(String(100), nullable=True, index=True)
    custom_date = Column(Date, nullable=True, index=True)
    damage_amount = Column(Numeric(10, 2), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id])
    object = relationship("Object", foreign_keys=[object_id])
    shift_schedule = relationship("ShiftSchedule", foreign_keys=[shift_schedule_id])
    employee = relationship("User", foreign_keys=[employee_id])
    creator = relationship("User", foreign_keys=[created_by])


