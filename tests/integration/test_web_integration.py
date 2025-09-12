"""Интеграционные тесты для веб-интерфейса."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.app import app
from apps.web.middleware.auth_middleware import require_owner_or_superadmin


class TestWebIntegration:
    """Интеграционные тесты веб-интерфейса."""
    
    @pytest.fixture
    def client(self):
        """Тестовый клиент."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth(self):
        """Мок аутентификации."""
        return {
            "id": 1220971779,
            "telegram_id": 1220971779,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "role": "owner"
        }
    
    @pytest.fixture
    def mock_db_session(self):
        """Мок сессии БД."""
        return AsyncMock(spec=AsyncSession)


class TestOwnerInterfaceIntegration:
    """Интеграционные тесты интерфейса владельца."""
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_dashboard_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции дашборда владельца."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/dashboard")
        assert response.status_code == 200
        assert "StaffProBot - Владелец" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_objects_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции управления объектами."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/objects")
        assert response.status_code == 200
        assert "Объекты" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_calendar_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции календаря."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/calendar")
        assert response.status_code == 200
        assert "Календарь" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_employees_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции управления сотрудниками."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/employees")
        assert response.status_code == 200
        assert "Сотрудники" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_shifts_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции управления сменами."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/shifts")
        assert response.status_code == 200
        assert "Управление сменами" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_reports_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции отчетов."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/reports")
        assert response.status_code == 200
        assert "Отчеты" in response.text
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_owner_profile_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции профиля."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/profile")
        assert response.status_code == 200
        assert "Профиль" in response.text


class TestNavigationIntegration:
    """Интеграционные тесты навигации."""
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_navigation_menu_consistency(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест консистентности навигационного меню."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        # Проверяем что на всех страницах есть одинаковое меню
        pages = [
            "/owner/dashboard",
            "/owner/objects",
            "/owner/calendar",
            "/owner/employees",
            "/owner/shifts",
            "/owner/reports",
            "/owner/profile"
        ]
        
        for page in pages:
            response = client.get(page)
            assert response.status_code == 200
            
            # Проверяем наличие основных пунктов меню
            assert "Дашборд" in response.text
            assert "Объекты" in response.text
            assert "Календарь" in response.text
            assert "Сотрудники" in response.text
            assert "Смены" in response.text
            assert "Отчеты" in response.text


class TestErrorHandlingIntegration:
    """Интеграционные тесты обработки ошибок."""
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_timeslot_create_redirect_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции редиректа при создании тайм-слотов."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем что объект не найден, но есть другие объекты
        mock_object = Mock()
        mock_object.id = 1
        mock_object.name = "Test Object"
        
        mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [
            None,  # get_object_by_id - объект не найден
            [mock_object]  # get_objects_by_owner - есть другие объекты
        ]
        
        # Тестируем редирект
        response = client.get("/owner/timeslots/object/999/create", follow_redirects=False)
        assert response.status_code == 302
        assert "/owner/timeslots/object/1/create" in response.headers["location"]
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_timeslot_create_no_objects_integration(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест интеграции создания тайм-слотов без объектов."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем что объект не найден и нет других объектов
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        # Тестируем ошибку
        response = client.get("/owner/timeslots/object/999/create")
        assert response.status_code == 404
        assert "У вас нет объектов" in response.text


class TestAPIIntegration:
    """Интеграционные тесты API."""
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_calendar_api_timeslots_status(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест API статуса тайм-слотов."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/calendar/api/timeslots-status?year=2025&month=1")
        assert response.status_code == 200
        
        data = response.json()
        assert "timeslots" in data
        assert "total" in data
    
    @patch('apps.web.middleware.auth_middleware.require_owner_or_superadmin')
    @patch('core.database.session.get_db_session')
    def test_calendar_api_objects(self, mock_db, mock_auth, client, mock_auth, mock_db_session):
        """Тест API объектов календаря."""
        mock_auth.return_value = mock_auth
        mock_db.return_value = mock_db_session
        
        # Мокаем запросы к БД
        mock_db_session.execute.return_value.scalars.return_value.all.return_value = []
        
        response = client.get("/owner/calendar/api/objects")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
