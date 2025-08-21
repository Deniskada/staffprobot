"""Unit-тесты для геолокационных сервисов."""

import pytest
from core.geolocation.distance_calculator import DistanceCalculator
from core.geolocation.location_validator import LocationValidator


class TestDistanceCalculator:
    """Тесты для калькулятора расстояний."""
    
    def test_parse_coordinates_valid(self):
        """Тест парсинга валидных координат."""
        coords = "55.7558,37.6176"
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is not None
        assert result == (55.7558, 37.6176)
    
    def test_parse_coordinates_invalid_format(self):
        """Тест парсинга неверного формата координат."""
        coords = "55.7558"
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is None
    
    def test_parse_coordinates_invalid_latitude(self):
        """Тест парсинга неверной широты."""
        coords = "91.0,37.6176"
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is None
    
    def test_parse_coordinates_invalid_longitude(self):
        """Тест парсинга неверной долготы."""
        coords = "55.7558,181.0"
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is None
    
    def test_parse_coordinates_empty(self):
        """Тест парсинга пустых координат."""
        coords = ""
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is None
    
    def test_parse_coordinates_none(self):
        """Тест парсинга None координат."""
        coords = None
        result = DistanceCalculator.parse_coordinates(coords)
        
        assert result is None
    
    def test_haversine_distance_same_point(self):
        """Тест расчета расстояния до той же точки."""
        lat1, lon1 = 55.7558, 37.6176
        lat2, lon2 = 55.7558, 37.6176
        
        distance = DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)
        
        assert distance == 0.0
    
    def test_haversine_distance_moscow_spb(self):
        """Тест расчета расстояния между Москвой и Санкт-Петербургом."""
        # Москва
        lat1, lon1 = 55.7558, 37.6176
        # Санкт-Петербург
        lat2, lon2 = 59.9311, 30.3609
        
        distance = DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)
        
        # Расстояние должно быть примерно 635 км
        assert 600000 < distance < 700000
    
    def test_calculate_distance_between_points_valid(self):
        """Тест расчета расстояния между точками в строковом формате."""
        point1 = "55.7558,37.6176"
        point2 = "59.9311,30.3609"
        
        distance = DistanceCalculator.calculate_distance_between_points(point1, point2)
        
        assert distance is not None
        assert distance > 0
    
    def test_calculate_distance_between_points_invalid(self):
        """Тест расчета расстояния с неверными координатами."""
        point1 = "invalid,coordinates"
        point2 = "55.7558,37.6176"
        
        distance = DistanceCalculator.calculate_distance_between_points(point1, point2)
        
        assert distance is None
    
    def test_is_within_distance_true(self):
        """Тест проверки расстояния в пределах допустимого."""
        point1 = "55.7558,37.6176"
        point2 = "55.7558,37.6177"  # Очень близко
        
        result = DistanceCalculator.is_within_distance(point1, point2, 100)
        
        assert result is True
    
    def test_is_within_distance_false(self):
        """Тест проверки расстояния за пределами допустимого."""
        point1 = "55.7558,37.6176"
        point2 = "59.9311,30.3609"  # Далеко
        
        result = DistanceCalculator.is_within_distance(point1, point2, 100)
        
        assert result is False


class TestLocationValidator:
    """Тесты для валидатора геолокации."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.validator = LocationValidator(max_distance_meters=100)
    
    def test_validate_coordinates_valid(self):
        """Тест валидации валидных координат."""
        coords = "55.7558,37.6176"
        result = self.validator.validate_coordinates(coords)
        
        assert result['valid'] is True
        assert result['lat'] == 55.7558
        assert result['lon'] == 37.6176
        assert 'parsed_coords' in result
    
    def test_validate_coordinates_invalid_format(self):
        """Тест валидации неверного формата координат."""
        coords = "invalid"
        result = self.validator.validate_coordinates(coords)
        
        assert result['valid'] is False
        assert 'error' in result
    
    def test_validate_coordinates_low_precision(self):
        """Тест валидации координат с низкой точностью."""
        coords = "55.7,37.6"
        result = self.validator.validate_coordinates(coords)
        
        assert result['valid'] is False
        assert 'error' in result
    
    def test_validate_shift_location_valid(self):
        """Тест валидации местоположения смены - валидное."""
        user_coords = "55.7558,37.6176"
        object_coords = "55.7558,37.6177"  # Очень близко
        
        result = self.validator.validate_shift_location(user_coords, object_coords)
        
        assert result['valid'] is True
        assert result['is_within_distance'] is True
        assert 'message' in result
        assert 'distance_meters' in result
    
    def test_validate_shift_location_too_far(self):
        """Тест валидации местоположения смены - слишком далеко."""
        user_coords = "55.7558,37.6176"
        object_coords = "59.9311,30.3609"  # Далеко
        
        result = self.validator.validate_shift_location(user_coords, object_coords)
        
        assert result['valid'] is False
        assert result['is_within_distance'] is False
        assert 'error' in result
        assert 'distance_meters' in result
    
    def test_validate_shift_location_invalid_user_coords(self):
        """Тест валидации местоположения с неверными координатами пользователя."""
        user_coords = "invalid"
        object_coords = "55.7558,37.6176"
        
        result = self.validator.validate_shift_location(user_coords, object_coords)
        
        assert result['valid'] is False
        assert 'error' in result
    
    def test_validate_shift_location_invalid_object_coords(self):
        """Тест валидации местоположения с неверными координатами объекта."""
        user_coords = "55.7558,37.6176"
        object_coords = "invalid"
        
        result = self.validator.validate_shift_location(user_coords, object_coords)
        
        assert result['valid'] is False
        assert 'error' in result
    
    def test_get_location_requirements(self):
        """Тест получения требований к геолокации."""
        requirements = self.validator.get_location_requirements()
        
        assert 'max_distance_meters' in requirements
        assert 'accuracy_meters' in requirements
        assert 'coordinate_format' in requirements
        assert 'precision_required' in requirements
        assert 'examples' in requirements
        
        assert requirements['max_distance_meters'] == 100
        assert requirements['accuracy_meters'] == 50
    
    def test_coordinate_accuracy_check(self):
        """Тест проверки точности координат."""
        # Координаты с достаточной точностью
        lat, lon = 55.7558, 37.6176
        result = self.validator._check_coordinate_accuracy(lat, lon)
        
        assert result is True
        
        # Координаты с недостаточной точностью
        lat, lon = 55.7, 37.6
        result = self.validator._check_coordinate_accuracy(lat, lon)
        
        assert result is False


class TestGeolocationIntegration:
    """Интеграционные тесты для геолокации."""
    
    def test_full_shift_location_validation_flow(self):
        """Тест полного процесса валидации местоположения для смены."""
        validator = LocationValidator(max_distance_meters=100)
        
        # Валидные координаты пользователя и объекта
        user_coords = "55.7558,37.6176"
        object_coords = "55.7558,37.6177"
        
        # Валидируем координаты пользователя
        user_validation = validator.validate_coordinates(user_coords)
        assert user_validation['valid'] is True
        
        # Валидируем координаты объекта
        object_validation = validator.validate_coordinates(object_coords)
        assert object_validation['valid'] is True
        
        # Валидируем местоположение для смены
        shift_validation = validator.validate_shift_location(user_coords, object_coords)
        assert shift_validation['valid'] is True
        assert shift_validation['is_within_distance'] is True
    
    def test_distance_calculation_consistency(self):
        """Тест консистентности расчета расстояний."""
        # Тестируем, что расстояние A->B равно расстоянию B->A
        point1 = "55.7558,37.6176"
        point2 = "59.9311,30.3609"
        
        distance1 = DistanceCalculator.calculate_distance_between_points(point1, point2)
        distance2 = DistanceCalculator.calculate_distance_between_points(point2, point1)
        
        assert distance1 is not None
        assert distance2 is not None
        assert abs(distance1 - distance2) < 0.1  # Разница должна быть минимальной
    
    def test_edge_cases(self):
        """Тест граничных случаев."""
        # Координаты на экваторе
        equator_coords = "0.0,0.0"
        result = DistanceCalculator.parse_coordinates(equator_coords)
        assert result == (0.0, 0.0)
        
        # Координаты на полюсах
        north_pole = "90.0,0.0"
        result = DistanceCalculator.parse_coordinates(north_pole)
        assert result == (90.0, 0.0)
        
        # Координаты на международной линии перемены дат
        date_line = "0.0,180.0"
        result = DistanceCalculator.parse_coordinates(date_line)
        assert result == (0.0, 180.0)
