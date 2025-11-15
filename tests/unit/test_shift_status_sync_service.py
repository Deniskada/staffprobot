"""Unit-тесты для синхронизации статусов смен."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.shift_status_sync_service import ShiftStatusSyncService
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from shared.services.shift_history_service import ShiftHistoryService


class TestShiftStatusSyncService:
    """Тесты для синхронизации статусов смен."""

    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def sync_service(self, mock_session):
        """Сервис синхронизации."""
        return ShiftStatusSyncService(mock_session)

    @pytest.fixture
    def sample_schedule(self):
        """Тестовое расписание."""
        schedule = MagicMock(spec=ShiftSchedule)
        schedule.id = 1
        schedule.status = "planned"
        schedule.user_id = 1
        schedule.object_id = 1
        schedule.updated_at = datetime.now(timezone.utc)
        return schedule

    @pytest.fixture
    def sample_shift(self):
        """Тестовая смена."""
        shift = MagicMock(spec=Shift)
        shift.id = 1
        shift.status = "active"
        shift.schedule_id = 1
        shift.user_id = 1
        shift.object_id = 1
        shift.end_time = None
        return shift

    @pytest.mark.asyncio
    async def test_sync_on_shift_open_success(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест успешной синхронизации при открытии смены."""
        # Мокаем запрос расписания
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        # Вызываем метод
        result = await sync_service.sync_on_shift_open(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        # Проверяем результат
        assert result is True
        # Расписание остается planned (не меняется)
        assert sample_schedule.status == "planned"

    @pytest.mark.asyncio
    async def test_sync_on_shift_open_no_schedule(self, sync_service, mock_session, sample_shift):
        """Тест синхронизации при открытии смены без расписания."""
        sample_shift.schedule_id = None

        result = await sync_service.sync_on_shift_open(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_on_shift_open_cancelled_schedule(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест синхронизации при открытии смены из отмененного расписания."""
        sample_schedule.status = "cancelled"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_shift_open(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        # Смена должна быть отменена
        assert sample_shift.status == "cancelled"
        assert sample_shift.end_time is not None

    @pytest.mark.asyncio
    async def test_sync_on_shift_open_completed_schedule(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест синхронизации при открытии смены из завершенного расписания."""
        sample_schedule.status = "completed"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_shift_open(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        # Смена должна быть отменена
        assert sample_shift.status == "cancelled"
        assert sample_shift.end_time is not None

    @pytest.mark.asyncio
    async def test_sync_on_shift_close_success(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест успешной синхронизации при закрытии смены."""
        sample_shift.status = "completed"
        sample_schedule.status = "planned"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        # Мокаем history_service
        mock_history = AsyncMock()
        sync_service._history_service = mock_history
        
        result = await sync_service.sync_on_shift_close(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is True
        # Расписание должно быть завершено
        assert sample_schedule.status == "completed"
        mock_history.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_on_shift_close_no_schedule(self, sync_service, mock_session, sample_shift):
        """Тест синхронизации при закрытии смены без расписания."""
        sample_shift.schedule_id = None

        result = await sync_service.sync_on_shift_close(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_on_shift_close_cancelled_schedule(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест синхронизации при закрытии смены из отмененного расписания."""
        sample_shift.status = "completed"
        sample_schedule.status = "cancelled"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_shift_close(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        # Смена должна быть отменена
        assert sample_shift.status == "cancelled"
        assert sample_shift.end_time is not None

    @pytest.mark.asyncio
    async def test_sync_on_shift_cancel_success(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест успешной синхронизации при отмене смены."""
        sample_shift.status = "cancelled"
        sample_schedule.status = "planned"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        # Мокаем history_service
        mock_history = AsyncMock()
        sync_service._history_service = mock_history
        
        result = await sync_service.sync_on_shift_cancel(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is True
        # Расписание должно быть отменено
        assert sample_schedule.status == "cancelled"
        mock_history.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_on_shift_cancel_completed_shift(self, sync_service, mock_session, sample_shift, sample_schedule):
        """Тест синхронизации при отмене завершенной смены."""
        sample_shift.status = "completed"
        sample_schedule.status = "planned"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_schedule
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_shift_cancel(
            sample_shift,
            actor_id=1,
            actor_role="employee",
            source="bot",
        )

        assert result is False
        # Расписание не должно быть отменено
        assert sample_schedule.status == "planned"

    @pytest.mark.asyncio
    async def test_sync_on_schedule_cancel_success(self, sync_service, mock_session, sample_schedule):
        """Тест успешной синхронизации при отмене расписания."""
        sample_schedule.status = "cancelled"
        
        # Мокаем связанные смены
        related_shift = MagicMock(spec=Shift)
        related_shift.id = 1
        related_shift.status = "active"
        related_shift.schedule_id = 1
        related_shift.end_time = None

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [related_shift]
        mock_session.execute.return_value = mock_result

        # Мокаем history_service
        mock_history = AsyncMock()
        sync_service._history_service = mock_history
        
        result = await sync_service.sync_on_schedule_cancel(
            sample_schedule,
            actor_id=1,
            actor_role="owner",
            source="web",
        )

        assert result == 1
        # Связанная смена должна быть отменена
        assert related_shift.status == "cancelled"
        assert related_shift.end_time is not None
        mock_history.log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_on_schedule_cancel_no_shifts(self, sync_service, mock_session, sample_schedule):
        """Тест синхронизации при отмене расписания без связанных смен."""
        sample_schedule.status = "cancelled"
        # Убираем actual_shifts из __dict__ если есть
        if "actual_shifts" in sample_schedule.__dict__:
            del sample_schedule.__dict__["actual_shifts"]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_schedule_cancel(
            sample_schedule,
            actor_id=1,
            actor_role="owner",
            source="web",
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_sync_on_schedule_cancel_completed_shift(self, sync_service, mock_session, sample_schedule):
        """Тест синхронизации при отмене расписания с завершенной сменой."""
        sample_schedule.status = "cancelled"
        
        # Мокаем завершенную смену
        completed_shift = MagicMock(spec=Shift)
        completed_shift.id = 1
        completed_shift.status = "completed"
        completed_shift.schedule_id = 1

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [completed_shift]
        mock_session.execute.return_value = mock_result

        result = await sync_service.sync_on_schedule_cancel(
            sample_schedule,
            actor_id=1,
            actor_role="owner",
            source="web",
        )

        assert result == 0
        # Завершенная смена не должна быть отменена
        assert completed_shift.status == "completed"

