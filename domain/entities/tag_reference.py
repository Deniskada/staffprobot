"""
Справочник тегов для договоров и профилей.

Содержит общепринятые теги для использования в шаблонах договоров
и профилях владельцев в России.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from domain.entities.base import Base


class TagReference(Base):
    """
    Справочник тегов для использования в шаблонах договоров и профилях.
    
    Содержит информацию о доступных тегах, их типах, описаниях
    и категориях для удобства использования.
    """
    __tablename__ = "tag_references"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Основная информация о теге
    key = Column(String(100), unique=True, nullable=False, index=True, 
                comment="Ключ тега (например: owner_name, company_inn)")
    
    label = Column(String(200), nullable=False, 
                  comment="Человекочитаемое название тега")
    
    description = Column(Text, nullable=True,
                        comment="Подробное описание назначения тега")
    
    # Категория тега для группировки
    category = Column(String(100), nullable=False, index=True,
                     comment="Категория тега (owner, company, employee, system)")
    
    # Тип данных для валидации
    data_type = Column(String(50), nullable=False, default="text",
                      comment="Тип данных: text, email, date, number, select, textarea")
    
    # Дополнительные параметры
    is_required = Column(Boolean, default=False, 
                        comment="Обязательное ли поле")
    
    is_system = Column(Boolean, default=False,
                      comment="Системный тег (автозаполняется)")
    
    is_active = Column(Boolean, default=True,
                      comment="Активен ли тег для использования")
    
    # Опции для select полей
    options = Column(JSON, nullable=True,
                    comment="Список опций для select полей")
    
    # Валидация
    validation_pattern = Column(String(500), nullable=True,
                               comment="Regex паттерн для валидации")
    
    validation_message = Column(String(200), nullable=True,
                               comment="Сообщение об ошибке валидации")
    
    # Метаинформация
    sort_order = Column(Integer, default=0,
                       comment="Порядок сортировки в интерфейсе")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<TagReference(key='{self.key}', category='{self.category}')>"
    
    def to_dict(self):
        """Преобразование в словарь для JSON API."""
        return {
            'id': self.id,
            'key': self.key,
            'label': self.label,
            'description': self.description,
            'category': self.category,
            'data_type': self.data_type,
            'is_required': self.is_required,
            'is_system': self.is_system,
            'is_active': self.is_active,
            'options': self.options,
            'validation_pattern': self.validation_pattern,
            'validation_message': self.validation_message,
            'sort_order': self.sort_order
        }
    
    def to_field_schema(self):
        """Преобразование в схему поля для динамических форм."""
        return {
            'key': self.key,
            'label': self.label,
            'type': self.data_type,
            'required': self.is_required,
            'options': self.options or [],
            'validation_pattern': self.validation_pattern,
            'validation_message': self.validation_message
        }
