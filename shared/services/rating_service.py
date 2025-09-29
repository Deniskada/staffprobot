"""
Сервис для расчета и управления рейтингами в системе отзывов.

Обеспечивает автоматический расчет рейтингов с учетом времени и взвешенного среднего.
"""

import math
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from core.logging.logger import logger
from domain.entities.review import Review, Rating


class RatingService:
    """Сервис для работы с рейтингами."""
    
    # Начальный рейтинг для новых объектов/сотрудников
    DEFAULT_RATING = 5.0
    
    # Коэффициент затухания для учета времени (в днях)
    # Чем больше значение, тем медленнее "стареют" отзывы
    DECAY_HALF_LIFE_DAYS = 90
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def calculate_rating(self, target_type: str, target_id: int) -> Optional[Rating]:
        """
        Расчет рейтинга для объекта или сотрудника.
        
        Args:
            target_type: Тип цели ('employee' или 'object')
            target_id: ID цели
            
        Returns:
            Rating: Объект рейтинга или None
        """
        try:
            # Получаем все одобренные отзывы
            query = select(Review).where(
                and_(
                    Review.target_type == target_type,
                    Review.target_id == target_id,
                    Review.status == 'approved',
                    Review.published_at.isnot(None)
                )
            ).order_by(Review.published_at.desc())
            
            result = await self.session.execute(query)
            all_reviews = result.scalars().all()
            
            # Исключаем отзывы с успешно обжалованными обжалованиями
            from domain.entities.review import ReviewAppeal
            reviews = []
            for review in all_reviews:
                appeal_query = select(ReviewAppeal).where(
                    and_(
                        ReviewAppeal.review_id == review.id,
                        ReviewAppeal.status == 'approved'
                    )
                )
                appeal_result = await self.session.execute(appeal_query)
                appeal = appeal_result.scalar_one_or_none()
                
                # Если обжалования нет или оно не одобрено, включаем отзыв
                if not appeal:
                    reviews.append(review)
            
            if not reviews:
                # Если отзывов нет, возвращаем начальный рейтинг
                return await self.get_or_create_rating(target_type, target_id)
            
            # Рассчитываем взвешенное среднее
            weighted_sum = 0.0
            total_weight = 0.0
            
            current_time = datetime.utcnow()
            
            for review in reviews:
                # Рассчитываем вес отзыва на основе времени
                weight = self._calculate_review_weight(review.published_at, current_time)
                
                # Добавляем к общей сумме
                weighted_sum += float(review.rating) * weight
                total_weight += weight
            
            if total_weight == 0:
                # Если все веса равны нулю (очень старые отзывы)
                average_rating = self.DEFAULT_RATING
            else:
                average_rating = weighted_sum / total_weight
            
            # Округляем до 0.5
            rounded_rating = round(average_rating * 2) / 2
            
            # Обновляем или создаем рейтинг
            rating = await self.get_or_create_rating(target_type, target_id)
            rating.average_rating = rounded_rating
            rating.total_reviews = len(reviews)
            rating.last_updated = current_time
            
            await self.session.commit()
            await self.session.refresh(rating)
            
            logger.info(f"Calculated rating for {target_type} {target_id}: {rounded_rating} from {len(reviews)} reviews")
            
            return rating
            
        except Exception as e:
            logger.error(f"Error calculating rating for {target_type} {target_id}: {e}")
            await self.session.rollback()
            return None
    
    def _calculate_review_weight(self, review_date: datetime, current_date: datetime) -> float:
        """
        Расчет веса отзыва на основе времени.
        
        Использует экспоненциальное затухание для учета "свежести" отзывов.
        
        Args:
            review_date: Дата публикации отзыва
            current_date: Текущая дата
            
        Returns:
            float: Вес отзыва (от 0 до 1)
        """
        # Вычисляем количество дней с момента публикации
        days_diff = (current_date - review_date).days
        
        # Если отзыв свежий (менее дня), вес = 1
        if days_diff <= 1:
            return 1.0
        
        # Экспоненциальное затухание
        # weight = e^(-ln(2) * days / half_life)
        weight = math.exp(-math.log(2) * days_diff / self.DECAY_HALF_LIFE_DAYS)
        
        # Минимальный вес - 0.1 (отзывы не теряют полностью свою значимость)
        return max(weight, 0.1)
    
    async def get_or_create_rating(self, target_type: str, target_id: int) -> Rating:
        """
        Получение существующего рейтинга или создание нового.
        
        Args:
            target_type: Тип цели
            target_id: ID цели
            
        Returns:
            Rating: Объект рейтинга
        """
        query = select(Rating).where(
            and_(
                Rating.target_type == target_type,
                Rating.target_id == target_id
            )
        )
        
        result = await self.session.execute(query)
        rating = result.scalar_one_or_none()
        
        if not rating:
            # Создаем новый рейтинг с начальным значением
            rating = Rating(
                target_type=target_type,
                target_id=target_id,
                average_rating=self.DEFAULT_RATING,
                total_reviews=0
            )
            
            self.session.add(rating)
            await self.session.commit()
            await self.session.refresh(rating)
            
            logger.info(f"Created new rating for {target_type} {target_id}")
        
        return rating
    
    async def get_rating(self, target_type: str, target_id: int) -> Optional[Rating]:
        """
        Получение рейтинга без пересчета.
        
        Args:
            target_type: Тип цели
            target_id: ID цели
            
        Returns:
            Rating: Объект рейтинга или None
        """
        query = select(Rating).where(
            and_(
                Rating.target_type == target_type,
                Rating.target_id == target_id
            )
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multiple_ratings(self, targets: List[Tuple[str, int]]) -> Dict[Tuple[str, int], Rating]:
        """
        Получение рейтингов для множественных целей.
        
        Args:
            targets: Список кортежей (target_type, target_id)
            
        Returns:
            Dict: Словарь с рейтингами
        """
        if not targets:
            return {}
        
        # Формируем условия для поиска
        conditions = []
        for target_type, target_id in targets:
            conditions.append(
                and_(
                    Rating.target_type == target_type,
                    Rating.target_id == target_id
                )
            )
        
        # Объединяем условия через OR
        from sqlalchemy import or_
        query = select(Rating).where(or_(*conditions))
        
        result = await self.session.execute(query)
        ratings = result.scalars().all()
        
        # Формируем словарь результатов
        rating_dict = {}
        for rating in ratings:
            key = (rating.target_type, rating.target_id)
            rating_dict[key] = rating
        
        return rating_dict
    
    async def update_rating_after_review_change(self, review: Review) -> Optional[Rating]:
        """
        Обновление рейтинга после изменения отзыва.
        
        Args:
            review: Измененный отзыв
            
        Returns:
            Rating: Обновленный рейтинг
        """
        return await self.calculate_rating(review.target_type, review.target_id)
    
    async def get_top_rated(self, target_type: str, limit: int = 10) -> List[Rating]:
        """
        Получение топ рейтинговых объектов/сотрудников.
        
        Args:
            target_type: Тип цели
            limit: Количество записей
            
        Returns:
            List[Rating]: Список рейтингов
        """
        query = select(Rating).where(
            Rating.target_type == target_type
        ).order_by(
            Rating.average_rating.desc(),
            Rating.total_reviews.desc()
        ).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_rating_statistics(self, target_type: str, target_id: int) -> Dict[str, Any]:
        """
        Получение статистики рейтинга.
        
        Args:
            target_type: Тип цели
            target_id: ID цели
            
        Returns:
            Dict: Статистика рейтинга
        """
        # Получаем все одобренные отзывы
        query = select(Review).where(
            and_(
                Review.target_type == target_type,
                Review.target_id == target_id,
                Review.status == 'approved'
            )
        )
        
        result = await self.session.execute(query)
        all_reviews = result.scalars().all()
        
        # Исключаем отзывы с успешно обжалованными обжалованиями
        from domain.entities.review import ReviewAppeal
        reviews = []
        for review in all_reviews:
            appeal_query = select(ReviewAppeal).where(
                and_(
                    ReviewAppeal.review_id == review.id,
                    ReviewAppeal.status == 'approved'
                )
            )
            appeal_result = await self.session.execute(appeal_query)
            appeal = appeal_result.scalar_one_or_none()
            
            # Если обжалования нет или оно не одобрено, включаем отзыв
            if not appeal:
                reviews.append(review)
        
        if not reviews:
            return {
                "total_reviews": 0,
                "average_rating": self.DEFAULT_RATING,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
                "recent_reviews": 0
            }
        
        # Подсчитываем распределение рейтингов
        rating_distribution = {str(i): 0 for i in range(1, 6)}
        recent_reviews = 0
        
        current_time = datetime.utcnow()
        thirty_days_ago = current_time - timedelta(days=30)
        
        for review in reviews:
            # Распределение по звездам
            rating_key = str(int(float(review.rating)))
            rating_distribution[rating_key] += 1
            
            # Недавние отзывы (за последние 30 дней)
            if review.published_at and review.published_at >= thirty_days_ago:
                recent_reviews += 1
        
        # Средний рейтинг
        total_rating = sum(float(review.rating) for review in reviews)
        average_rating = total_rating / len(reviews)
        
        return {
            "total_reviews": len(reviews),
            "average_rating": round(average_rating, 2),
            "rating_distribution": rating_distribution,
            "recent_reviews": recent_reviews
        }
    
    def format_rating_display(self, rating: float) -> str:
        """
        Форматирование рейтинга для отображения.
        
        Args:
            rating: Рейтинг (от 1.0 до 5.0)
            
        Returns:
            str: Форматированный рейтинг
        """
        return f"{rating:.1f}"
    
    def get_star_rating(self, rating: float) -> Dict[str, Any]:
        """
        Получение информации о звездном рейтинге.
        
        Args:
            rating: Рейтинг (от 1.0 до 5.0)
            
        Returns:
            Dict: Информация о звездах
        """
        full_stars = int(rating)
        has_half_star = (rating - full_stars) >= 0.5
        empty_stars = 5 - full_stars - (1 if has_half_star else 0)
        
        return {
            "full_stars": full_stars,
            "has_half_star": has_half_star,
            "empty_stars": empty_stars,
            "rating": rating,
            "formatted": self.format_rating_display(rating)
        }
    
    async def recalculate_all_ratings(self, target_type: Optional[str] = None) -> int:
        """
        Пересчет всех рейтингов (для административных задач).
        
        Args:
            target_type: Тип цели для пересчета (если None, то все типы)
            
        Returns:
            int: Количество обновленных рейтингов
        """
        try:
            # Получаем все уникальные цели из отзывов
            query = select(Review.target_type, Review.target_id).distinct()
            
            if target_type:
                query = query.where(Review.target_type == target_type)
            
            result = await self.session.execute(query)
            targets = result.fetchall()
            
            updated_count = 0
            
            for target_type_val, target_id_val in targets:
                rating = await self.calculate_rating(target_type_val, target_id_val)
                if rating:
                    updated_count += 1
            
            logger.info(f"Recalculated {updated_count} ratings")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error recalculating ratings: {e}")
            await self.session.rollback()
            return 0
