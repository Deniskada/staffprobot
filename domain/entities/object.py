"""Модель объекта."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Numeric, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base
from sqlalchemy.orm import relationship
from typing import Optional




class Object(Base):
    """Модель объекта."""
    
    __tablename__ = "objects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    address = Column(Text, nullable=True)
    coordinates = Column(String(100), nullable=False)  # "lat,lon" формат для MVP
    opening_time = Column(Time, nullable=False)
    closing_time = Column(Time, nullable=False)
    hourly_rate = Column(Numeric(10, 2), nullable=False)
    required_employees = Column(Text, nullable=True)  # JSON строка для MVP
    max_distance_meters = Column(Integer, nullable=False, default=500)  # Максимальное расстояние для геолокации
    auto_close_minutes = Column(Integer, nullable=False, default=60)  # Автоматическое закрытие смен через N минут
    available_for_applicants = Column(Boolean, default=False)  # Доступен для соискателей
    work_conditions = Column(Text, nullable=True)  # Условия работы
    shift_tasks = Column(JSONB, nullable=True)  # Список задач на смене
    employee_position = Column(Text, nullable=True)  # Должность сотрудника (краткое описание выполняемой работы)
    # График работы: битовая маска дней (1=Пн ... 64=Вс), по умолчанию Пн-Пт (31)
    work_days_mask = Column(Integer, nullable=False, server_default="31")
    # Периодичность повторения недель: 1 = каждую неделю
    schedule_repeat_weeks = Column(Integer, nullable=False, server_default="1")
    # Часовой пояс объекта (например: "Europe/Moscow", "America/New_York")
    timezone = Column(String(50), nullable=True, default="Europe/Moscow")
    # Система оплаты труда (переопределяет org_unit)
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True, index=True)
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True, index=True)
    # Настройки штрафов за опоздание
    inherit_late_settings = Column(Boolean, default=True, nullable=False, index=True)  # Наследовать от подразделения
    late_threshold_minutes = Column(Integer, nullable=True)  # Допустимое опоздание (может быть отрицательным)
    late_penalty_per_minute = Column(Numeric(10, 2), nullable=True)  # Стоимость минуты штрафа (₽)
    # Подразделение
    org_unit_id = Column(Integer, ForeignKey("org_structure_units.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    owner = relationship("User", backref="owned_objects")
    payment_system = relationship("PaymentSystem", backref="objects")
    payment_schedule = relationship("PaymentSchedule", foreign_keys=[payment_schedule_id], backref="assigned_objects")
    org_unit = relationship("OrgStructureUnit", backref="objects")
    manager_permissions = relationship("ManagerObjectPermission", back_populates="object", lazy="select")
    # planning_templates = relationship("PlanningTemplate", back_populates="object")
    
    def __repr__(self) -> str:
        return f"<Object(id={self.id}, name='{self.name}', owner_id={self.owner_id})>"
    
    @property
    def working_hours(self) -> str:
        """Время работы объекта в читаемом формате."""
        return f"{self.opening_time.strftime('%H:%M')} - {self.closing_time.strftime('%H:%M')}"
    
    def is_working_now(self) -> bool:
        """Проверка, работает ли объект сейчас."""
        from datetime import datetime, time
        now = datetime.now().time()
        return self.opening_time <= now <= self.closing_time
    
    def get_coordinates_tuple(self) -> tuple[float, float]:
        """Получение координат в виде кортежа."""
        try:
            lat, lon = self.coordinates.split(',')
            return float(lat.strip()), float(lon.strip())
        except (ValueError, AttributeError):
            return (0.0, 0.0)
    
    def set_coordinates(self, lat: float, lon: float) -> None:
        """Установка координат."""
        self.coordinates = f"{lat},{lon}"
    
    def get_effective_payment_system_id(self) -> Optional[int]:
        """
        Получить ID системы оплаты с учетом наследования от подразделения.
        
        Логика:
        1. Если у объекта указана payment_system_id → используем её
        2. Иначе, если есть подразделение → берем от него (с учетом наследования)
        3. Иначе None
        
        Returns:
            Optional[int]: ID системы оплаты или None
        """
        if self.payment_system_id is not None:
            return self.payment_system_id
        
        if self.org_unit is not None:
            return self.org_unit.get_inherited_payment_system_id()
        
        return None
    
    def get_effective_payment_schedule_id(self) -> Optional[int]:
        """
        Получить ID графика выплат с учетом наследования от подразделения.
        
        Returns:
            Optional[int]: ID графика выплат или None
        """
        if self.payment_schedule_id is not None:
            return self.payment_schedule_id
        
        if self.org_unit is not None:
            return self.org_unit.get_inherited_payment_schedule_id()
        
        return None
    
    def get_effective_late_settings(self) -> dict:
        """
        Получить настройки штрафов за опоздание с учетом наследования.
        
        Returns:
            dict: {
                'threshold_minutes': int or None,
                'penalty_per_minute': Decimal or None,
                'source': str ('object', 'org_unit', 'default')
            }
        """
        if not self.inherit_late_settings and self.late_threshold_minutes is not None and self.late_penalty_per_minute is not None:
            return {
                'threshold_minutes': self.late_threshold_minutes,
                'penalty_per_minute': self.late_penalty_per_minute,
                'source': 'object'
            }
        
        if self.org_unit is not None:
            org_settings = self.org_unit.get_inherited_late_settings()
            if org_settings['threshold_minutes'] is not None:
                return {
                    'threshold_minutes': org_settings['threshold_minutes'],
                    'penalty_per_minute': org_settings['penalty_per_minute'],
                    'source': 'org_unit'
                }
        
        # Используем константы по умолчанию
        return {
            'threshold_minutes': None,
            'penalty_per_minute': None,
            'source': 'default'
        }
    
    # Связи с заявками и собеседованиями
    applications = relationship("Application", back_populates="object", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="object", cascade="all, delete-orphan")





