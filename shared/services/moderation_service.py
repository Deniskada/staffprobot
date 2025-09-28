"""
Сервис модерации отзывов в системе StaffProBot.

Обеспечивает автоматическую модерацию, фильтрацию контента и управление процессом одобрения/отклонения отзывов.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from core.logging.logger import logger
from domain.entities.review import Review, ReviewAppeal
from domain.entities.user import User


class ModerationService:
    """Сервис для модерации отзывов."""
    
    # Шаблоны решений для отклонений
    REJECTION_TEMPLATES = {
        "spam": "Отзыв отклонен: обнаружен спам или рекламный контент",
        "inappropriate": "Отзыв отклонен: содержит нецензурную лексику или неподходящий контент",
        "irrelevant": "Отзыв отклонен: не относится к работе или объекту",
        "duplicate": "Отзыв отклонен: дублирует существующий отзыв",
        "insufficient": "Отзыв отклонен: недостаточно информации для оценки",
        "fake": "Отзыв отклонен: подозрение на фальшивый отзыв",
        "personal": "Отзыв отклонен: содержит персональную информацию"
    }
    
    # Время модерации (48 часов)
    MODERATION_TIMEOUT_HOURS = 48
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def moderate_review(self, review_id: int, moderator_id: int, decision: str, notes: Optional[str] = None) -> bool:
        """
        Модерация отзыва.
        
        Args:
            review_id: ID отзыва
            moderator_id: ID модератора
            decision: Решение ('approved' или 'rejected')
            notes: Дополнительные заметки модератора
            
        Returns:
            bool: True если модерация прошла успешно
        """
        try:
            # Получаем отзыв
            query = select(Review).where(Review.id == review_id)
            result = await self.session.execute(query)
            review = result.scalar_one_or_none()
            
            if not review:
                logger.error(f"Review {review_id} not found")
                return False
            
            if review.status not in ['pending', 'appealed']:
                logger.warning(f"Review {review_id} is not pending moderation")
                return False
            
            # Обновляем статус отзыва
            review.status = decision
            review.moderation_notes = notes
            
            if decision == 'approved':
                review.published_at = datetime.utcnow()
                logger.info(f"Review {review_id} approved by moderator {moderator_id}")
            else:
                logger.info(f"Review {review_id} rejected by moderator {moderator_id}")
            
            await self.session.commit()
            
            # Отправляем уведомления (TODO: интеграция с системой уведомлений)
            await self._send_moderation_notifications(review, decision)
            
            return True
            
        except Exception as e:
            logger.error(f"Error moderating review {review_id}: {e}")
            await self.session.rollback()
            return False
    
    async def auto_moderate_review(self, review: Review) -> Dict[str, Any]:
        """
        Автоматическая модерация отзыва.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат автоматической модерации
        """
        try:
            # Проверяем различные критерии
            checks = {
                'spam': self._check_spam(review),
                'inappropriate': self._check_inappropriate_content(review),
                'duplicate': await self._check_duplicate(review),
                'insufficient': self._check_insufficient_content(review),
                'personal_info': self._check_personal_info(review)
            }
            
            # Определяем общий результат
            failed_checks = [check for check, result in checks.items() if result['failed']]
            
            if failed_checks:
                # Есть нарушения - требуется ручная модерация
                auto_result = 'manual_review'
                template = self._get_rejection_template(failed_checks[0])
            else:
                # Все проверки пройдены - можно одобрить автоматически
                auto_result = 'auto_approved'
                template = None
            
            logger.info(f"Auto moderation for review {review.id}: {auto_result}")
            
            return {
                'result': auto_result,
                'checks': checks,
                'template': template,
                'failed_checks': failed_checks
            }
            
        except Exception as e:
            logger.error(f"Error in auto moderation for review {review.id}: {e}")
            return {
                'result': 'error',
                'checks': {},
                'template': None,
                'failed_checks': []
            }
    
    def _check_spam(self, review: Review) -> Dict[str, Any]:
        """
        Проверка на спам.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат проверки
        """
        content = (review.title + ' ' + (review.content or '')).lower()
        
        # Паттерны спама
        spam_patterns = [
            r'купить|продать|заказать|скидка|акция|бесплатно',
            r'http[s]?://|www\.|\.com|\.ru|\.net',
            r'\d{3,}',  # Много цифр подряд (телефоны)
            r'[!]{3,}',  # Много восклицательных знаков
            r'[а-яё]{50,}',  # Очень длинные слова (возможно, без пробелов)
        ]
        
        spam_score = 0
        detected_patterns = []
        
        for pattern in spam_patterns:
            matches = re.findall(pattern, content)
            if matches:
                spam_score += len(matches)
                detected_patterns.append(pattern)
        
        # Пороговое значение для спама
        is_spam = spam_score >= 3 or len(detected_patterns) >= 2
        
        return {
            'failed': is_spam,
            'score': spam_score,
            'detected_patterns': detected_patterns,
            'reason': f'Обнаружены признаки спама (балл: {spam_score})' if is_spam else None
        }
    
    def _check_inappropriate_content(self, review: Review) -> Dict[str, Any]:
        """
        Проверка на нецензурную лексику.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат проверки
        """
        content = (review.title + ' ' + (review.content or '')).lower()
        
        # Список нецензурных слов (упрощенный)
        inappropriate_words = [
            'мат', 'ругательство', 'оскорбление', 'хамство'
            # В реальной системе здесь был бы более полный список
        ]
        
        # Проверяем наличие нецензурных слов
        found_words = []
        for word in inappropriate_words:
            if word in content:
                found_words.append(word)
        
        has_inappropriate = len(found_words) > 0
        
        return {
            'failed': has_inappropriate,
            'found_words': found_words,
            'reason': f'Обнаружена нецензурная лексика: {", ".join(found_words)}' if has_inappropriate else None
        }
    
    async def _check_duplicate(self, review: Review) -> Dict[str, Any]:
        """
        Проверка на дубликаты.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат проверки
        """
        try:
            # Ищем похожие отзывы от того же пользователя
            query = select(Review).where(
                and_(
                    Review.reviewer_id == review.reviewer_id,
                    Review.target_type == review.target_type,
                    Review.target_id == review.target_id,
                    Review.id != review.id,
                    Review.status == 'approved'
                )
            )
            
            result = await self.session.execute(query)
            existing_reviews = result.scalars().all()
            
            # Проверяем схожесть содержимого
            current_content = (review.title + ' ' + (review.content or '')).lower()
            
            for existing_review in existing_reviews:
                existing_content = (existing_review.title + ' ' + (existing_review.content or '')).lower()
                
                # Простая проверка схожести (можно улучшить)
                similarity = self._calculate_similarity(current_content, existing_content)
                
                if similarity > 0.8:  # 80% схожести
                    return {
                        'failed': True,
                        'similar_review_id': existing_review.id,
                        'similarity': similarity,
                        'reason': f'Обнаружен дубликат отзыва (схожесть: {similarity:.1%})'
                    }
            
            return {
                'failed': False,
                'reason': None
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicates for review {review.id}: {e}")
            return {
                'failed': False,
                'reason': 'Ошибка проверки дубликатов'
            }
    
    def _check_insufficient_content(self, review: Review) -> Dict[str, Any]:
        """
        Проверка на недостаточность контента.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат проверки
        """
        content_length = len((review.title + ' ' + (review.content or '')).strip())
        
        # Минимальная длина контента
        min_length = 20
        
        is_insufficient = content_length < min_length
        
        return {
            'failed': is_insufficient,
            'content_length': content_length,
            'min_length': min_length,
            'reason': f'Недостаточно информации (длина: {content_length}, минимум: {min_length})' if is_insufficient else None
        }
    
    def _check_personal_info(self, review: Review) -> Dict[str, Any]:
        """
        Проверка на персональную информацию.
        
        Args:
            review: Объект отзыва
            
        Returns:
            Dict: Результат проверки
        """
        content = review.title + ' ' + (review.content or '')
        
        # Паттерны персональной информации
        personal_patterns = [
            r'\b\d{3}-\d{3}-\d{4}\b',  # Телефоны
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
            r'\b\d{4}\s\d{4}\s\d{4}\s\d{4}\b',  # Номера карт
            r'\b\d{10,}\b',  # Длинные числовые последовательности
        ]
        
        found_patterns = []
        for pattern in personal_patterns:
            matches = re.findall(pattern, content)
            if matches:
                found_patterns.append(pattern)
        
        has_personal_info = len(found_patterns) > 0
        
        return {
            'failed': has_personal_info,
            'found_patterns': found_patterns,
            'reason': 'Обнаружена персональная информация' if has_personal_info else None
        }
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Простой расчет схожести текстов.
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            float: Коэффициент схожести (0-1)
        """
        # Убираем пунктуацию и приводим к нижнему регистру
        text1 = re.sub(r'[^\w\s]', '', text1.lower())
        text2 = re.sub(r'[^\w\s]', '', text2.lower())
        
        # Разбиваем на слова
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 and not words2:
            return 1.0
        
        if not words1 or not words2:
            return 0.0
        
        # Расчет коэффициента Жаккара
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def _get_rejection_template(self, check_type: str) -> str:
        """
        Получение шаблона отклонения.
        
        Args:
            check_type: Тип проверки
            
        Returns:
            str: Текст шаблона
        """
        return self.REJECTION_TEMPLATES.get(check_type, "Отзыв отклонен")
    
    async def get_pending_reviews(self, limit: int = 20, offset: int = 0) -> List[Review]:
        """
        Получение отзывов, ожидающих модерации.
        
        Args:
            limit: Количество записей
            offset: Смещение
            
        Returns:
            List[Review]: Список отзывов
        """
        try:
            query = select(Review).where(
                Review.status == 'pending'
            ).order_by(
                Review.created_at.asc()
            ).limit(limit).offset(offset)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []
    
    async def get_overdue_reviews(self) -> List[Review]:
        """
        Получение просроченных отзывов на модерации.
        
        Returns:
            List[Review]: Список просроченных отзывов
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.MODERATION_TIMEOUT_HOURS)
            
            query = select(Review).where(
                and_(
                    Review.status == 'pending',
                    Review.created_at <= cutoff_time
                )
            ).order_by(Review.created_at.asc())
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting overdue reviews: {e}")
            return []
    
    async def get_moderation_statistics(self) -> Dict[str, Any]:
        """
        Получение статистики модерации.
        
        Returns:
            Dict: Статистика модерации
        """
        try:
            # Общее количество отзывов по статусам
            status_query = select(Review.status, func.count(Review.id)).group_by(Review.status)
            status_result = await self.session.execute(status_query)
            status_counts = dict(status_result.fetchall())
            
            # Отзывы за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_query = select(func.count(Review.id)).where(Review.created_at >= week_ago)
            recent_result = await self.session.execute(recent_query)
            recent_count = recent_result.scalar()
            
            # Просроченные отзывы
            overdue_reviews = await self.get_overdue_reviews()
            
            return {
                'total_reviews': sum(status_counts.values()),
                'status_counts': status_counts,
                'recent_reviews': recent_count,
                'overdue_reviews': len(overdue_reviews),
                'pending_reviews': status_counts.get('pending', 0),
                'approved_reviews': status_counts.get('approved', 0),
                'rejected_reviews': status_counts.get('rejected', 0),
                'appealed_reviews': status_counts.get('appealed', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting moderation statistics: {e}")
            return {}
    
    async def bulk_moderate_reviews(self, review_ids: List[int], moderator_id: int, decision: str, notes: Optional[str] = None) -> Dict[str, int]:
        """
        Массовая модерация отзывов.
        
        Args:
            review_ids: Список ID отзывов
            moderator_id: ID модератора
            decision: Решение
            notes: Заметки
            
        Returns:
            Dict: Результат массовой модерации
        """
        success_count = 0
        error_count = 0
        
        for review_id in review_ids:
            try:
                success = await self.moderate_review(review_id, moderator_id, decision, notes)
                if success:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error(f"Error in bulk moderation for review {review_id}: {e}")
                error_count += 1
        
        logger.info(f"Bulk moderation completed: {success_count} successful, {error_count} errors")
        
        return {
            'total': len(review_ids),
            'successful': success_count,
            'errors': error_count
        }
    
    async def _send_moderation_notifications(self, review: Review, decision: str) -> None:
        """
        Отправка уведомлений о результатах модерации.
        
        Args:
            review: Объект отзыва
            decision: Решение модерации
        """
        try:
            from shared.templates.notifications.review_notifications import ReviewNotificationService
            
            notification_service = ReviewNotificationService(self.session)
            
            # Отправляем уведомление автору отзыва
            await notification_service.send_review_status_notification(
                user_id=review.reviewer_id,
                review_data={
                    "target_type": "сотруднику" if review.target_type == "employee" else "объекту",
                    "target_id": review.target_id,
                    "rejection_reason": review.moderation_notes
                },
                status=decision
            )
            
            # Если отзыв одобрен, уведомляем владельца объекта/сотрудника
            if decision == "approved":
                # TODO: Получить ID владельца объекта/сотрудника
                # await notification_service.send_new_review_notification(
                #     target_owner_id=owner_id,
                #     review_data={
                #         "target_type": review.target_type,
                #         "target_id": review.target_id,
                #         "rating": float(review.rating),
                #         "title": review.title
                #     }
                # )
                pass
            
            logger.info(f"Notification sent for review {review.id} with decision {decision}")
        except Exception as e:
            logger.error(f"Error sending moderation notifications: {e}")
    
    async def get_moderator_performance(self, moderator_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Получение статистики работы модератора.
        
        Args:
            moderator_id: ID модератора
            days: Количество дней для анализа
            
        Returns:
            Dict: Статистика работы модератора
        """
        try:
            # TODO: Реализовать отслеживание действий модераторов
            # Пока возвращаем заглушку
            return {
                'moderator_id': moderator_id,
                'period_days': days,
                'moderated_reviews': 0,
                'approved_reviews': 0,
                'rejected_reviews': 0,
                'average_time': 0
            }
        except Exception as e:
            logger.error(f"Error getting moderator performance: {e}")
            return {}
