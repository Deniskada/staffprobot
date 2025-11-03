"""Модель для отслеживания деплоев (DORA метрики)."""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .base import Base


class Deployment(Base):
    """
    Деплой в production.
    
    Используется для расчёта DORA метрик:
    - Deployment Frequency
    - Lead Time for Changes
    - Change Failure Rate
    """
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    commit_sha = Column(String(40), nullable=False, index=True)
    commit_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=True, index=True)  # success, failed, rolled_back
    duration_seconds = Column(Integer, nullable=True)
    triggered_by = Column(String(100), nullable=True)  # GitHub Actions, manual, etc
    tests_passed = Column(Integer, nullable=True)
    tests_failed = Column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Deployment(id={self.id}, sha='{self.commit_sha[:7]}', status='{self.status}')>"

