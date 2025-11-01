"""Модель тарифного плана."""

from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TariffPlan(Base):
    """Модель тарифного плана."""
    
    __tablename__ = "tariff_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="RUB")
    billing_period = Column(String(20), nullable=False, default="month")  # month, year
    
    # Лимиты
    max_objects = Column(Integer, nullable=False, default=2)
    max_employees = Column(Integer, nullable=False, default=5)
    max_managers = Column(Integer, nullable=False, default=0)
    
    # Возможности тарифа (JSONB)
    features = Column(JSON, nullable=False, default=list)
    
    # Статус
    is_active = Column(Boolean, nullable=False, default=True)
    is_popular = Column(Boolean, nullable=False, default=False)  # Популярный тариф
    
    # Льготный период (Grace Period) для новых владельцев (в днях)
    grace_period_days = Column(Integer, nullable=True, default=0)  # Количество дней льготного использования
    
    # Временные метки
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    subscriptions = relationship("UserSubscription", back_populates="tariff_plan")
    
    def __repr__(self) -> str:
        return f"<TariffPlan(id={self.id}, name='{self.name}', price={self.price})>"
    
    def to_dict(self) -> dict:
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if self.price else 0,
            "currency": self.currency,
            "billing_period": self.billing_period,
            "max_objects": self.max_objects,
            "max_employees": self.max_employees,
            "max_managers": self.max_managers,
            "features": self.features or [],
            "is_active": self.is_active,
            "is_popular": self.is_popular,
            "grace_period_days": self.grace_period_days or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def has_feature(self, feature: str) -> bool:
        """Проверка наличия возможности в тарифе."""
        return feature in (self.features or [])
    
    def get_price_per_month(self) -> float:
        """Получение цены за месяц."""
        if self.billing_period == "month":
            return float(self.price) if self.price else 0
        elif self.billing_period == "year":
            return float(self.price) / 12 if self.price else 0
        return float(self.price) if self.price else 0
