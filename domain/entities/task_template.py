"""Модель шаблона задач."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base
from sqlalchemy.orm import relationship
from typing import Optional, List, Dict, Any


class TaskTemplate(Base):
    """Модель шаблона задач."""
    
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey("task_categories.id"), nullable=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True)  # NULL = общий шаблон
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL = системный шаблон
    tasks = Column(JSONB, nullable=False)  # Список задач в формате JSON
    is_public = Column(Boolean, default=False)  # Доступен для всех владельцев
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)  # Порядок сортировки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    category = relationship("TaskCategory", backref="templates")
    object = relationship("Object", backref="task_templates")
    owner = relationship("User", backref="task_templates")
    
    def __repr__(self) -> str:
        return f"<TaskTemplate(id={self.id}, name='{self.name}', category_id={self.category_id})>"
    
    @property
    def display_name(self) -> str:
        """Отображаемое имя шаблона."""
        return self.name
    
    @property
    def tasks_list(self) -> List[Dict[str, Any]]:
        """Список задач в виде Python списка."""
        return self.tasks if self.tasks else []
    
    def add_task(self, task_name: str, task_description: str = "", priority: int = 1) -> None:
        """Добавить задачу в шаблон."""
        if not self.tasks:
            self.tasks = []
        
        task = {
            "name": task_name,
            "description": task_description,
            "priority": priority,
            "completed": False
        }
        
        self.tasks.append(task)
    
    def remove_task(self, task_index: int) -> None:
        """Удалить задачу из шаблона по индексу."""
        if self.tasks and 0 <= task_index < len(self.tasks):
            self.tasks.pop(task_index)
    
    def update_task(self, task_index: int, task_name: str = None, task_description: str = None, priority: int = None) -> None:
        """Обновить задачу в шаблоне."""
        if self.tasks and 0 <= task_index < len(self.tasks):
            task = self.tasks[task_index]
            if task_name is not None:
                task["name"] = task_name
            if task_description is not None:
                task["description"] = task_description
            if priority is not None:
                task["priority"] = priority
    
    def get_tasks_by_priority(self) -> List[Dict[str, Any]]:
        """Получить задачи, отсортированные по приоритету."""
        if not self.tasks:
            return []
        
        return sorted(self.tasks, key=lambda x: x.get("priority", 1), reverse=True)
    
    def get_high_priority_tasks(self) -> List[Dict[str, Any]]:
        """Получить задачи с высоким приоритетом (>= 3)."""
        if not self.tasks:
            return []
        
        return [task for task in self.tasks if task.get("priority", 1) >= 3]
