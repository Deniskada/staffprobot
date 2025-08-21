#!/usr/bin/env python3
"""
Скрипт для тестирования API с базой данных
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

def test_create_user():
    """Тестирует создание пользователя."""
    print("\n👤 Тестируем создание пользователя...")
    user_data = {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Тест",
        "last_name": "Пользователь",
        "phone": "+79001234567",
        "role": "employee",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users", json=user_data)
        print(f"✅ Создание пользователя: {response.status_code}")
        print(f"📊 Ответ: {response.json()}")
        return response.json().get("user_id")
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        return None

def test_create_object(user_id):
    """Тестирует создание объекта."""
    print(f"\n🏢 Тестируем создание объекта для пользователя {user_id}...")
    object_data = {
        "name": "Тестовый объект",
        "owner_id": user_id,
        "address": "ул. Тестовая, 1",
        "coordinates": "55.7558,37.6176",
        "opening_time": "09:00:00",
        "closing_time": "18:00:00",
        "hourly_rate": 500.00,
        "required_employees": "Охранник, уборщик",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/objects", json=object_data)
        print(f"✅ Создание объекта: {response.status_code}")
        print(f"📊 Ответ: {response.json()}")
        return response.json().get("object_id")
    except Exception as e:
        print(f"❌ Ошибка создания объекта: {e}")
        return None

def test_get_objects():
    """Тестирует получение списка объектов."""
    print("\n📋 Тестируем получение списка объектов...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/objects")
        print(f"✅ Получение объектов: {response.status_code}")
        data = response.json()
        print(f"📊 Количество объектов: {data.get('count', 0)}")
        if data.get('objects'):
            for obj in data['objects']:
                print(f"  - {obj['name']} (ID: {obj['id']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка получения объектов: {e}")
        return False

def test_get_users():
    """Тестирует получение списка пользователей."""
    print("\n👥 Тестируем получение списка пользователей...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users")
        print(f"✅ Получение пользователей: {response.status_code}")
        data = response.json()
        print(f"📊 Количество пользователей: {data.get('count', 0)}")
        if data.get('users'):
            for user in data['users']:
                print(f"  - {user['first_name']} {user['last_name']} (ID: {user['id']})")
        return True
    except Exception as e:
        print(f"❌ Ошибка получения пользователей: {e}")
        return False

def test_create_shift(user_id, object_id):
    """Тестирует создание смены."""
    print(f"\n⏰ Тестируем создание смены для пользователя {user_id} на объекте {object_id}...")
    from datetime import datetime, timedelta
    
    shift_data = {
        "user_id": user_id,
        "object_id": object_id,
        "start_time": datetime.now().isoformat(),
        "status": "active",
        "start_coordinates": "55.7558,37.6176",
        "hourly_rate": 500.00,
        "notes": "Тестовая смена"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/shifts", json=shift_data)
        print(f"✅ Создание смены: {response.status_code}")
        print(f"📊 Ответ: {response.json()}")
        return response.json().get("shift_id")
    except Exception as e:
        print(f"❌ Ошибка создания смены: {e}")
        return None

def main():
    """Главная функция тестирования."""
    print("🚀 Начинаем тестирование API с базой данных...")
    print(f"📍 API URL: {BASE_URL}")
    
    # Ждем немного, чтобы API успел запуститься
    print("⏳ Ждем 3 секунды для запуска API...")
    time.sleep(3)
    
    # Тестируем health check
    if not test_health():
        print("❌ API недоступен, прекращаем тестирование")
        return
    
    # Тестируем создание пользователя
    user_id = test_create_user()
    if not user_id:
        print("❌ Не удалось создать пользователя, прекращаем тестирование")
        return
    
    # Тестируем создание объекта
    object_id = test_create_object(user_id)
    if not object_id:
        print("❌ Не удалось создать объект, прекращаем тестирование")
        return
    
    # Тестируем создание смены
    shift_id = test_create_shift(user_id, object_id)
    if not shift_id:
        print("❌ Не удалось создать смену")
    
    # Тестируем получение данных
    test_get_objects()
    test_get_users()
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    main()
