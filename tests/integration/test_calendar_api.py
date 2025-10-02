"""Интеграционные тесты для API календаря."""

import pytest
from httpx import AsyncClient
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.app import app
from core.database.session import get_db_session
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift import Shift


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Создает тестового пользователя."""
    user = User(
        telegram_id=123456789,
        first_name="Test",
        last_name="User",
        role=UserRole.OWNER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_object(db_session: AsyncSession, test_user):
    """Создает тестовый объект."""
    obj = Object(
        name="Test Object",
        owner_id=test_user.id,
        hourly_rate=500.0,
        work_conditions="Test conditions",
        shift_tasks=["Task 1", "Task 2"],
        coordinates="55.7558,37.6176"
    )
    db_session.add(obj)
    await db_session.commit()
    await db_session.refresh(obj)
    return obj


@pytest.fixture
async def test_timeslot(db_session: AsyncSession, test_object):
    """Создает тестовый тайм-слот."""
    slot = TimeSlot(
        object_id=test_object.id,
        slot_date=date.today(),
        start_time=datetime.strptime("09:00", "%H:%M").time(),
        end_time=datetime.strptime("17:00", "%H:%M").time(),
        hourly_rate=500.0,
        max_employees=2,
        is_active=True,
        notes="Test timeslot"
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)
    return slot


@pytest.fixture
async def test_shift_schedule(db_session: AsyncSession, test_user, test_object, test_timeslot):
    """Создает тестовую запланированную смену."""
    schedule = ShiftSchedule(
        user_id=test_user.id,
        object_id=test_object.id,
        time_slot_id=test_timeslot.id,
        planned_start=datetime.combine(date.today(), datetime.strptime("09:00", "%H:%M").time()),
        planned_end=datetime.combine(date.today(), datetime.strptime("17:00", "%H:%M").time()),
        status="planned",
        hourly_rate=500.0,
        notes="Test shift"
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)
    return schedule


@pytest.fixture
async def test_shift(db_session: AsyncSession, test_user, test_object, test_timeslot, test_shift_schedule):
    """Создает тестовую фактическую смену."""
    shift = Shift(
        user_id=test_user.id,
        object_id=test_object.id,
        time_slot_id=test_timeslot.id,
        start_time=datetime.combine(date.today(), datetime.strptime("09:00", "%H:%M").time()),
        end_time=datetime.combine(date.today(), datetime.strptime("17:00", "%H:%M").time()),
        status="completed",
        hourly_rate=500.0,
        total_hours=8.0,
        total_payment=4000.0,
        notes="Test shift",
        is_planned=True,
        schedule_id=test_shift_schedule.id
    )
    db_session.add(shift)
    await db_session.commit()
    await db_session.refresh(shift)
    return shift


class TestCalendarAPI:
    """Интеграционные тесты для API календаря."""

    async def test_owner_calendar_api_data(self, client: AsyncClient, test_user, test_object, 
                                         test_timeslot, test_shift_schedule, test_shift):
        """Тест API календаря для владельца."""
        # Создаем JWT токен
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": test_user.role})
        
        # Параметры запроса
        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        # Выполняем запрос
        response = await client.get(
            f"/owner/calendar/api/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "timeslots" in data
        assert "shifts" in data
        assert "metadata" in data
        
        # Проверяем тайм-слоты
        assert len(data["timeslots"]) == 1
        timeslot = data["timeslots"][0]
        assert timeslot["id"] == test_timeslot.id
        assert timeslot["object_id"] == test_object.id
        assert timeslot["object_name"] == test_object.name
        
        # Проверяем смены
        assert len(data["shifts"]) == 1
        shift = data["shifts"][0]
        assert shift["id"] == test_shift_schedule.id
        assert shift["user_id"] == test_user.id
        assert shift["object_id"] == test_object.id

    async def test_manager_calendar_api_data(self, client: AsyncClient, test_user, test_object,
                                           test_timeslot, test_shift_schedule):
        """Тест API календаря для управляющего."""
        # Создаем JWT токен для управляющего
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": UserRole.MANAGER})
        
        # Параметры запроса
        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        # Выполняем запрос
        response = await client.get(
            f"/manager/calendar/api/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "timeslots" in data
        assert "shifts" in data
        assert "metadata" in data

    async def test_employee_calendar_api_data(self, client: AsyncClient, test_user, test_object,
                                            test_timeslot, test_shift_schedule):
        """Тест API календаря для сотрудника."""
        # Создаем JWT токен для сотрудника
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": UserRole.EMPLOYEE})
        
        # Параметры запроса
        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        # Выполняем запрос
        response = await client.get(
            f"/employee/api/calendar/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "timeslots" in data
        assert "shifts" in data
        assert "metadata" in data

    async def test_calendar_api_with_object_filter(self, client: AsyncClient, test_user, test_object,
                                                 test_timeslot, test_shift_schedule):
        """Тест API календаря с фильтром по объектам."""
        # Создаем JWT токен
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": test_user.role})
        
        # Параметры запроса
        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        object_ids = f"{test_object.id}"
        
        # Выполняем запрос
        response = await client.get(
            f"/owner/calendar/api/data?start_date={start_date}&end_date={end_date}&object_ids={object_ids}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем, что возвращаются только данные для указанного объекта
        assert len(data["timeslots"]) == 1
        assert data["timeslots"][0]["object_id"] == test_object.id

    async def test_calendar_api_invalid_date_format(self, client: AsyncClient, test_user):
        """Тест API календаря с неверным форматом даты."""
        # Создаем JWT токен
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": test_user.role})
        
        # Выполняем запрос с неверным форматом даты
        response = await client.get(
            "/owner/calendar/api/data?start_date=invalid-date&end_date=2024-01-07",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Неверный формат даты" in data["detail"]

    async def test_calendar_api_unauthorized(self, client: AsyncClient):
        """Тест API календаря без авторизации."""
        # Выполняем запрос без токена
        response = await client.get("/owner/calendar/api/data?start_date=2024-01-01&end_date=2024-01-07")
        
        # Проверяем ответ
        assert response.status_code == 401

    async def test_calendar_api_cache_performance(self, client: AsyncClient, test_user, test_object,
                                                test_timeslot, test_shift_schedule):
        """Тест производительности кэширования API календаря."""
        # Создаем JWT токен
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": test_user.role})
        
        # Параметры запроса
        start_date = date.today().isoformat()
        end_date = (date.today() + timedelta(days=7)).isoformat()
        
        # Первый запрос
        import time
        start_time = time.time()
        response1 = await client.get(
            f"/owner/calendar/api/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        first_request_time = time.time() - start_time
        
        # Второй запрос (должен использовать кэш)
        start_time = time.time()
        response2 = await client.get(
            f"/owner/calendar/api/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        second_request_time = time.time() - start_time
        
        # Проверяем ответы
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Проверяем, что данные одинаковые
        data1 = response1.json()
        data2 = response2.json()
        assert data1["timeslots"] == data2["timeslots"]
        assert data1["shifts"] == data2["shifts"]
        
        # Второй запрос должен быть быстрее (кэш)
        assert second_request_time < first_request_time

    async def test_calendar_api_large_date_range(self, client: AsyncClient, test_user, test_object):
        """Тест API календаря с большим диапазоном дат."""
        # Создаем JWT токен
        from core.auth.jwt_handler import create_access_token
        token = create_access_token(data={"sub": str(test_user.telegram_id), "role": test_user.role})
        
        # Параметры запроса с большим диапазоном
        start_date = (date.today() - timedelta(days=30)).isoformat()
        end_date = (date.today() + timedelta(days=30)).isoformat()
        
        # Выполняем запрос
        response = await client.get(
            f"/owner/calendar/api/data?start_date={start_date}&end_date={end_date}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Проверяем ответ
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем структуру ответа
        assert "timeslots" in data
        assert "shifts" in data
        assert "metadata" in data
        
        # Проверяем метаданные
        metadata = data["metadata"]
        assert "date_range_start" in metadata
        assert "date_range_end" in metadata
        assert "user_role" in metadata
        assert "total_timeslots" in metadata
        assert "total_shifts" in metadata
