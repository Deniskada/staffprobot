"""
Модель для хранения кастомных шаблонов уведомлений
Iteration 25, Phase 3
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from typing import Optional

from .base import Base
from .notification import NotificationType, NotificationChannel


class NotificationTemplate(Base):
    """Кастомные шаблоны уведомлений (переопределяют статические)"""
    
    __tablename__ = "notification_templates"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    
    # Идентификация шаблона
    template_key = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
        comment="Уникальный ключ шаблона (например: 'shift_reminder')"
    )
    
    type = Column(
        SQLEnum(NotificationType),
        index=True,
        nullable=False,
        comment="Тип уведомления"
    )
    
    channel = Column(
        SQLEnum(NotificationChannel),
        nullable=True,
        comment="Канал доставки (если null - для всех каналов)"
    )
    
    # Название и описание
    name = Column(
        String(200),
        nullable=False,
        comment="Название шаблона"
    )
    
    description = Column(
        Text,
        nullable=True,
        comment="Описание шаблона"
    )
    
    # Содержимое шаблона
    subject_template = Column(
        String(500),
        nullable=True,
        comment="Шаблон заголовка (с переменными $variable)"
    )
    
    plain_template = Column(
        Text,
        nullable=False,
        comment="Текстовый шаблон (Plain Text с переменными $variable)"
    )
    
    html_template = Column(
        Text,
        nullable=True,
        comment="HTML шаблон (с переменными $variable)"
    )
    
    # Переменные шаблона
    variables = Column(
        Text,
        nullable=True,
        comment="JSON список доступных переменных"
    )
    
    # Статус
    is_active = Column(
        Boolean,
        default=True,
        index=True,
        comment="Активен ли шаблон"
    )
    
    is_default = Column(
        Boolean,
        default=False,
        comment="Является ли дефолтным (из статических шаблонов)"
    )
    
    # Метаданные
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Дата создания"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment="Дата обновления"
    )
    
    created_by = Column(
        Integer,
        nullable=True,
        comment="ID пользователя, создавшего шаблон"
    )
    
    updated_by = Column(
        Integer,
        nullable=True,
        comment="ID пользователя, обновившего шаблон"
    )
    
    # Версионирование
    version = Column(
        Integer,
        default=1,
        comment="Версия шаблона"
    )
    
    def __repr__(self) -> str:
        return f"<NotificationTemplate(id={self.id}, key='{self.template_key}', type={self.type})>"
