"""
Unit тесты для сервисов отзывов и рейтингов.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from shared.services.rating_service import RatingService
from shared.services.moderation_service import ModerationService
from shared.services.appeal_service import AppealService
from shared.services.review_permission_service import ReviewPermissionService
from domain.entities.review import Review, ReviewStatus, AppealStatus, Rating, ReviewAppeal


class TestRatingService:
    """Тесты для RatingService."""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def rating_service(self, mock_db):
        """Экземпляр RatingService."""
        return RatingService(mock_db)
    
    @pytest.mark.asyncio
    async def test_calculate_weighted_average_rating(self, rating_service):
        """Тест расчета взвешенного среднего рейтинга."""
        # Мокаем данные отзывов
        mock_reviews = [
            MagicMock(rating=5.0, created_at=datetime.utcnow() - timedelta(days=30)),
            MagicMock(rating=4.0, created_at=datetime.utcnow() - timedelta(days=60)),
            MagicMock(rating=3.0, created_at=datetime.utcnow() - timedelta(days=120)),
        ]
        
        # Мокаем результат запроса
        rating_service.db.execute.return_value.scalars.return_value.all.return_value = mock_reviews
        
        # Вызываем метод
        avg_rating, total_reviews = await rating_service._calculate_weighted_average_rating(
            "employee", 1
        )
        
        # Проверяем результат
        assert total_reviews == 3
        assert 3.0 <= avg_rating <= 5.0  # Средний рейтинг должен быть в разумных пределах
    
    @pytest.mark.asyncio
    async def test_get_star_rating(self, rating_service):
        """Тест получения звездного рейтинга."""
        # Тест полных звезд
        stars = rating_service.get_star_rating(5.0)
        assert stars["full_stars"] == 5
        assert stars["half_stars"] == 0
        assert stars["empty_stars"] == 0
        
        # Тест половины звезды
        stars = rating_service.get_star_rating(4.5)
        assert stars["full_stars"] == 4
        assert stars["half_stars"] == 1
        assert stars["empty_stars"] == 0
        
        # Тест пустых звезд
        stars = rating_service.get_star_rating(2.0)
        assert stars["full_stars"] == 2
        assert stars["half_stars"] == 0
        assert stars["empty_stars"] == 3


class TestModerationService:
    """Тесты для ModerationService."""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def moderation_service(self, mock_db):
        """Экземпляр ModerationService."""
        return ModerationService(mock_db)
    
    @pytest.mark.asyncio
    async def test_check_for_spam(self, moderation_service):
        """Тест проверки на спам."""
        # Тест спама
        spam_content = "Купите сейчас! Скидка 50%! http://spam.com"
        assert await moderation_service._check_for_spam(spam_content) == True
        
        # Тест нормального контента
        normal_content = "Отличный сотрудник, рекомендую!"
        assert await moderation_service._check_for_spam(normal_content) == False
    
    @pytest.mark.asyncio
    async def test_check_for_profanity(self, moderation_service):
        """Тест проверки на нецензурную лексику."""
        # Тест нецензурной лексики
        profanity_content = "Этот сотрудник полное дерьмо!"
        assert await moderation_service._check_for_profanity(profanity_content) == True
        
        # Тест нормального контента
        normal_content = "Хороший работник, спасибо за работу!"
        assert await moderation_service._check_for_profanity(normal_content) == False
    
    @pytest.mark.asyncio
    async def test_check_content_length(self, moderation_service):
        """Тест проверки длины контента."""
        # Тест короткого контента
        short_content = "Ок"
        assert await moderation_service._check_content_length(short_content) == False
        
        # Тест достаточной длины
        long_content = "Этот сотрудник показал отличные результаты в работе. Очень ответственный и пунктуальный."
        assert await moderation_service._check_content_length(long_content) == True


class TestAppealService:
    """Тесты для AppealService."""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def appeal_service(self, mock_db):
        """Экземпляр AppealService."""
        return AppealService(mock_db)
    
    @pytest.mark.asyncio
    async def test_check_appeal_eligibility(self, appeal_service):
        """Тест проверки права на обжалование."""
        # Мокаем отзыв
        mock_review = MagicMock()
        mock_review.status = ReviewStatus.REJECTED.value
        mock_review.created_at = datetime.utcnow() - timedelta(days=1)
        
        # Мокаем результат запроса
        appeal_service.db.execute.return_value.scalar_one_or_none.return_value = mock_review
        
        # Проверяем право на обжалование
        eligibility = await appeal_service.check_appeal_eligibility(1, 1)
        
        assert eligibility["can_appeal"] == True
        assert "reason" in eligibility
    
    @pytest.mark.asyncio
    async def test_check_appeal_eligibility_already_appealed(self, appeal_service):
        """Тест проверки права на обжалование - уже обжаловано."""
        # Мокаем отзыв
        mock_review = MagicMock()
        mock_review.status = ReviewStatus.REJECTED.value
        mock_review.created_at = datetime.utcnow() - timedelta(days=1)
        
        # Мокаем существующее обжалование
        mock_appeal = MagicMock()
        
        # Мокаем результаты запросов
        appeal_service.db.execute.return_value.scalar_one_or_none.side_effect = [mock_review, mock_appeal]
        
        # Проверяем право на обжалование
        eligibility = await appeal_service.check_appeal_eligibility(1, 1)
        
        assert eligibility["can_appeal"] == False
        assert "уже обжалован" in eligibility["reason"]


class TestReviewPermissionService:
    """Тесты для ReviewPermissionService."""
    
    @pytest.fixture
    def mock_db(self):
        """Мок базы данных."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def permission_service(self, mock_db):
        """Экземпляр ReviewPermissionService."""
        return ReviewPermissionService(mock_db)
    
    @pytest.mark.asyncio
    async def test_can_create_review_valid(self, permission_service):
        """Тест проверки прав на создание отзыва - валидный случай."""
        # Мокаем договор
        mock_contract = MagicMock()
        mock_contract.owner_id = 1
        mock_contract.employee_id = 2
        mock_contract.status = "active"
        
        # Мокаем результаты запросов
        permission_service._get_contract.return_value = mock_contract
        permission_service._is_target_linked_to_contract.return_value = True
        permission_service._get_existing_review.return_value = None
        permission_service._check_target_permissions.return_value = True
        
        # Проверяем права
        result = await permission_service.can_create_review(1, "employee", 2, 1)
        
        assert result["can_create"] == True
        assert result["reason"] == "Все проверки пройдены"
    
    @pytest.mark.asyncio
    async def test_can_create_review_contract_not_found(self, permission_service):
        """Тест проверки прав на создание отзыва - договор не найден."""
        # Мокаем отсутствие договора
        permission_service._get_contract.return_value = None
        
        # Проверяем права
        result = await permission_service.can_create_review(1, "employee", 2, 1)
        
        assert result["can_create"] == False
        assert result["reason"] == "Договор не найден"
    
    @pytest.mark.asyncio
    async def test_can_create_review_user_not_participant(self, permission_service):
        """Тест проверки прав на создание отзыва - пользователь не участник."""
        # Мокаем договор
        mock_contract = MagicMock()
        mock_contract.owner_id = 1
        mock_contract.employee_id = 2
        mock_contract.status = "active"
        
        # Мокаем результаты запросов
        permission_service._get_contract.return_value = mock_contract
        
        # Проверяем права (пользователь 3 не участвует в договоре)
        result = await permission_service.can_create_review(3, "employee", 2, 1)
        
        assert result["can_create"] == False
        assert result["reason"] == "Пользователь не участвует в данном договоре"
    
    @pytest.mark.asyncio
    async def test_can_create_review_contract_inactive(self, permission_service):
        """Тест проверки прав на создание отзыва - неактивный договор."""
        # Мокаем договор
        mock_contract = MagicMock()
        mock_contract.owner_id = 1
        mock_contract.employee_id = 2
        mock_contract.status = "draft"  # Неактивный статус
        
        # Мокаем результаты запросов
        permission_service._get_contract.return_value = mock_contract
        
        # Проверяем права
        result = await permission_service.can_create_review(1, "employee", 2, 1)
        
        assert result["can_create"] == False
        assert result["reason"] == "Отзыв можно оставить только по завершенному или активному договору"
    
    @pytest.mark.asyncio
    async def test_can_create_review_already_exists(self, permission_service):
        """Тест проверки прав на создание отзыва - отзыв уже существует."""
        # Мокаем договор
        mock_contract = MagicMock()
        mock_contract.owner_id = 1
        mock_contract.employee_id = 2
        mock_contract.status = "active"
        
        # Мокаем существующий отзыв
        mock_existing_review = MagicMock()
        mock_existing_review.id = 123
        
        # Мокаем результаты запросов
        permission_service._get_contract.return_value = mock_contract
        permission_service._is_target_linked_to_contract.return_value = True
        permission_service._get_existing_review.return_value = mock_existing_review
        
        # Проверяем права
        result = await permission_service.can_create_review(1, "employee", 2, 1)
        
        assert result["can_create"] == False
        assert result["reason"] == "Отзыв по данному договору уже оставлен"
        assert result["existing_review_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__])
