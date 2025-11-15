"""
Unit тесты для NotificationTemplateService
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json

from apps.web.services.notification_template_service import NotificationTemplateService
from domain.entities.notification_template import NotificationTemplate
from domain.entities.notification import NotificationType, NotificationChannel


class TestNotificationTemplateService:
    """Тесты для NotificationTemplateService"""

    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.scalar = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.add = MagicMock()
        session.delete = MagicMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Экземпляр сервиса с мок сессией"""
        return NotificationTemplateService(mock_session)

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
            variables=json.dumps(["user_name", "object_name"]),
            is_active=True,
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    @pytest.mark.asyncio


    async def test_get_templates_paginated_success(self, service, mock_session, sample_template):
        """Тест успешного получения шаблонов с пагинацией"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [sample_template]
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 1

        # Act
        templates, total_count = await service.get_templates_paginated(
            page=1,
            per_page=20
        )

        # Assert
        assert len(templates) == 1
        assert total_count == 1
        assert templates[0].id == 1
        assert templates[0].is_active is True
        mock_session.execute.assert_called()

    @pytest.mark.asyncio


    async def test_get_templates_paginated_with_filters(self, service, mock_session):
        """Тест получения шаблонов с фильтрами"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 0

        # Act
        await service.get_templates_paginated(
            page=1,
            per_page=10,
            type_filter=NotificationType.SHIFT_REMINDER.value,
            is_active=True,
            search_query="test"
        )

        # Assert
        mock_session.execute.assert_called()

    @pytest.mark.asyncio


    async def test_get_templates_paginated_default_active_only(self, service, mock_session):
        """Тест что по умолчанию показываются только активные шаблоны"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.scalar.return_value = 0

        # Act
        await service.get_templates_paginated(page=1, per_page=20)

        # Assert
        # Проверяем, что в запросе есть фильтр is_active = True
        call_args = mock_session.execute.call_args[0][0]
        assert "is_active" in str(call_args)

    @pytest.mark.asyncio


    async def test_get_template_by_id_success(self, service, mock_session, sample_template):
        """Тест получения шаблона по ID"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act
        template = await service.get_template_by_id(1)

        # Assert
        assert template is not None
        assert template.id == 1
        assert template.template_key == "test_template"

    @pytest.mark.asyncio


    async def test_get_template_by_id_not_found(self, service, mock_session):
        """Тест получения несуществующего шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act
        template = await service.get_template_by_id(999)

        # Assert
        assert template is None

    @pytest.mark.asyncio


    async def test_create_template_success(self, service, mock_session):
        """Тест создания нового шаблона"""
        # Arrange
        # Настраиваем мок так, чтобы get_template_by_key возвращал None (шаблон не существует)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Шаблон не существует
        mock_session.execute.return_value = mock_result
        
        template_key = "new_template"
        notification_type = NotificationType.SHIFT_REMINDER
        channel = NotificationChannel.TELEGRAM
        name = "New Template"
        plain_template = "New plain message"
        subject_template = "New Subject"
        html_template = "<p>New HTML message</p>"
        description = "New description"
        variables = ["user_name", "object_name"]

        # Act
        template = await service.create_template(
            template_key=template_key,
            notification_type=notification_type,
            channel=channel,
            name=name,
            plain_template=plain_template,
            subject_template=subject_template,
            html_template=html_template,
            description=description,
            variables=variables
        )

        # Assert
        assert template is not None
        assert template.template_key == "new_template"
        assert template.name == "New Template"
        assert template.is_active is True
        assert template.is_default is False
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_create_template_with_existing_key(self, service, mock_session):
        """Тест создания шаблона с существующим ключом"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Существующий шаблон
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Шаблон с ключом 'existing_template' уже существует"):
            await service.create_template(
                template_key="existing_template",
                notification_type=NotificationType.SHIFT_REMINDER,
                channel=NotificationChannel.TELEGRAM,
                name="Existing Template",
                plain_template="Message",
                subject_template="Subject",
                html_template="<p>HTML</p>",
                variables=[]
            )

    @pytest.mark.asyncio


    async def test_update_template_success(self, service, mock_session, sample_template):
        """Тест обновления шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act
        updated_template = await service.update_template(
            template_id=1,
            name="Updated Template",
            description="Updated description",
            subject_template="Updated Subject",
            plain_template="Updated plain message",
            html_template="<p>Updated HTML message</p>",
            variables=["user_name", "object_name", "shift_time"]
        )

        # Assert
        assert updated_template is not None
        assert updated_template.name == "Updated Template"
        assert updated_template.description == "Updated description"
        assert updated_template.variables == '["user_name", "object_name", "shift_time"]'
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_update_template_not_found(self, service, mock_session):
        """Тест обновления несуществующего шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        update_data = {"name": "Updated Template"}

        # Act & Assert
        with pytest.raises(ValueError, match="Шаблон с ID 999 не найден"):
            await service.update_template(999, update_data)

    @pytest.mark.asyncio


    async def test_update_default_template(self, service, mock_session, sample_template):
        """Тест обновления дефолтного шаблона"""
        # Arrange
        sample_template.is_default = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        update_data = {"name": "Updated Template"}

        # Act & Assert
        with pytest.raises(ValueError, match="Нельзя обновить дефолтный шаблон"):
            await service.update_template(1, update_data)

    @pytest.mark.asyncio


    async def test_delete_template_success(self, service, mock_session, sample_template):
        """Тест удаления шаблона (деактивация)"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act
        await service.delete_template(1)

        # Assert
        assert sample_template.is_active is False
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_delete_template_not_found(self, service, mock_session):
        """Тест удаления несуществующего шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Шаблон с ID 999 не найден"):
            await service.delete_template(999)

    @pytest.mark.asyncio


    async def test_delete_default_template(self, service, mock_session, sample_template):
        """Тест удаления дефолтного шаблона"""
        # Arrange
        sample_template.is_default = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Нельзя удалить дефолтный шаблон"):
            await service.delete_template(1)

    @pytest.mark.asyncio


    async def test_restore_template_success(self, service, mock_session, sample_template):
        """Тест восстановления шаблона (активация)"""
        # Arrange
        sample_template.is_active = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act
        await service.restore_template(1)

        # Assert
        assert sample_template.is_active is True
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_restore_template_not_found(self, service, mock_session):
        """Тест восстановления несуществующего шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Шаблон с ID 999 не найден"):
            await service.restore_template(999)

    @pytest.mark.asyncio


    async def test_hard_delete_template_success(self, service, mock_session, sample_template):
        """Тест жёсткого удаления шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result

        # Act
        await service.hard_delete_template(1)

        # Assert
        mock_session.delete.assert_called_once_with(sample_template)
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio


    async def test_hard_delete_template_not_found(self, service, mock_session):
        """Тест жёсткого удаления несуществующего шаблона"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        # Act & Assert
        with pytest.raises(ValueError, match="Шаблон с ID 999 не найден"):
            await service.hard_delete_template(999)

    @pytest.mark.asyncio


    async def test_get_available_types_success(self, service):
        """Тест получения доступных типов уведомлений"""
        # Act
        types = await service.get_available_types()

        # Assert
        assert isinstance(types, list)
        assert len(types) > 0
        assert all("value" in t and "label" in t for t in types)
        # Проверяем, что есть основные типы
        type_values = [t["value"] for t in types]
        assert "shift_reminder" in type_values
        assert "contract_signed" in type_values

    @pytest.mark.asyncio


    async def test_get_available_channels_success(self, service):
        """Тест получения доступных каналов"""
        # Act
        channels = await service.get_available_channels()

        # Assert
        assert isinstance(channels, list)
        assert len(channels) > 0
        assert all("value" in c and "label" in c for c in channels)
        # Проверяем, что есть основные каналы
        channel_values = [c["value"] for c in channels]
        assert "telegram" in channel_values
        assert "email" in channel_values

    @pytest.mark.asyncio


    async def test_get_all_static_templates_success(self, service):
        """Тест получения всех статических шаблонов"""
        # Act
        templates = await service.get_all_static_templates()

        # Assert
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert all("type" in t for t in templates)
        assert all("type_value" in t for t in templates)
        assert all("title" in t for t in templates)
        assert all("category" in t for t in templates)

    @pytest.mark.asyncio


    async def test_get_template_category(self, service):
        """Тест определения категории шаблона"""
        # Act & Assert
        assert service._get_template_category(NotificationType.SHIFT_REMINDER) == "Смены"
        assert service._get_template_category(NotificationType.CONTRACT_SIGNED) == "Договоры"
        assert service._get_template_category(NotificationType.REVIEW_RECEIVED) == "Отзывы"
        assert service._get_template_category(NotificationType.PAYMENT_SUCCESS) == "Платежи"
        assert service._get_template_category(NotificationType.WELCOME) == "Системные"

    @pytest.mark.asyncio


    async def test_get_template_statistics_success(self, service, mock_session):
        """Тест получения статистики шаблонов"""
        # Arrange
        mock_session.scalar.return_value = 5  # Для кастомных шаблонов

        # Act
        stats = await service.get_template_statistics()

        # Assert
        assert stats["total_static"] == 31  # Реальное количество статических шаблонов (обновлено после добавления новых типов)
        assert stats["total_custom"] == 5
        assert stats["active_custom"] == 5

    @pytest.mark.asyncio


    async def test_validate_template_data_success(self, service):
        """Тест валидации данных шаблона"""
        # Arrange
        valid_data = {
            "template_key": "test_template",
            "name": "Test Template",
            "type": NotificationType.SHIFT_REMINDER,
            "channel": NotificationChannel.TELEGRAM,
            "subject_template": "Test Subject",
            "plain_template": "Test message",
            "html_template": "<p>Test HTML</p>",
            "variables": ["user_name"]
        }

        # Act
        result = service._validate_template_data(valid_data)

        # Assert
        assert result == valid_data

    @pytest.mark.asyncio


    async def test_validate_template_data_missing_required_fields(self, service):
        """Тест валидации с отсутствующими обязательными полями"""
        # Arrange
        invalid_data = {
            "template_key": "test_template",
            # Отсутствует name
            "type": NotificationType.SHIFT_REMINDER,
            "channel": NotificationChannel.TELEGRAM
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Missing required fields"):
            service._validate_template_data(invalid_data)

    @pytest.mark.asyncio


    async def test_validate_template_data_invalid_type(self, service):
        """Тест валидации с неверным типом"""
        # Arrange
        invalid_data = {
            "template_key": "test_template",
            "name": "Test Template",
            "type": "INVALID_TYPE",
            "channel": NotificationChannel.TELEGRAM,
            "subject_template": "Test Subject",
            "plain_template": "Test message",
            "html_template": "<p>Test HTML</p>",
            "variables": []
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid notification type"):
            service._validate_template_data(invalid_data)

    @pytest.mark.asyncio


    async def test_database_error_handling(self, service, mock_session):
        """Тест обработки ошибок базы данных"""
        # Arrange
        mock_session.execute.side_effect = Exception("Database connection failed")

        # Act
        templates, total_count = await service.get_templates_paginated(page=1, per_page=20)
        
        # Assert
        assert templates == []
        assert total_count == 0

    @pytest.mark.asyncio


    async def test_commit_error_handling(self, service, mock_session, sample_template):
        """Тест обработки ошибок при коммите"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_template
        mock_session.execute.return_value = mock_result
        mock_session.commit.side_effect = Exception("Commit failed")

        # Act & Assert
        with pytest.raises(Exception, match="Commit failed"):
            await service.delete_template(1)
        
        # Проверяем, что был вызван rollback
        mock_session.rollback.assert_called_once()
