"""Middleware для проверки авторизации и ролей."""

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Optional, List
from core.auth.user_manager import user_manager
from apps.web.services.auth_service import AuthService
from domain.entities.user import UserRole
from core.logging.logger import logger


class AuthMiddleware:
    """Middleware для проверки авторизации и ролей."""
    
    def __init__(self):
        self.auth_service = AuthService()
        self.user_manager = user_manager
    
    async def get_current_user(self, request: Request) -> Optional[dict]:
        """Получение текущего пользователя из JWT токена."""
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        try:
            payload = await self.auth_service.verify_token(token)
            if not payload:
                return None
            
            # Получаем пользователя из базы данных
            user = await self.user_manager.get_user_by_telegram_id(payload.get("telegram_id"))
            return user
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None
    
    def require_auth(self, redirect_to: str = "/auth/login"):
        """Декоратор для проверки авторизации."""
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                user = await self.get_current_user(request)
                if not user:
                    if request.url.path.startswith("/api/"):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Требуется авторизация"
                        )
                    return RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)
                
                # Добавляем пользователя в контекст запроса
                request.state.current_user = user
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
    
    def require_role(self, required_roles: List[UserRole], redirect_to: str = "/auth/login"):
        """Декоратор для проверки ролей."""
        def decorator(func):
            async def wrapper(request: Request, *args, **kwargs):
                user = await self.get_current_user(request)
                if not user:
                    if request.url.path.startswith("/api/"):
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Требуется авторизация"
                        )
                    return RedirectResponse(url=redirect_to, status_code=status.HTTP_302_FOUND)
                
                user_role = UserRole(user.get("role", "employee"))
                if user_role not in required_roles:
                    if request.url.path.startswith("/api/"):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Недостаточно прав доступа"
                        )
                    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
                
                # Добавляем пользователя в контекст запроса
                request.state.current_user = user
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
    
    def require_owner_or_superadmin(self, redirect_to: str = "/auth/login"):
        """Декоратор для проверки роли владельца или суперадмина."""
        return self.require_role([UserRole.OWNER, UserRole.SUPERADMIN], redirect_to)
    
    def require_employee_or_owner(self, redirect_to: str = "/auth/login"):
        """Декоратор для проверки роли сотрудника или владельца."""
        return self.require_role([UserRole.EMPLOYEE, UserRole.OWNER, UserRole.SUPERADMIN], redirect_to)
    
    def require_superadmin(self, redirect_to: str = "/auth/login"):
        """Декоратор для проверки роли суперадмина."""
        return self.require_role([UserRole.SUPERADMIN], redirect_to)


# Глобальный экземпляр middleware
auth_middleware = AuthMiddleware()
