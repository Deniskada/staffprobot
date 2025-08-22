"""Unit тесты для ObjectService."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import time
from apps.bot.services.object_service import ObjectService
from domain.entities.object import Object
from domain.entities.user import User


class TestObjectService:
    """Тесты для ObjectService."""
    
    @pytest.fixture
    def object_service(self):
        """Экземпляр ObjectService для тестов."""
        with patch('apps.bot.services.object_service.LocationValidator'):
            service = ObjectService()
            return service
    
    @pytest.fixture
    def mock_session(self):
        """Mock для сессии базы данных."""
        session = MagicMock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=None)
        return session
    
    @pytest.fixture
    def sample_user(self):
        """Тестовый пользователь."""
        user = User()
        user.id = 1
        user.telegram_id = 12345
        user.first_name = "Test"
        user.username = "testuser"
        return user
    
    @pytest.fixture
    def sample_object_data(self):
        """Тестовые данные объекта."""
        return {
            'name': 'Тестовый объект',
            'address': 'ул. Тестовая, 1',
            'coordinates': '55.7558,37.6176',
            'opening_time': '09:00',
            'closing_time': '18:00',
            'hourly_rate': 500.0,
            'owner_id': 12345
        }
    
    def test_init(self, object_service):
        """Тест инициализации ObjectService."""
        assert object_service is not None
        assert hasattr(object_service, 'location_validator')
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_create_object_success(self, mock_get_session, object_service, mock_session, sample_user, sample_object_data):
        """Тест успешного создания объекта."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock для валидации координат
        object_service.location_validator.validate_coordinates.return_value = {'valid': True}
        
        # Mock для поиска пользователя
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_session.execute.return_value = mock_result
        
        # Mock для созданного объекта
        created_object = Object(
            id=1,
            name=sample_object_data['name'],
            address=sample_object_data['address'],
            coordinates=sample_object_data['coordinates'],
            opening_time=time(9, 0),
            closing_time=time(18, 0),
            hourly_rate=sample_object_data['hourly_rate'],
            owner_id=sample_user.id
        )
        mock_session.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        
        # Выполняем тест
        result = object_service.create_object(**sample_object_data)
        
        # Проверяем результат
        assert result['success'] is True
        assert result['object_id'] == 1
        assert 'Тестовый объект' in result['message']
        
        # Проверяем вызовы
        object_service.location_validator.validate_coordinates.assert_called_once_with('55.7558,37.6176')
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
    
    def test_create_object_invalid_coordinates(self, object_service, sample_object_data):
        """Тест создания объекта с неверными координатами."""
        # Mock для валидации координат
        object_service.location_validator.validate_coordinates.return_value = {
            'valid': False,
            'error': 'Неверный формат координат'
        }
        
        # Выполняем тест
        result = object_service.create_object(**sample_object_data)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'Ошибка координат' in result['error']
        assert 'Неверный формат координат' in result['error']
    
    def test_create_object_invalid_time_format(self, object_service, sample_object_data):
        """Тест создания объекта с неверным форматом времени."""
        # Mock для валидации координат
        object_service.location_validator.validate_coordinates.return_value = {'valid': True}
        
        # Неверный формат времени
        sample_object_data['opening_time'] = 'invalid_time'
        
        # Выполняем тест
        result = object_service.create_object(**sample_object_data)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'Неверный формат времени' in result['error']
    
    def test_create_object_closing_before_opening(self, object_service, sample_object_data):
        """Тест создания объекта с временем закрытия раньше открытия."""
        # Mock для валидации координат
        object_service.location_validator.validate_coordinates.return_value = {'valid': True}
        
        # Время закрытия раньше открытия
        sample_object_data['opening_time'] = '18:00'
        sample_object_data['closing_time'] = '09:00'
        
        # Выполняем тест
        result = object_service.create_object(**sample_object_data)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'Время закрытия должно быть позже времени открытия' in result['error']
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_create_object_user_not_found(self, mock_get_session, object_service, mock_session, sample_object_data):
        """Тест создания объекта для несуществующего пользователя."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        object_service.location_validator.validate_coordinates.return_value = {'valid': True}
        
        # Mock для поиска пользователя - пользователь не найден
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Выполняем тест
        result = object_service.create_object(**sample_object_data)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'Пользователь не найден в базе данных' in result['error']
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_get_all_objects_success(self, mock_get_session, object_service, mock_session):
        """Тест получения всех объектов."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock объекты
        obj1 = Mock()
        obj1.id = 1
        obj1.name = 'Объект 1'
        obj1.address = 'Адрес 1'
        obj1.coordinates = '55.7558,37.6176'
        obj1.hourly_rate = 500.0
        obj1.opening_time = time(9, 0)
        obj1.closing_time = time(18, 0)
        obj1.is_active = True
        obj1.created_at = None
        obj1.max_distance_meters = 500
        
        obj2 = Mock()
        obj2.id = 2
        obj2.name = 'Объект 2'
        obj2.address = 'Адрес 2'
        obj2.coordinates = '55.7559,37.6177'
        obj2.hourly_rate = 600.0
        obj2.opening_time = time(8, 0)
        obj2.closing_time = time(20, 0)
        obj2.is_active = True
        obj2.created_at = None
        obj2.max_distance_meters = 300
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [obj1, obj2]
        mock_session.execute.return_value = mock_result
        
        # Выполняем тест
        result = object_service.get_all_objects()
        
        # Проверяем результат
        assert len(result) == 2
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Объект 1'
        assert result[0]['max_distance_meters'] == 500
        assert result[1]['id'] == 2
        assert result[1]['name'] == 'Объект 2'
        assert result[1]['max_distance_meters'] == 300
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_get_object_by_id_success(self, mock_get_session, object_service, mock_session):
        """Тест получения объекта по ID."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock объект
        obj = Mock()
        obj.id = 1
        obj.name = 'Тестовый объект'
        obj.address = 'Тестовый адрес'
        obj.coordinates = '55.7558,37.6176'
        obj.hourly_rate = 500.0
        obj.opening_time = time(9, 0)
        obj.closing_time = time(18, 0)
        obj.is_active = True
        obj.created_at = None
        obj.max_distance_meters = 400
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = obj
        mock_session.execute.return_value = mock_result
        
        # Выполняем тест
        result = object_service.get_object_by_id(1)
        
        # Проверяем результат
        assert result is not None
        assert result['id'] == 1
        assert result['name'] == 'Тестовый объект'
        assert result['max_distance_meters'] == 400
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_get_object_by_id_not_found(self, mock_get_session, object_service, mock_session):
        """Тест получения несуществующего объекта по ID."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Выполняем тест
        result = object_service.get_object_by_id(999)
        
        # Проверяем результат
        assert result is None
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_get_user_objects_success(self, mock_get_session, object_service, mock_session, sample_user):
        """Тест получения объектов пользователя."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock для поиска пользователя
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock объект пользователя
        obj = Mock()
        obj.id = 1
        obj.name = 'Объект пользователя'
        obj.address = 'Адрес'
        obj.coordinates = '55.7558,37.6176'
        obj.hourly_rate = 500.0
        obj.opening_time = time(9, 0)
        obj.closing_time = time(18, 0)
        obj.is_active = True
        obj.created_at = None
        obj.max_distance_meters = 500
        
        mock_objects_result = Mock()
        mock_objects_result.scalars.return_value.all.return_value = [obj]
        
        # Настраиваем последовательность вызовов execute
        mock_session.execute.side_effect = [mock_user_result, mock_objects_result]
        
        # Выполняем тест
        result = object_service.get_user_objects(12345)
        
        # Проверяем результат
        assert len(result) == 1
        assert result[0]['id'] == 1
        assert result[0]['name'] == 'Объект пользователя'
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_get_user_objects_user_not_found(self, mock_get_session, object_service, mock_session):
        """Тест получения объектов несуществующего пользователя."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        # Выполняем тест
        result = object_service.get_user_objects(99999)
        
        # Проверяем результат
        assert result == []
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_update_object_field_max_distance_success(self, mock_get_session, object_service, mock_session, sample_user):
        """Тест успешного обновления поля max_distance_meters."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock для поиска пользователя
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock объект
        obj = Mock()
        obj.id = 1
        obj.owner_id = sample_user.id
        obj.max_distance_meters = 500
        
        mock_object_result = Mock()
        mock_object_result.scalar_one_or_none.return_value = obj
        
        # Настраиваем последовательность вызовов execute
        mock_session.execute.side_effect = [mock_user_result, mock_object_result]
        
        # Выполняем тест
        result = object_service.update_object_field(1, 'max_distance_meters', '300', 12345)
        
        # Проверяем результат
        assert result['success'] is True
        assert obj.max_distance_meters == 300
        assert result['new_value'] == '300'
        mock_session.commit.assert_called_once()
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_update_object_field_invalid_distance(self, mock_get_session, object_service, mock_session, sample_user):
        """Тест обновления поля max_distance_meters с неверным значением."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock для поиска пользователя
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock объект
        obj = Mock()
        obj.id = 1
        obj.owner_id = sample_user.id
        
        mock_object_result = Mock()
        mock_object_result.scalar_one_or_none.return_value = obj
        
        # Настраиваем последовательность вызовов execute
        mock_session.execute.side_effect = [mock_user_result, mock_object_result]
        
        # Выполняем тест с неверным значением (слишком большое)
        result = object_service.update_object_field(1, 'max_distance_meters', '10000', 12345)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'от 10 до 5000 метров' in result['error']
    
    @patch('apps.bot.services.object_service.get_sync_session')
    def test_update_object_field_access_denied(self, mock_get_session, object_service, mock_session, sample_user):
        """Тест обновления объекта без прав доступа."""
        # Настраиваем моки
        mock_get_session.return_value = mock_session
        
        # Mock для поиска пользователя
        mock_user_result = Mock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock объект с другим владельцем
        obj = Mock()
        obj.id = 1
        obj.owner_id = 999  # Другой владелец
        
        mock_object_result = Mock()
        mock_object_result.scalar_one_or_none.return_value = obj
        
        # Настраиваем последовательность вызовов execute
        mock_session.execute.side_effect = [mock_user_result, mock_object_result]
        
        # Выполняем тест
        result = object_service.update_object_field(1, 'max_distance_meters', '300', 12345)
        
        # Проверяем результат
        assert result['success'] is False
        assert 'нет прав для редактирования' in result['error']
