"""Модель категории задач."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from .base import Base
from typing import Optional


class TaskCategory(Base):
    """Модель категории задач."""
    
    __tablename__ = "task_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # Иконка Bootstrap Icons
    color = Column(String(7), nullable=True)  # Цвет в HEX формате
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)  # Порядок сортировки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<TaskCategory(id={self.id}, name='{self.name}')>"
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя категории."""
        return self.name
    
    @property
    def icon_class(self) -> str:
        """CSS класс иконки."""
        return f"bi bi-{self.icon}" if self.icon else "bi bi-list"
    
    @property
    def color_style(self) -> str:
        """CSS стиль для цвета."""
        return f"color: {self.color};" if self.color else ""
