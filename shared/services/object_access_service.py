"""Сервис прав доступа к объектам для календаря."""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from domain.entities.user import User
from domain.entities.object import Object
from shared.services.manager_permission_service import ManagerPermissionService

logger = logging.getLogger(__name__)


class ObjectAccessService:
    """Сервис для определения прав доступа к объектам для разных ролей."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_accessible_objects(
        self, 
        user_telegram_id: int, 
        user_role: str
    ) -> List[Dict[str, Any]]:
        """
        Получить список доступных объектов для пользователя в зависимости от роли.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_role: Роль пользователя (owner, manager, employee, applicant)
            
        Returns:
            Список объектов с информацией о правах доступа
        """
        try:
            # Получаем пользователя из БД
            user_query = select(User).where(User.telegram_id == user_telegram_id)
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User with telegram_id {user_telegram_id} not found")
                return []
            
            # Определяем доступные объекты в зависимости от роли
            if user_role == "owner":
                return await self._get_owner_objects(user.id)
            elif user_role == "manager":
                return await self._get_manager_objects(user.id)
            elif user_role in ["employee", "applicant"]:
                return await self._get_employee_objects(user.id)
            else:
                logger.warning(f"Unknown user role: {user_role}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting accessible objects for user {user_telegram_id}: {e}", exc_info=True)
            return []
    
    async def _get_owner_objects(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить объекты владельца."""
        try:
            objects_query = select(Object).where(
                and_(
                    Object.owner_id == user_id,
                    Object.is_active == True
                )
            ).order_by(Object.name)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            
            accessible_objects = []
            for obj in objects:
                accessible_objects.append({
                    'id': obj.id,
                    'name': obj.name,
                    'address': obj.address,
                    'owner_id': obj.owner_id,
                    'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0,
                    'coordinates': obj.coordinates,
                    'work_conditions': obj.work_conditions,
                    'shift_tasks': obj.shift_tasks,
                    'available_for_applicants': obj.available_for_applicants,
                    'timezone': obj.timezone or 'Europe/Moscow',
                    'can_view': True,
                    'can_edit': True,
                    'can_delete': True,
                    'can_manage_employees': True,
                    'can_view_finances': True,
                    'can_edit_rates': True,
                    'can_edit_schedule': True
                })
            
            logger.info(f"Found {len(accessible_objects)} objects for owner {user_id}")
            return accessible_objects
            
        except Exception as e:
            logger.error(f"Error getting owner objects for user {user_id}: {e}", exc_info=True)
            return []
    
    async def _get_manager_objects(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить объекты управляющего через права доступа."""
        try:
            permission_service = ManagerPermissionService(self.db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            accessible_objects_list = []
            for obj in accessible_objects:
                # Получаем права доступа для этого объекта
                permissions = await permission_service.get_object_permissions(user_id, obj.id)
                
                accessible_objects_list.append({
                    'id': obj.id,
                    'name': obj.name,
                    'address': obj.address,
                    'owner_id': obj.owner_id,
                    'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0,
                    'coordinates': obj.coordinates,
                    'work_conditions': obj.work_conditions,
                    'shift_tasks': obj.shift_tasks,
                    'available_for_applicants': obj.available_for_applicants,
                    'can_view': permissions.get('can_view', False),
                    'can_edit': permissions.get('can_edit', False),
                    'can_delete': permissions.get('can_delete', False),
                    'can_manage_employees': permissions.get('can_manage_employees', False),
                    'can_view_finances': permissions.get('can_view_finances', False),
                    'can_edit_rates': permissions.get('can_edit_rates', False),
                    'can_edit_schedule': permissions.get('can_edit_schedule', False)
                })
            
            logger.info(f"Found {len(accessible_objects_list)} objects for manager {user_id}")
            return accessible_objects_list
            
        except Exception as e:
            logger.error(f"Error getting manager objects for user {user_id}: {e}", exc_info=True)
            return []
    
    async def _get_employee_objects(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить объекты доступные для сотрудника/соискателя."""
        try:
            # Для сотрудников показываем только объекты, доступные для заявок
            objects_query = select(Object).where(
                and_(
                    Object.available_for_applicants == True,
                    Object.is_active == True
                )
            ).order_by(Object.name)
            
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            
            accessible_objects = []
            for obj in objects:
                accessible_objects.append({
                    'id': obj.id,
                    'name': obj.name,
                    'address': obj.address,
                    'owner_id': obj.owner_id,
                    'hourly_rate': float(obj.hourly_rate) if obj.hourly_rate else 0,
                    'coordinates': obj.coordinates,
                    'work_conditions': obj.work_conditions,
                    'shift_tasks': obj.shift_tasks,
                    'available_for_applicants': obj.available_for_applicants,
                    'timezone': obj.timezone or 'Europe/Moscow',
                    'can_view': True,
                    'can_edit': False,
                    'can_delete': False,
                    'can_manage_employees': False,
                    'can_view_finances': False,
                    'can_edit_rates': False,
                    'can_edit_schedule': False
                })
            
            logger.info(f"Found {len(accessible_objects)} objects for employee {user_id}")
            return accessible_objects
            
        except Exception as e:
            logger.error(f"Error getting employee objects for user {user_id}: {e}", exc_info=True)
            return []
    
    async def get_object_ids(self, user_telegram_id: int, user_role: str) -> List[int]:
        """
        Получить только ID доступных объектов для оптимизации запросов.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_role: Роль пользователя
            
        Returns:
            Список ID доступных объектов
        """
        accessible_objects = await self.get_accessible_objects(user_telegram_id, user_role)
        return [obj['id'] for obj in accessible_objects]
    
    async def can_access_object(
        self, 
        user_telegram_id: int, 
        user_role: str, 
        object_id: int,
        permission: str = 'can_view'
    ) -> bool:
        """
        Проверить, может ли пользователь получить доступ к объекту.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_role: Роль пользователя
            object_id: ID объекта
            permission: Тип разрешения (can_view, can_edit, etc.)
            
        Returns:
            True если доступ разрешен, False иначе
        """
        try:
            accessible_objects = await self.get_accessible_objects(user_telegram_id, user_role)
            
            for obj in accessible_objects:
                if obj['id'] == object_id:
                    return obj.get(permission, False)
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking object access for user {user_telegram_id}, object {object_id}: {e}", exc_info=True)
            return False
    
    async def get_objects_with_permission(
        self,
        user_telegram_id: int,
        user_role: str,
        permission: str = 'can_view'
    ) -> List[Dict[str, Any]]:
        """
        Получить объекты, к которым у пользователя есть конкретное разрешение.
        
        Args:
            user_telegram_id: Telegram ID пользователя
            user_role: Роль пользователя
            permission: Тип разрешения
            
        Returns:
            Список объектов с указанным разрешением
        """
        try:
            accessible_objects = await self.get_accessible_objects(user_telegram_id, user_role)
            return [obj for obj in accessible_objects if obj.get(permission, False)]
            
        except Exception as e:
            logger.error(f"Error getting objects with permission {permission} for user {user_telegram_id}: {e}", exc_info=True)
            return []
