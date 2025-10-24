from __future__ import annotations

from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    code = Column(String(100), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=100, nullable=False)

    # late | cancellation | task | incident
    scope = Column(String(50), nullable=False, index=True)

    # JSON (в виде текста) для простоты миграции; парсится на уровне сервиса
    condition_json = Column(Text, nullable=False)
    action_json = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", backref="rules", foreign_keys=[owner_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Rule id={self.id} code={self.code} scope={self.scope} active={self.is_active}>"


