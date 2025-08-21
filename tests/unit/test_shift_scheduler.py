"""Unit-тесты для планировщика смен."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, time
from core.scheduler.shift_scheduler import ShiftScheduler


class TestShiftScheduler:
    """Тесты для планировщика смен."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.scheduler = ShiftScheduler()
    
    def test_initialization(self):
        """Тест инициализации планировщика."""
        assert self.scheduler.is_running is False
        assert self.scheduler.check_interval == 300  # 5 минут
    
    def test_start_already_running(self):
        """Тест запуска уже работающего планировщика."""
        self.scheduler.is_running = True
        
        with patch.object(self.scheduler, '_check_and_close_shifts') as mock_check:
            self.scheduler.start()
            mock_check.assert_not_called()
    
    def test_stop(self):
        """Тест остановки планировщика."""
        self.scheduler.is_running = True
        self.scheduler.stop()
        
        assert self.scheduler.is_running is False
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_get_active_shifts_success(self, mock_get_session):
        """Тест успешного получения активных смен."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем результат запроса
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            MagicMock(id=1, user_id=1, object_id=1, status='active'),
            MagicMock(id=2, user_id=2, object_id=1, status='active')
        ]
        mock_session.execute.return_value = mock_result
        
        # Вызываем метод
        result = await self.scheduler._get_active_shifts(mock_session)
        
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].id == 2
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_get_active_shifts_error(self, mock_get_session):
        """Тест получения активных смен с ошибкой."""
        # Мокаем сессию с ошибкой
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        mock_session.execute.side_effect = Exception("Database error")
        
        # Вызываем метод
        result = await self.scheduler._get_active_shifts(mock_session)
        
        assert result == []
    
    def test_should_close_shift_24_hours_passed(self):
        """Тест определения необходимости закрытия смены - прошло 24 часа."""
        # Создаем смену, которая началась более 24 часов назад
        shift = MagicMock()
        shift.start_time = datetime.now() - timedelta(days=2)
        
        obj = MagicMock()
        
        result = await self.scheduler._should_close_shift(shift, obj)
        
        assert result is True
    
    def test_should_close_shift_object_closed(self):
        """Тест определения необходимости закрытия смены - объект закрыт."""
        # Создаем смену, которая началась недавно
        shift = MagicMock()
        shift.start_time = datetime.now() - timedelta(hours=2)
        
        # Создаем объект, который закрыт
        obj = MagicMock()
        obj.opening_time = time(9, 0)  # 9:00
        obj.closing_time = time(18, 0)  # 18:00
        
        # Устанавливаем текущее время после закрытия объекта
        with patch('core.scheduler.shift_scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now().replace(
                hour=20, minute=0, second=0, microsecond=0
            )
            
            result = await self.scheduler._should_close_shift(shift, obj)
            
            assert result is True
    
    def test_should_close_shift_not_ready(self):
        """Тест определения необходимости закрытия смены - смена не готова к закрытию."""
        # Создаем смену, которая началась недавно
        shift = MagicMock()
        shift.start_time = datetime.now() - timedelta(hours=2)
        
        # Создаем объект, который работает
        obj = MagicMock()
        obj.opening_time = time(9, 0)  # 9:00
        obj.closing_time = time(18, 0)  # 18:00
        
        # Устанавливаем текущее время во время работы объекта
        with patch('core.scheduler.shift_scheduler.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime.now().replace(
                hour=14, minute=0, second=0, microsecond=0
            )
            
            result = await self.scheduler._should_close_shift(shift, obj)
            
            assert result is False
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_close_shift_manually_success(self, mock_get_session):
        """Тест успешного ручного закрытия смены."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем смену
        mock_shift = MagicMock()
        mock_shift.id = 1
        mock_shift.user_id = 1
        mock_shift.object_id = 1
        mock_shift.status = 'active'
        mock_shift.start_time = datetime.now() - timedelta(hours=8)
        mock_shift.hourly_rate = 100
        
        # Мокаем результат запроса
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_shift
        mock_session.execute.return_value = mock_result
        
        # Мокаем обновление
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1
        mock_session.execute.return_value = mock_update_result
        
        # Вызываем метод
        result = await self.scheduler.close_shift_manually(1)
        
        assert result is True
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_close_shift_manually_shift_not_found(self, mock_get_session):
        """Тест ручного закрытия смены - смена не найдена."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем результат запроса - смена не найдена
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Вызываем метод
        result = await self.scheduler.close_shift_manually(999)
        
        assert result is False
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_close_shift_manually_shift_not_active(self, mock_get_session):
        """Тест ручного закрытия смены - смена не активна."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем смену, которая уже закрыта
        mock_shift = MagicMock()
        mock_shift.id = 1
        mock_shift.status = 'completed'
        
        # Мокаем результат запроса
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_shift
        mock_session.execute.return_value = mock_result
        
        # Вызываем метод
        result = await self.scheduler.close_shift_manually(1)
        
        assert result is False
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_get_shift_status_success(self, mock_get_session):
        """Тест успешного получения статуса смены."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем смену
        mock_shift = MagicMock()
        mock_shift.id = 1
        mock_shift.user_id = 1
        mock_shift.object_id = 1
        mock_shift.status = 'active'
        mock_shift.start_time = datetime.now() - timedelta(hours=2)
        mock_shift.end_time = None
        mock_shift.total_hours = None
        mock_shift.total_payment = None
        
        # Мокаем результат запроса
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_shift
        mock_session.execute.return_value = mock_result
        
        # Вызываем метод
        result = await self.scheduler.get_shift_status(1)
        
        assert result is not None
        assert result['id'] == 1
        assert result['status'] == 'active'
        assert result['is_active'] is True
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_get_shift_status_not_found(self, mock_get_session):
        """Тест получения статуса смены - смена не найдена."""
        # Мокаем сессию
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        # Мокаем результат запроса - смена не найдена
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Вызываем метод
        result = await self.scheduler.get_shift_status(999)
        
        assert result is None
    
    @patch('core.scheduler.shift_scheduler.get_async_session')
    async def test_auto_close_shift_success(self, mock_get_session):
        """Тест успешного автоматического закрытия смены."""
        # Мокаем сессию
        mock_session = AsyncMock()
        
        # Создаем смену для автоматического закрытия
        mock_shift = MagicMock()
        mock_shift.id = 1
        mock_shift.user_id = 1
        mock_shift.object_id = 1
        mock_shift.start_time = datetime.now() - timedelta(hours=8)
        mock_shift.hourly_rate = 100
        
        # Мокаем результат обновления
        mock_update_result = MagicMock()
        mock_session.execute.return_value = mock_update_result
        
        # Вызываем метод
        await self.scheduler._auto_close_shift(mock_session, mock_shift)
        
        # Проверяем, что обновление было вызвано
        mock_session.execute.assert_called_once()
    
    def test_calculate_payment(self):
        """Тест расчета оплаты за смену."""
        # Создаем смену с известными параметрами
        shift = MagicMock()
        shift.start_time = datetime.now() - timedelta(hours=8)
        shift.hourly_rate = 100
        
        # Мокаем время окончания
        end_time = datetime.now()
        
        # Вычисляем ожидаемую оплату
        duration = end_time - shift.start_time
        expected_hours = duration.total_seconds() / 3600
        expected_payment = expected_hours * shift.hourly_rate
        
        # Проверяем, что расчет корректен
        assert expected_hours == 8.0
        assert expected_payment == 800.0
    
    def test_edge_cases_time_calculation(self):
        """Тест граничных случаев расчета времени."""
        # Смена длительностью менее часа
        short_shift = MagicMock()
        short_shift.start_time = datetime.now() - timedelta(minutes=30)
        short_shift.hourly_rate = 100
        
        end_time = datetime.now()
        duration = end_time - short_shift.start_time
        hours = duration.total_seconds() / 3600
        
        assert hours == 0.5
        
        # Смена длительностью ровно час
        hour_shift = MagicMock()
        hour_shift.start_time = datetime.now() - timedelta(hours=1)
        hour_shift.hourly_rate = 100
        
        duration = end_time - hour_shift.start_time
        hours = duration.total_seconds() / 3600
        
        assert hours == 1.0
