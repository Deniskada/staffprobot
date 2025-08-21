#!/usr/bin/env python3
"""
Ручное тестирование API сервера
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_manual():
    """Ручное тестирование API."""
    print("🔍 Ручное тестирование API сервера...")
    
    # 1. Health check
    print("\n1️⃣ Health check:")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 2. Корневой endpoint
    print("\n2️⃣ Корневой endpoint:")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 3. Создание объекта
    print("\n3️⃣ Создание объекта:")
    object_data = {
        "name": "Новый тестовый объект",
        "owner_id": 2,
        "address": "ул. Тестовая, 100",
        "coordinates": "55.7558,37.6176",
        "opening_time": "08:00:00",
        "closing_time": "22:00:00",
        "hourly_rate": 750.00,
        "required_employees": "Охранник, менеджер",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/objects", json=object_data)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 4. Получение списка объектов
    print("\n4️⃣ Список объектов:")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/objects")
        print(f"   Статус: {response.status_code}")
        data = response.json()
        print(f"   Количество: {data.get('count', 0)}")
        if data.get('objects'):
            for obj in data['objects']:
                print(f"   - {obj['name']} (ID: {obj['id']}, адрес: {obj['address']})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 5. Создание пользователя
    print("\n5️⃣ Создание пользователя:")
    user_data = {
        "telegram_id": 111222333,
        "username": "test_employee",
        "first_name": "Иван",
        "last_name": "Иванов",
        "phone": "+79005554433",
        "role": "employee",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/users", json=user_data)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 6. Получение списка пользователей
    print("\n6️⃣ Список пользователей:")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/users")
        print(f"   Статус: {response.status_code}")
        data = response.json()
        print(f"   Количество: {data.get('count', 0)}")
        if data.get('users'):
            for user in data['users']:
                print(f"   - {user['first_name']} {user['last_name']} (ID: {user['id']}, роль: {user['role']})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 7. Создание смены
    print("\n7️⃣ Создание смены:")
    shift_data = {
        "user_id": 2,
        "object_id": 2,
        "start_time": "2025-01-20T14:00:00",
        "status": "active",
        "start_coordinates": "55.7558,37.6176",
        "hourly_rate": 750.00,
        "notes": "Тестовая смена для нового объекта"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/shifts", json=shift_data)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 8. Получение списка смен
    print("\n8️⃣ Список смен:")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/shifts")
        print(f"   Статус: {response.status_code}")
        data = response.json()
        print(f"   Количество: {data.get('count', 0)}")
        if data.get('shifts'):
            for shift in data['shifts']:
                print(f"   - Смена {shift['id']} (статус: {shift['status']}, пользователь: {shift['user_id']})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # 9. Тест несуществующего endpoint
    print("\n9️⃣ Тест несуществующего endpoint:")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/nonexistent")
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    print("\n✅ Ручное тестирование завершено!")

if __name__ == "__main__":
    test_manual()
