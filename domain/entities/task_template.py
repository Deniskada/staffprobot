"""Модель шаблона задач v2."""

from __future__ import annotations

from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TaskTemplateV2(Base):
    """Шаблон задачи (v2 - новая архитектура)."""
    
    __tablename__ = "task_templates_v2"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    org_unit_id = Column(Integer, ForeignKey("org_structure_units.id"), nullable=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, index=True)

    code = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    requires_media = Column(Boolean, default=False, nullable=False)
    requires_geolocation = Column(Boolean, default=False, nullable=False)  # Требовать геопозицию при выполнении
    is_mandatory = Column(Boolean, default=False, nullable=False)
    default_bonus_amount = Column(Numeric(10, 2), nullable=True)  # Бонус или штраф

    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_id], backref="task_templates_v2")
    org_unit = relationship("OrgStructureUnit", foreign_keys=[org_unit_id], backref="task_templates_v2")
    object = relationship("Object", foreign_keys=[object_id], backref="task_templates_v2")

    def __repr__(self) -> str:
        return f"<TaskTemplateV2 id={self.id} code={self.code} title={self.title}>"
