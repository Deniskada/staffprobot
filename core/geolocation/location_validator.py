"""Сервис для валидации геолокации при работе со сменами."""

from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)
from core.config.settings import settings
from .distance_calculator import DistanceCalculator


class LocationValidator:
    """Валидатор геолокации для смен."""
    
    def __init__(self, max_distance_meters: Optional[int] = None):
        """
        Инициализация валидатора.
        
        Args:
            max_distance_meters: Максимальное расстояние в метрах (по умолчанию из настроек)
        """
        self.max_distance_meters = max_distance_meters or settings.max_distance_meters
        self.accuracy_meters = settings.location_accuracy_meters
        
        logger.info(
            f"LocationValidator initialized with max_distance={self.max_distance_meters}m, "
            f"accuracy={self.accuracy_meters}m"
        )
    
    def validate_coordinates(self, coordinates: str) -> Dict[str, Any]:
        """
        Валидирует формат и корректность координат.
        
        Args:
            coordinates: Строка с координатами в формате 'lat,lon'
            
        Returns:
            Словарь с результатом валидации
        """
        try:
            # Парсим координаты
            coords = DistanceCalculator.parse_coordinates(coordinates)
            
            if coords is None:
                return {
                    'valid': False,
                    'error': 'Неверный формат координат. Используйте формат: широта,долгота',
                    'coordinates': coordinates
                }
            
            lat, lon = coords
            
            # Проверяем точность координат (более мягкая проверка для реальных GPS)
            if not self._check_coordinate_accuracy(lat, lon):
                # Для реальных GPS координат из Telegram делаем предупреждение, но не блокируем
                logger.warning(
                    f"Low precision coordinates detected: {coordinates} "
                    f"(lat_precision: {len(str(lat).split('.')[-1]) if '.' in str(lat) else 0}, "
                    f"lon_precision: {len(str(lon).split('.')[-1]) if '.' in str(lon) else 0})"
                )
            
            return {
                'valid': True,
                'coordinates': coordinates,
                'lat': lat,
                'lon': lon,
                'parsed_coords': coords
            }
            
        except Exception as e:
            logger.error(
                f"Error validating coordinates '{coordinates}': {e}"
            )
            return {
                'valid': False,
                'error': f'Ошибка валидации координат: {str(e)}',
                'coordinates': coordinates
            }
    
    def validate_shift_location(
        self, 
        user_coordinates: str, 
        object_coordinates: str,
        max_distance_meters: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Валидирует местоположение пользователя относительно объекта.
        
        Args:
            user_coordinates: Координаты пользователя
            object_coordinates: Координаты объекта
            max_distance_meters: Максимальное расстояние в метрах (если не указано, используется из настроек)
            
        Returns:
            Словарь с результатом валидации
        """
        try:
            # Валидируем координаты пользователя
            user_validation = self.validate_coordinates(user_coordinates)
            if not user_validation['valid']:
                return user_validation
            
            # Валидируем координаты объекта
            object_validation = self.validate_coordinates(object_coordinates)
            if not object_validation['valid']:
                return object_validation
            
            # Вычисляем расстояние
            distance = DistanceCalculator.calculate_distance_between_points(
                user_coordinates, object_coordinates
            )
            
            if distance is None:
                return {
                    'valid': False,
                    'error': 'Не удалось вычислить расстояние между точками',
                    'user_coordinates': user_coordinates,
                    'object_coordinates': object_coordinates
                }
            
            # Используем переданное значение или значение по умолчанию
            max_distance = max_distance_meters or self.max_distance_meters
            
            # Проверяем, находится ли пользователь в пределах допустимого расстояния
            is_within_distance = distance <= max_distance
            
            result = {
                'valid': is_within_distance,
                'distance_meters': round(distance, 2),
                'max_distance_meters': max_distance,
                'is_within_distance': is_within_distance,
                'user_coordinates': user_coordinates,
                'object_coordinates': object_coordinates,
                'user_lat': user_validation['lat'],
                'user_lon': user_validation['lon'],
                'object_lat': object_validation['lat'],
                'object_lon': object_validation['lon']
            }
            
            if is_within_distance:
                result['message'] = f'Местоположение подтверждено. Расстояние: {result["distance_meters"]} м'
            else:
                result['error'] = (
                    f'Вы находитесь слишком далеко от объекта. '
                    f'Расстояние: {result["distance_meters"]} м, '
                    f'максимально допустимое: {self.max_distance_meters} м'
                )
            
            logger.info(
                f"Shift location validation completed: distance={distance:.2f}m, "
                f"within range: {is_within_distance}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Error validating shift location between '{user_coordinates}' and '{object_coordinates}': {e}"
            )
            return {
                'valid': False,
                'error': f'Ошибка валидации местоположения: {str(e)}',
                'user_coordinates': user_coordinates,
                'object_coordinates': object_coordinates
            }
    
    def _check_coordinate_accuracy(self, lat: float, lon: float) -> bool:
        """
        Проверяет точность координат.
        
        Args:
            lat: Широта
            lon: Долгота
            
        Returns:
            True, если координаты достаточно точные
        """
        # Для простоты проверяем количество знаков после запятой
        # Более точная проверка может включать анализ GPS точности
        lat_str = str(lat)
        lon_str = str(lon)
        
        # Проверяем, что координаты имеют достаточную точность
        # Обычно GPS дает точность до 5-6 знаков после запятой
        lat_precision = len(lat_str.split('.')[-1]) if '.' in lat_str else 0
        lon_precision = len(lon_str.split('.')[-1]) if '.' in lon_str else 0
        
        # Минимальная точность: 2 знака после запятой (~1 км) - более мягкая для реальных GPS
        min_precision = 2
        
        return lat_precision >= min_precision and lon_precision >= min_precision
    
    def get_location_requirements(self) -> Dict[str, Any]:
        """
        Возвращает требования к геолокации.
        
        Returns:
            Словарь с требованиями
        """
        return {
            'max_distance_meters': self.max_distance_meters,
            'accuracy_meters': self.accuracy_meters,
            'coordinate_format': 'широта,долгота (например: 55.7558,37.6176)',
            'precision_required': 'минимум 4 знака после запятой',
            'examples': {
                'moscow_center': '55.7558,37.6176',
                'spb_center': '59.9311,30.3609',
                'novosibirsk_center': '55.0084,82.9357'
            }
        }
