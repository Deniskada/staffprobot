"""
Утилиты и хелперы для тестов StaffProBot
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
from domain.entities.notification_template import NotificationTemplate


class TestDataFactory:
    """Фабрика тестовых данных"""

    @staticmethod
    def create_notification(
        id: int = 1,
        user_id: int = 123,
        type: NotificationType = NotificationType.SHIFT_REMINDER,
        channel: NotificationChannel = NotificationChannel.TELEGRAM,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        status: NotificationStatus = NotificationStatus.SENT,
        title: str = "Test Notification",
        message: str = "Test message",
        created_at: Optional[datetime] = None,
        sent_at: Optional[datetime] = None,
        read_at: Optional[datetime] = None,
        retry_count: int = 0,
        error_message: Optional[str] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Notification:
        """Создание тестового уведомления"""
        if created_at is None:
            created_at = datetime.now()
        if sent_at is None:
            sent_at = created_at + timedelta(minutes=1)
        
        return Notification(
            id=id,
            user_id=user_id,
            type=type,
            channel=channel,
            priority=priority,
            status=status,
            title=title,
            message=message,
            created_at=created_at,
            sent_at=sent_at,
            read_at=read_at,
            retry_count=retry_count,
            error_message=error_message,
            scheduled_at=scheduled_at
        )

    @staticmethod
    def create_template(
        id: int = 1,
        template_key: str = "test_template",
        name: str = "Test Template",
        description: str = "Test description",
        type: NotificationType = NotificationType.SHIFT_REMINDER,
        channel: NotificationChannel = NotificationChannel.TELEGRAM,
        subject_template: str = "Test Subject",
        plain_template: str = "Test plain message",
        html_template: str = "<p>Test HTML message</p>",
        variables: List[str] = None,
        is_active: bool = True,
        is_default: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ) -> NotificationTemplate:
        """Создание тестового шаблона"""
        if variables is None:
            variables = ["user_name", "object_name"]
        if created_at is None:
            created_at = datetime.now()
        if updated_at is None:
            updated_at = created_at

        return NotificationTemplate(
            id=id,
            template_key=template_key,
            name=name,
            description=description,
            type=type,
            channel=channel,
            subject_template=subject_template,
            plain_template=plain_template,
            html_template=html_template,
            variables=json.dumps(variables),
            is_active=is_active,
            is_default=is_default,
            created_at=created_at,
            updated_at=updated_at
        )

    @staticmethod
    def create_template_data(
        template_key: str = "test_template",
        name: str = "Test Template",
        description: str = "Test description",
        type: str = "SHIFT_REMINDER",
        channel: str = "TELEGRAM",
        subject_template: str = "Test Subject",
        plain_template: str = "Test plain message",
        html_template: str = "<p>Test HTML message</p>",
        variables: List[str] = None
    ) -> Dict[str, Any]:
        """Создание данных для создания шаблона"""
        if variables is None:
            variables = ["user_name", "object_name"]

        return {
            "template_key": template_key,
            "name": name,
            "description": description,
            "type": type,
            "channel": channel,
            "subject_template": subject_template,
            "plain_template": plain_template,
            "html_template": html_template,
            "variables": variables
        }

    @staticmethod
    def create_user_data(
        id: int = 1,
        telegram_id: int = 123456789,
        role: str = "superadmin",
        is_active: bool = True,
        email: str = "test@example.com",
        first_name: str = "Test",
        last_name: str = "User"
    ) -> Dict[str, Any]:
        """Создание данных пользователя"""
        return {
            "id": id,
            "telegram_id": telegram_id,
            "role": role,
            "is_active": is_active,
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }

    @staticmethod
    def create_notification_statistics() -> Dict[str, Any]:
        """Создание статистики уведомлений"""
        return {
            "total_notifications": 1000,
            "sent_notifications": 800,
            "delivered_notifications": 750,
            "failed_notifications": 50,
            "read_notifications": 600,
            "cancelled_notifications": 100,
            "scheduled_notifications": 25,
            "deleted_notifications": 75,
            "delivery_rate": 0.8,
            "read_rate": 0.8
        }

    @staticmethod
    def create_channel_statistics() -> Dict[str, int]:
        """Создание статистики по каналам"""
        return {
            "telegram": 500,
            "email": 300,
            "sms": 150,
            "push": 50
        }

    @staticmethod
    def create_type_statistics() -> Dict[str, int]:
        """Создание статистики по типам"""
        return {
            "SHIFT_REMINDER": 200,
            "SHIFT_CONFIRMED": 150,
            "SHIFT_CANCELLED": 50,
            "CONTRACT_SIGNED": 100,
            "CONTRACT_TERMINATED": 25,
            "PAYMENT_SUCCESS": 75,
            "PAYMENT_FAILED": 15,
            "REVIEW_RECEIVED": 80,
            "WELCOME": 30,
            "PASSWORD_RESET": 20,
            "SYSTEM_MAINTENANCE": 5
        }

    @staticmethod
    def create_daily_statistics() -> List[Dict[str, Any]]:
        """Создание ежедневной статистики"""
        return [
            {
                "date": "2025-10-14",
                "sent": 50,
                "delivered": 45,
                "failed": 5
            },
            {
                "date": "2025-10-13",
                "sent": 45,
                "delivered": 40,
                "failed": 5
            },
            {
                "date": "2025-10-12",
                "sent": 60,
                "delivered": 55,
                "failed": 5
            }
        ]


class MockServiceFactory:
    """Фабрика мок-сервисов"""

    @staticmethod
    def create_admin_notification_service_mock(
        notifications: List[Notification] = None,
        statistics: Dict[str, Any] = None,
        channel_stats: Dict[str, int] = None,
        type_stats: Dict[str, int] = None,
        daily_stats: List[Dict[str, Any]] = None
    ) -> AsyncMock:
        """Создание мок AdminNotificationService"""
        if notifications is None:
            notifications = [TestDataFactory.create_notification()]
        if statistics is None:
            statistics = TestDataFactory.create_notification_statistics()
        if channel_stats is None:
            channel_stats = TestDataFactory.create_channel_statistics()
        if type_stats is None:
            type_stats = TestDataFactory.create_type_statistics()
        if daily_stats is None:
            daily_stats = TestDataFactory.create_daily_statistics()

        mock_service = AsyncMock()
        mock_service.get_notifications_paginated.return_value = (notifications, len(notifications))
        mock_service.get_notification_statistics.return_value = statistics
        mock_service.get_channel_statistics.return_value = channel_stats
        mock_service.get_type_statistics.return_value = type_stats
        mock_service.get_daily_statistics.return_value = daily_stats
        mock_service.get_notification_by_id.return_value = notifications[0] if notifications else None
        mock_service.retry_notification.return_value = True
        mock_service.cancel_notification.return_value = True
        mock_service.export_notifications.return_value = {
            "csv_data": "id,title,status\n1,Test,SENT",
            "filename": "notifications_2025-10-14.csv"
        }

        return mock_service

    @staticmethod
    def create_notification_template_service_mock(
        templates: List[NotificationTemplate] = None,
        statistics: Dict[str, Any] = None,
        available_types: List[Dict[str, str]] = None,
        available_channels: List[Dict[str, str]] = None,
        static_templates: List[Dict[str, Any]] = None
    ) -> AsyncMock:
        """Создание мок NotificationTemplateService"""
        if templates is None:
            templates = [TestDataFactory.create_template()]
        if statistics is None:
            statistics = {
                "total_templates": 50,
                "active_templates": 45,
                "inactive_templates": 5,
                "custom_templates": 20,
                "default_templates": 30
            }
        if available_types is None:
            available_types = [
                {"value": "SHIFT_REMINDER", "label": "Shift Reminder"},
                {"value": "CONTRACT_SIGNED", "label": "Contract Signed"}
            ]
        if available_channels is None:
            available_channels = [
                {"value": "TELEGRAM", "label": "Telegram"},
                {"value": "EMAIL", "label": "Email"}
            ]
        if static_templates is None:
            static_templates = [
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

        mock_service = AsyncMock()
        mock_service.get_templates_paginated.return_value = (templates, len(templates))
        mock_service.get_template_by_id.return_value = templates[0] if templates else None
        mock_service.create_template.return_value = templates[0] if templates else None
        mock_service.update_template.return_value = templates[0] if templates else None
        mock_service.delete_template.return_value = None
        mock_service.restore_template.return_value = None
        mock_service.hard_delete_template.return_value = None
        mock_service.toggle_template_activity.return_value = templates[0] if templates else None
        mock_service.get_template_statistics.return_value = statistics
        mock_service.get_available_types.return_value = available_types
        mock_service.get_available_channels.return_value = available_channels
        mock_service.get_all_static_templates.return_value = static_templates

        return mock_service

    @staticmethod
    def create_notification_bulk_service_mock() -> AsyncMock:
        """Создание мок NotificationBulkService"""
        mock_service = AsyncMock()
        mock_service.cancel_notifications.return_value = {"cancelled": 5, "failed": 0}
        mock_service.retry_notifications.return_value = {"retried": 3, "failed": 2}
        mock_service.delete_notifications.return_value = {"deleted": 4, "failed": 1}
        mock_service.export_notifications.return_value = {
            "csv_data": "id,title,status\n1,Test,SENT",
            "filename": "notifications_2025-10-14.csv"
        }

        return mock_service


class AssertionHelpers:
    """Хелперы для ассертов"""

    @staticmethod
    def assert_notification_equal(actual: Notification, expected: Notification):
        """Проверка равенства уведомлений"""
        assert actual.id == expected.id
        assert actual.user_id == expected.user_id
        assert actual.type == expected.type
        assert actual.channel == expected.channel
        assert actual.priority == expected.priority
        assert actual.status == expected.status
        assert actual.title == expected.title
        assert actual.message == expected.message

    @staticmethod
    def assert_template_equal(actual: NotificationTemplate, expected: NotificationTemplate):
        """Проверка равенства шаблонов"""
        assert actual.id == expected.id
        assert actual.template_key == expected.template_key
        assert actual.name == expected.name
        assert actual.description == expected.description
        assert actual.type == expected.type
        assert actual.channel == expected.channel
        assert actual.subject_template == expected.subject_template
        assert actual.plain_template == expected.plain_template
        assert actual.html_template == expected.html_template
        assert actual.is_active == expected.is_active
        assert actual.is_default == expected.is_default

    @staticmethod
    def assert_api_response_success(response_data: Dict[str, Any], expected_message: str = None):
        """Проверка успешного API ответа"""
        assert "status" in response_data
        assert response_data["status"] == "success"
        if expected_message:
            assert expected_message in response_data.get("message", "")

    @staticmethod
    def assert_api_response_error(response_data: Dict[str, Any], expected_error: str = None):
        """Проверка ошибочного API ответа"""
        assert "status" in response_data
        assert response_data["status"] == "error"
        if expected_error:
            assert expected_error in response_data.get("detail", "")

    @staticmethod
    def assert_pagination_response(response_data: Dict[str, Any], expected_count: int):
        """Проверка ответа с пагинацией"""
        assert "items" in response_data or "templates" in response_data or "notifications" in response_data
        assert "total_count" in response_data
        assert response_data["total_count"] == expected_count


class DatabaseMockHelpers:
    """Хелперы для мокирования базы данных"""

    @staticmethod
    def create_mock_session():
        """Создание мок сессии БД"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        session.scalars = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        session.merge = AsyncMock()
        return session

    @staticmethod
    def setup_mock_query_result(session, result_data, count_result=None):
        """Настройка мок результата запроса"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = result_data
        mock_result.scalar_one_or_none.return_value = result_data[0] if result_data else None
        session.execute.return_value = mock_result
        
        if count_result is not None:
            session.scalar.return_value = count_result
        else:
            session.scalar.return_value = len(result_data)

    @staticmethod
    def setup_mock_error(session, error_message):
        """Настройка мок ошибки"""
        session.execute.side_effect = Exception(error_message)
        session.commit.side_effect = Exception(error_message)
