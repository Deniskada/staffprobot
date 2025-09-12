"""Простые unit-тесты для веб-роутов."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from apps.web.routes.owner import router


class TestOwnerRoutesSimple:
    """Простые тесты для роутов владельца."""
    
    @pytest.fixture
    def app(self):
        """FastAPI приложение для тестов."""
        app = FastAPI()
        app.include_router(router, prefix="/owner")
        return app
    
    @pytest.fixture
    def client(self, app):
        """Тестовый клиент."""
        return TestClient(app)
    
    def test_router_import(self):
        """Тест импорта роутера."""
        assert router is not None
        assert hasattr(router, 'routes')
        assert len(router.routes) > 0
    
    def test_router_prefix(self):
        """Тест префикса роутера."""
        assert router.prefix == "/owner"
    
    def test_router_tags(self):
        """Тест тегов роутера."""
        assert "owner" in router.tags
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_dashboard_redirect(self, mock_auth, client):
        """Тест редиректа с /owner/ на /owner/dashboard."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/")
            assert response.status_code == 200
            assert "StaffProBot - Владелец" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_objects_list(self, mock_auth, client):
        """Тест списка объектов."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/objects")
            assert response.status_code == 200
            assert "Объекты" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_calendar(self, mock_auth, client):
        """Тест календаря."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/calendar")
            assert response.status_code == 200
            assert "Календарь" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_employees(self, mock_auth, client):
        """Тест сотрудников."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/employees")
            assert response.status_code == 200
            assert "Сотрудники" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_shifts(self, mock_auth, client):
        """Тест смен."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/shifts")
            assert response.status_code == 200
            assert "Управление сменами" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_reports(self, mock_auth, client):
        """Тест отчетов."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/reports")
            assert response.status_code == 200
            assert "Отчеты" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_owner_profile(self, mock_auth, client):
        """Тест профиля."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/profile")
            assert response.status_code == 200
            assert "Профиль" in response.text


class TestOwnerAPISimple:
    """Простые тесты для API роутов."""
    
    @pytest.fixture
    def app(self):
        """FastAPI приложение для тестов."""
        app = FastAPI()
        app.include_router(router, prefix="/owner")
        return app
    
    @pytest.fixture
    def client(self, app):
        """Тестовый клиент."""
        return TestClient(app)
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_calendar_api_objects(self, mock_auth, client):
        """Тест API объектов календаря."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/calendar/api/objects")
            assert response.status_code == 200
            assert isinstance(response.json(), list)
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    def test_calendar_api_timeslots_status(self, mock_auth, client):
        """Тест API статуса тайм-слотов."""
        mock_auth.return_value = {"id": 1220971779, "role": "owner"}
        
        with patch('core.database.session.get_db_session'):
            response = client.get("/owner/calendar/api/timeslots-status?year=2025&month=1")
            assert response.status_code == 200
            
            data = response.json()
            assert "timeslots" in data
            assert "total" in data
