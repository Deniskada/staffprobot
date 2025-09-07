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
            logger.debug("No access token found in cookies")
            return None
        
        try:
            logger.debug(f"Verifying token: {token[:20]}...")
            payload = await self.auth_service.verify_token(token)
            if not payload:
                logger.warning("Token verification failed - no payload")
                return None
            
            logger.debug(f"Token payload: {payload}")
            telegram_id = payload.get("telegram_id")
            if not telegram_id:
                logger.warning("No telegram_id in token payload")
                return None
            
            # Получаем пользователя из базы данных
            logger.debug(f"Getting user by telegram_id: {telegram_id}")
            user = await self.user_manager.get_user_by_telegram_id(telegram_id)
            if not user:
                logger.warning(f"User not found for telegram_id: {telegram_id}")
                return None
            
            logger.debug(f"User found: {user}")
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

# Функции-зависимости для FastAPI
async def get_current_user(request: Request) -> Optional[dict]:
    """Получение текущего пользователя."""
    return await auth_middleware.get_current_user(request)

async def require_auth(request: Request) -> dict:
    """Требует авторизации."""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    return user

async def require_owner_or_superadmin(request: Request) -> dict:
    """Требует роль владельца или суперадмина."""
    user = await auth_middleware.get_current_user(request)
    if not user:
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется авторизация"
            )
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_roles = user.get("roles", [user.get("role", "employee")])
    if not any(role in ["owner", "superadmin"] for role in user_roles):
        if request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав доступа"
            )
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return user

async def require_superadmin(request: Request) -> dict:
    """Требует роль суперадмина."""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    user_roles = user.get("roles", [user.get("role", "employee")])
    if "superadmin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    
    return user
