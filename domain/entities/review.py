"""
Модель отзывов и рейтингов для системы StaffProBot.

Включает модели для отзывов, медиа-файлов, обжалований, рейтингов и правил системы.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """Статусы отзывов."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPEALED = "appealed"


class AppealStatus(str, Enum):
    """Статусы обжалований."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Review(Base):
    """Модель отзыва."""
    
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(20), nullable=False, index=True)  # 'employee', 'object'
    target_id = Column(Integer, nullable=False, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)
    rating = Column(Numeric(2,1), nullable=False)  # 1.0 - 5.0
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)  # 'pending', 'approved', 'rejected', 'appealed'
    moderation_notes = Column(Text, nullable=True)
    is_anonymous = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    contract = relationship("Contract", foreign_keys=[contract_id])
    media_files = relationship("ReviewMedia", back_populates="review", cascade="all, delete-orphan")
    appeals = relationship("ReviewAppeal", back_populates="review", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Review(id={self.id}, reviewer_id={self.reviewer_id}, target_type='{self.target_type}', target_id={self.target_id}, rating={self.rating}, status='{self.status}')>"
    
    @property
    def is_published(self) -> bool:
        """Проверяет, опубликован ли отзыв."""
        return self.status == "approved" and self.published_at is not None
    
    @property
    def can_be_appealed(self) -> bool:
        """Проверяет, можно ли обжаловать отзыв."""
        return self.status in ["approved", "rejected"] and len(self.appeals) == 0


class ReviewMedia(Base):
    """Модель медиа-файлов отзыва."""
    
    __tablename__ = "review_media"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    file_type = Column(String(20), nullable=False)  # 'photo', 'video', 'audio', 'document'
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    review = relationship("Review", back_populates="media_files")
    
    def __repr__(self) -> str:
        return f"<ReviewMedia(id={self.id}, review_id={self.review_id}, file_type='{self.file_type}', file_size={self.file_size})>"
    
    @property
    def size_mb(self) -> float:
        """Размер файла в мегабайтах."""
        return self.file_size / (1024 * 1024)


class ReviewAppeal(Base):
    """Модель обжалования отзыва."""
    
    __tablename__ = "review_appeals"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, index=True)
    appellant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appeal_reason = Column(Text, nullable=False)
    appeal_evidence = Column(JSONB, nullable=True)  # Медиа-файлы как JSON
    status = Column(String(20), default="pending", nullable=False, index=True)  # 'pending', 'approved', 'rejected'
    moderator_decision = Column(String(20), nullable=True)  # 'approved', 'rejected'
    decision_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    review = relationship("Review", back_populates="appeals")
    appellant = relationship("User", foreign_keys=[appellant_id])
    
    def __repr__(self) -> str:
        return f"<ReviewAppeal(id={self.id}, review_id={self.review_id}, appellant_id={self.appellant_id}, status='{self.status}')>"
    
    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли обжалование решения."""
        return self.status == "pending"


class Rating(Base):
    """Модель рейтинга объекта или сотрудника."""
    
    __tablename__ = "ratings"
    
    id = Column(Integer, primary_key=True, index=True)
    target_type = Column(String(20), nullable=False, index=True)  # 'employee', 'object'
    target_id = Column(Integer, nullable=False, index=True)
    average_rating = Column(Numeric(3,2), default=5.0, nullable=False)  # Начальный рейтинг 5.0
    total_reviews = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Rating(id={self.id}, target_type='{self.target_type}', target_id={self.target_id}, average_rating={self.average_rating}, total_reviews={self.total_reviews})>"
    
    @property
    def rating_stars(self) -> float:
        """Рейтинг в звездах (округленный до 0.5)."""
        return round(self.average_rating * 2) / 2


class SystemRule(Base):
    """Модель правил системы."""
    
    __tablename__ = "system_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False, index=True)  # 'review_guidelines', 'appeal_process', 'moderation_policy'
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self) -> str:
        return f"<SystemRule(id={self.id}, rule_type='{self.rule_type}', title='{self.title}', is_active={self.is_active})>"
