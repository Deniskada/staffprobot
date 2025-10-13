#!/usr/bin/env python3
"""Создание JWT токена для администратора."""

import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.session import get_async_session
from apps.web.services.auth_service import AuthService

async def create_admin_token():
    """Создание JWT токена для администратора."""
    try:
        # Получаем сессию БД
        async with get_async_session() as session:
            # Создаем сервис аутентификации
            auth_service = AuthService()
            
            # Данные пользователя-администратора
            user_data = {
                "id": 123456789,  # telegram_id (замените на свой)
                "telegram_id": 123456789,
                "username": "admin",
                "first_name": "Администратор",
                "last_name": "Системы",
                "role": "superadmin",
                "roles": ["superadmin", "admin", "moderator"]
            }
            
            # Создаем токен
            token = await auth_service.create_token(user_data)
            
            print(f"JWT Token для администратора: {token}")
            print(f"\nДля входа в систему:")
            print(f"1. Откройте браузер и перейдите по адресу: http://localhost:8001")
            print(f"2. Введите токен в поле авторизации")
            print(f"\nТокен действителен в течение {auth_service.token_expire_minutes} минут")
            
            # Декодируем токен для проверки
            decoded = await auth_service.verify_token(token)
            print(f"\nДекодированный токен: {decoded}")
            
    except Exception as e:
        print(f"Ошибка создания токена администратора: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(create_admin_token())


