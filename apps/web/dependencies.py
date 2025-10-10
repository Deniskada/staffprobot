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
                # Используем telegram_id для поиска пользователя (в токене это поле 'id')
                telegram_id = user_data.get("telegram_id") or user_data.get("id")
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


async def require_manager_payroll_permission(
    request: Request, 
    current_user: dict = Depends(require_auth)
) -> dict:
    """
    Проверка права управляющего на работу с начислениями.
    
    Управляющий должен иметь активный договор с правом can_manage_payroll в manager_permissions.
    
    Args:
        request: HTTP запрос
        current_user: Текущий пользователь
        
    Returns:
        dict: Данные пользователя
        
    Raises:
        HTTPException: 403 если нет прав
    """
    from domain.entities.contract import Contract
    
    # Проверить роль
    user_role = current_user.get("role", "employee")
    if user_role not in ["manager", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для управляющих и владельцев"
        )
    
    # Владелец всегда имеет доступ
    if user_role == "owner":
        return current_user
    
    # Для управляющего проверить право can_manage_payroll
    async with get_async_session() as session:
        from domain.entities.user import User
        from apps.web.middleware.role_middleware import get_user_id_from_current_user
        
        # Получить внутренний user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Пользователь не найден"
            )
        
        # Найти активный договор управляющего
        query = select(Contract).where(
            Contract.employee_id == user_id,
            Contract.is_manager == True,
            Contract.is_active == True,
            Contract.status == "active"
        )
        
        result = await session.execute(query)
        manager_contract = result.scalar_one_or_none()
        
        if not manager_contract:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Активный договор управляющего не найден"
            )
        
        # Проверить право can_manage_payroll
        permissions = manager_contract.manager_permissions or {}
        if not permissions.get("can_manage_payroll", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет права на управление начислениями"
            )
        
        return current_user
