"""Middleware для проверки авторизации и ролей."""

from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Optional, List
from core.auth.user_manager import user_manager
from apps.web.services.auth_service import AuthService
from domain.entities.user import UserRole
from core.logging.logger import logger
from core.database.session import get_async_session
from sqlalchemy import select
from domain.entities.owner_profile import OwnerProfile
from shared.services.industry_terms_service import IndustryTermsService


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
            user_id = payload.get("sub")
            telegram_id = payload.get("telegram_id")
            if user_id:
                user = await self.user_manager.get_user_by_internal_id(int(user_id))
            elif telegram_id:
                user = await self.user_manager.get_user_by_telegram_id(int(telegram_id))
            else:
                logger.warning("No user_id or telegram_id in token payload")
                return None
            if not user:
                logger.warning(f"User not found for user_id={user_id} telegram_id={telegram_id}")
                return None

            # UI-предпочтения владельца: тема/язык/отрасль + словарь терминов
            try:
                async with get_async_session() as session:
                    prof = (
                        await session.execute(
                            select(OwnerProfile).where(OwnerProfile.user_id == user["id"])
                        )
                    ).scalar_one_or_none()
                    if prof:
                        user["theme"] = prof.theme or "light"
                        user["language"] = prof.language or "ru"
                        user["industry"] = prof.industry or "grocery"
                        user["ui_terms"] = await IndustryTermsService.get_terms(
                            session, user["industry"], user["language"]
                        )
            except Exception as prefs_err:
                logger.warning(f"Failed to load ui prefs for user {user.get('id')}: {prefs_err}")
            
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
    """Требует роль владельца, управляющего или суперадмина. Всегда возвращает dict."""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    user_role = user.get("role", "employee")
    user_roles = user.get("roles") or []
    if not isinstance(user_roles, (list, tuple)):
        user_roles = [user_roles] if user_roles else []
    allowed = {"owner", "superadmin", "manager"}
    if user_role in allowed or any(r in allowed for r in user_roles):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав доступа",
    )

async def require_superadmin(request: Request) -> dict:
    """Требует роль суперадмина."""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация"
        )
    
    # Проверяем основную роль пользователя
    user_role = user.get("role", "employee")
    user_roles = user.get("roles", [])
    
    if user_role != "superadmin" and "superadmin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа"
        )
    
    return user


async def require_owner_or_superadmin_web(request: Request) -> dict:
    """
    Роуты владельца/superadmin: тот же user-dict, что и get_current_user
    (JWT + OwnerProfile: theme, language, ui_terms, внутренний id).
    Не путать с Depends(require_role) из dependencies — там возвращается ORM User.
    """
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
        )
    user_role = user.get("role", "employee")
    user_roles = user.get("roles") or []
    if not isinstance(user_roles, (list, tuple)):
        user_roles = [user_roles] if user_roles else []
    allowed = {"owner", "superadmin"}
    if user_role in allowed or any(r in allowed for r in user_roles):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав доступа",
    )
