"""
Модель заявки на работу
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
import enum


class ApplicationStatus(enum.Enum):
    """Статусы заявки на работу"""
    PENDING = "PENDING"  # На рассмотрении
    APPROVED = "APPROVED"  # Одобрена
    REJECTED = "REJECTED"  # Отклонена
    INTERVIEW = "INTERVIEW"  # Собеседование


class Application(Base):
    """Заявка на работу"""
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    
    # Связи
    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    
    # Основная информация
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False)
    message = Column(Text, nullable=True)  # Сообщение от соискателя
    preferred_schedule = Column(String(50), nullable=True)  # Предпочитаемый график
    
    # Информация о собеседовании
    interview_scheduled_at = Column(DateTime, nullable=True)
    interview_type = Column(String(20), nullable=True)  # online, offline
    interview_result = Column(Text, nullable=True)  # Результат собеседования
    
    # Метаданные
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Связи
    applicant = relationship("User", foreign_keys=[applicant_id], back_populates="applications")
    object = relationship("Object", foreign_keys=[object_id], back_populates="applications")
    interview = relationship("Interview", back_populates="application", uselist=False)
    
    def __repr__(self):
        return f"<Application(id={self.id}, applicant_id={self.applicant_id}, object_id={self.object_id}, status={self.status.value})>"
