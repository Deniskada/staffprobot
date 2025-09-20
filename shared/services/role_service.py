"""Сервис для управления ролями пользователей."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from domain.entities.user import User, UserRole
from domain.entities.contract import Contract
from domain.entities.object import Object
from core.logging.logger import logger


class RoleService:
    """Сервис для управления ролями пользователей."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_role(self, user_id: int, role: UserRole) -> bool:
        """Добавление роли пользователю."""
        try:
            # Получаем пользователя
            user_query = select(User).where(User.id == user_id)
            result = await self.session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for role addition")
                return False
            
            # Добавляем роль
            if not user.roles:
                user.roles = []
            
            if role.value not in user.roles:
                user.roles.append(role.value)
                # Помечаем поле как измененное для SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user, 'roles')
                await self.session.commit()
                logger.info(f"Added role {role.value} to user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to add role {role.value} to user {user_id}: {e}")
            await self.session.rollback()
            return False
    
    async def remove_role(self, user_id: int, role: UserRole) -> bool:
        """Удаление роли у пользователя."""
        try:
            # Получаем пользователя
            user_query = select(User).where(User.id == user_id)
            result = await self.session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User {user_id} not found for role removal")
                return False
            
            # Удаляем роль
            if user.roles and role.value in user.roles:
                user.roles.remove(role.value)
                # Помечаем поле как измененное для SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(user, 'roles')
                await self.session.commit()
                logger.info(f"Removed role {role.value} from user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove role {role.value} from user {user_id}: {e}")
            await self.session.rollback()
            return False
    
    async def has_role(self, user_id: int, role: UserRole) -> bool:
        """Проверка наличия роли у пользователя."""
        try:
            user_query = select(User).where(User.id == user_id)
            result = await self.session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            return user.has_role(role)
            
        except Exception as e:
            logger.error(f"Failed to check role {role.value} for user {user_id}: {e}")
            return False
    
    async def get_user_roles(self, user_id: int) -> List[str]:
        """Получение списка ролей пользователя."""
        try:
            user_query = select(User).where(User.id == user_id)
            result = await self.session.execute(user_query)
            user = result.scalar_one_or_none()
            
            if not user:
                return []
            
            return user.get_roles()
            
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id}: {e}")
            return []
    
    async def has_any_role(self, user_id: int, roles: List[UserRole]) -> bool:
        """Проверка наличия любой из указанных ролей."""
        try:
            user_roles = await self.get_user_roles(user_id)
            return any(role.value in user_roles for role in roles)
            
        except Exception as e:
            logger.error(f"Failed to check any role for user {user_id}: {e}")
            return False
    
    async def has_all_roles(self, user_id: int, roles: List[UserRole]) -> bool:
        """Проверка наличия всех указанных ролей."""
        try:
            user_roles = await self.get_user_roles(user_id)
            return all(role.value in user_roles for role in roles)
            
        except Exception as e:
            logger.error(f"Failed to check all roles for user {user_id}: {e}")
            return False
    
    async def assign_owner_role(self, user_id: int) -> bool:
        """Назначение роли владельца пользователю."""
        return await self.add_role(user_id, UserRole.OWNER)
    
    async def assign_employee_role(self, user_id: int) -> bool:
        """Назначение роли сотрудника пользователю."""
        return await self.add_role(user_id, UserRole.EMPLOYEE)
    
    async def assign_manager_role(self, user_id: int) -> bool:
        """Назначение роли управляющего пользователю."""
        return await self.add_role(user_id, UserRole.MANAGER)
    
    async def assign_applicant_role(self, user_id: int) -> bool:
        """Назначение роли соискателя пользователю."""
        return await self.add_role(user_id, UserRole.APPLICANT)
    
    async def remove_owner_role(self, user_id: int) -> bool:
        """Удаление роли владельца у пользователя."""
        return await self.remove_role(user_id, UserRole.OWNER)
    
    async def remove_employee_role(self, user_id: int) -> bool:
        """Удаление роли сотрудника у пользователя."""
        return await self.remove_role(user_id, UserRole.EMPLOYEE)
    
    async def remove_manager_role(self, user_id: int) -> bool:
        """Удаление роли управляющего у пользователя."""
        return await self.remove_role(user_id, UserRole.MANAGER)
    
    async def remove_applicant_role(self, user_id: int) -> bool:
        """Удаление роли соискателя у пользователя."""
        return await self.remove_role(user_id, UserRole.APPLICANT)
    
    async def update_roles_from_objects(self, user_id: int) -> bool:
        """Обновление ролей на основе объектов пользователя."""
        try:
            # Проверяем, есть ли у пользователя объекты
            objects_query = select(Object).where(Object.owner_id == user_id)
            result = await self.session.execute(objects_query)
            objects = result.scalars().all()
            
            if objects:
                # Если есть объекты - добавляем роль владельца
                await self.assign_owner_role(user_id)
            else:
                # Если нет объектов - удаляем роль владельца
                await self.remove_owner_role(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update roles from objects for user {user_id}: {e}")
            return False
    
    async def update_roles_from_contracts(self, user_id: int) -> bool:
        """Обновление ролей на основе договоров пользователя."""
        try:
            # Проверяем активные договоры как сотрудника
            employee_contracts_query = select(Contract).where(
                Contract.employee_id == user_id,
                Contract.is_active == True
            )
            result = await self.session.execute(employee_contracts_query)
            employee_contracts = result.scalars().all()
            
            if employee_contracts:
                # Если есть активные договоры - добавляем роль сотрудника
                await self.assign_employee_role(user_id)
                
                # Проверяем, есть ли договоры с правами управляющего
                manager_contracts = [c for c in employee_contracts if c.is_manager]
                if manager_contracts:
                    await self.assign_manager_role(user_id)
                else:
                    await self.remove_manager_role(user_id)
            else:
                # Если нет активных договоров - удаляем роли сотрудника и управляющего
                await self.remove_employee_role(user_id)
                await self.remove_manager_role(user_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update roles from contracts for user {user_id}: {e}")
            return False
    
    async def get_users_by_role(self, role: UserRole) -> List[User]:
        """Получение пользователей по роли."""
        try:
            query = select(User).where(User.roles.contains([role.value]))
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get users by role {role.value}: {e}")
            return []
    
    async def get_available_interfaces(self, user_id: int) -> List[str]:
        """Получение доступных интерфейсов для пользователя."""
        try:
            user_roles = await self.get_user_roles(user_id)
            interfaces = []
            
            if UserRole.SUPERADMIN.value in user_roles:
                interfaces.append("admin")
            if UserRole.OWNER.value in user_roles:
                interfaces.append("owner")
            if UserRole.MANAGER.value in user_roles:
                interfaces.append("manager")
            if UserRole.EMPLOYEE.value in user_roles or UserRole.APPLICANT.value in user_roles:
                interfaces.append("employee")
            
            return interfaces
            
        except Exception as e:
            logger.error(f"Failed to get available interfaces for user {user_id}: {e}")
            return []
    
    async def get_primary_interface(self, user_id: int) -> Optional[str]:
        """Получение основного интерфейса для пользователя (по приоритету)."""
        try:
            interfaces = await self.get_available_interfaces(user_id)
            
            # Приоритет интерфейсов
            priority = ["admin", "owner", "manager", "employee"]
            
            for interface in priority:
                if interface in interfaces:
                    return interface
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get primary interface for user {user_id}: {e}")
            return None
