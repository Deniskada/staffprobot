#!/usr/bin/env python3
"""Создание JWT токена для модератора."""

import asyncio
import sys
import os

# Добавляем корневую директорию проекта в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database.session import get_async_session
from apps.web.services.auth_service import AuthService

async def create_moderator_token():
    """Создание JWT токена для модератора."""
    try:
        # Получаем сессию БД
        async with get_async_session() as session:
            # Создаем сервис аутентификации
            auth_service = AuthService()
            
            # Данные пользователя-модератора (ID=4, telegram_id=1821645654)
            user_data = {
                "id": 1821645654,  # telegram_id
                "telegram_id": 1821645654,
                "username": "denisinovikov",
                "first_name": "Дрим",
                "last_name": "Байкер",
                "role": "superadmin",
                "roles": ["superadmin", "moderator"]
            }
            
            # Создаем токен
            token = await auth_service.create_token(user_data)
            
            print(f"JWT Token: {token}")
            
            # Декодируем токен для проверки
            decoded = await auth_service.verify_token(token)
            print(f"Decoded token: {decoded}")
            
    except Exception as e:
        print(f"Error creating moderator token: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(create_moderator_token())
