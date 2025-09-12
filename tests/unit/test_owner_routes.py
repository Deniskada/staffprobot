"""Unit тесты для веб-роутов владельца (owner.py)."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, date

from apps.web.routes.owner import router
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.time_slot import TimeSlot


class TestOwnerRoutes:
    """Тесты для роутов владельца."""
    
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
    
    @pytest.fixture
    def mock_current_user(self):
        """Мок текущего пользователя."""
        return {
            "id": 1220971779,
            "telegram_id": 1220971779,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "role": "owner"
        }
    
    @pytest.fixture
    def mock_user_entity(self):
        """Мок сущности пользователя."""
        user = Mock(spec=User)
        user.id = 1
        user.telegram_id = 1220971779
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"
        user.role = "owner"
        return user
    
    @pytest.fixture
    def mock_object_entity(self):
        """Мок сущности объекта."""
        obj = Mock(spec=Object)
        obj.id = 1
        obj.name = "Test Object"
        obj.address = "Test Address"
        obj.owner_id = 1
        obj.hourly_rate = 100.0
        obj.opening_time = datetime.strptime("09:00", "%H:%M").time()
        obj.closing_time = datetime.strptime("18:00", "%H:%M").time()
        obj.is_active = True
        return obj
    
    @pytest.fixture
    def mock_shift_entity(self):
        """Мок сущности смены."""
        shift = Mock(spec=Shift)
        shift.id = 1
        shift.object_id = 1
        shift.user_id = 1
        shift.start_time = datetime.now()
        shift.end_time = datetime.now()
        shift.status = "active"
        shift.type = "shift"
        return shift
    
    @pytest.fixture
    def mock_timeslot_entity(self):
        """Мок сущности тайм-слота."""
        timeslot = Mock(spec=TimeSlot)
        timeslot.id = 1
        timeslot.object_id = 1
        timeslot.start_time = datetime.now()
        timeslot.end_time = datetime.now()
        timeslot.hourly_rate = 100.0
        timeslot.is_active = True
        return timeslot


class TestOwnerDashboard:
    """Тесты для дашборда владельца."""
    
    def test_owner_dashboard_redirect(self, client):
        """Тест редиректа с /owner/ на /owner/dashboard."""
        response = client.get("/owner/")
        assert response.status_code == 200
        assert "StaffProBot - Владелец" in response.text
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    def test_owner_dashboard_with_auth(self, mock_auth, client, mock_current_user):
        """Тест дашборда с аутентификацией."""
        mock_auth.return_value = mock_current_user
        
        with patch('apps.web.routes.owner.get_db_session') as mock_db:
            mock_session = AsyncMock(spec=AsyncSession)
            mock_db.return_value = mock_session
            
            response = client.get("/owner/dashboard")
            assert response.status_code == 200


class TestOwnerObjects:
    """Тесты для управления объектами."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_owner_objects_list(self, mock_db, mock_auth, client, mock_current_user, mock_object_entity):
        """Тест списка объектов владельца."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_object_entity]
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/objects")
            assert response.status_code == 200
            assert "Объекты" in response.text
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_owner_objects_create_form(self, mock_db, mock_auth, client, mock_current_user):
        """Тест формы создания объекта."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        response = client.get("/owner/objects/create")
        assert response.status_code == 200
        assert "Создание объекта" in response.text


class TestOwnerTimeslots:
    """Тесты для управления тайм-слотами."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_timeslot_create_form(self, mock_db, mock_auth, client, mock_current_user, mock_object_entity):
        """Тест формы создания тайм-слота."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем ObjectService
        with patch('apps.web.routes.owner.ObjectService') as mock_service:
            mock_service_instance = Mock()
            mock_service_instance.get_object_by_id.return_value = mock_object_entity
            mock_service.return_value = mock_service_instance
            
            response = client.get("/owner/timeslots/object/1/create")
            assert response.status_code == 200
            assert "Создание тайм-слота" in response.text
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_timeslot_create_redirect_on_invalid_object(self, mock_db, mock_auth, client, mock_current_user, mock_object_entity):
        """Тест редиректа при создании тайм-слота с несуществующего объекта."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем ObjectService - объект не найден, но есть другие объекты
        with patch('apps.web.routes.owner.ObjectService') as mock_service:
            mock_service_instance = Mock()
            mock_service_instance.get_object_by_id.return_value = None  # Объект не найден
            mock_service_instance.get_objects_by_owner.return_value = [mock_object_entity]  # Есть другие объекты
            mock_service.return_value = mock_service_instance
            
            response = client.get("/owner/timeslots/object/999/create", follow_redirects=False)
            assert response.status_code == 302  # Редирект на первый объект


class TestOwnerShifts:
    """Тесты для управления сменами."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_shifts_list(self, mock_db, mock_auth, client, mock_current_user, mock_shift_entity):
        """Тест списка смен."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_shift_entity]
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/shifts")
            assert response.status_code == 200
            assert "Управление сменами" in response.text


class TestOwnerEmployees:
    """Тесты для управления сотрудниками."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_employees_list(self, mock_db, mock_auth, client, mock_current_user):
        """Тест списка сотрудников."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/employees")
            assert response.status_code == 200
            assert "Сотрудники" in response.text


class TestOwnerCalendar:
    """Тесты для календаря."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_calendar_view(self, mock_db, mock_auth, client, mock_current_user, mock_object_entity):
        """Тест календарного представления."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = [mock_object_entity]
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/calendar")
            assert response.status_code == 200
            assert "Календарь" in response.text


class TestOwnerReports:
    """Тесты для отчетов."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_reports_view(self, mock_db, mock_auth, client, mock_current_user):
        """Тест страницы отчетов."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/reports")
            assert response.status_code == 200
            assert "Отчеты" in response.text


class TestOwnerProfile:
    """Тесты для профиля владельца."""
    
    @patch('apps.web.routes.owner.require_owner_or_superadmin')
    @patch('apps.web.routes.owner.get_db_session')
    def test_profile_view(self, mock_db, mock_auth, client, mock_current_user):
        """Тест страницы профиля."""
        mock_auth.return_value = mock_current_user
        mock_session = AsyncMock(spec=AsyncSession)
        mock_db.return_value = mock_session
        
        # Мокаем запросы к БД
        with patch('apps.web.routes.owner.select') as mock_select:
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            
            response = client.get("/owner/profile")
            assert response.status_code == 200
            assert "Профиль" in response.text
