"""
Упрощенные интеграционные тесты для API отзывов.
"""

import pytest
from fastapi.testclient import TestClient
from apps.web.app import app


class TestReviewAPISimple:
    """Упрощенные тесты для API отзывов."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент FastAPI."""
        return TestClient(app)
    
    def test_api_endpoints_exist(self, client):
        """Тест существования API endpoints."""
        # Проверяем, что endpoints возвращают 401 (не авторизован), а не 404 (не найден)
        endpoints = [
            "/api/reviews/my-reviews",
            "/api/reviews/available-targets/employee",
            "/api/reviews/available-targets/object",
            "/api/reviews/1",
            "/api/ratings/employee/1",
            "/api/ratings/top/employee",
            "/api/ratings/employee/1/statistics",
            "/api/appeals/my-appeals",
            "/api/appeals/details/1",
            "/api/reports/reviews/reviews-summary",
            "/api/reports/reviews/reviews-by-object?object_id=1",
            "/api/reports/reviews/reviews-by-employee?employee_id=1",
            "/api/reports/reviews/moderation-stats",
            "/api/media/limits",
            "/moderator/api/",
            "/moderator/api/reviews",
            "/moderator/api/appeals",
            "/moderator/api/statistics"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Должен возвращать 401 (не авторизован) или 422 (неверные параметры), но не 404
            assert response.status_code in [401, 422, 400], f"Endpoint {endpoint} returned {response.status_code}"
    
    def test_web_routes_exist(self, client):
        """Тест существования веб-роутов."""
        web_routes = [
            "/owner/reviews",
            "/employee/reviews", 
            "/manager/reviews",
            "/moderator/",
            "/moderator/reviews",
            "/moderator/appeals",
            "/moderator/statistics"
        ]
        
        for route in web_routes:
            response = client.get(route)
            # Должен возвращать 401 (не авторизован), но не 404
            assert response.status_code in [401, 302], f"Route {route} returned {response.status_code}"
    
    def test_post_endpoints_exist(self, client):
        """Тест существования POST endpoints."""
        post_endpoints = [
            ("/api/reviews/create", {"target_type": "employee", "target_id": 1, "contract_id": 1, "title": "Test", "rating": 5.0}),
            ("/api/appeals/create", {"review_id": 1, "appeal_reason": "Test"}),
            ("/api/media/upload/photo", {"file": ("test.jpg", b"fake", "image/jpeg")}),
            ("/moderator/api/reviews/1/moderate", {"status": "approved"}),
            ("/moderator/api/appeals/1/review", {"decision": "approved"})
        ]
        
        for endpoint, data in post_endpoints:
            if endpoint == "/api/media/upload/photo":
                response = client.post(endpoint, files=data)
            else:
                response = client.post(endpoint, json=data)
            
            # Должен возвращать 401 (не авторизован) или 422 (неверные данные), но не 404
            assert response.status_code in [401, 422, 400], f"POST {endpoint} returned {response.status_code}"
    
    def test_api_documentation_accessible(self, client):
        """Тест доступности документации API."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/redoc")
        assert response.status_code == 200
    
    def test_health_check(self, client):
        """Тест проверки здоровья приложения."""
        response = client.get("/health")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
