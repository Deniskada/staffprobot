"""
Сервис обжалований отзывов в системе StaffProBot.

Обеспечивает подачу, рассмотрение и управление обжалованиями отзывов.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from core.logging.logger import logger
from domain.entities.review import Review, ReviewAppeal
from domain.entities.user import User


class AppealService:
    """Сервис для работы с обжалованиями отзывов."""
    
    # Максимальное количество обжалований на отзыв
    MAX_APPEALS_PER_REVIEW = 1
    
    # Время рассмотрения обжалования (72 часа)
    APPEAL_REVIEW_TIMEOUT_HOURS = 72
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def create_appeal(
        self, 
        review_id: int, 
        appellant_id: int, 
        appeal_reason: str, 
        evidence: Optional[Dict[str, Any]] = None
    ) -> Optional[ReviewAppeal]:
        """
        Создание обжалования отзыва.
        
        Args:
            review_id: ID отзыва
            appellant_id: ID подающего обжалование
            appeal_reason: Причина обжалования
            evidence: Доказательства (медиа-файлы, ссылки и т.д.)
            
        Returns:
            ReviewAppeal: Созданное обжалование или None
        """
        try:
            # Проверяем, существует ли отзыв
            review_query = select(Review).where(Review.id == review_id)
            review_result = await self.session.execute(review_query)
            review = review_result.scalar_one_or_none()
            
            if not review:
                logger.error(f"Review {review_id} not found for appeal")
                return None
            
            # Проверяем, можно ли обжаловать отзыв
            if not self._can_appeal_review(review, appellant_id):
                logger.warning(f"Review {review_id} cannot be appealed by user {appellant_id}")
                return None
            
            # Проверяем, не превышено ли количество обжалований
            existing_appeals_query = select(ReviewAppeal).where(
                and_(
                    ReviewAppeal.review_id == review_id,
                    ReviewAppeal.status != 'rejected'  # Отклоненные обжалования не учитываем
                )
            )
            existing_result = await self.session.execute(existing_appeals_query)
            existing_appeals = existing_result.scalars().all()
            
            if len(existing_appeals) >= self.MAX_APPEALS_PER_REVIEW:
                logger.warning(f"Maximum appeals reached for review {review_id}")
                return None
            
            # Создаем обжалование
            appeal = ReviewAppeal(
                review_id=review_id,
                appellant_id=appellant_id,
                appeal_reason=appeal_reason,
                appeal_evidence=evidence,
                status='pending'
            )
            
            self.session.add(appeal)
            
            # Обновляем статус отзыва на "appealed"
            review.status = 'appealed'
            
            await self.session.commit()
            await self.session.refresh(appeal)
            
            logger.info(f"Created appeal {appeal.id} for review {review_id} by user {appellant_id}")
            
            # Отправляем уведомления (TODO: интеграция с системой уведомлений)
            await self._send_appeal_notifications(appeal)
            
            return appeal
            
        except Exception as e:
            logger.error(f"Error creating appeal for review {review_id}: {e}")
            await self.session.rollback()
            return None
    
    def _can_appeal_review(self, review: Review, appellant_id: int) -> bool:
        """
        Проверка возможности обжалования отзыва.
        
        Args:
            review: Объект отзыва
            appellant_id: ID подающего обжалование
            
        Returns:
            bool: True если можно обжаловать
        """
        # Нельзя обжаловать неопубликованные отзывы
        if review.status not in ['approved', 'rejected']:
            return False
        
        # Автор отзыва может обжаловать отклоненный отзыв
        if review.reviewer_id == appellant_id and review.status == 'rejected':
            return True
        
        # Цель отзыва может обжаловать любой отзыв о себе
        if review.status == 'approved':
            # TODO: Проверить, является ли appellant_id целью отзыва
            # Это требует дополнительной логики для определения связи пользователя с объектом/сотрудником
            return True
        
        return False
    
    async def review_appeal(
        self, 
        appeal_id: int, 
        moderator_id: int, 
        decision: str, 
        decision_notes: Optional[str] = None
    ) -> bool:
        """
        Рассмотрение обжалования модератором.
        
        Args:
            appeal_id: ID обжалования
            moderator_id: ID модератора
            decision: Решение ('approved' или 'rejected')
            decision_notes: Заметки модератора
            
        Returns:
            bool: True если рассмотрение прошло успешно
        """
        try:
            # Получаем обжалование
            appeal_query = select(ReviewAppeal).where(ReviewAppeal.id == appeal_id)
            appeal_result = await self.session.execute(appeal_query)
            appeal = appeal_result.scalar_one_or_none()
            
            if not appeal:
                logger.error(f"Appeal {appeal_id} not found")
                return False
            
            if appeal.status != 'pending':
                logger.warning(f"Appeal {appeal_id} is not pending")
                return False
            
            # Обновляем обжалование
            appeal.status = decision
            appeal.moderator_decision = decision
            appeal.decision_notes = decision_notes
            appeal.decided_at = datetime.utcnow()
            
            # Обновляем статус отзыва в зависимости от решения
            review_query = select(Review).where(Review.id == appeal.review_id)
            review_result = await self.session.execute(review_query)
            review = review_result.scalar_one_or_none()
            
            if review:
                if decision == 'approved':
                    # Если обжалование одобрено, возвращаем отзыв на модерацию
                    review.status = 'pending'
                    review.moderation_notes = f"Возвращен на модерацию после обжалования. {decision_notes or ''}"
                else:
                    # Если обжалование отклонено, оставляем статус отзыва как есть
                    pass
            
            await self.session.commit()
            
            logger.info(f"Appeal {appeal_id} reviewed by moderator {moderator_id} with decision {decision}")
            
            # Отправляем уведомления (TODO: интеграция с системой уведомлений)
            await self._send_appeal_decision_notifications(appeal)
            
            return True
            
        except Exception as e:
            logger.error(f"Error reviewing appeal {appeal_id}: {e}")
            await self.session.rollback()
            return False
    
    async def get_user_appeals(self, user_id: int, limit: int = 20, offset: int = 0) -> List[ReviewAppeal]:
        """
        Получение обжалований пользователя.
        
        Args:
            user_id: ID пользователя
            limit: Количество записей
            offset: Смещение
            
        Returns:
            List[ReviewAppeal]: Список обжалований
        """
        try:
            query = select(ReviewAppeal).where(
                ReviewAppeal.appellant_id == user_id
            ).order_by(
                ReviewAppeal.created_at.desc()
            ).limit(limit).offset(offset)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting user appeals: {e}")
            return []
    
    async def get_pending_appeals(self, limit: int = 20, offset: int = 0) -> List[ReviewAppeal]:
        """
        Получение обжалований, ожидающих рассмотрения.
        
        Args:
            limit: Количество записей
            offset: Смещение
            
        Returns:
            List[ReviewAppeal]: Список обжалований
        """
        try:
            query = select(ReviewAppeal).where(
                ReviewAppeal.status == 'pending'
            ).order_by(
                ReviewAppeal.created_at.asc()
            ).limit(limit).offset(offset)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting pending appeals: {e}")
            return []
    
    async def get_overdue_appeals(self) -> List[ReviewAppeal]:
        """
        Получение просроченных обжалований.
        
        Returns:
            List[ReviewAppeal]: Список просроченных обжалований
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.APPEAL_REVIEW_TIMEOUT_HOURS)
            
            query = select(ReviewAppeal).where(
                and_(
                    ReviewAppeal.status == 'pending',
                    ReviewAppeal.created_at <= cutoff_time
                )
            ).order_by(ReviewAppeal.created_at.asc())
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting overdue appeals: {e}")
            return []
    
    async def get_appeal_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики обжалований.
        
        Returns:
            Dict: Статистика обжалований
        """
        try:
            # Общее количество обжалований по статусам
            status_query = select(ReviewAppeal.status, func.count(ReviewAppeal.id)).group_by(ReviewAppeal.status)
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.fetchall())
            
            # Обжалования за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(ReviewAppeal.id)).where(ReviewAppeal.created_at >= week_ago)
            recent_result = await self.session.execute(recent_query)
            recent_count = recent_result.scalar()
            
            # Просроченные обжалования
            overdue_appeals = await self.get_overdue_appeals()
            
            return {
                'total_appeals': sum(status_counts.values()),
                'status_counts': status_counts,
                'recent_appeals': recent_count,
                'overdue_appeals': len(overdue_appeals),
                'pending_appeals': status_counts.get('pending', 0),
                'approved_appeals': status_counts.get('approved', 0),
                'rejected_appeals': status_counts.get('rejected', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting appeal statistics: {e}")
            return {}
    
    async def get_appeal_details(self, appeal_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение детальной информации об обжаловании.
        
        Args:
            appeal_id: ID обжалования
            
        Returns:
            Dict: Детальная информация об обжаловании
        """
        try:
            # Получаем обжалование с связанными данными
            appeal_query = select(ReviewAppeal).where(ReviewAppeal.id == appeal_id)
            appeal_result = await self.session.execute(appeal_query)
            appeal = appeal_result.scalar_one_or_none()
            
            if not appeal:
                return None
            
            # Получаем отзыв
            review_query = select(Review).where(Review.id == appeal.review_id)
            review_result = await self.session.execute(review_query)
            review = review_result.scalar_one_or_none()
            
            # Получаем информацию о подающем обжалование
            appellant_query = select(User).where(User.id == appeal.appellant_id)
            appellant_result = await self.session.execute(appellant_query)
            appellant = appellant_result.scalar_one_or_none()
            
            return {
                'appeal': {
                    'id': appeal.id,
                    'review_id': appeal.review_id,
                    'appellant_id': appeal.appellant_id,
                    'appeal_reason': appeal.appeal_reason,
                    'appeal_evidence': appeal.appeal_evidence,
                    'status': appeal.status,
                    'moderator_decision': appeal.moderator_decision,
                    'decision_notes': appeal.decision_notes,
                    'created_at': appeal.created_at.isoformat(),
                    'decided_at': appeal.decided_at.isoformat() if appeal.decided_at else None
                },
                'review': {
                    'id': review.id if review else None,
                    'title': review.title if review else None,
                    'content': review.content if review else None,
                    'rating': float(review.rating) if review else None,
                    'target_type': review.target_type if review else None,
                    'target_id': review.target_id if review else None,
                    'status': review.status if review else None,
                    'created_at': review.created_at.isoformat() if review else None
                },
                'appellant': {
                    'id': appellant.id if appellant else None,
                    'first_name': appellant.first_name if appellant else None,
                    'last_name': appellant.last_name if appellant else None,
                    'username': appellant.username if appellant else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting appeal details: {e}")
            return None
    
    async def can_user_appeal_review(self, review_id: int, user_id: int) -> Dict[str, Any]:
        """
        Проверка возможности обжалования отзыва пользователем.
        
        Args:
            review_id: ID отзыва
            user_id: ID пользователя
            
        Returns:
            Dict: Информация о возможности обжалования
        """
        try:
            # Получаем отзыв
            review_query = select(Review).where(Review.id == review_id)
            review_result = await self.session.execute(review_query)
            review = review_result.scalar_one_or_none()
            
            if not review:
                return {
                    'can_appeal': False,
                    'reason': 'Отзыв не найден'
                }
            
            # Проверяем статус отзыва
            if review.status not in ['approved', 'rejected']:
                return {
                    'can_appeal': False,
                    'reason': 'Отзыв не может быть обжалован в текущем статусе'
                }
            
            # Проверяем количество существующих обжалований
            existing_appeals_query = select(ReviewAppeal).where(
                and_(
                    ReviewAppeal.review_id == review_id,
                    ReviewAppeal.status != 'rejected'
                )
            )
            existing_result = await self.session.execute(existing_appeals_query)
            existing_appeals = existing_result.scalars().all()
            
            if len(existing_appeals) >= self.MAX_APPEALS_PER_REVIEW:
                return {
                    'can_appeal': False,
                    'reason': f'Превышено максимальное количество обжалований ({self.MAX_APPEALS_PER_REVIEW})'
                }
            
            # Проверяем права пользователя
            can_appeal = self._can_appeal_review(review, user_id)
            
            if not can_appeal:
                return {
                    'can_appeal': False,
                    'reason': 'У вас нет прав на обжалование этого отзыва'
                }
            
            return {
                'can_appeal': True,
                'reason': None,
                'existing_appeals_count': len(existing_appeals)
            }
            
        except Exception as e:
            logger.error(f"Error checking appeal possibility: {e}")
            return {
                'can_appeal': False,
                'reason': 'Ошибка проверки прав на обжалование'
            }
    
    async def _send_appeal_notifications(self, appeal: ReviewAppeal) -> None:
        """
        Отправка уведомлений о подаче обжалования.
        
        Args:
            appeal: Объект обжалования
        """
        try:
            # TODO: Интеграция с системой уведомлений
            logger.info(f"Notification sent for appeal {appeal.id}")
        except Exception as e:
            logger.error(f"Error sending appeal notifications: {e}")
    
    async def _send_appeal_decision_notifications(self, appeal: ReviewAppeal) -> None:
        """
        Отправка уведомлений о решении по обжалованию.
        
        Args:
            appeal: Объект обжалования
        """
        try:
            # TODO: Интеграция с системой уведомлений
            logger.info(f"Notification sent for appeal decision {appeal.id}")
        except Exception as e:
            logger.error(f"Error sending appeal decision notifications: {e}")
