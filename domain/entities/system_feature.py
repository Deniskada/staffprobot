"""
Модель функций системы.

Справочник дополнительных функций, которые могут быть включены/выключены
владельцами и привязаны к тарифным планам.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import List, Dict, Any


class SystemFeature(Base):
    """
    Функция системы.
    
    Определяет дополнительные возможности, которые могут быть включены
    в тарифные планы и управляться пользователями.
    """
    __tablename__ = "system_features"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Уникальный ключ функции (для кода)
    key = Column(String(100), unique=True, nullable=False, index=True,
                comment="Уникальный ключ функции (например: shared_calendar)")
    
    # Название и описание
    name = Column(String(200), nullable=False,
                 comment="Человекочитаемое название функции")
    
    description = Column(Text, nullable=True,
                        comment="Продающее описание функции")
    
    # Порядок отображения
    sort_order = Column(Integer, default=0, nullable=False,
                       comment="Порядок сортировки в интерфейсе")
    
    # Связанные элементы UI (JSONB)
    menu_items = Column(JSON, nullable=False, default=list,
                       comment="Список ID пунктов меню, связанных с функцией")
    
    form_elements = Column(JSON, nullable=False, default=list,
                          comment="Список ID элементов форм, связанных с функцией")
    
    # Статус функции
    is_active = Column(Boolean, nullable=False, default=True,
                      comment="Активна ли функция в системе (глобально)")
    
    # Статистика использования
    usage_count = Column(Integer, default=0, nullable=False,
                        comment="Счетчик использования функции")
    
    # Метаинформация
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemFeature(key='{self.key}', name='{self.name}', is_active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON API."""
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'description': self.description,
            'sort_order': self.sort_order,
            'menu_items': self.menu_items or [],
            'form_elements': self.form_elements or [],
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_menu_items(self) -> List[str]:
        """Получить список связанных пунктов меню."""
        return self.menu_items or []
    
    def get_form_elements(self) -> List[str]:
        """Получить список связанных элементов форм."""
        return self.form_elements or []
    
    def increment_usage(self):
        """Увеличить счетчик использования."""
        self.usage_count = (self.usage_count or 0) + 1

