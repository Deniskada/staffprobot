"""Модель метрик использования лимитов тарифа."""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from .base import Base


class UsageMetrics(Base):
    """Метрики использования лимитов тарифа пользователем."""
    
    __tablename__ = "usage_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False, index=True)
    
    # Лимиты тарифа
    max_objects = Column(Integer, nullable=False, default=0)
    max_employees = Column(Integer, nullable=False, default=0)
    max_managers = Column(Integer, nullable=False, default=0)
    
    # Текущее использование
    current_objects = Column(Integer, nullable=False, default=0)
    current_employees = Column(Integer, nullable=False, default=0)
    current_managers = Column(Integer, nullable=False, default=0)
    
    # Дополнительные метрики
    total_shifts = Column(Integer, nullable=False, default=0)  # Общее количество смен
    active_contracts = Column(Integer, nullable=False, default=0)  # Активные договоры
    api_requests_count = Column(Integer, nullable=False, default=0)  # API запросы
    storage_used_mb = Column(Integer, nullable=False, default=0)  # Использование хранилища в МБ
    
    # Детальные данные
    detailed_usage = Column(JSON, nullable=True)  # Детальная информация об использовании
    
    # Период метрик
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связанные объекты
    user = relationship("User", back_populates="usage_metrics")
    subscription = relationship("UserSubscription", back_populates="usage_metrics")
    
    def __repr__(self) -> str:
        return f"<UsageMetrics(id={self.id}, user_id={self.user_id}, objects={self.current_objects}/{self.max_objects})>"
    
    def get_usage_percentage(self, limit_type: str) -> float:
        """Получить процент использования лимита."""
        limits = {
            "objects": (self.current_objects, self.max_objects),
            "employees": (self.current_employees, self.max_employees),
            "managers": (self.current_managers, self.max_managers),
        }
        
        if limit_type not in limits:
            return 0.0
        
        current, maximum = limits[limit_type]
        if maximum == -1:  # Безлимит
            return 0.0
        if maximum == 0:
            return 100.0
        
        return min(100.0, (current / maximum) * 100)
    
    def is_limit_exceeded(self, limit_type: str) -> bool:
        """Проверить, превышен ли лимит."""
        return self.get_usage_percentage(limit_type) >= 100.0
    
    def get_remaining_limit(self, limit_type: str) -> int:
        """Получить оставшийся лимит."""
        limits = {
            "objects": (self.current_objects, self.max_objects),
            "employees": (self.current_employees, self.max_employees),
            "managers": (self.current_managers, self.max_managers),
        }
        
        if limit_type not in limits:
            return 0
        
        current, maximum = limits[limit_type]
        if maximum == -1:  # Безлимит
            return -1
        if maximum == 0:
            return 0
        
        return max(0, maximum - current)
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "max_objects": self.max_objects,
            "max_employees": self.max_employees,
            "max_managers": self.max_managers,
            "current_objects": self.current_objects,
            "current_employees": self.current_employees,
            "current_managers": self.current_managers,
            "total_shifts": self.total_shifts,
            "active_contracts": self.active_contracts,
            "api_requests_count": self.api_requests_count,
            "storage_used_mb": self.storage_used_mb,
            "detailed_usage": self.detailed_usage,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_percentages": {
                "objects": self.get_usage_percentage("objects"),
                "employees": self.get_usage_percentage("employees"),
                "managers": self.get_usage_percentage("managers"),
            },
            "remaining_limits": {
                "objects": self.get_remaining_limit("objects"),
                "employees": self.get_remaining_limit("employees"),
                "managers": self.get_remaining_limit("managers"),
            }
        }
