"""ORM модель уведомлений."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from domain.entities.base import Base


class Notification(Base):
    """Уведомление для пользователя."""

    __tablename__ = "notifications"

    id: int = Column(Integer, primary_key=True, index=True)
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: str = Column(String(64), nullable=False)
    payload: Dict[str, Any] = Column(JSON, nullable=False, default=dict)
    is_read: bool = Column(Boolean, nullable=False, default=False)
    created_at: datetime = Column(DateTime(timezone=True), nullable=False)
    read_at: Optional[datetime] = Column(DateTime(timezone=True))
    source: str = Column(String(32), nullable=False, default="system")
    channel: str = Column(String(32), nullable=False, default="web")

    user = relationship("User", back_populates="notifications")
