"""
Модель профиля организации (реквизиты ИП/ЮЛ).

Хранит реквизиты для подстановки в шаблоны договоров.
Пользователь может иметь несколько профилей организаций.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from domain.entities.base import Base
from typing import Optional


class OrganizationProfile(Base):
    """
    Профиль организации с реквизитами.
    
    Содержит реквизиты ИП или ЮЛ для использования в шаблонах договоров.
    Привязывается к подразделению для автоматической подстановки данных.
    """
    __tablename__ = "organization_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), 
                     nullable=False, index=True,
                     comment="ID пользователя-владельца")
    
    # Основная информация
    profile_name = Column(String(200), nullable=False,
                         comment="Название профиля (например: ИП Иванов, ООО Ромашка)")
    
    # Тип собственника
    legal_type = Column(String(20), nullable=False,
                       comment="Тип: individual (ФЛ/ИП) или legal (ЮЛ)")
    
    # Флаг профиля по умолчанию
    is_default = Column(Boolean, nullable=False, default=False,
                       comment="Профиль по умолчанию для данного пользователя")
    
    # Реквизиты организации (JSONB)
    requisites = Column(JSON, nullable=False, default=dict,
                       comment="Реквизиты ИП или ЮЛ в формате {field_name: value}")
    
    # Метаинформация
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", backref="organization_profiles")
    
    def __repr__(self):
        return f"<OrganizationProfile(id={self.id}, profile_name='{self.profile_name}', legal_type='{self.legal_type}')>"
    
    def to_dict(self):
        """Преобразование в словарь для JSON API."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'profile_name': self.profile_name,
            'legal_type': self.legal_type,
            'is_default': self.is_default,
            'requisites': self.requisites,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_requisite_value(self, field_name: str) -> Optional[str]:
        """Получить значение реквизита."""
        if not self.requisites:
            return None
        return self.requisites.get(field_name)
    
    def set_requisite_value(self, field_name: str, value: str):
        """Установить значение реквизита."""
        if self.requisites is None:
            self.requisites = {}
        self.requisites[field_name] = value
    
    def get_tags_for_templates(self) -> dict:
        """
        Получить теги для подстановки в шаблоны договоров.
        
        Возвращает словарь вида {tag_key: value} для Jinja2 шаблонов.
        """
        if not self.requisites:
            return {}
        
        # Возвращаем все реквизиты как есть
        return dict(self.requisites)
    
    def is_complete(self) -> bool:
        """Проверить, заполнены ли все обязательные поля."""
        if not self.requisites:
            return False
        
        # Обязательные поля для ИП
        if self.legal_type == 'individual':
            required_fields = [
                'owner_fullname', 'owner_inn', 'owner_ogrnip'
            ]
        # Обязательные поля для ЮЛ
        else:
            required_fields = [
                'company_full_name', 'company_inn', 'company_ogrn', 'company_kpp'
            ]
        
        for field in required_fields:
            value = self.requisites.get(field)
            if not value or not str(value).strip():
                return False
        
        return True
    
    def get_completion_percentage(self) -> float:
        """Рассчитать процент заполненности профиля."""
        if not self.requisites:
            return 0.0
        
        # Список всех полей для данного типа
        if self.legal_type == 'individual':
            all_fields = [
                'owner_fullname', 'owner_ogrnip', 'owner_inn', 'owner_okved',
                'owner_phone', 'owner_email', 'owner_registration_address',
                'owner_postal_address', 'owner_account_number', 'owner_bik',
                'owner_correspondent_account'
            ]
        else:
            all_fields = [
                'company_full_name', 'company_short_name', 'company_ogrn',
                'company_inn', 'company_kpp', 'company_legal_address',
                'company_postal_address', 'company_okpo', 'company_okved',
                'company_account_number', 'company_bik', 'company_correspondent_account',
                'company_director_position', 'company_director_fullname', 'company_basis'
            ]
        
        filled_count = sum(
            1 for field in all_fields
            if self.requisites.get(field) and str(self.requisites.get(field)).strip()
        )
        
        return (filled_count / len(all_fields)) * 100.0 if all_fields else 0.0

