"""Модель для отчетов о багах."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from .base import Base


class BugLog(Base):
    """
    Отчёт о баге от пользователя.
    
    Хранит информацию о проблеме, приоритете, статусе и связи с GitHub Issue.
    """
    __tablename__ = "bug_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(200), nullable=False)
    what_doing = Column(Text, nullable=False, comment="Что делал пользователь")
    expected = Column(Text, nullable=False, comment="Что ожидал увидеть")
    actual = Column(Text, nullable=False, comment="Что произошло на самом деле")
    screenshot_url = Column(String(500), nullable=True)
    priority = Column(String(20), nullable=False, server_default='medium')  # low, medium, high, critical
    status = Column(String(20), nullable=False, server_default='open')  # open, in_progress, resolved, closed
    github_issue_number = Column(Integer, nullable=True)
    assigned_to = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self) -> str:
        return f"<BugLog(id={self.id}, title='{self.title}', priority='{self.priority}', status='{self.status}')>"

