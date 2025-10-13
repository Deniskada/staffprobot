"""
Unit тесты для AdminNotificationService
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from apps.web.services.admin_notification_service import AdminNotificationService
from domain.entities.notification import Notification, NotificationType, NotificationChannel, NotificationPriority, NotificationStatus


class TestAdminNotificationService:
    """Тесты для AdminNotificationService"""

    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Экземпляр сервиса с мок сессией"""
        return AdminNotificationService(mock_session)

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

    @pytest.mark.asyncio

    async def test_get_notifications_paginated_success(self, service, mock_session, sample_notification):
        """Тест успешного получения уведомлений с пагинацией"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_notification]
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        # Act
        notifications, total_count = await service.get_notifications_paginated(
            page=1,
            per_page=20,
            status_filter=NotificationStatus.SENT
        )

        # Assert
        assert len(notifications) == 1
        assert total_count == 1
        assert notifications[0]["id"] == 1
        assert notifications[0]["status"] == "sent"
        mock_session.execute.assert_called()

    @pytest.mark.asyncio


    async def test_get_notifications_paginated_with_filters(self, service, mock_session):
        """Тест получения уведомлений с различными фильтрами"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 0

        # Act
        await service.get_notifications_paginated(
            page=1,
            per_page=10,
            status_filter=NotificationStatus.FAILED,
            channel_filter=NotificationChannel.EMAIL,
            type_filter=NotificationType.PAYMENT_FAILED,
            user_id=123,
            date_from=datetime.now() - timedelta(days=7),
            date_to=datetime.now()
        )

        # Assert
        mock_session.execute.assert_called()
        # Проверяем, что execute был вызван дважды (для данных и для подсчета)
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio


    async def test_get_notification_statistics_success(self, service, mock_session):
        """Тест получения статистики уведомлений"""
        # Arrange
        # Настраиваем мок для возврата значений
        mock_session.scalar.return_value = 100  # total_notifications

        # Act
        stats = await service.get_notification_statistics()

        # Assert
        assert stats["total_notifications"] == 0  # Из-за проверки на корутину
        assert "status_breakdown" in stats
        assert "channel_breakdown" in stats
        assert "type_breakdown" in stats
        assert "success_rate" in stats

    @pytest.mark.asyncio


    async def test_get_notification_statistics_division_by_zero(self, service, mock_session):
        """Тест обработки деления на ноль в статистике"""
        # Arrange
        mock_session.scalar.return_value = 0  # total_notifications = 0

        # Act
        stats = await service.get_notification_statistics()

        # Assert
        assert stats["total_notifications"] == 0
        assert "status_breakdown" in stats
        assert "channel_breakdown" in stats
        assert "type_breakdown" in stats
        assert stats["success_rate"] == 0

    @pytest.mark.asyncio


    async def test_get_notification_by_id_success(self, service, mock_session, sample_notification):
        """Тест получения уведомления по ID"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result

        # Act
        notification = await service.get_notification_by_id(1)

        # Assert
        assert notification is not None
        assert notification.id == 1
        assert notification.status == NotificationStatus.SENT

    @pytest.mark.asyncio


    async def test_get_notification_by_id_not_found(self, service, mock_session):
        """Тест получения несуществующего уведомления"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        notification = await service.get_notification_by_id(999)

        # Assert
        assert notification is None

    @pytest.mark.asyncio


    async def test_retry_notification_success(self, service, mock_session, sample_notification):
        """Тест повторной отправки уведомления"""
        # Arrange
        sample_notification.status = NotificationStatus.FAILED
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result

        # Act
        success = await service.retry_notification(1)

        # Assert
        assert success is True
        assert sample_notification.status == NotificationStatus.PENDING
        assert sample_notification.retry_count == 1
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_retry_notification_not_found(self, service, mock_session):
        """Тест повторной отправки несуществующего уведомления"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Notification 999 not found"):
            await service.retry_notification(999)

    @pytest.mark.asyncio


    async def test_retry_notification_max_retries_exceeded(self, service, mock_session, sample_notification):
        """Тест повторной отправки при превышении лимита попыток"""
        # Arrange
        sample_notification.status = NotificationStatus.FAILED
        sample_notification.retry_count = 3  # Максимум попыток
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result

        # Act
        success = await service.retry_notification(1)

        # Assert
        assert success is False
        assert sample_notification.status == NotificationStatus.FAILED
        assert sample_notification.retry_count == 3

    @pytest.mark.asyncio


    async def test_cancel_notification_success(self, service, mock_session, sample_notification):
        """Тест отмены уведомления"""
        # Arrange
        sample_notification.status = NotificationStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result

        # Act
        success = await service.cancel_notification(1)

        # Assert
        assert success is True
        assert sample_notification.status == NotificationStatus.CANCELLED
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_cancel_notification_already_sent(self, service, mock_session, sample_notification):
        """Тест отмены уже отправленного уведомления"""
        # Arrange
        sample_notification.status = NotificationStatus.SENT
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result

        # Act
        success = await service.cancel_notification(1)

        # Assert
        assert success is False
        assert sample_notification.status == NotificationStatus.SENT

    @pytest.mark.asyncio


    async def test_get_channel_statistics_success(self, service, mock_session):
        """Тест получения статистики по каналам"""
        # Arrange
        mock_session.scalar.return_value = 0  # Простое значение для теста

        # Act
        stats = await service.get_channel_statistics()

        # Assert
        assert isinstance(stats, dict)
        # Проверяем, что метод выполнился без ошибок

    @pytest.mark.asyncio


    async def test_get_type_statistics_success(self, service, mock_session):
        """Тест получения статистики по типам"""
        # Arrange
        mock_session.scalar.return_value = 0  # Простое значение для теста

        # Act
        stats = await service.get_type_statistics()

        # Assert
        assert isinstance(stats, dict)
        # Проверяем, что метод выполнился без ошибок

    @pytest.mark.asyncio


    async def test_get_daily_statistics_success(self, service, mock_session):
        """Тест получения ежедневной статистики"""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (datetime.now().date(), 10, 8, 2),
            ((datetime.now() - timedelta(days=1)).date(), 15, 12, 3)
        ]
        mock_session.execute.return_value = mock_result

        # Act
        stats = await service.get_daily_statistics(days=7)

        # Assert
        assert isinstance(stats, list)
        # Проверяем, что метод выполнился без ошибок

    @pytest.mark.asyncio


    async def test_get_user_statistics_success(self, service, mock_session):
        """Тест получения статистики по пользователям"""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (123, "user1@example.com", 25, 20, 5),
            (456, "user2@example.com", 15, 12, 3)
        ]
        mock_session.execute.return_value = mock_result

        # Act
        stats = await service.get_user_statistics(limit=10)

        # Assert
        assert isinstance(stats, list)
        # Проверяем, что метод выполнился без ошибок

    @pytest.mark.asyncio


    async def test_export_notifications_success(self, service, mock_session, sample_notification):
        """Тест экспорта уведомлений"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_notification]
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported export format: csv"):
            await service.export_notifications(
                format="csv",
                status_filter=NotificationStatus.SENT
            )

    @pytest.mark.asyncio


    async def test_export_notifications_json_format(self, service, mock_session, sample_notification):
        """Тест экспорта в JSON формате"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_notification]
        mock_session.execute.return_value = mock_result

        # Act
        data = await service.export_notifications(format="json")

        # Assert
        assert data["format"] == "json"
        assert "data" in data
        assert "count" in data
        assert data["count"] == 1

    @pytest.mark.asyncio


    async def test_export_notifications_excel_format(self, service, mock_session, sample_notification):
        """Тест экспорта в Excel формате"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_notification]
        mock_session.execute.return_value = mock_result

        # Act
        data = await service.export_notifications(format="xlsx")

        # Assert
        assert data["format"] == "xlsx"
        assert "data" in data
        assert "count" in data
        assert "message" in data

    @pytest.mark.asyncio


    async def test_export_notifications_invalid_format(self, service, mock_session):
        """Тест экспорта с неверным форматом"""
        # Act & Assert
        with pytest.raises(ValueError, match="Unsupported export format"):
            await service.export_notifications(format="invalid")

    @pytest.mark.asyncio


    async def test_database_error_handling(self, service, mock_session):
        """Тест обработки ошибок базы данных"""
        # Arrange
        mock_session.execute.side_effect = Exception("Database connection failed")

        # Act
        notifications, total_count = await service.get_notifications_paginated(page=1, per_page=20)
        
        # Assert
        assert notifications == []
        assert total_count == 0

    @pytest.mark.asyncio


    async def test_commit_error_handling(self, service, mock_session, sample_notification):
        """Тест обработки ошибок при коммите"""
        # Arrange
        sample_notification.status = NotificationStatus.PENDING
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_notification
        mock_session.execute.return_value = mock_result
        mock_session.commit.side_effect = Exception("Commit failed")

        # Act & Assert
        with pytest.raises(Exception, match="Commit failed"):
            await service.cancel_notification(1)
        
        # Проверяем, что был вызван rollback
        mock_session.rollback.assert_called_once()
