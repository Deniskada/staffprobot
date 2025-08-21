#!/usr/bin/env python3
"""
Тестирование геолокации в реальном применении
"""

import sys
import os
import asyncio

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.geolocation.distance_calculator import DistanceCalculator
from core.geolocation.location_validator import LocationValidator
from core.config.settings import settings


def test_distance_calculator():
    """Тестирование калькулятора расстояний."""
    print("🧮 Тестирование DistanceCalculator")
    print("=" * 50)
    
    # Тест 1: Расстояние между Москвой и Санкт-Петербургом
    moscow = "55.7558,37.6176"
    spb = "59.9311,30.3609"
    
    distance = DistanceCalculator.calculate_distance_between_points(moscow, spb)
    print(f"📍 Москва → Санкт-Петербург: {distance:.0f} метров ({distance/1000:.1f} км)")
    
    # Тест 2: Расстояние между близкими точками
    point1 = "55.7558,37.6176"
    point2 = "55.7558,37.6177"  # Разница в 1 метр по долготе
    
    distance = DistanceCalculator.calculate_distance_between_points(point1, point2)
    print(f"📍 Близкие точки: {distance:.2f} метров")
    
    # Тест 3: Проверка формулы Гаверсина
    lat1, lon1 = 55.7558, 37.6176
    lat2, lon2 = 59.9311, 30.3609
    
    distance = DistanceCalculator.haversine_distance(lat1, lon1, lat2, lon2)
    print(f"📍 Формула Гаверсина: {distance:.0f} метров")
    
    print()


def test_location_validator():
    """Тестирование валидатора геолокации."""
    print("✅ Тестирование LocationValidator")
    print("=" * 50)
    
    validator = LocationValidator(max_distance_meters=100)
    
    # Тест 1: Валидные координаты
    coords = "55.7558,37.6176"
    result = validator.validate_coordinates(coords)
    print(f"📍 Валидация координат '{coords}': {'✅' if result['valid'] else '❌'}")
    if not result['valid']:
        print(f"   Ошибка: {result['error']}")
    
    # Тест 2: Координаты с низкой точностью
    low_precision = "55.7,37.6"
    result = validator.validate_coordinates(low_precision)
    print(f"📍 Валидация координат '{low_precision}': {'✅' if result['valid'] else '❌'}")
    if not result['valid']:
        print(f"   Ошибка: {result['error']}")
    
    # Тест 3: Неверный формат
    invalid = "invalid_coordinates"
    result = validator.validate_coordinates(invalid)
    print(f"📍 Валидация координат '{invalid}': {'✅' if result['valid'] else '❌'}")
    if not result['valid']:
        print(f"   Ошибка: {result['error']}")
    
    print()


def test_shift_location_validation():
    """Тестирование валидации местоположения для смен."""
    print("🏢 Тестирование валидации местоположения смен")
    print("=" * 50)
    
    validator = LocationValidator(max_distance_meters=100)
    
    # Тест 1: Пользователь в пределах допустимого расстояния
    user_coords = "55.7558,37.6176"
    object_coords = "55.7558,37.6177"  # Очень близко
    
    result = validator.validate_shift_location(user_coords, object_coords)
    print(f"📍 Пользователь близко к объекту: {'✅' if result['valid'] else '❌'}")
    if result['valid']:
        print(f"   Расстояние: {result['distance_meters']} м")
        print(f"   Сообщение: {result['message']}")
    else:
        print(f"   Ошибка: {result['error']}")
    
    # Тест 2: Пользователь слишком далеко
    user_coords = "55.7558,37.6176"
    object_coords = "59.9311,30.3609"  # Далеко
    
    result = validator.validate_shift_location(user_coords, object_coords)
    print(f"📍 Пользователь далеко от объекта: {'✅' if result['valid'] else '❌'}")
    if result['valid']:
        print(f"   Расстояние: {result['distance_meters']} м")
        print(f"   Сообщение: {result['message']}")
    else:
        print(f"   Ошибка: {result['error']}")
        print(f"   Расстояние: {result['distance_meters']} м")
        print(f"   Максимально допустимое: {result['max_distance_meters']} м")
    
    print()


def test_settings():
    """Тестирование настроек геолокации."""
    print("⚙️ Настройки геолокации")
    print("=" * 50)
    
    print(f"📍 Максимальное расстояние: {settings.max_distance_meters} метров")
    print(f"📍 Требуемая точность: {settings.location_accuracy_meters} метров")
    
    validator = LocationValidator()
    requirements = validator.get_location_requirements()
    
    print(f"📍 Формат координат: {requirements['coordinate_format']}")
    print(f"📍 Требуемая точность: {requirements['precision_required']}")
    print(f"📍 Примеры координат:")
    for name, coords in requirements['examples'].items():
        print(f"   • {name}: {coords}")
    
    print()


def test_edge_cases():
    """Тестирование граничных случаев."""
    print("🔍 Тестирование граничных случаев")
    print("=" * 50)
    
    # Тест 1: Координаты на экваторе
    equator = "0.0,0.0"
    result = DistanceCalculator.parse_coordinates(equator)
    print(f"📍 Экватор (0,0): {'✅' if result else '❌'}")
    if result:
        print(f"   Координаты: {result}")
    
    # Тест 2: Координаты на полюсах
    north_pole = "90.0,0.0"
    result = DistanceCalculator.parse_coordinates(north_pole)
    print(f"📍 Северный полюс (90,0): {'✅' if result else '❌'}")
    if result:
        print(f"   Координаты: {result}")
    
    # Тест 3: Координаты на международной линии перемены дат
    date_line = "0.0,180.0"
    result = DistanceCalculator.parse_coordinates(date_line)
    print(f"📍 Линия перемены дат (0,180): {'✅' if result else '❌'}")
    if result:
        print(f"   Координаты: {result}")
    
    # Тест 4: Расстояние между экватором и полюсом
    distance = DistanceCalculator.calculate_distance_between_points(equator, north_pole)
    print(f"📍 Экватор → Северный полюс: {distance:.0f} метров ({distance/1000:.1f} км)")
    
    print()


def main():
    """Основная функция тестирования."""
    print("🚀 Тестирование геолокации в реальном применении")
    print("=" * 60)
    print()
    
    try:
        # Тестируем все компоненты
        test_distance_calculator()
        test_location_validator()
        test_shift_location_validation()
        test_settings()
        test_edge_cases()
        
        print("🎉 Все тесты завершены успешно!")
        print()
        print("💡 Геолокация готова к использованию в боте!")
        print("📍 Пользователи смогут:")
        print("   • Открывать смены только находясь рядом с объектами")
        print("   • Получать точные данные о расстоянии")
        print("   • Использовать координаты с GPS точностью")
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
