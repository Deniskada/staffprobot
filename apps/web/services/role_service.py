"""Сервис управления ролями пользователей."""

from typing import List, Dict, Any
from core.auth.user_manager import UserManager
from core.logging.logger import logger
from domain.entities.user import UserRole

class RoleService:
    """Сервис для управления ролями пользователей."""
    
    def __init__(self):
        self.user_manager = UserManager()
    
    async def update_user_roles(self, user_id: int) -> List[str]:
        """Автоматически обновляет роли пользователя на основе его активности."""
        try:
            user = await self.user_manager.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found for role update")
                return []
            
            new_roles = [UserRole.APPLICANT.value]  # Базовая роль
            
            # Проверяем, есть ли объекты у пользователя
            if await self._has_objects(user_id):
                new_roles.append(UserRole.OWNER.value)
                logger.info(f"User {user_id} has objects, adding owner role")
            
            # Проверяем, есть ли действующие договоры
            if await self._has_active_contracts(user_id):
                new_roles.append(UserRole.EMPLOYEE.value)
                logger.info(f"User {user_id} has active contracts, adding employee role")
            
            # Обновляем роли в БД
            await self.user_manager.update_user_roles(user_id, new_roles)
            logger.info(f"Updated roles for user {user_id}: {new_roles}")
            return new_roles
            
        except Exception as e:
            logger.error(f"Error updating roles for user {user_id}: {e}")
            return []
    
    async def _has_objects(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя объекты."""
        # TODO: Реализовать проверку объектов
        # Пока возвращаем False, так как объекты еще не реализованы
        return False
    
    async def _has_active_contracts(self, user_id: int) -> bool:
        """Проверяет, есть ли у пользователя действующие договоры."""
        # TODO: Реализовать проверку договоров
        # Пока возвращаем False, так как договоры еще не реализованы
        return False
    
    async def add_role(self, user_id: int, role: str) -> bool:
        """Добавляет роль пользователю."""
        try:
            user = await self.user_manager.get_user_by_id(user_id)
            if not user:
                return False
            
            current_roles = user.get("roles", [])
            if role not in current_roles:
                new_roles = current_roles + [role]
                await self.user_manager.update_user_roles(user_id, new_roles)
                logger.info(f"Added role {role} to user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error adding role {role} to user {user_id}: {e}")
            return False
    
    async def remove_role(self, user_id: int, role: str) -> bool:
        """Удаляет роль у пользователя."""
        try:
            user = await self.user_manager.get_user_by_id(user_id)
            if not user:
                return False
            
            current_roles = user.get("roles", [])
            if role in current_roles:
                new_roles = [r for r in current_roles if r != role]
                await self.user_manager.update_user_roles(user_id, new_roles)
                logger.info(f"Removed role {role} from user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing role {role} from user {user_id}: {e}")
            return False
    
    async def set_roles(self, user_id: int, roles: List[str]) -> bool:
        """Устанавливает роли пользователя."""
        try:
            success = await self.user_manager.update_user_roles(user_id, roles)
            if success:
                logger.info(f"Set roles for user {user_id}: {roles}")
            return success
            
        except Exception as e:
            logger.error(f"Error setting roles for user {user_id}: {e}")
            return False
    
    async def get_user_roles(self, user_id: int) -> List[str]:
        """Получает роли пользователя."""
        try:
            user = await self.user_manager.get_user_by_id(user_id)
            if not user:
                return []
            
            return user.get("roles", [])
            
        except Exception as e:
            logger.error(f"Error getting roles for user {user_id}: {e}")
            return []
    
    def has_role(self, user_data: Dict[str, Any], role: str) -> bool:
        """Проверяет, имеет ли пользователь указанную роль."""
        roles = user_data.get("roles", [])
        return role in roles
    
    def has_any_role(self, user_data: Dict[str, Any], required_roles: List[str]) -> bool:
        """Проверяет, имеет ли пользователь хотя бы одну из указанных ролей."""
        user_roles = user_data.get("roles", [])
        return any(role in user_roles for role in required_roles)
    
    def can_manage_objects(self, user_data: Dict[str, Any]) -> bool:
        """Проверяет, может ли пользователь управлять объектами."""
        return self.has_any_role(user_data, [UserRole.OWNER.value, UserRole.SUPERADMIN.value])
    
    def can_manage_users(self, user_data: Dict[str, Any]) -> bool:
        """Проверяет, может ли пользователь управлять пользователями."""
        return self.has_any_role(user_data, [UserRole.OWNER.value, UserRole.SUPERADMIN.value])
    
    def can_work_shifts(self, user_data: Dict[str, Any]) -> bool:
        """Проверяет, может ли пользователь работать сменами."""
        return self.has_any_role(user_data, [UserRole.EMPLOYEE.value, UserRole.OWNER.value, UserRole.SUPERADMIN.value])
