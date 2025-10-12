"""
Unit-тесты для ShiftTaskService.

Тестируем:
- Создание задач из объекта
- Создание задач из тайм-слота
- Отметку задачи как выполненной
- Проверку невыполненных обязательных задач
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.services.shift_task_service import ShiftTaskService
from domain.entities.shift_task import ShiftTask, TimeslotTaskTemplate
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot


@pytest.fixture
def mock_db_session():
    """Mock для AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def shift_task_service(mock_db_session):
    """Фикстура для ShiftTaskService."""
    return ShiftTaskService(mock_db_session)


@pytest.fixture
def sample_object():
    """Пример объекта с задачами."""
    return Object(
        id=1,
        name="Test Object",
        shift_tasks=[
            {"text": "Проверить оборудование", "is_mandatory": True, "deduction_amount": -100},
            {"text": "Сделать отчет", "is_mandatory": False, "deduction_amount": 50}
        ]
    )


@pytest.fixture
def sample_timeslot():
    """Пример тайм-слота."""
    return TimeSlot(
        id=10,
        object_id=1
    )


@pytest.mark.asyncio
async def test_get_shift_tasks(shift_task_service, mock_db_session):
    """Тест получения всех задач смены."""
    # Arrange
    tasks = [
        MagicMock(id=1, shift_id=100, task_text="Task 1", is_completed=False, is_mandatory=True),
        MagicMock(id=2, shift_id=100, task_text="Task 2", is_completed=True, is_mandatory=False)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = tasks
    mock_db_session.execute.return_value = mock_result
    
    # Act
    all_tasks = await shift_task_service.get_shift_tasks(100)
    
    # Assert
    assert len(all_tasks) == 2
    assert all_tasks[0].id == 1
    assert all_tasks[1].id == 2


@pytest.mark.asyncio
async def test_mark_task_completed(shift_task_service, mock_db_session):
    """Тест отметки задачи как выполненной."""
    # Arrange
    task = MagicMock()
    task.id = 1
    task.shift_id = 100
    task.task_text = "Test task"
    task.is_completed = False
    task.is_mandatory = True
    task.deduction_amount = Decimal("-100.00")
    
    # Настраиваем, чтобы mark_completed изменял is_completed
    def mark_completed_side_effect():
        task.is_completed = True
        task.completed_at = datetime.now()
    
    task.mark_completed.side_effect = mark_completed_side_effect
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = task
    mock_db_session.execute.return_value = mock_result
    
    # Act
    completed_task = await shift_task_service.mark_task_completed(1)
    
    # Assert
    assert completed_task is not None
    assert completed_task.is_completed is True
    assert task.mark_completed.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_mark_task_completed_not_found(shift_task_service, mock_db_session):
    """Тест отметки несуществующей задачи."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Act
    result = await shift_task_service.mark_task_completed(999)
    
    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_incomplete_tasks(shift_task_service, mock_db_session):
    """Тест получения невыполненных задач."""
    # Arrange
    tasks = [
        MagicMock(id=1, shift_id=100, task_text="Task 1", is_completed=False, is_mandatory=True),
        MagicMock(id=3, shift_id=100, task_text="Task 3", is_completed=False, is_mandatory=False)
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = tasks
    mock_db_session.execute.return_value = mock_result
    
    # Act
    incomplete_tasks = await shift_task_service.get_incomplete_tasks(100)
    
    # Assert
    assert len(incomplete_tasks) == 2
    assert incomplete_tasks[0].is_completed is False
    assert incomplete_tasks[1].is_completed is False


@pytest.mark.asyncio
async def test_get_completed_tasks(shift_task_service, mock_db_session):
    """Тест получения выполненных задач."""
    # Arrange
    tasks = [
        MagicMock(id=2, shift_id=100, task_text="Task 2", is_completed=True, is_mandatory=True),
    ]
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = tasks
    mock_db_session.execute.return_value = mock_result
    
    # Act
    completed_tasks = await shift_task_service.get_completed_tasks(100)
    
    # Assert
    assert len(completed_tasks) == 1
    assert completed_tasks[0].is_completed is True


@pytest.mark.asyncio
async def test_create_tasks_for_shift_from_object(shift_task_service, mock_db_session, sample_object):
    """Тест создания задач для смены из объекта."""
    # Arrange
    shift_id = 100
    object_id = 1
    timeslot_id = None
    
    # Mock для получения объекта
    mock_obj_result = MagicMock()
    mock_obj_result.scalar_one_or_none.return_value = sample_object
    
    # Mock для получения timeslot templates (пустой список)
    mock_tmpl_result = MagicMock()
    mock_tmpl_result.scalars.return_value.all.return_value = []
    
    mock_db_session.execute.side_effect = [mock_obj_result, mock_tmpl_result]
    
    # Act
    created_tasks = await shift_task_service.create_tasks_for_shift(shift_id, object_id, timeslot_id)
    
    # Assert
    assert len(created_tasks) == 2
    assert mock_db_session.add.call_count == 2
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_create_tasks_empty_object(shift_task_service, mock_db_session):
    """Тест создания задач с пустым объектом."""
    # Arrange
    shift_id = 100
    object_id = 1
    timeslot_id = None
    
    obj_no_tasks = Object(id=1, name="Empty Object", shift_tasks=[])
    
    mock_obj_result = MagicMock()
    mock_obj_result.scalar_one_or_none.return_value = obj_no_tasks
    
    mock_tmpl_result = MagicMock()
    mock_tmpl_result.scalars.return_value.all.return_value = []
    
    mock_db_session.execute.side_effect = [mock_obj_result, mock_tmpl_result]
    
    # Act
    created_tasks = await shift_task_service.create_tasks_for_shift(shift_id, object_id, timeslot_id)
    
    # Assert
    assert len(created_tasks) == 0
    assert mock_db_session.add.call_count == 0

