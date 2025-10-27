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
            # FastAPI не может возвращать Response из dependency напрямую
            # Нужно либо raise HTTPException, либо использовать middleware
            raise HTTPException(
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Location": "/auth/login"}
            )
        
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав доступа"
            )
        return current_user
    return role_checker


async def require_manager_payroll_permission(
    request: Request, 
    current_user = Depends(get_current_user_dependency())
):
    """
    Проверка права управляющего на работу с начислениями.
    
    Управляющий должен иметь активный договор с правом can_manage_payroll в manager_permissions.
    
    Args:
        request: HTTP запрос
        current_user: Объект User (текущий пользователь)
        
    Returns:
        User: Объект пользователя
        
    Raises:
        HTTPException: 403 если нет прав
    """
    from domain.entities.contract import Contract
    from domain.entities.user import User
    from core.database.session import get_async_session
    from sqlalchemy import select, and_
    
    # Проверка аутентификации
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if current_user is None:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Проверить роли (current_user - это объект User с множественными ролями)
    if not hasattr(current_user, 'roles'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь не найден"
        )
    
    user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
    
    # Проверить, есть ли роль manager или owner
    if not any(role in ["manager", "owner"] for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ только для управляющих и владельцев"
        )
    
    # Владелец всегда имеет доступ
    if "owner" in user_roles:
        return current_user
    
    # Для управляющего проверить право can_manage_payroll
    async with get_async_session() as session:
        # Найти активный договор управляющего (используем current_user.id)
        query = select(Contract).where(
            Contract.employee_id == current_user.id,
            Contract.is_manager == True,
            Contract.is_active == True,
            Contract.status == "active"
        ).order_by(Contract.created_at.desc())
        
        result = await session.execute(query)
        manager_contract = result.scalars().first()  # Берем первый (последний созданный)
        
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
