"""
Интеграционные тесты для API отзывов и рейтингов.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from apps.web.app import app
from core.database.session import get_db_session
from domain.entities.user import User, UserRole
from domain.entities.contract import Contract
from domain.entities.review import Review, ReviewStatus


class TestReviewAPI:
    """Тесты для API отзывов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Мок пользователя."""
        user = MagicMock()
        user.id = 1
        user.telegram_id = 123456789
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        user.role = UserRole.EMPLOYEE.value
        return user
    
    @pytest.fixture
    def mock_contract(self):
        """Мок договора."""
        contract = MagicMock()
        contract.id = 1
        contract.owner_id = 1
        contract.employee_id = 2
        contract.status = "active"
        contract.contract_number = "CONTRACT-001"
        contract.title = "Test Contract"
        return contract
    
    def test_get_available_targets_unauthorized(self, client):
        """Тест получения доступных целей без авторизации."""
        response = client.get("/api/reviews/available-targets/employee")
        assert response.status_code == 401
    
    def test_get_my_reviews_unauthorized(self, client):
        """Тест получения моих отзывов без авторизации."""
        response = client.get("/api/reviews/my-reviews")
        assert response.status_code == 401
    
    def test_create_review_unauthorized(self, client):
        """Тест создания отзыва без авторизации."""
        data = {
            "target_type": "employee",
            "target_id": 1,
            "contract_id": 1,
            "title": "Test Review",
            "rating": 5.0,
            "content": "Great employee!",
            "is_anonymous": False
        }
        response = client.post("/api/reviews/create", data=data)
        assert response.status_code == 401
    
    def test_get_review_details_unauthorized(self, client):
        """Тест получения деталей отзыва без авторизации."""
        response = client.get("/api/reviews/1")
        assert response.status_code == 401


class TestRatingAPI:
    """Тесты для API рейтингов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_get_rating_unauthorized(self, client):
        """Тест получения рейтинга без авторизации."""
        response = client.get("/api/ratings/employee/1")
        assert response.status_code == 401
    
    def test_get_top_rated_unauthorized(self, client):
        """Тест получения топ рейтингов без авторизации."""
        response = client.get("/api/ratings/top/employee")
        assert response.status_code == 401
    
    def test_get_rating_statistics_unauthorized(self, client):
        """Тест получения статистики рейтинга без авторизации."""
        response = client.get("/api/ratings/employee/1/statistics")
        assert response.status_code == 401


class TestAppealAPI:
    """Тесты для API обжалований."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_create_appeal_unauthorized(self, client):
        """Тест создания обжалования без авторизации."""
        data = {
            "review_id": 1,
            "appeal_reason": "Unfair rejection",
            "appeal_evidence": "Evidence here"
        }
        response = client.post("/api/appeals/create", data=data)
        assert response.status_code == 401
    
    def test_get_my_appeals_unauthorized(self, client):
        """Тест получения моих обжалований без авторизации."""
        response = client.get("/api/appeals/my-appeals")
        assert response.status_code == 401
    
    def test_get_appeal_details_unauthorized(self, client):
        """Тест получения деталей обжалования без авторизации."""
        response = client.get("/api/appeals/details/1")
        assert response.status_code == 401


class TestModeratorAPI:
    """Тесты для API модерации."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_get_moderator_dashboard_unauthorized(self, client):
        """Тест получения дашборда модератора без авторизации."""
        response = client.get("/moderator/api/")
        assert response.status_code == 401
    
    def test_get_pending_reviews_unauthorized(self, client):
        """Тест получения отзывов на модерации без авторизации."""
        response = client.get("/moderator/api/reviews")
        assert response.status_code == 401
    
    def test_moderate_review_unauthorized(self, client):
        """Тест модерации отзыва без авторизации."""
        data = {
            "status": "approved",
            "moderation_notes": "Good review"
        }
        response = client.post("/moderator/api/reviews/1/moderate", json=data)
        assert response.status_code == 401


class TestReviewReportsAPI:
    """Тесты для API отчетов по отзывам."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_get_reviews_summary_unauthorized(self, client):
        """Тест получения сводного отчета без авторизации."""
        response = client.get("/api/reports/reviews/reviews-summary")
        assert response.status_code == 401
    
    def test_get_reviews_by_object_unauthorized(self, client):
        """Тест получения отзывов по объекту без авторизации."""
        response = client.get("/api/reports/reviews/reviews-by-object?object_id=1")
        assert response.status_code == 401
    
    def test_get_reviews_by_employee_unauthorized(self, client):
        """Тест получения отзывов по сотруднику без авторизации."""
        response = client.get("/api/reports/reviews/reviews-by-employee?employee_id=1")
        assert response.status_code == 401
    
    def test_get_moderation_stats_unauthorized(self, client):
        """Тест получения статистики модерации без авторизации."""
        response = client.get("/api/reports/reviews/moderation-stats")
        assert response.status_code == 401


class TestMediaAPI:
    """Тесты для API медиа-файлов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_upload_media_unauthorized(self, client):
        """Тест загрузки медиа-файла без авторизации."""
        files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
        response = client.post("/api/media/upload/photo", files=files)
        assert response.status_code == 401
    
    def test_get_media_limits_unauthorized(self, client):
        """Тест получения лимитов медиа-файлов без авторизации."""
        response = client.get("/api/media/limits")
        assert response.status_code == 401


class TestWebRoutes:
    """Тесты для веб-роутов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_owner_reviews_page_unauthorized(self, client):
        """Тест страницы отзывов владельца без авторизации."""
        response = client.get("/owner/reviews")
        assert response.status_code == 401
    
    def test_employee_reviews_page_unauthorized(self, client):
        """Тест страницы отзывов сотрудника без авторизации."""
        response = client.get("/employee/reviews")
        assert response.status_code == 401
    
    def test_manager_reviews_page_unauthorized(self, client):
        """Тест страницы отзывов управляющего без авторизации."""
        response = client.get("/manager/reviews")
        assert response.status_code == 401
    
    def test_moderator_dashboard_unauthorized(self, client):
        """Тест дашборда модератора без авторизации."""
        response = client.get("/moderator/")
        assert response.status_code == 401
    
    def test_moderator_reviews_page_unauthorized(self, client):
        """Тест страницы отзывов модератора без авторизации."""
        response = client.get("/moderator/reviews")
        assert response.status_code == 401
    
    def test_moderator_appeals_page_unauthorized(self, client):
        """Тест страницы обжалований модератора без авторизации."""
        response = client.get("/moderator/appeals")
        assert response.status_code == 401


class TestAPIValidation:
    """Тесты валидации API."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_create_review_invalid_target_type(self, client):
        """Тест создания отзыва с недопустимым типом цели."""
        data = {
            "target_type": "invalid_type",
            "target_id": 1,
            "contract_id": 1,
            "title": "Test Review",
            "rating": 5.0,
            "content": "Great employee!",
            "is_anonymous": False
        }
        response = client.post("/api/reviews/create", data=data)
        assert response.status_code == 401  # Сначала проверка авторизации
    
    def test_create_review_invalid_rating(self, client):
        """Тест создания отзыва с недопустимым рейтингом."""
        data = {
            "target_type": "employee",
            "target_id": 1,
            "contract_id": 1,
            "title": "Test Review",
            "rating": 6.0,  # Недопустимый рейтинг
            "content": "Great employee!",
            "is_anonymous": False
        }
        response = client.post("/api/reviews/create", data=data)
        assert response.status_code == 401  # Сначала проверка авторизации
    
    def test_get_available_targets_invalid_type(self, client):
        """Тест получения доступных целей с недопустимым типом."""
        response = client.get("/api/reviews/available-targets/invalid_type")
        assert response.status_code == 401  # Сначала проверка авторизации


if __name__ == "__main__":
    pytest.main([__file__])
