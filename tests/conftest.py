"""
Конфигурация pytest для тестов StaffProBot
Объединяет фикстуры БД и моки для unit тестов
"""
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import json

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from domain.entities import Base
from core.database.connection import get_async_session
from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority, NotificationStatus
from domain.entities.notification_template import NotificationTemplate


# Используем тестовую БД (используем dev БД для интеграционных тестов)
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:password@postgres:5432/staffprobot_dev"


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для всех тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Фикстуры для работы с реальной БД (интеграционные тесты)
# =============================================================================

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Создать тестовый движок БД."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False
    )
    
    # Создать все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Удалить все таблицы после тестов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    """Создать сессию БД для каждого теста."""
    async_session_maker = sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        # Откат всех изменений после теста
        await session.rollback()


# =============================================================================
# Моки для unit тестов
# =============================================================================

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
def delivery_trends():
    """Образец трендов доставки"""
    return {
        "dates": ["2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05"],
        "sent": [150, 180, 165, 200, 175],
        "delivered": [140, 170, 155, 190, 165],
        "failed": [10, 10, 10, 10, 10]
    }


@pytest.fixture
def error_analysis():
    """Образец анализа ошибок"""
    return {
        "total_errors": 50,
        "error_types": {
            "network_timeout": 20,
            "invalid_recipient": 15,
            "service_unavailable": 10,
            "unknown_error": 5
        },
        "most_common_error": "network_timeout",
        "error_rate": 0.05
    }


@pytest.fixture
def top_users():
    """Образец топ пользователей"""
    return [
        {"user_id": 1, "user_name": "Иван Иванов", "notification_count": 50},
        {"user_id": 2, "user_name": "Петр Петров", "notification_count": 45},
        {"user_id": 3, "user_name": "Сидор Сидоров", "notification_count": 40},
        {"user_id": 4, "user_name": "Мария Иванова", "notification_count": 35},
        {"user_id": 5, "user_name": "Анна Петрова", "notification_count": 30}
    ]


@pytest.fixture
def mock_redis_cache():
    """Мок Redis кеша"""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.exists = AsyncMock(return_value=False)
    return cache


@pytest.fixture
def mock_notification_dispatcher():
    """Мок диспетчера уведомлений"""
    dispatcher = AsyncMock()
    dispatcher.send_notification = AsyncMock(return_value=True)
    dispatcher.send_batch = AsyncMock(return_value=[True, True, True])
    return dispatcher


@pytest.fixture
def mock_email_sender():
    """Мок отправителя email"""
    sender = AsyncMock()
    sender.send = AsyncMock(return_value=True)
    sender.send_batch = AsyncMock(return_value=[True, True, True])
    return sender


@pytest.fixture
def mock_telegram_sender():
    """Мок отправителя Telegram"""
    sender = AsyncMock()
    sender.send = AsyncMock(return_value=True)
    sender.send_batch = AsyncMock(return_value=[True, True, True])
    return sender


@pytest.fixture
def mock_sms_sender():
    """Мок отправителя SMS"""
    sender = AsyncMock()
    sender.send = AsyncMock(return_value=True)
    sender.send_batch = AsyncMock(return_value=[True, True, True])
    return sender


# =============================================================================
# Фикстуры для тестирования админ-панели уведомлений
# =============================================================================

@pytest.fixture
def mock_admin_notification_service():
    """Мок сервиса администрирования уведомлений"""
    service = AsyncMock()
    service.get_dashboard_stats = AsyncMock(return_value={
        "total_notifications": 1000,
        "today_count": 50,
        "week_count": 300,
        "month_count": 1000,
        "delivery_rate": 0.95,
        "read_rate": 0.80
    })
    service.get_notifications = AsyncMock(return_value={
        "notifications": [],
        "total": 0,
        "page": 1,
        "per_page": 10,
        "total_pages": 0
    })
    service.get_notification_by_id = AsyncMock(return_value=None)
    service.retry_notification = AsyncMock(return_value=True)
    service.cancel_notification = AsyncMock(return_value=True)
    service.delete_notification = AsyncMock(return_value=True)
    service.bulk_cancel = AsyncMock(return_value=0)
    service.bulk_retry = AsyncMock(return_value=0)
    service.bulk_delete = AsyncMock(return_value=0)
    service.export_notifications = AsyncMock(return_value="")
    return service


@pytest.fixture
def mock_notification_template_service():
    """Мок сервиса шаблонов уведомлений"""
    service = AsyncMock()
    service.get_all_templates = AsyncMock(return_value=[])
    service.get_template_by_id = AsyncMock(return_value=None)
    service.get_template_by_key = AsyncMock(return_value=None)
    service.create_template = AsyncMock(return_value=None)
    service.update_template = AsyncMock(return_value=None)
    service.delete_template = AsyncMock(return_value=True)
    service.toggle_template_status = AsyncMock(return_value=True)
    service.render_template = AsyncMock(return_value={"subject": "", "plain": "", "html": ""})
    return service
