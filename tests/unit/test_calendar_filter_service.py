"""Тесты для универсального сервиса фильтрации календаря."""

import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.calendar_filter_service import CalendarFilterService
from shared.services.object_access_service import ObjectAccessService
from shared.models.calendar_data import CalendarData, CalendarTimeslot, CalendarShift, TimeslotStatus, ShiftType, ShiftStatus
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift


@pytest.fixture
def mock_db_session():
    """Мок сессии базы данных."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def calendar_service(mock_db_session):
    """Экземпляр сервиса календаря."""
    return CalendarFilterService(mock_db_session)


@pytest.fixture
def sample_user():
    """Тестовый пользователь."""
    user = User()
    user.id = 1
    user.telegram_id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.role = UserRole.OWNER
    return user


@pytest.fixture
def sample_object():
    """Тестовый объект."""
    obj = Object()
    obj.id = 1
    obj.name = "Test Object"
    obj.owner_id = 1
    obj.hourly_rate = 500.0
    obj.work_conditions = "Test conditions"
    obj.shift_tasks = ["Task 1", "Task 2"]
    obj.coordinates = "55.7558,37.6176"
    return obj


@pytest.fixture
def sample_timeslot():
    """Тестовый тайм-слот."""
    slot = TimeSlot()
    slot.id = 1
    slot.object_id = 1
    slot.slot_date = date.today()
    slot.start_time = time(9, 0)
    slot.end_time = time(17, 0)
    slot.hourly_rate = 500.0
    slot.max_employees = 2
    slot.is_active = True
    slot.notes = "Test timeslot"
    slot.object = sample_object()
    return slot


@pytest.fixture
def sample_shift_schedule():
    """Тестовая запланированная смена."""
    schedule = ShiftSchedule()
    schedule.id = 1
    schedule.user_id = 1
    schedule.object_id = 1
    schedule.time_slot_id = 1
    schedule.planned_start = datetime.combine(date.today(), time(9, 0))
    schedule.planned_end = datetime.combine(date.today(), time(17, 0))
    schedule.status = "planned"
    schedule.hourly_rate = 500.0
    schedule.notes = "Test shift"
    schedule.actual_shift_id = None
    schedule.user = sample_user()
    schedule.object = sample_object()
    return schedule


@pytest.fixture
def sample_shift():
    """Тестовая фактическая смена."""
    shift = Shift()
    shift.id = 1
    shift.user_id = 1
    shift.object_id = 1
    shift.time_slot_id = 1
    shift.start_time = datetime.combine(date.today(), time(9, 0))
    shift.end_time = datetime.combine(date.today(), time(17, 0))
    shift.status = "completed"
    shift.hourly_rate = 500.0
    shift.total_hours = 8.0
    shift.total_payment = 4000.0
    shift.notes = "Test shift"
    shift.is_planned = True
    shift.schedule_id = 1
    shift.user = sample_user()
    shift.object = sample_object()
    return shift


class TestCalendarFilterService:
    """Тесты для CalendarFilterService."""

    @pytest.mark.asyncio
    async def test_get_calendar_data_empty_result(self, calendar_service, mock_db_session):
        """Тест получения пустых данных календаря."""
        # Настраиваем моки
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None
        
        # Вызываем метод
        result = await calendar_service.get_calendar_data(
            user_telegram_id=999999999,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Проверяем результат
        assert isinstance(result, CalendarData)
        assert len(result.timeslots) == 0
        assert len(result.shifts) == 0
        assert result.user_role == "owner"

    @pytest.mark.asyncio
    async def test_get_calendar_data_with_timeslots(self, calendar_service, mock_db_session, 
                                                   sample_user, sample_object, sample_timeslot):
        """Тест получения данных календаря с тайм-слотами."""
        # Настраиваем моки
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user
        
        timeslots_result = MagicMock()
        timeslots_result.scalars.return_value.all.return_value = [sample_timeslot]
        
        shifts_result = MagicMock()
        shifts_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [user_result, timeslots_result, shifts_result]
        
        # Мокаем ObjectAccessService
        calendar_service.object_access_service.get_accessible_objects = AsyncMock(
            return_value=[{
                'id': 1,
                'name': 'Test Object',
                'hourly_rate': 500.0,
                'work_conditions': 'Test conditions',
                'shift_tasks': ['Task 1', 'Task 2'],
                'coordinates': '55.7558,37.6176',
                'can_edit': True,
                'can_edit_schedule': True,
                'can_view': True
            }]
        )
        
        # Вызываем метод
        result = await calendar_service.get_calendar_data(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Проверяем результат
        assert isinstance(result, CalendarData)
        assert len(result.timeslots) == 1
        assert len(result.shifts) == 0
        
        timeslot = result.timeslots[0]
        assert timeslot.id == 1
        assert timeslot.object_id == 1
        assert timeslot.object_name == "Test Object"
        assert timeslot.hourly_rate == 500.0
        assert timeslot.max_employees == 2
        assert timeslot.status == TimeslotStatus.EMPTY

    @pytest.mark.asyncio
    async def test_get_calendar_data_with_shifts(self, calendar_service, mock_db_session,
                                               sample_user, sample_object, sample_shift_schedule):
        """Тест получения данных календаря со сменами."""
        # Настраиваем моки
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user
        
        timeslots_result = MagicMock()
        timeslots_result.scalars.return_value.all.return_value = []
        
        shifts_result = MagicMock()
        shifts_result.scalars.return_value.all.return_value = [sample_shift_schedule]
        
        mock_db_session.execute.side_effect = [user_result, timeslots_result, shifts_result]
        
        # Мокаем ObjectAccessService
        calendar_service.object_access_service.get_accessible_objects = AsyncMock(
            return_value=[{
                'id': 1,
                'name': 'Test Object',
                'hourly_rate': 500.0,
                'work_conditions': 'Test conditions',
                'shift_tasks': ['Task 1', 'Task 2'],
                'coordinates': '55.7558,37.6176',
                'can_edit': True,
                'can_edit_schedule': True,
                'can_view': True
            }]
        )
        
        # Вызываем метод
        result = await calendar_service.get_calendar_data(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Проверяем результат
        assert isinstance(result, CalendarData)
        assert len(result.timeslots) == 0
        assert len(result.shifts) == 1
        
        shift = result.shifts[0]
        assert shift.id == 1
        assert shift.user_id == 1
        assert shift.object_id == 1
        assert shift.shift_type == ShiftType.SCHEDULED
        assert shift.status == ShiftStatus.PLANNED

    @pytest.mark.asyncio
    async def test_cache_functionality(self, calendar_service, mock_db_session, sample_user):
        """Тест функциональности кэширования."""
        # Настраиваем моки
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user
        
        timeslots_result = MagicMock()
        timeslots_result.scalars.return_value.all.return_value = []
        
        shifts_result = MagicMock()
        shifts_result.scalars.return_value.all.return_value = []
        
        mock_db_session.execute.side_effect = [user_result, timeslots_result, shifts_result]
        
        # Мокаем ObjectAccessService
        calendar_service.object_access_service.get_accessible_objects = AsyncMock(
            return_value=[]
        )
        
        # Первый вызов
        result1 = await calendar_service.get_calendar_data(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Второй вызов (должен использовать кэш)
        result2 = await calendar_service.get_calendar_data(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Проверяем, что результаты одинаковые
        assert result1.timeslots == result2.timeslots
        assert result1.shifts == result2.shifts
        
        # Проверяем, что второй вызов не обращался к БД
        assert mock_db_session.execute.call_count == 3  # Только первый вызов

    @pytest.mark.asyncio
    async def test_filter_cancelled_shifts(self, calendar_service, mock_db_session,
                                         sample_user, sample_object):
        """Тест фильтрации отменённых смен."""
        # Создаем отменённую смену
        cancelled_shift = Shift()
        cancelled_shift.id = 1
        cancelled_shift.user_id = 1
        cancelled_shift.object_id = 1
        cancelled_shift.start_time = datetime.combine(date.today(), time(9, 0))
        cancelled_shift.end_time = datetime.combine(date.today(), time(17, 0))
        cancelled_shift.status = "cancelled"
        cancelled_shift.hourly_rate = 500.0
        cancelled_shift.user = sample_user
        cancelled_shift.object = sample_object
        
        # Настраиваем моки
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = sample_user
        
        timeslots_result = MagicMock()
        timeslots_result.scalars.return_value.all.return_value = []
        
        shifts_result = MagicMock()
        shifts_result.scalars.return_value.all.return_value = [cancelled_shift]
        
        mock_db_session.execute.side_effect = [user_result, timeslots_result, shifts_result]
        
        # Мокаем ObjectAccessService
        calendar_service.object_access_service.get_accessible_objects = AsyncMock(
            return_value=[{
                'id': 1,
                'name': 'Test Object',
                'hourly_rate': 500.0,
                'work_conditions': 'Test conditions',
                'shift_tasks': ['Task 1', 'Task 2'],
                'coordinates': '55.7558,37.6176',
                'can_edit': True,
                'can_edit_schedule': True,
                'can_view': True
            }]
        )
        
        # Вызываем метод
        result = await calendar_service.get_calendar_data(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date.today(),
            date_range_end=date.today() + timedelta(days=7)
        )
        
        # Проверяем, что отменённая смена не попала в результат
        assert len(result.shifts) == 0

    @pytest.mark.asyncio
    async def test_timeslot_status_calculation(self, calendar_service):
        """Тест расчёта статуса тайм-слотов."""
        # Создаем тестовые данные
        timeslot = CalendarTimeslot(
            id=1,
            object_id=1,
            object_name="Test Object",
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(17, 0),
            hourly_rate=500.0,
            max_employees=2,
            current_employees=0,
            available_slots=2,
            status=TimeslotStatus.EMPTY,
            is_active=True
        )
        
        # Смена без привязки к тайм-слоту
        shift = CalendarShift(
            id=1,
            user_id=1,
            user_name="Test User",
            object_id=1,
            object_name="Test Object",
            shift_type=ShiftType.ACTUAL,
            status=ShiftStatus.ACTIVE,
            hourly_rate=500.0
        )
        
        # Вызываем метод обновления статусов
        updated_timeslots = calendar_service._update_timeslot_statuses([timeslot], [shift])
        
        # Проверяем, что статус не изменился (смена не привязана к тайм-слоту)
        assert len(updated_timeslots) == 1
        assert updated_timeslots[0].status == TimeslotStatus.EMPTY

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, calendar_service):
        """Тест генерации ключей кэша."""
        # Тест без фильтра объектов
        key1 = calendar_service._generate_cache_key(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date(2024, 1, 1),
            date_range_end=date(2024, 1, 7)
        )
        
        # Тест с фильтром объектов
        key2 = calendar_service._generate_cache_key(
            user_telegram_id=123456789,
            user_role="owner",
            date_range_start=date(2024, 1, 1),
            date_range_end=date(2024, 1, 7),
            object_filter=[1, 2, 3]
        )
        
        # Проверяем, что ключи разные
        assert key1 != key2
        assert len(key1) == 32  # MD5 hash length
        assert len(key2) == 32

    @pytest.mark.asyncio
    async def test_cache_ttl(self, calendar_service):
        """Тест TTL кэша."""
        # Сохраняем данные в кэш
        test_data = {"test": "data"}
        calendar_service._set_cache("test_key", test_data, ttl_minutes=1)
        
        # Проверяем, что данные есть в кэше
        cached_data = calendar_service._get_from_cache("test_key")
        assert cached_data == test_data
        
        # Проверяем, что данные есть в TTL
        assert "test_key" in calendar_service._cache_ttl


class TestObjectAccessService:
    """Тесты для ObjectAccessService."""

    @pytest.mark.asyncio
    async def test_get_accessible_objects_owner(self, mock_db_session):
        """Тест получения объектов для владельца."""
        # Создаем тестовые объекты
        obj1 = Object()
        obj1.id = 1
        obj1.name = "Object 1"
        obj1.owner_id = 1
        
        obj2 = Object()
        obj2.id = 2
        obj2.name = "Object 2"
        obj2.owner_id = 1
        
        # Настраиваем мок
        result = MagicMock()
        result.scalars.return_value.all.return_value = [obj1, obj2]
        mock_db_session.execute.return_value = result
        
        # Создаем сервис
        service = ObjectAccessService(mock_db_session)
        
        # Вызываем метод
        accessible_objects = await service.get_accessible_objects(1, UserRole.OWNER)
        
        # Проверяем результат
        assert len(accessible_objects) == 2
        assert accessible_objects[0]['id'] == 1
        assert accessible_objects[1]['id'] == 2

    @pytest.mark.asyncio
    async def test_get_accessible_objects_manager(self, mock_db_session):
        """Тест получения объектов для управляющего."""
        # Настраиваем мок для пустого результата
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = result
        
        # Создаем сервис
        service = ObjectAccessService(mock_db_session)
        
        # Вызываем метод
        accessible_objects = await service.get_accessible_objects(1, UserRole.MANAGER)
        
        # Проверяем результат
        assert len(accessible_objects) == 0

    @pytest.mark.asyncio
    async def test_get_accessible_objects_employee(self, mock_db_session):
        """Тест получения объектов для сотрудника."""
        # Настраиваем мок для пустого результата
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = result
        
        # Создаем сервис
        service = ObjectAccessService(mock_db_session)
        
        # Вызываем метод
        accessible_objects = await service.get_accessible_objects(1, UserRole.EMPLOYEE)
        
        # Проверяем результат
        assert len(accessible_objects) == 0

    @pytest.mark.asyncio
    async def test_get_accessible_objects_superadmin(self, mock_db_session):
        """Тест получения объектов для суперадмина."""
        # Создаем тестовые объекты
        obj1 = Object()
        obj1.id = 1
        obj1.name = "Object 1"
        obj1.owner_id = 1
        
        # Настраиваем мок
        result = MagicMock()
        result.scalars.return_value.all.return_value = [obj1]
        mock_db_session.execute.return_value = result
        
        # Создаем сервис
        service = ObjectAccessService(mock_db_session)
        
        # Вызываем метод
        accessible_objects = await service.get_accessible_objects(1, UserRole.SUPERADMIN)
        
        # Проверяем результат
        assert len(accessible_objects) == 1
        assert accessible_objects[0]['id'] == 1
