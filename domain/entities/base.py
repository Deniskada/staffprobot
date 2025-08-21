"""
Базовый файл для всех доменных сущностей
Решает проблему циклических импортов
"""

from sqlalchemy.ext.declarative import declarative_base

# Создаем общую Base для всех моделей
Base = declarative_base()


