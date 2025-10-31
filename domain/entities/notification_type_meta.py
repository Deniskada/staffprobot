"""
Мета-информация о типах уведомлений.
Iteration 37: Notification System Overhaul
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from typing import Optional, List

from .base import Base


class NotificationTypeMeta(Base):
    """Мета-информация о типах уведомлений (для UI и настроек)"""
    
    __tablename__ = "notification_types_meta"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    
    # Идентификация типа
    type_code = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
        comment="Код типа (соответствует NotificationType enum)"
    )
    
    # Названия и описания
    title = Column(
        String(200),
        nullable=False,
        comment="Название типа на русском (для UI)"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Подробное описание для пользователей"
    )
    
    # Категоризация
    category = Column(
        String(50),
        index=True,
        nullable=False,
        comment="Категория: shifts, contracts, reviews, payments, system, tasks, applications"
    )
    
    # Настройки поведения
    default_priority = Column(
        String(20),
        nullable=False,
        default="normal",
        comment="Приоритет по умолчанию: low, normal, high, critical"
    )
    
    is_user_configurable = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Показывать ли в настройках владельца/пользователя"
    )
    
    is_admin_only = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Только для администраторов (не показывать владельцу)"
    )
    
    # Доступные каналы
    available_channels = Column(
        JSON,
        nullable=False,
        default=list,
        comment="Список доступных каналов: ['telegram', 'inapp', 'email']"
    )
    
    # Сортировка и отображение
    sort_order = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Порядок отображения в UI"
    )
    
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Активен ли тип уведомления"
    )
    
    # Системные поля
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def __repr__(self):
        return f"<NotificationTypeMeta(type_code={self.type_code}, title={self.title})>"
    
    def to_dict(self):
        """Преобразование в словарь для API/UI"""
        return {
            "id": self.id,
            "type_code": self.type_code,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "default_priority": self.default_priority,
            "is_user_configurable": self.is_user_configurable,
            "is_admin_only": self.is_admin_only,
            "available_channels": self.available_channels,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

