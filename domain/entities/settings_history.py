from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from datetime import datetime
from .base import Base


class SettingsHistory(Base):
    """Модель истории изменений системных настроек"""
    __tablename__ = "settings_history"

    id = Column(Integer, primary_key=True)
    setting_key = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_by = Column(String(100))  # telegram_id пользователя
    change_reason = Column(String(255))  # причина изменения
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
