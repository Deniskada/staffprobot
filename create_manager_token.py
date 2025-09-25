#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')

import asyncio
from apps.web.services.auth_service import AuthService
from apps.web.database import get_async_session

async def create_token():
    try:
        async with get_async_session() as db:
            auth_service = AuthService(db)
            # Создаем токен для пользователя 5577223137 с ролью manager
            token = await auth_service.create_access_token({'id': '5577223137', 'role': 'manager'})
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
