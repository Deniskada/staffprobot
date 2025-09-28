"""
Модель системных настроек для хранения конфигурации домена и SSL
"""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from datetime import datetime
from core.database.connection import Base


class SystemSettings(Base):
    """Модель системных настроек"""
    
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<SystemSettings(key='{self.key}', value='{self.value[:50]}...')>"
    
    @classmethod
    def get_default_settings(cls) -> dict:
        """Возвращает настройки по умолчанию"""
        return {
            'domain': 'localhost:8001',
            'ssl_email': 'admin@localhost',
            'nginx_config_path': '/etc/nginx/sites-available',
            'certbot_path': '/usr/bin/certbot',
            'use_https': 'false',
            'ssl_enabled': 'false'
        }
