"""
Профиль владельца с динамическими полями.

Позволяет владельцу создавать свой профиль с произвольными полями
на основе справочника тегов для использования в шаблонах договоров.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from domain.entities.base import Base


class OwnerProfile(Base):
    """
    Профиль владельца с динамическими полями.
    
    Содержит информацию о владельце бизнеса, которая может использоваться
    в шаблонах договоров через систему тегов.
    """
    __tablename__ = "owner_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с пользователем
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True,
                     comment="ID пользователя-владельца")
    
    # Основная информация
    profile_name = Column(String(200), nullable=False, default="Мой профиль",
                         comment="Название профиля")
    
    # Тип собственника
    legal_type = Column(String(20), nullable=False, default="individual",
                       comment="Тип: individual (ФЛ) или legal (ЮЛ)")
    
    # Динамические поля профиля
    profile_data = Column(JSON, nullable=False, default=dict,
                         comment="Динамические поля профиля в формате {tag_key: value}")
    
    # Активные теги профиля
    active_tags = Column(JSON, nullable=False, default=list,
                        comment="Список активных тегов профиля")
    
    # Новые поля для расширенного профиля
    about_company = Column(Text, nullable=True,
                          comment="О компании - описание, история, масштаб")
    
    values = Column(Text, nullable=True,
                   comment="Ценности компании - принципы, структура")
    
    photos = Column(JSON, nullable=False, default=list,
                   comment="Фотографии компании (массив URL/путей, до 5 шт)")
    
    contact_phone = Column(String(20), nullable=True,
                          comment="Телефон для связи")
    
    contact_messengers = Column(JSON, nullable=False, default=list,
                               comment="Активные мессенджеры: whatsapp, telegram, max")
    
    enabled_features = Column(JSON, nullable=False, default=list,
                             comment="Включенные дополнительные функции (массив ключей функций)")
    
    # Настройки
    is_complete = Column(Boolean, default=False,
                        comment="Заполнен ли профиль полностью")
    
    is_public = Column(Boolean, default=False,
                      comment="Доступен ли профиль другим пользователям")
    
    # Метаинформация
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="owner_profile")
    
    def __repr__(self):
        return f"<OwnerProfile(user_id={self.user_id}, legal_type='{self.legal_type}')>"
    
    def to_dict(self):
        """Преобразование в словарь для JSON API."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'profile_name': self.profile_name,
            'legal_type': self.legal_type,
            'profile_data': self.profile_data,
            'active_tags': self.active_tags,
            'is_complete': self.is_complete,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_tag_value(self, tag_key: str) -> str:
        """Получить значение тега из профиля."""
        return self.profile_data.get(tag_key, "")
    
    def set_tag_value(self, tag_key: str, value: str):
        """Установить значение тега в профиле."""
        if self.profile_data is None:
            self.profile_data = {}
        self.profile_data[tag_key] = value
    
    def get_tags_for_templates(self) -> dict:
        """
        Получить все теги профиля для использования в шаблонах.
        
        Возвращает словарь вида {tag_key: value} для подстановки в Jinja2 шаблоны.
        """
        result = {}
        
        # Добавляем все динамические поля
        if self.profile_data:
            result.update(self.profile_data)
        
        # Добавляем системные теги
        result.update({
            'current_date': None,  # Будет заполнено при рендеринге
            'current_time': None,  # Будет заполнено при рендеринге
            'current_year': None,  # Будет заполнено при рендеринге
        })
        
        return result
    
    def is_tag_filled(self, tag_key: str) -> bool:
        """Проверить, заполнен ли тег в профиле."""
        value = self.get_tag_value(tag_key)
        return bool(value and str(value).strip())
    
    def get_completion_percentage(self, required_tags: list = None) -> float:
        """
        Рассчитать процент заполненности профиля.
        
        Учитывает как теги, так и новые поля профиля.
        
        Args:
            required_tags: Список обязательных тегов. Если None, используются все активные теги.
        
        Returns:
            Процент заполненности от 0.0 до 100.0
        """
        total_fields = 0
        filled_fields = 0
        
        # Учитываем теги
        if not required_tags:
            required_tags = self.active_tags or []
        
        if required_tags:
            total_fields += len(required_tags)
            filled_fields += sum(1 for tag in required_tags if self.is_tag_filled(tag))
        
        # Учитываем новые поля профиля
        profile_fields = {
            'about_company': self.about_company,
            'values': self.values,
            'contact_phone': self.contact_phone,
            'photos': self.photos,
            'contact_messengers': self.contact_messengers
        }
        
        total_fields += len(profile_fields)
        filled_fields += sum(1 for key, value in profile_fields.items() 
                            if value and (isinstance(value, list) and len(value) > 0 or 
                                        isinstance(value, str) and value.strip()))
        
        if total_fields == 0:
            return 0.0
        
        return (filled_fields / total_fields) * 100.0
