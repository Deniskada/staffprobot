"""
Модель шаблона планирования
"""
from datetime import time
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base


class PlanningTemplate(Base):
    """Шаблон планирования для быстрого создания тайм-слотов"""
    
    __tablename__ = "planning_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, comment="Название шаблона")
    description = Column(Text, comment="Описание шаблона")
    owner_telegram_id = Column(Integer, nullable=False, index=True, comment="Telegram ID владельца")
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=True, comment="ID объекта (null для универсальных шаблонов)")
    is_active = Column(Boolean, default=True, comment="Активен ли шаблон")
    is_public = Column(Boolean, default=False, comment="Публичный ли шаблон (для всех владельцев)")
    
    # Временные параметры
    start_time = Column(String(5), nullable=False, comment="Время начала (HH:MM)")
    end_time = Column(String(5), nullable=False, comment="Время окончания (HH:MM)")
    hourly_rate = Column(Integer, nullable=False, comment="Почасовая ставка")
    
    # Параметры повторения
    repeat_type = Column(String(20), default="none", comment="Тип повторения: none, daily, weekly, monthly")
    repeat_days = Column(String(20), comment="Дни недели для повторения (1,2,3,4,5,6,7)")
    repeat_interval = Column(Integer, default=1, comment="Интервал повторения")
    repeat_end_date = Column(DateTime, comment="Дата окончания повторения")
    
    # Метаданные
    created_at = Column(DateTime, default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    # Связи
    object = relationship("Object")
    template_slots = relationship("TemplateTimeSlot", back_populates="template", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<PlanningTemplate(id={self.id}, name='{self.name}', object_id={self.object_id})>"


class TemplateTimeSlot(Base):
    """Тайм-слот в шаблоне планирования"""
    
    __tablename__ = "template_time_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("planning_templates.id"), nullable=False, comment="ID шаблона")
    day_of_week = Column(Integer, nullable=False, comment="День недели (0=Понедельник, 6=Воскресенье)")
    start_time = Column(String(5), nullable=False, comment="Время начала (HH:MM)")
    end_time = Column(String(5), nullable=False, comment="Время окончания (HH:MM)")
    hourly_rate = Column(Integer, nullable=False, comment="Почасовая ставка")
    is_active = Column(Boolean, default=True, comment="Активен ли слот")
    
    # Связи
    template = relationship("PlanningTemplate", back_populates="template_slots")
    
    def __repr__(self) -> str:
        return f"<TemplateTimeSlot(id={self.id}, day={self.day_of_week}, time='{self.start_time}-{self.end_time}')>"
