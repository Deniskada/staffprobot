"""Модель истории операций со сменами и расписаниями."""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from .base import Base


class ShiftHistory(Base):
    """История изменений смен и расписаний."""

    __tablename__ = "shift_history"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True, index=True)
    schedule_id = Column(Integer, ForeignKey("shift_schedules.id"), nullable=True, index=True)

    operation = Column(String(50), nullable=False)  # plan, cancel, open, close, auto_close, etc.
    source = Column(String(32), nullable=False, default="web")  # web, bot, system, celery

    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    actor_role = Column(String(32), nullable=True)  # owner, manager, employee, superadmin, system

    old_status = Column(String(32), nullable=True)
    new_status = Column(String(32), nullable=True)

    payload = Column(JSONB, nullable=True)  # Доп. данные: {"reason": "...", "notes": "..."}

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация истории в словарь."""
        return {
            "id": self.id,
            "shift_id": self.shift_id,
            "schedule_id": self.schedule_id,
            "operation": self.operation,
            "source": self.source,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "payload": self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

