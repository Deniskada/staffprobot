"""
Integration тесты для admin_notifications.py роутов
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json

from apps.web.app import app
from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
from domain.entities.notification_template import NotificationTemplate


class TestAdminNotificationsRoutes:
    """Integration тесты для админских роутов уведомлений"""

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
    def sample_notification(self):
        """Образец уведомления для тестов"""
        return Notification(
            id=1,
            user_id=123,
            type=NotificationType.SHIFT_REMINDER,
            channel=NotificationChannel.TELEGRAM,
            priority=NotificationPriority.NORMAL,
            status=NotificationStatus.SENT,
            title="Напоминание о смене",
            message="У вас смена через 2 часа",
            created_at=datetime.now(),
            sent_at=datetime.now() + timedelta(minutes=1)
        )

    @pytest.fixture
    def sample_template(self):
        """Образец шаблона для тестов"""
        return NotificationTemplate(
            id=1,
            template_key="test_template",
            name="Test Template",
            description="Test description",
            type=NotificationType.SHIFT_REMINDER,
            channel=NotificationChannel.TELEGRAM,
            subject_template="Test Subject",
            plain_template="Test plain message",
            html_template="<p>Test HTML message</p>",
            variables='["user_name", "object_name"]',
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_dashboard_route_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест успешного доступа к дашборду"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        # Мокаем сервис
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_notification_statistics.return_value = {
                "total_notifications": 100,
                "sent_notifications": 80,
                "delivery_rate": 0.8
            }
            mock_service.get_channel_statistics.return_value = {
                "telegram": 50,
                "email": 30,
                "sms": 20
            }
            mock_service.get_type_statistics.return_value = {
                "SHIFT_REMINDER": 25,
                "CONTRACT_SIGNED": 20
            }
            mock_service.get_daily_statistics.return_value = [
                {"date": "2025-10-14", "sent": 10, "delivered": 8, "failed": 2}
            ]
            mock_service.get_recent_notifications.return_value = []

            # Act
            response = client.get("/admin/notifications/")

            # Assert
            assert response.status_code == 200
            assert "Дашборд уведомлений" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_dashboard_route_unauthorized(self, mock_get_db_session, mock_require_superadmin, client):
        """Тест доступа к дашборду без авторизации"""
        # Arrange
        mock_require_superadmin.side_effect = Exception("Unauthorized")

        # Act
        response = client.get("/admin/notifications/")

        # Assert
        assert response.status_code == 401

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_notifications_list_route_success(self, mock_get_db_session, mock_require_superadmin, 
                                                  client, mock_superadmin_user, sample_notification):
        """Тест успешного доступа к списку уведомлений"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_notifications_paginated.return_value = ([sample_notification], 1)
            mock_service.get_notification_statistics.return_value = {"total_notifications": 1}

            # Act
            response = client.get("/admin/notifications/list")

            # Assert
            assert response.status_code == 200
            assert "Список уведомлений" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_notifications_list_with_filters(self, mock_get_db_session, mock_require_superadmin, 
                                                  client, mock_superadmin_user):
        """Тест списка уведомлений с фильтрами"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_notifications_paginated.return_value = ([], 0)
            mock_service.get_notification_statistics.return_value = {"total_notifications": 0}

            # Act
            response = client.get("/admin/notifications/list?status_filter=SENT&channel_filter=TELEGRAM&page=1&per_page=20")

            # Assert
            assert response.status_code == 200

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_templates_list_route_success(self, mock_get_db_session, mock_require_superadmin, 
                                              client, mock_superadmin_user, sample_template):
        """Тест успешного доступа к списку шаблонов"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_templates_paginated.return_value = ([sample_template], 1)
            mock_service.get_available_types.return_value = [
                {"value": "SHIFT_REMINDER", "label": "Shift Reminder"}
            ]
            mock_service.get_template_statistics.return_value = {"total_templates": 1}

            # Act
            response = client.get("/admin/notifications/templates")

            # Assert
            assert response.status_code == 200
            assert "Шаблоны уведомлений" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_templates_list_with_status_filter(self, mock_get_db_session, mock_require_superadmin, 
                                                   client, mock_superadmin_user):
        """Тест списка шаблонов с фильтром по статусу"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_templates_paginated.return_value = ([], 0)
            mock_service.get_available_types.return_value = []
            mock_service.get_template_statistics.return_value = {"total_templates": 0}

            # Act
            response = client.get("/admin/notifications/templates?status_filter=inactive")

            # Assert
            assert response.status_code == 200

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_template_create_page_route_success(self, mock_get_db_session, mock_require_superadmin, 
                                                    client, mock_superadmin_user):
        """Тест страницы создания шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_available_types.return_value = [
                {"value": "SHIFT_REMINDER", "label": "Shift Reminder"}
            ]
            mock_service.get_available_channels.return_value = [
                {"value": "TELEGRAM", "label": "Telegram"}
            ]

            # Act
            response = client.get("/admin/notifications/templates/create")

            # Assert
            assert response.status_code == 200
            assert "Создание шаблона уведомления" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_template_create_page_with_prefill(self, mock_get_db_session, mock_require_superadmin, 
                                                   client, mock_superadmin_user):
        """Тест страницы создания шаблона с предзаполнением"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_available_types.return_value = [
                {"value": "SHIFT_REMINDER", "label": "Shift Reminder"}
            ]
            mock_service.get_available_channels.return_value = [
                {"value": "TELEGRAM", "label": "Telegram"}
            ]
            mock_service.get_all_static_templates.return_value = [
                {
                    "type_value": "SHIFT_REMINDER",
                    "title": "Напоминание о смене",
                    "plain_template": "У вас смена через 2 часа",
                    "html_template": "<p>У вас смена через 2 часа</p>",
                    "subject_template": "Напоминание о смене",
                    "variables": ["user_name", "object_name"],
                    "category": "Смены"
                }
            ]

            # Act
            response = client.get("/admin/notifications/templates/create?from_static=SHIFT_REMINDER")

            # Assert
            assert response.status_code == 200
            assert "Переопределение шаблона" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_template_view_route_success(self, mock_get_db_session, mock_require_superadmin, 
                                             client, mock_superadmin_user, sample_template):
        """Тест просмотра шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_template_by_id.return_value = sample_template

            # Act
            response = client.get("/admin/notifications/templates/1")

            # Assert
            assert response.status_code == 200
            assert "Test Template" in response.text

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_template_view_route_not_found(self, mock_get_db_session, mock_require_superadmin, 
                                               client, mock_superadmin_user):
        """Тест просмотра несуществующего шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_template_by_id.return_value = None

            # Act
            response = client.get("/admin/notifications/templates/999")

            # Assert
            assert response.status_code == 404

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_notification_get_success(self, mock_get_db_session, mock_require_superadmin, 
                                              client, mock_superadmin_user, sample_notification):
        """Тест API получения уведомления"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_notification_by_id.return_value = sample_notification

            # Act
            response = client.get("/admin/notifications/api/notifications/1")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["data"]["id"] == 1

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_notification_retry_success(self, mock_get_db_session, mock_require_superadmin, 
                                                client, mock_superadmin_user):
        """Тест API повторной отправки уведомления"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.retry_notification.return_value = True

            # Act
            response = client.post("/admin/notifications/api/notifications/1/retry")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "retried" in data["message"].lower()

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_notification_cancel_success(self, mock_get_db_session, mock_require_superadmin, 
                                                 client, mock_superadmin_user):
        """Тест API отмены уведомления"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.cancel_notification.return_value = True

            # Act
            response = client.post("/admin/notifications/api/notifications/1/cancel")

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "cancelled" in data["message"].lower()

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_template_create_success(self, mock_get_db_session, mock_require_superadmin, 
                                             client, mock_superadmin_user, sample_template):
        """Тест API создания шаблона"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.create_template.return_value = sample_template

            template_data = {
                "template_key": "test_template",
                "name": "Test Template",
                "description": "Test description",
                "type": "SHIFT_REMINDER",
                "channel": "TELEGRAM",
                "subject_template": "Test Subject",
                "plain_template": "Test message",
                "html_template": "<p>Test HTML</p>",
                "variables": ["user_name", "object_name"]
            }

            # Act
            response = client.post("/admin/notifications/api/templates/create", json=template_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "created" in data["message"].lower()

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_template_delete_success(self, mock_get_db_session, mock_require_superadmin, 
                                             client, mock_superadmin_user):
        """Тест API удаления шаблона"""
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

    async def test_api_template_restore_success(self, mock_get_db_session, mock_require_superadmin, 
                                              client, mock_superadmin_user):
        """Тест API восстановления шаблона"""
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

    async def test_api_bulk_cancel_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест API массовой отмены уведомлений"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationBulkService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.cancel_notifications.return_value = {"cancelled": 5, "failed": 0}

            bulk_data = {
                "notification_ids": [1, 2, 3, 4, 5],
                "operation": "cancel"
            }

            # Act
            response = client.post("/admin/notifications/api/bulk/cancel", json=bulk_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["cancelled"] == 5
            assert data["failed"] == 0

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_api_bulk_export_success(self, mock_get_db_session, mock_require_superadmin, 
                                         client, mock_superadmin_user):
        """Тест API массового экспорта"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.export_notifications.return_value = {
                "csv_data": "id,title,status\n1,Test,SENT",
                "filename": "notifications_2025-10-14.csv"
            }

            export_data = {
                "format": "csv",
                "status_filter": "SENT"
            }

            # Act
            response = client.post("/admin/notifications/api/bulk/export", json=export_data)

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv"
            assert "notifications_2025-10-14.csv" in response.headers["content-disposition"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_error_handling_database_error(self, mock_get_db_session, mock_require_superadmin, 
                                               client, mock_superadmin_user):
        """Тест обработки ошибок базы данных"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.AdminNotificationService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_notification_statistics.side_effect = Exception("Database error")

            # Act
            response = client.get("/admin/notifications/")

            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "Ошибка загрузки дашборда" in data["detail"]

    @patch('apps.web.routes.admin_notifications.require_superadmin')
    @patch('apps.web.routes.admin_notifications.get_db_session')
    @pytest.mark.asyncio

    async def test_error_handling_validation_error(self, mock_get_db_session, mock_require_superadmin, 
                                                 client, mock_superadmin_user):
        """Тест обработки ошибок валидации"""
        # Arrange
        mock_require_superadmin.return_value = mock_superadmin_user
        mock_session = AsyncMock()
        mock_get_db_session.return_value = mock_session
        
        with patch('apps.web.routes.admin_notifications.NotificationTemplateService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.create_template.side_effect = ValueError("Missing required fields")

            template_data = {
                "template_key": "test_template"
                # Отсутствуют обязательные поля
            }

            # Act
            response = client.post("/admin/notifications/api/templates/create", json=template_data)

            # Assert
            assert response.status_code == 400
            data = response.json()
            assert "Missing required fields" in data["detail"]
