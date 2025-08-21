"""Сервис для расчета расстояний между географическими координатами."""

import math
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DistanceCalculator:
    """Калькулятор расстояний между географическими координатами."""
    
    # Радиус Земли в метрах
    EARTH_RADIUS_METERS = 6371000
    
    @staticmethod
    def haversine_distance(
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Вычисляет расстояние между двумя точками на сфере (формула Гаверсина).
        
        Args:
            lat1: Широта первой точки в градусах
            lon1: Долгота первой точки в градусах
            lat2: Широта второй точки в градусах
            lon2: Долгота второй точки в градусах
            
        Returns:
            Расстояние в метрах
        """
        try:
            # Конвертируем градусы в радианы
            lat1_rad = math.radians(lat1)
            lon1_rad = math.radians(lon1)
            lat2_rad = math.radians(lat2)
            lon2_rad = math.radians(lon2)
            
            # Разности координат
            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad
            
            # Формула Гаверсина
            a = (math.sin(dlat / 2) ** 2 + 
                 math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            distance = DistanceCalculator.EARTH_RADIUS_METERS * c
            
            logger.debug(
                f"Distance calculated: {distance:.2f}m between ({lat1}, {lon1}) and ({lat2}, {lon2})"
            )
            
            return distance
            
        except Exception as e:
            logger.error(
                f"Error calculating distance between ({lat1}, {lon1}) and ({lat2}, {lon2}): {e}"
            )
            raise
    
    @staticmethod
    def parse_coordinates(coordinates: str) -> Optional[Tuple[float, float]]:
        """
        Парсит координаты из строки формата 'lat,lon'.
        
        Args:
            coordinates: Строка с координатами
            
        Returns:
            Кортеж (широта, долгота) или None при ошибке
        """
        try:
            if not coordinates or ',' not in coordinates:
                return None
                
            lat_str, lon_str = coordinates.split(',', 1)
            lat = float(lat_str.strip())
            lon = float(lon_str.strip())
            
            # Валидация диапазонов
            if not (-90 <= lat <= 90):
                logger.warning(f"Invalid latitude: {lat}")
                return None
                
            if not (-180 <= lon <= 180):
                logger.warning(f"Invalid longitude: {lon}")
                return None
            
            return (lat, lon)
            
        except (ValueError, AttributeError) as e:
            logger.error(f"Error parsing coordinates '{coordinates}': {e}")
            return None
    
    @staticmethod
    def calculate_distance_between_points(
        point1: str, 
        point2: str
    ) -> Optional[float]:
        """
        Вычисляет расстояние между двумя точками в строковом формате.
        
        Args:
            point1: Координаты первой точки ('lat,lon')
            point2: Координаты второй точки ('lat,lon')
            
        Returns:
            Расстояние в метрах или None при ошибке
        """
        try:
            coords1 = DistanceCalculator.parse_coordinates(point1)
            coords2 = DistanceCalculator.parse_coordinates(point2)
            
            if coords1 is None or coords2 is None:
                return None
            
            lat1, lon1 = coords1
            lat2, lon2 = coords2
            
            return DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)
            
        except Exception as e:
            logger.error(
                f"Error calculating distance between points '{point1}' and '{point2}': {e}"
            )
            return None
    
    @staticmethod
    def is_within_distance(
        point1: str, 
        point2: str, 
        max_distance_meters: float
    ) -> bool:
        """
        Проверяет, находится ли точка1 в пределах указанного расстояния от точки2.
        
        Args:
            point1: Координаты первой точки ('lat,lon')
            point2: Координаты второй точки ('lat,lon')
            max_distance_meters: Максимальное расстояние в метрах
            
        Returns:
            True, если точки находятся в пределах указанного расстояния
        """
        try:
            distance = DistanceCalculator.calculate_distance_between_points(point1, point2)
            
            if distance is None:
                return False
            
            is_within = distance <= max_distance_meters
            
            logger.debug(
                f"Distance check completed: {distance:.2f}m between '{point1}' and '{point2}', "
                f"max allowed: {max_distance_meters}m, within range: {is_within}"
            )
            
            return is_within
            
        except Exception as e:
            logger.error(
                f"Error checking distance constraint between '{point1}' and '{point2}', "
                f"max allowed: {max_distance_meters}m: {e}"
            )
            return False
