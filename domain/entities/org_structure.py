"""Модель организационной структуры."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from domain.entities.base import Base
from typing import Optional, List


class OrgStructureUnit(Base):
    """
    Подразделение организационной структуры.
    
    Поддерживает древовидную структуру с наследованием настроек:
    - Система оплаты труда
    - График выплат
    - Настройки штрафов за опоздание
    """
    
    __tablename__ = "org_structure_units"
    
    # Основные поля
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("org_structure_units.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Информация о подразделении
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Настройки, которые могут наследоваться
    payment_system_id = Column(Integer, ForeignKey("payment_systems.id", ondelete="SET NULL"), nullable=True)
    payment_schedule_id = Column(Integer, ForeignKey("payment_schedules.id", ondelete="SET NULL"), nullable=True)
    
    # Настройки штрафов за опоздание (наследуются от родителя, если inherit_late_settings=True)
    inherit_late_settings = Column(Boolean, default=True, nullable=False)
    late_threshold_minutes = Column(Integer, nullable=True)  # Допустимое опоздание в минутах
    late_penalty_per_minute = Column(Numeric(10, 2), nullable=True)  # Стоимость минуты штрафа
    
    # Настройки штрафов за отмену смены (наследуются от родителя, если inherit_cancellation_settings=True)
    inherit_cancellation_settings = Column(Boolean, default=True, nullable=False)
    cancellation_short_notice_hours = Column(Integer, nullable=True)  # Минимальный срок отмены (часов)
    cancellation_short_notice_fine = Column(Numeric(10, 2), nullable=True)  # Штраф за отмену в короткий срок (₽)
    cancellation_invalid_reason_fine = Column(Numeric(10, 2), nullable=True)  # Штраф за неуважительную причину (₽)
    
    # Telegram группа для фото/видео отчетов по задачам
    telegram_report_chat_id = Column(String(100), nullable=True)  # ID Telegram группы для отчетов
    
    # Профиль организации для подстановки в договоры
    organization_profile_id = Column(Integer, ForeignKey("organization_profiles.id", ondelete="SET NULL"), 
                                     nullable=True, index=True,
                                     comment="Профиль организации для договоров в этом подразделении")
    
    # Уровень в иерархии (для оптимизации запросов)
    level = Column(Integer, default=0, nullable=False, index=True)
    
    # Активность
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", backref="org_units")
    parent = relationship("OrgStructureUnit", remote_side=[id], backref="children")
    payment_system = relationship("PaymentSystem", backref="org_units")
    payment_schedule = relationship("PaymentSchedule", foreign_keys=[payment_schedule_id], backref="org_units")
    
    # Обратная связь с объектами (будет добавлена в следующей фазе)
    # objects = relationship("Object", backref="org_unit")
    
    def __repr__(self) -> str:
        return f"<OrgStructureUnit(id={self.id}, name='{self.name}', owner_id={self.owner_id}, level={self.level})>"
    
    def get_full_path(self) -> str:
        """
        Получить полный путь подразделения в иерархии.
        
        Returns:
            str: Путь вида "Компания / Отдел продаж / Московский офис"
        """
        if self.parent:
            return f"{self.parent.get_full_path()} / {self.name}"
        return self.name
    
    def is_root(self) -> bool:
        """Проверить, является ли подразделение корневым."""
        return self.parent_id is None
    
    def has_children(self) -> bool:
        """Проверить, есть ли дочерние подразделения."""
        return len(self.children) > 0 if hasattr(self, 'children') else False
    
    def calculate_level(self) -> int:
        """
        Рассчитать уровень подразделения в иерархии.
        
        Returns:
            int: Уровень (0 для корня, 1 для первого уровня и т.д.)
        """
        if self.parent is None:
            return 0
        return self.parent.calculate_level() + 1
    
    def get_inherited_payment_system_id(self) -> Optional[int]:
        """
        Получить ID системы оплаты с учетом наследования.
        
        Returns:
            Optional[int]: ID системы оплаты или None
        """
        if self.payment_system_id is not None:
            return self.payment_system_id
        
        if self.parent is not None:
            return self.parent.get_inherited_payment_system_id()
        
        return None
    
    def get_inherited_payment_schedule_id(self) -> Optional[int]:
        """
        Получить ID графика выплат с учетом наследования.
        
        Returns:
            Optional[int]: ID графика выплат или None
        """
        if self.payment_schedule_id is not None:
            return self.payment_schedule_id
        
        if self.parent is not None:
            return self.parent.get_inherited_payment_schedule_id()
        
        return None
    
    def get_inherited_late_settings(self) -> dict:
        """
        Получить настройки штрафов за опоздание с учетом наследования.
        
        Returns:
            dict: {
                'threshold_minutes': int or None,
                'penalty_per_minute': Decimal or None,
                'inherited_from': str or None (название подразделения, от которого унаследовано)
            }
        """
        if not self.inherit_late_settings and self.late_threshold_minutes is not None and self.late_penalty_per_minute is not None:
            return {
                'threshold_minutes': self.late_threshold_minutes,
                'penalty_per_minute': self.late_penalty_per_minute,
                'inherited_from': None
            }
        
        if self.parent is not None:
            parent_settings = self.parent.get_inherited_late_settings()
            if parent_settings['inherited_from'] is None:
                parent_settings['inherited_from'] = self.parent.name
            return parent_settings
        
        # По умолчанию возвращаем None, если настройки нигде не определены
        return {
            'threshold_minutes': None,
            'penalty_per_minute': None,
            'inherited_from': None
        }
    
    def get_inherited_cancellation_settings(self) -> dict:
        """
        Получить настройки штрафов за отмену смены с учетом наследования.
        
        Returns:
            dict: {
                'short_notice_hours': int or None,
                'short_notice_fine': Decimal or None,
                'invalid_reason_fine': Decimal or None,
                'inherited_from': str or None (название подразделения, от которого унаследовано)
            }
        """
        if not self.inherit_cancellation_settings and self.cancellation_short_notice_hours is not None:
            return {
                'short_notice_hours': self.cancellation_short_notice_hours,
                'short_notice_fine': self.cancellation_short_notice_fine,
                'invalid_reason_fine': self.cancellation_invalid_reason_fine,
                'inherited_from': None
            }
        
        if self.parent is not None:
            parent_settings = self.parent.get_inherited_cancellation_settings()
            if parent_settings['inherited_from'] is None:
                parent_settings['inherited_from'] = self.parent.name
            return parent_settings
        
        # По умолчанию возвращаем None, если настройки нигде не определены
        return {
            'short_notice_hours': None,
            'short_notice_fine': None,
            'invalid_reason_fine': None,
            'inherited_from': None
        }

