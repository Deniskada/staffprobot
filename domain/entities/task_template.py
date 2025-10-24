from __future__ import annotations

from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskTemplate(Base):
    __tablename__ = "task_templates"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    org_unit_id = Column(Integer, ForeignKey("org_structure_units.id"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, index=True)

    code = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    requires_media = Column(Boolean, default=False, nullable=False)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    default_bonus_amount = Column(Numeric(10, 2), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TaskTemplate id={self.id} code={self.code} title={self.title}>"
