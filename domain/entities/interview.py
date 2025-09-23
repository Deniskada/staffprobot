"""
Модель собеседования
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
import enum


class InterviewType(enum.Enum):
    """Типы собеседования"""
    ONLINE = "online"  # Онлайн
    OFFLINE = "offline"  # Очно


class InterviewStatus(enum.Enum):
    """Статусы собеседования"""
    SCHEDULED = "scheduled"  # Запланировано
    COMPLETED = "completed"  # Завершено
    CANCELLED = "cancelled"  # Отменено
    PENDING = "pending"  # В ожидании


class Interview(Base):
    """Собеседование"""
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    # Основная информация
    scheduled_at = Column(DateTime, nullable=False)
    type = Column(Enum(InterviewType), default=InterviewType.OFFLINE, nullable=False)
    status = Column(Enum(InterviewStatus), default=InterviewStatus.SCHEDULED, nullable=False)
    
    # Детали собеседования
    location = Column(String(255), nullable=True)  # Место проведения
    contact_person = Column(String(255), nullable=True)  # Контактное лицо
    contact_phone = Column(String(50), nullable=True)  # Телефон для связи
    notes = Column(Text, nullable=True)  # Дополнительная информация
    result = Column(Text, nullable=True)  # Результат собеседования
    
    # Метаданные
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    applicant = relationship("User", foreign_keys=[applicant_id], back_populates="interviews")
    object = relationship("Object", foreign_keys=[object_id], back_populates="interviews")
    application = relationship("Application", foreign_keys=[application_id], back_populates="interview")
    
    def __repr__(self):
        return f"<Interview(id={self.id}, applicant_id={self.applicant_id}, object_id={self.object_id}, scheduled_at={self.scheduled_at})>"
