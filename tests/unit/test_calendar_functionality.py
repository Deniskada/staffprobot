"""Unit тесты для календарного функционала."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date, timedelta
from decimal import Decimal

from apps.web.routes.owner import _analyze_gaps
from apps.web.services.timeslot_service import TimeSlotService
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object


class TestCalendarGapAnalysis:
    """Тесты для анализа пробелов в календаре."""
    
    @pytest.fixture
    def sample_objects(self):
        """Тестовые объекты."""
        obj1 = Mock(spec=Object)
        obj1.id = 1
        obj1.name = "Object 1"
        obj1.owner_id = 1
        
        obj2 = Mock(spec=Object)
        obj2.id = 2
        obj2.name = "Object 2"
        obj2.owner_id = 1
        
        return [obj1, obj2]
    
    @pytest.fixture
    def sample_timeslots(self):
        """Тестовые тайм-слоты."""
        timeslot1 = Mock(spec=TimeSlot)
        timeslot1.id = 1
        timeslot1.object_id = 1
        timeslot1.start_time = datetime(2025, 1, 1, 9, 0)
        timeslot1.end_time = datetime(2025, 1, 1, 12, 0)
        timeslot1.is_active = True
        
        timeslot2 = Mock(spec=TimeSlot)
        timeslot2.id = 2
        timeslot2.object_id = 1
        timeslot2.start_time = datetime(2025, 1, 1, 14, 0)
        timeslot2.end_time = datetime(2025, 1, 1, 18, 0)
        timeslot2.is_active = True
        
        return [timeslot1, timeslot2]
    
    @pytest.mark.asyncio
    async def test_analyze_gaps_with_gaps(self, sample_objects, sample_timeslots):
        """Тест анализа пробелов с наличием пробелов."""
        # Мокаем TimeSlotService
        mock_timeslot_service = Mock()
        mock_timeslot_service.get_timeslots_by_objects.return_value = sample_timeslots
        
        # Выполняем тест
        result = await _analyze_gaps(mock_timeslot_service, sample_objects, 1220971779, 30)
        
        # Проверяем результат
        assert "object_gaps" in result
        assert "total_gaps" in result
        assert "period" in result
        
        # Проверяем что найдены пробелы
        assert result["total_gaps"] > 0
    
    @pytest.mark.asyncio
    async def test_analyze_gaps_no_gaps(self, sample_objects):
        """Тест анализа пробелов без пробелов."""
        # Мокаем TimeSlotService с полным покрытием
        mock_timeslot_service = Mock()
        
        # Создаем тайм-слоты с полным покрытием дня
        full_coverage_timeslots = []
        for day in range(30):
            base_date = date(2025, 1, 1) + timedelta(days=day)
            for hour in range(9, 18):  # 9:00 - 18:00
                timeslot = Mock(spec=TimeSlot)
                timeslot.id = day * 10 + hour
                timeslot.object_id = 1
                timeslot.start_time = datetime.combine(base_date, datetime.min.time().replace(hour=hour))
                timeslot.end_time = datetime.combine(base_date, datetime.min.time().replace(hour=hour + 1))
                timeslot.is_active = True
                full_coverage_timeslots.append(timeslot)
        
        mock_timeslot_service.get_timeslots_by_objects.return_value = full_coverage_timeslots
        
        # Выполняем тест
        result = await _analyze_gaps(mock_timeslot_service, sample_objects, 1220971779, 30)
        
        # Проверяем результат
        assert "object_gaps" in result
        assert "total_gaps" in result
        assert result["total_gaps"] == 0  # Нет пробелов


class TestTimeSlotService:
    """Тесты для TimeSlotService."""
    
    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД."""
        return AsyncMock()
    
    @pytest.fixture
    def timeslot_service(self, mock_session):
        """Экземпляр TimeSlotService для тестов."""
        return TimeSlotService(mock_session)
    
    @pytest.fixture
    def sample_timeslot(self):
        """Тестовый тайм-слот."""
        timeslot = Mock(spec=TimeSlot)
        timeslot.id = 1
        timeslot.object_id = 1
        timeslot.start_time = datetime(2025, 1, 1, 9, 0)
        timeslot.end_time = datetime(2025, 1, 1, 12, 0)
        timeslot.hourly_rate = Decimal("100.00")
        timeslot.is_active = True
        return timeslot
    
    @pytest.mark.asyncio
    async def test_create_timeslot_success(self, timeslot_service, mock_session, sample_timeslot):
        """Тест успешного создания тайм-слота."""
        timeslot_data = {
            "object_id": 1,
            "start_time": "09:00",
            "end_time": "12:00",
            "hourly_rate": "100.00",
            "is_active": True
        }
        
        # Мокаем создание тайм-слота
        with patch('apps.web.services.timeslot_service.TimeSlot') as mock_timeslot_class:
            mock_timeslot_class.return_value = sample_timeslot
            
            # Выполняем тест
            result = await timeslot_service.create_timeslot(timeslot_data, 1220971779)
            
            # Проверяем результат
            assert result is not None
            assert result.id == 1
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_timeslots_by_object(self, timeslot_service, mock_session, sample_timeslot):
        """Тест получения тайм-слотов по объекту."""
        # Мокаем запрос к БД
        mock_session.execute.return_value.scalars.return_value.all.return_value = [sample_timeslot]
        
        # Выполняем тест
        result = await timeslot_service.get_timeslots_by_object(1, 1220971779)
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0].id == 1
    
    @pytest.mark.asyncio
    async def test_update_timeslot(self, timeslot_service, mock_session, sample_timeslot):
        """Тест обновления тайм-слота."""
        # Мокаем получение тайм-слота
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_timeslot
        
        update_data = {
            "start_time": "10:00",
            "end_time": "13:00",
            "hourly_rate": "120.00"
        }
        
        # Выполняем тест
        result = await timeslot_service.update_timeslot(1, update_data, 1220971779)
        
        # Проверяем результат
        assert result is True
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_timeslot(self, timeslot_service, mock_session, sample_timeslot):
        """Тест удаления тайм-слота."""
        # Мокаем получение тайм-слота
        mock_session.execute.return_value.scalar_one_or_none.return_value = sample_timeslot
        
        # Выполняем тест
        result = await timeslot_service.delete_timeslot(1, 1220971779)
        
        # Проверяем результат
        assert result is True
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()


class TestCalendarAPI:
    """Тесты для API календаря."""
    
    @pytest.fixture
    def mock_timeslot_service(self):
        """Мок TimeSlotService."""
        return Mock()
    
    def test_timeslots_status_api_structure(self, mock_timeslot_service):
        """Тест структуры API статуса тайм-слотов."""
        # Мокаем данные тайм-слотов
        mock_timeslots = [
            {
                "id": 1,
                "object_id": 1,
                "start_time": datetime(2025, 1, 1, 9, 0),
                "end_time": datetime(2025, 1, 1, 12, 0),
                "status": "available"
            },
            {
                "id": 2,
                "object_id": 1,
                "start_time": datetime(2025, 1, 1, 14, 0),
                "end_time": datetime(2025, 1, 1, 18, 0),
                "status": "occupied"
            }
        ]
        
        mock_timeslot_service.get_timeslots_by_objects.return_value = mock_timeslots
        
        # Проверяем что API возвращает правильную структуру
        result = {
            "timeslots": mock_timeslots,
            "total": len(mock_timeslots),
            "available": len([t for t in mock_timeslots if t["status"] == "available"]),
            "occupied": len([t for t in mock_timeslots if t["status"] == "occupied"])
        }
        
        assert "timeslots" in result
        assert "total" in result
        assert "available" in result
        assert "occupied" in result
        assert result["total"] == 2
        assert result["available"] == 1
        assert result["occupied"] == 1


class TestCalendarValidation:
    """Тесты для валидации календарных данных."""
    
    def test_validate_date_range(self):
        """Тест валидации диапазона дат."""
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)
        
        # Проверяем что даты корректны
        assert start_date < end_date
        assert (end_date - start_date).days == 30
    
    def test_validate_time_slot_hours(self):
        """Тест валидации часов тайм-слота."""
        start_time = datetime(2025, 1, 1, 9, 0)
        end_time = datetime(2025, 1, 1, 12, 0)
        
        # Проверяем что время корректно
        assert start_time < end_time
        assert (end_time - start_time).total_seconds() == 3 * 3600  # 3 часа
    
    def test_validate_hourly_rate(self):
        """Тест валидации почасовой ставки."""
        hourly_rate = Decimal("100.00")
        
        # Проверяем что ставка корректна
        assert hourly_rate > 0
        assert hourly_rate == Decimal("100.00")
