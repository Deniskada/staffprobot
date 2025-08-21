#!/usr/bin/env python3
"""
Тестовый скрипт для API с заглушками
"""

import requests
import json
import time

# Базовый URL API
BASE_URL = "http://localhost:8000"

def test_health():
    """Тестирует health check endpoint."""
    print("🔍 Тестируем health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"📊 Ответ: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Ошибка health check: {e}")
        return False

def test_root():
    """Тестирует корневой endpoint."""
    print("\n🏠 Тестируем корневой endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Root endpoint: {response.status_code}")
        print(f"📊 Ответ: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Ошибка root endpoint: {e}")
        return False

def test_get_objects():
    """Тестирует получение списка объектов."""
    print("\n📋 Тестируем получение списка объектов...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/objects")
        print(f"✅ Получение объектов: {response.status_code}")
        data = response.json()
        print(f"📊 Количество объектов: {data.get('count', 0)}")
        print(f"📝 Сообщение: {data.get('message', 'N/A')}")
        if data.get('objects'):
            for obj in data['objects']:
                print(f"  - {obj['name']} (ID: {obj['id']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка получения объектов: {e}")
        return False

def test_get_object_by_id():
    """Тестирует получение объекта по ID."""
    print("\n🔍 Тестируем получение объекта по ID...")
    try:
        # Тестируем существующий объект
        response = requests.get(f"{BASE_URL}/api/v1/objects/1")
        print(f"✅ Получение объекта 1: {response.status_code}")
        data = response.json()
        print(f"📊 Объект: {data.get('name', 'N/A')} (ID: {data.get('id', 'N/A')})")
        
        # Тестируем несуществующий объект
        response = requests.get(f"{BASE_URL}/api/v1/objects/999")
        print(f"✅ Получение объекта 999: {response.status_code}")
        data = response.json()
        print(f"📊 Ошибка: {data.get('message', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка получения объекта по ID: {e}")
        return False

def test_get_users():
    """Тестирует получение списка пользователей."""
    print("\n👥 Тестируем получение списка пользователей...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users")
        print(f"✅ Получение пользователей: {response.status_code}")
        data = response.json()
        print(f"📊 Количество пользователей: {data.get('count', 0)}")
        print(f"📝 Сообщение: {data.get('message', 'N/A')}")
        if data.get('users'):
            for user in data['users']:
                print(f"  - {user['first_name']} {user['last_name']} (ID: {user['id']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка получения пользователей: {e}")
        return False

def test_get_user_by_id():
    """Тестирует получение пользователя по ID."""
    print("\n🔍 Тестируем получение пользователя по ID...")
    try:
        # Тестируем существующего пользователя
        response = requests.get(f"{BASE_URL}/api/v1/users/1")
        print(f"✅ Получение пользователя 1: {response.status_code}")
        data = response.json()
        print(f"📊 Пользователь: {data.get('first_name', 'N/A')} {data.get('last_name', 'N/A')} (ID: {data.get('id', 'N/A')})")
        
        # Тестируем несуществующего пользователя
        response = requests.get(f"{BASE_URL}/api/v1/users/999")
        print(f"✅ Получение пользователя 999: {response.status_code}")
        data = response.json()
        print(f"📊 Ошибка: {data.get('message', 'N/A')}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка получения пользователя по ID: {e}")
        return False

def test_get_shifts():
    """Тестирует получение списка смен."""
    print("\n⏰ Тестируем получение списка смен...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/shifts")
        print(f"✅ Получение смен: {response.status_code}")
        data = response.json()
        print(f"📊 Количество смен: {data.get('count', 0)}")
        print(f"📝 Сообщение: {data.get('message', 'N/A')}")
        if data.get('shifts'):
            for shift in data['shifts']:
                print(f"  - Смена {shift['id']} (статус: {shift['status']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка получения смен: {e}")
        return False

def test_create_object():
    """Тестирует создание объекта."""
    print("\n🏢 Тестируем создание объекта...")
    object_data = {
        "name": "Новый объект",
        "owner_id": 1,
        "address": "ул. Новая, 2",
        "coordinates": "55.7558,37.6176",
        "opening_time": "08:00:00",
        "closing_time": "20:00:00",
        "hourly_rate": 600.00,
        "required_employees": "Охранник",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/objects", json=object_data)
        print(f"✅ Создание объекта: {response.status_code}")
        data = response.json()
        print(f"📊 Ответ: {data}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания объекта: {e}")
        return False

def test_create_user():
    """Тестирует создание пользователя."""
    print("\n👤 Тестируем создание пользователя...")
    user_data = {
        "telegram_id": 987654321,
        "username": "new_user",
        "first_name": "Новый",
        "last_name": "Пользователь",
        "phone": "+79009876543",
        "role": "manager",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users", json=user_data)
        print(f"✅ Создание пользователя: {response.status_code}")
        data = response.json()
        print(f"📊 Ответ: {data}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        return False

def test_create_shift():
    """Тестирует создание смены."""
    print("\n⏰ Тестируем создание смены...")
    from datetime import datetime
    
    shift_data = {
        "user_id": 1,
        "object_id": 1,
        "start_time": datetime.now().isoformat(),
        "status": "active",
        "start_coordinates": "55.7558,37.6176",
        "hourly_rate": 500.00,
        "notes": "Тестовая смена"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/shifts", json=shift_data)
        print(f"✅ Создание смены: {response.status_code}")
        data = response.json()
        print(f"📊 Ответ: {data}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания смены: {e}")
        return False

def main():
    """Главная функция тестирования."""
    print("🚀 Начинаем тестирование API с заглушками...")
    print(f"📍 API URL: {BASE_URL}")
    
    # Ждем немного, чтобы API успел запуститься
    print("⏳ Ждем 3 секунды для запуска API...")
    time.sleep(3)
    
    # Тестируем health check
    if not test_health():
        print("❌ API недоступен, прекращаем тестирование")
        return
    
    # Тестируем корневой endpoint
    test_root()
    
    # Тестируем GET endpoints
    test_get_objects()
    test_get_object_by_id()
    test_get_users()
    test_get_user_by_id()
    test_get_shifts()
    
    # Тестируем POST endpoints
    test_create_object()
    test_create_user()
    test_create_shift()
    
    print("\n✅ Тестирование завершено!")
    print("📝 Примечание: Все данные являются заглушками, база данных недоступна")

if __name__ == "__main__":
    main()
