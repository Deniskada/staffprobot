"""Middleware для проверки множественных ролей."""

from typing import List, Optional, Union
from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from shared.services.role_service import RoleService
from shared.services.manager_permission_service import ManagerPermissionService
from domain.entities.user import UserRole
from core.logging.logger import logger
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.dependencies import get_current_user_dependency


async def get_user_id_from_current_user(current_user, session: AsyncSession) -> Optional[int]:
    """Получает внутренний ID пользователя из current_user."""
    if isinstance(current_user, dict):
        # current_user - это словарь из JWT payload
        telegram_id = current_user.get("id")
        from sqlalchemy import select
        from domain.entities.user import User
        
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        # current_user - это объект User
        return current_user.id


async def require_any_role(roles: List[UserRole]):
    """Декоратор для проверки наличия любой из указанных ролей."""
    async def role_checker(request: Request, current_user: dict = Depends(require_owner_or_superadmin)):
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        from core.database.session import get_async_session
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            if not user_id:
                return RedirectResponse(url="/auth/login", status_code=302)
            
            role_service = RoleService(session)
            has_role = await role_service.has_any_role(user_id, roles)
            
            if not has_role:
                logger.warning(f"User {user_id} does not have any of required roles: {[r.value for r in roles]}")
                raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
            
            return current_user
    
    return role_checker


async def require_all_roles(roles: List[UserRole]):
    """Декоратор для проверки наличия всех указанных ролей."""
    async def role_checker(request: Request, current_user: dict = Depends(require_owner_or_superadmin)):
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        from core.database.session import get_async_session
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            if not user_id:
                return RedirectResponse(url="/auth/login", status_code=302)
            
            role_service = RoleService(session)
            has_roles = await role_service.has_all_roles(user_id, roles)
            
            if not has_roles:
                logger.warning(f"User {user_id} does not have all required roles: {[r.value for r in roles]}")
                raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
            
            return current_user
    
    return role_checker


async def require_manager_or_owner(request: Request, current_user: dict = Depends(get_current_user_dependency())):
    """Проверка роли управляющего или владельца."""
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Если пользователь не аутентифицирован
    if current_user is None:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    from core.database.session import get_async_session
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        role_service = RoleService(session)
        has_role = await role_service.has_any_role(user_id, [UserRole.MANAGER, UserRole.OWNER, UserRole.SUPERADMIN])
        
        if not has_role:
            logger.warning(f"User {user_id} is not a manager or owner")
            raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
        
        return current_user


async def require_manager_permission(permission: str):
    """Декоратор для проверки конкретного права управляющего."""
    async def permission_checker(request: Request, current_user: dict = Depends(require_manager_or_owner)):
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        from core.database.session import get_async_session
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            if not user_id:
                return RedirectResponse(url="/auth/login", status_code=302)
            
            # Получаем договоры управляющего
            permission_service = ManagerPermissionService(session)
            manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
            
            if not manager_contracts:
                logger.warning(f"User {user_id} has no manager contracts")
                raise HTTPException(status_code=403, detail="Нет прав управляющего")
            
            # Проверяем, есть ли хотя бы одно право на любой объект
            has_permission = False
            for contract in manager_contracts:
                accessible_objects = await permission_service.get_objects_with_permission(contract.id, permission)
                if accessible_objects:
                    has_permission = True
                    break
            
            if not has_permission:
                logger.warning(f"User {user_id} does not have permission {permission}")
                raise HTTPException(status_code=403, detail=f"Нет права: {permission}")
            
            return current_user
    
    return permission_checker


async def require_object_access(object_id: int):
    """Декоратор для проверки доступа к конкретному объекту."""
    async def access_checker(request: Request, current_user: dict = Depends(require_owner_or_superadmin)):
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        from core.database.session import get_async_session
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            if not user_id:
                return RedirectResponse(url="/auth/login", status_code=302)
            
            role_service = RoleService(session)
            
            # Проверяем, является ли пользователь владельцем объекта
            is_owner = await role_service.has_role(user_id, UserRole.OWNER)
            if is_owner:
                from sqlalchemy import select
                from domain.entities.object import Object
                
                object_query = select(Object).where(Object.id == object_id)
                result = await session.execute(object_query)
                obj = result.scalar_one_or_none()
                
                if obj and obj.owner_id == user_id:
                    return current_user
            
            # Проверяем права управляющего
            is_manager = await role_service.has_role(user_id, UserRole.MANAGER)
            if is_manager:
                permission_service = ManagerPermissionService(session)
                accessible_objects = await permission_service.get_user_accessible_objects(user_id)
                
                if any(obj.id == object_id for obj in accessible_objects):
                    return current_user
            
            logger.warning(f"User {user_id} does not have access to object {object_id}")
            raise HTTPException(status_code=403, detail="Нет доступа к объекту")
    
    return access_checker


async def require_applicant_object_access(object_id: int):
    """Декоратор для проверки доступности объекта для соискателей."""
    async def access_checker(request: Request, current_user: dict = Depends(require_owner_or_superadmin)):
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        from core.database.session import get_async_session
        async with get_async_session() as session:
            from sqlalchemy import select
            from domain.entities.object import Object
            
            # Проверяем, доступен ли объект для соискателей
            object_query = select(Object).where(Object.id == object_id)
            result = await session.execute(object_query)
            obj = result.scalar_one_or_none()
            
            if not obj or not obj.available_for_applicants:
                logger.warning(f"Object {object_id} is not available for applicants")
                raise HTTPException(status_code=403, detail="Объект недоступен для соискателей")
            
            return current_user
    
    return access_checker


