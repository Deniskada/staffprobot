"""
Конфигурация pytest для тестов StaffProBot
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.database.connection import get_async_session
from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
from domain.entities.notification_template import NotificationTemplate


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """Мок сессии базы данных для unit тестов"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.merge = AsyncMock()
    return session


@pytest.fixture
def sample_notification():
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
        sent_at=datetime.now() + timedelta(minutes=1),
        retry_count=0,
        error_message=None,
        read_at=None,
        scheduled_at=None
    )


@pytest.fixture
def sample_template():
    """Образец шаблона для тестов"""
    return NotificationTemplate(
        id=1,
        template_key="test_shift_reminder",
        name="Test Shift Reminder",
        description="Test shift reminder template",
        type=NotificationType.SHIFT_REMINDER,
        channel=NotificationChannel.TELEGRAM,
        subject_template="Напоминание о смене",
        plain_template="Уважаемый $user_name! У вас смена на объекте $object_name в $shift_time.",
        html_template="<p>Уважаемый <strong>$user_name</strong>! У вас смена на объекте <strong>$object_name</strong> в <strong>$shift_time</strong>.</p>",
        variables='["user_name", "object_name", "shift_time"]',
        is_active=True,
        is_default=False,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_template_data():
    """Образец данных для создания шаблона"""
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
def mock_superadmin_user():
    """Мок пользователя-суперадмина"""
    return {
        "id": 1,
        "telegram_id": 123456789,
        "role": "superadmin",
        "is_active": True,
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User"
    }


@pytest.fixture
def mock_owner_user():
    """Мок пользователя-владельца"""
    return {
        "id": 2,
        "telegram_id": 987654321,
        "role": "owner",
        "is_active": True,
        "email": "owner@example.com",
        "first_name": "Owner",
        "last_name": "User"
    }


@pytest.fixture
def mock_manager_user():
    """Мок пользователя-управляющего"""
    return {
        "id": 3,
        "telegram_id": 555666777,
        "role": "manager",
        "is_active": True,
        "email": "manager@example.com",
        "first_name": "Manager",
        "last_name": "User"
    }


@pytest.fixture
def mock_employee_user():
    """Мок пользователя-сотрудника"""
    return {
        "id": 4,
        "telegram_id": 111222333,
        "role": "employee",
        "is_active": True,
        "email": "employee@example.com",
        "first_name": "Employee",
        "last_name": "User"
    }


@pytest.fixture
def notification_statistics():
    """Образец статистики уведомлений"""
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


@pytest.fixture
def channel_statistics():
    """Образец статистики по каналам"""
    return {
        "telegram": 500,
        "email": 300,
        "sms": 150,
        "push": 50
    }


@pytest.fixture
def type_statistics():
    """Образец статистики по типам"""
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


@pytest.fixture
def daily_statistics():
    """Образец ежедневной статистики"""
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


@pytest.fixture
def user_statistics():
    """Образец статистики по пользователям"""
    return [
        {
            "user_id": 123,
            "email": "user1@example.com",
            "total_notifications": 100,
            "delivered_notifications": 90,
            "failed_notifications": 10
        },
        {
            "user_id": 456,
            "email": "user2@example.com",
            "total_notifications": 80,
            "delivered_notifications": 75,
            "failed_notifications": 5
        }
    ]


@pytest.fixture
def template_statistics():
    """Образец статистики шаблонов"""
    return {
        "total_templates": 50,
        "active_templates": 45,
        "inactive_templates": 5,
        "custom_templates": 20,
        "default_templates": 30
    }


@pytest.fixture
def static_templates_data():
    """Образец данных статических шаблонов"""
    return [
        {
            "type": NotificationType.SHIFT_REMINDER,
            "type_value": "SHIFT_REMINDER",
            "type_label": "Shift Reminder",
            "title": "Напоминание о смене",
            "plain_template": "Уважаемый $user_name! У вас смена на объекте $object_name в $shift_time.",
            "html_template": "<p>Уважаемый <strong>$user_name</strong>! У вас смена на объекте <strong>$object_name</strong> в <strong>$shift_time</strong>.</p>",
            "subject_template": "Напоминание о смене",
            "variables": ["user_name", "object_name", "shift_time"],
            "category": "Смены"
        },
        {
            "type": NotificationType.CONTRACT_SIGNED,
            "type_value": "CONTRACT_SIGNED",
            "type_label": "Contract Signed",
            "title": "Договор подписан",
            "plain_template": "Поздравляем! Ваш договор №$contract_number подписан и активирован.",
            "html_template": "<p>Поздравляем! Ваш договор №<strong>$contract_number</strong> подписан и активирован.</p>",
            "subject_template": "Договор подписан",
            "variables": ["contract_number", "start_date", "end_date", "hourly_rate"],
            "category": "Договоры"
        }
    ]


@pytest.fixture
def bulk_operation_data():
    """Образец данных для массовых операций"""
    return {
        "notification_ids": [1, 2, 3, 4, 5],
        "operation": "cancel",
        "reason": "Test bulk operation"
    }


@pytest.fixture
def export_data():
    """Образец данных для экспорта"""
    return {
        "format": "csv",
        "status_filter": "SENT",
        "date_from": "2025-10-01",
        "date_to": "2025-10-14"
    }


# Фикстуры для мокирования зависимостей
@pytest.fixture
def mock_require_superadmin(mock_superadmin_user):
    """Мок для require_superadmin зависимости"""
    def _mock_require_superadmin():
        return mock_superadmin_user
    return _mock_require_superadmin


@pytest.fixture
def mock_require_owner(mock_owner_user):
    """Мок для require_owner зависимости"""
    def _mock_require_owner():
        return mock_owner_user
    return _mock_require_owner


@pytest.fixture
def mock_require_manager(mock_manager_user):
    """Мок для require_manager зависимости"""
    def _mock_require_manager():
        return mock_manager_user
    return _mock_require_manager


@pytest.fixture
def mock_require_employee(mock_employee_user):
    """Мок для require_employee зависимости"""
    def _mock_require_employee():
        return mock_employee_user
    return _mock_require_employee


@pytest.fixture
def mock_get_db_session(mock_db_session):
    """Мок для get_db_session зависимости"""
    def _mock_get_db_session():
        return mock_db_session
    return _mock_get_db_session


# Настройки pytest
def pytest_configure(config):
    """Конфигурация pytest"""
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Модификация коллекции тестов"""
    for item in items:
        # Автоматически помечаем тесты как unit или integration
        if "test_admin_notification_service" in item.name or "test_notification_template_service" in item.name:
            item.add_marker(pytest.mark.unit)
        elif "test_admin_notifications_routes" in item.name or "test_template_crud_operations" in item.name:
            item.add_marker(pytest.mark.integration)
