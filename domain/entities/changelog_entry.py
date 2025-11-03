"""Модель для журнала изменений и улучшений."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.sql import func
from .base import Base


class ChangelogEntry(Base):
    """
    Запись в журнале архитектурных изменений и улучшений.
    
    Используется для:
    - Отслеживания эволюции архитектуры
    - Генерации отчётов для разработчика
    - Обучения AI-ассистента
    """
    __tablename__ = "changelog_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    component = Column(String(100), nullable=False, comment="Компонент системы")  # shift_management, billing, etc
    change_type = Column(String(50), nullable=False, comment="Тип изменения")  # feature, fix, refactor, docs
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False)  # low, medium, high, critical
    status = Column(String(20), nullable=False)  # planned, in_progress, completed, cancelled
    commit_sha = Column(String(40), nullable=True)
    github_issue = Column(Integer, nullable=True)
    created_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    impact_score = Column(Float, nullable=True, comment="Оценка влияния на систему (для ML)")
    indexed_in_brain = Column(Boolean, nullable=False, server_default='false', comment="Проиндексировано в Project Brain")
    
    def __repr__(self) -> str:
        return f"<ChangelogEntry(id={self.id}, type='{self.change_type}', component='{self.component}', status='{self.status}')>"

