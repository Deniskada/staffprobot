"""Зависимости для веб-приложения."""

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from typing import List, Optional
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.user import User
from apps.web.services.auth_service import AuthService

auth_service = AuthService()


def get_current_user_dependency():
    """Фабрика для создания зависимости get_current_user."""
    async def get_current_user(request: Request) -> Optional[User]:
        """Получение текущего пользователя из сессии."""
        # Получаем токен из cookies
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        try:
            # Верифицируем токен
            user_data = await auth_service.verify_token(token)
            if not user_data:
                return None
            
            # Получаем пользователя из базы данных
            async with get_async_session() as session:
                # Используем telegram_id для поиска пользователя
                telegram_id = user_data.get("telegram_id")
                if not telegram_id:
                    return None
                    
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
                return user
        except Exception:
            return None
    
    return get_current_user


async def require_auth(request: Request, current_user: Optional[User] = Depends(get_current_user_dependency())):
    """Проверка авторизации пользователя."""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    return current_user


def require_role(roles: List[str]):
    """Декоратор для проверки роли пользователя."""
    async def role_checker(request: Request, current_user: Optional[User] = Depends(get_current_user_dependency())):
        if not current_user:
            return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
        
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав доступа"
            )
        return current_user
    return role_checker
