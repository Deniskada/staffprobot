"""Модель прав управляющего на объекты."""

from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from datetime import datetime
from typing import Optional


class ManagerObjectPermission(Base):
    """Права управляющего на конкретный объект."""
    
    __tablename__ = "manager_object_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    
    # Детальные права на объект
    can_view = Column(Boolean, default=False, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_manage_employees = Column(Boolean, default=False, nullable=False)
    can_view_finances = Column(Boolean, default=False, nullable=False)
    can_edit_rates = Column(Boolean, default=False, nullable=False)
    can_edit_schedule = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Связи
    contract = relationship("Contract", back_populates="object_permissions")
    object = relationship("Object", back_populates="manager_permissions")
    
    def __repr__(self) -> str:
        return f"<ManagerObjectPermission(id={self.id}, contract_id={self.contract_id}, object_id={self.object_id})>"
    
    def has_any_permission(self) -> bool:
        """Проверка, есть ли у управляющего хотя бы одно право на объект."""
        return any([
            self.can_view,
            self.can_edit,
            self.can_delete,
            self.can_manage_employees,
            self.can_view_finances,
            self.can_edit_rates,
            self.can_edit_schedule
        ])
    
    def get_permissions_dict(self) -> dict:
        """Получение прав в виде словаря."""
        return {
            "can_view": self.can_view,
            "can_edit": self.can_edit,
            "can_delete": self.can_delete,
            "can_manage_employees": self.can_manage_employees,
            "can_view_finances": self.can_view_finances,
            "can_edit_rates": self.can_edit_rates,
            "can_edit_schedule": self.can_edit_schedule
        }
    
    def set_permissions(self, permissions: dict) -> None:
        """Установка прав из словаря."""
        self.can_view = permissions.get("can_view", False)
        self.can_edit = permissions.get("can_edit", False)
        self.can_delete = permissions.get("can_delete", False)
        self.can_manage_employees = permissions.get("can_manage_employees", False)
        self.can_view_finances = permissions.get("can_view_finances", False)
        self.can_edit_rates = permissions.get("can_edit_rates", False)
        self.can_edit_schedule = permissions.get("can_edit_schedule", False)
