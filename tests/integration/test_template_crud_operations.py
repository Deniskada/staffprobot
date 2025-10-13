"""
Integration тесты для CRUD операций с шаблонами уведомлений
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime
import json

from apps.web.app import app
from domain.entities.notification_template import NotificationTemplate
from domain.entities.notification import NotificationType, NotificationChannel


class TestTemplateCRUDOperations:
    """Integration тесты для CRUD операций с шаблонами"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_superadmin_user(self):
        """Мок суперадмина"""
        return {
            "id": 1,
            "telegram_id": 123456789,
            "role": "superadmin",
            "is_active": True
        }

    @pytest.fixture
    def sample_template_data(self):
        """Образец данных шаблона для создания"""
        return {
            "template_key": "test_shift_reminder",
            "name": "Test Shift Reminder",
            "description": "Test shift reminder template",
            "type": "SHIFT_REMINDER",
            "channel": "TELEGRAM",
            "subject_template": "Напоминание о смене",
            "plain_template": "Уважаемый $user_name! У вас смена на объекте $object_name в $shift_time.",
            "html_template": "<p>Уважаемый <strong>$user_name</strong>! У вас смена на объекте <strong>$object_name</strong> в <strong>$shift_time</strong>.</p>",
            "variables": ["user_name", "object_name", "shift_time"]
        }

    @pytest.fixture
    def created_template(self, sample_template_data):
        """Образец созданного шаблона"""
        return NotificationTemplate(
            id=1,
            template_key=sample_template_data["template_key"],
            name=sample_template_data["name"],
            description=sample_template_data["description"],
            type=NotificationType.SHIFT_REMINDER,
            channel=NotificationChannel.TELEGRAM,
            subject_template=sample_template_data["subject_template"],
            plain_template=sample_template_data["plain_template"],
            html_template=sample_template_data["html_template"],
            variables=json.dumps(sample_template_data["variables"]),
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_create_template_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user, sample_template_data, created_template):
        """Тест успешного создания шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.create_template.return_value = created_template

            # Act
            response = client.post("/admin/notifications/api/templates/create", json=sample_template_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "created" in data["message"].lower()
            assert data["template"]["id"] == 1
            assert data["template"]["template_key"] == "test_shift_reminder"

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_create_template_duplicate_key(self, mock_get_db_session, mock_require_superadmin, 
                                               client, mock_superadmin_user, sample_template_data):
        """Тест создания шаблона с дублирующимся ключом"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.create_template.side_effect = ValueError("Template with key 'test_shift_reminder' already exists")

            # Act
            response = client.post("/admin/notifications/api/templates/create", json=sample_template_data)

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "already exists" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_create_template_missing_required_fields(self, mock_get_db_session, mock_require_superadmin, 
                                                         client, mock_superadmin_user):
        """Тест создания шаблона с отсутствующими обязательными полями"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        invalid_data = {
            "template_key": "test_template"
            # Отсутствуют обязательные поля
        }

        # Act
        response = client.post("/admin/notifications/api/templates/create", json=invalid_data)

        # Assert
        assert response.status_code == 422  # Validation error

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_update_template_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user, created_template):
        """Тест успешного обновления шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Обновленный шаблон
            updated_template = created_template
            updated_template.name = "Updated Test Shift Reminder"
            updated_template.description = "Updated description"
            updated_template.plain_template = "Updated message for $user_name"
            updated_template.variables = '["user_name", "object_name", "shift_time", "location"]'
            
            mock_service.update_template.return_value = updated_template

            update_data = {
                "name": "Updated Test Shift Reminder",
                "description": "Updated description",
                "plain_template": "Updated message for $user_name",
                "variables": ["user_name", "object_name", "shift_time", "location"]
            }

            # Act
            response = client.post("/admin/notifications/api/templates/edit/1", json=update_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "updated" in data["message"].lower()
            assert data["template"]["name"] == "Updated Test Shift Reminder"

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_update_template_not_found(self, mock_get_db_session, mock_require_superadmin, 
                                           client, mock_superadmin_user):
        """Тест обновления несуществующего шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.update_template.side_effect = ValueError("Template with ID 999 not found")

            update_data = {"name": "Updated Template"}

            # Act
            response = client.post("/admin/notifications/api/templates/edit/999", json=update_data)

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "not found" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_update_default_template(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест обновления дефолтного шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.update_template.side_effect = ValueError("Cannot update default template")

            update_data = {"name": "Updated Template"}

            # Act
            response = client.post("/admin/notifications/api/templates/edit/1", json=update_data)

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "Cannot update default template" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_delete_template_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест успешного удаления шаблона (деактивация)"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.delete_template.return_value = None

            # Act
            response = client.post("/admin/notifications/api/templates/delete/1")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "деактивирован" in data["message"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_delete_template_not_found(self, mock_get_db_session, mock_require_superadmin, 
                                           client, mock_superadmin_user):
        """Тест удаления несуществующего шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.delete_template.side_effect = ValueError("Template with ID 999 not found")

            # Act
            response = client.post("/admin/notifications/api/templates/delete/999")

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "not found" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_delete_default_template(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест удаления дефолтного шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.delete_template.side_effect = ValueError("Cannot delete default template")

            # Act
            response = client.post("/admin/notifications/api/templates/delete/1")

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "Cannot delete default template" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_restore_template_success(self, mock_get_db_session, mock_require_superadmin, 
                                          client, mock_superadmin_user):
        """Тест успешного восстановления шаблона (активация)"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.restore_template.return_value = None

            # Act
            response = client.post("/admin/notifications/api/templates/restore/1")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "восстановлён" in data["message"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_restore_template_not_found(self, mock_get_db_session, mock_require_superadmin, 
                                            client, mock_superadmin_user):
        """Тест восстановления несуществующего шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.restore_template.side_effect = ValueError("Template with ID 999 not found")

            # Act
            response = client.post("/admin/notifications/api/templates/restore/999")

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "not found" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_hard_delete_template_success(self, mock_get_db_session, mock_require_superadmin, 
                                              client, mock_superadmin_user):
        """Тест жёсткого удаления шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.hard_delete_template.return_value = None

            # Act
            response = client.post("/admin/notifications/api/templates/delete/1?hard_delete=true")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "удалён из базы данных" in data["message"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_toggle_template_activity_success(self, mock_get_db_session, mock_require_superadmin, 
                                                  client, mock_superadmin_user, created_template):
        """Тест переключения активности шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            
            # Переключаем активность
            created_template.is_active = False
            mock_service.toggle_template_activity.return_value = created_template

            # Act
            response = client.post("/admin/notifications/api/templates/toggle/1")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["template"]["is_active"] is False

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_get_template_by_id_success(self, mock_get_db_session, mock_require_superadmin, 
                                            client, mock_superadmin_user, created_template):
        """Тест получения шаблона по ID"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_template_by_id.return_value = created_template

            # Act
            response = client.get("/admin/notifications/api/templates/1")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["template"]["id"] == 1
            assert data["template"]["template_key"] == "test_shift_reminder"

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_get_template_by_id_not_found(self, mock_get_db_session, mock_require_superadmin, 
                                              client, mock_superadmin_user):
        """Тест получения несуществующего шаблона по ID"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_template_by_id.return_value = None

            # Act
            response = client.get("/admin/notifications/api/templates/999")

            # Assert
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_get_templates_list_success(self, mock_get_db_session, mock_require_superadmin, 
                                            client, mock_superadmin_user, created_template):
        """Тест получения списка шаблонов"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_templates_paginated.return_value = ([created_template], 1)

            # Act
            response = client.get("/admin/notifications/api/templates")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["templates"]) == 1
            assert data["total_count"] == 1

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_get_templates_list_with_filters(self, mock_get_db_session, mock_require_superadmin, 
                                                  client, mock_superadmin_user, created_template):
        """Тест получения списка шаблонов с фильтрами"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_templates_paginated.return_value = ([created_template], 1)

            # Act
            response = client.get("/admin/notifications/api/templates?type_filter=SHIFT_REMINDER&is_active=true&page=1&per_page=20")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert len(data["templates"]) == 1

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_database_error_handling(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест обработки ошибок базы данных"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.create_template.side_effect = Exception("Database connection failed")

            template_data = {
                "template_key": "test_template",
                "name": "Test Template",
                "type": "SHIFT_REMINDER",
                "channel": "TELEGRAM",
                "subject_template": "Test Subject",
                "plain_template": "Test message",
                "html_template": "<p>Test HTML</p>",
                "variables": []
            }

            # Act
            response = client.post("/admin/notifications/api/templates/create", json=template_data)

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Ошибка создания шаблона" in data["detail"]
