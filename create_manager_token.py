#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')

import asyncio
from apps.web.services.auth_service import AuthService
from core.database.session import get_async_session

async def create_token():
    try:
        auth_service = AuthService()
        # Создаем токен для пользователя 5577223137 с ролью manager
        user_data = {
            'id': '5577223137',
            'telegram_id': '5577223137',
            'username': 'manager_user',
            'first_name': 'Manager',
            'last_name': 'User',
            'role': 'manager'
        }
        token = await auth_service.create_token(user_data)
        print(f'JWT Token: {token}')
        
        # Проверим токен
        decoded = await auth_service.verify_token(token)
        print(f'Decoded token: {decoded}')
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_token())
