"""Модель для FAQ (База знаний)."""

from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .base import Base


class FAQEntry(Base):
    """
    Запись в базе знаний (FAQ).
    
    Хранит часто задаваемые вопросы и ответы для пользователей.
    """
    __tablename__ = "faq_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False, index=True, comment="Категория вопроса")  # shifts, salary, technical
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    order_index = Column(Integer, nullable=False, server_default='0', comment="Порядок отображения")
    views_count = Column(Integer, nullable=False, server_default='0', comment="Количество просмотров")
    helpful_count = Column(Integer, nullable=False, server_default='0', comment="Количество отметок 'полезно'")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<FAQEntry(id={self.id}, category='{self.category}', question='{self.question[:30]}...')>"

