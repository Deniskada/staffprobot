"""Сервис для управления правами управляющих на объекты."""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from domain.entities.manager_object_permission import ManagerObjectPermission
from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.user import User
from core.logging.logger import logger


class ManagerPermissionService:
    """Сервис для управления правами управляющих на объекты."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_permission(
        self, 
        contract_id: int, 
        object_id: int, 
        permissions: Dict[str, bool]
    ) -> Optional[ManagerObjectPermission]:
        """Создание прав управляющего на объект."""
        try:
            # Проверяем, что договор существует и является управляющим
            contract_query = select(Contract).where(
                and_(Contract.id == contract_id, Contract.is_manager == True)
            )
            result = await self.session.execute(contract_query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                logger.warning(f"Contract {contract_id} not found or not a manager contract")
                return None
            
            # Проверяем, что объект существует
            object_query = select(Object).where(Object.id == object_id)
            result = await self.session.execute(object_query)
            obj = result.scalar_one_or_none()
            
            if not obj:
                logger.warning(f"Object {object_id} not found")
                return None
            
            # Создаем права
            permission = ManagerObjectPermission(
                contract_id=contract_id,
                object_id=object_id
            )
            permission.set_permissions(permissions)
            
            self.session.add(permission)
            await self.session.commit()
            
            logger.info(f"Created manager permissions for contract {contract_id} on object {object_id}")
            return permission
            
        except Exception as e:
            logger.error(f"Failed to create manager permission: {e}")
            await self.session.rollback()
            return None
    
    async def update_permission(
        self, 
        permission_id: int, 
        permissions: Dict[str, bool]
    ) -> bool:
        """Обновление прав управляющего на объект."""
        try:
            permission_query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.id == permission_id
            )
            result = await self.session.execute(permission_query)
            permission = result.scalar_one_or_none()
            
            if not permission:
                logger.warning(f"Permission {permission_id} not found")
                return False
            
            permission.set_permissions(permissions)
            await self.session.commit()
            
            logger.info(f"Updated manager permission {permission_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update manager permission {permission_id}: {e}")
            await self.session.rollback()
            return False
    
    async def delete_permission(self, permission_id: int) -> bool:
        """Удаление прав управляющего на объект."""
        try:
            permission_query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.id == permission_id
            )
            result = await self.session.execute(permission_query)
            permission = result.scalar_one_or_none()
            
            if not permission:
                logger.warning(f"Permission {permission_id} not found")
                return False
            
            await self.session.delete(permission)
            await self.session.commit()
            
            logger.info(f"Deleted manager permission {permission_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete manager permission {permission_id}: {e}")
            await self.session.rollback()
            return False
    
    async def get_permission(self, contract_id: int, object_id: int) -> Optional[ManagerObjectPermission]:
        """Получение прав управляющего на конкретный объект."""
        try:
            query = select(ManagerObjectPermission).where(
                and_(
                    ManagerObjectPermission.contract_id == contract_id,
                    ManagerObjectPermission.object_id == object_id
                )
            )
            result = await self.session.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get permission for contract {contract_id} on object {object_id}: {e}")
            return None
    
    async def get_contract_permissions(self, contract_id: int) -> List[ManagerObjectPermission]:
        """Получение всех прав управляющего по договору."""
        try:
            query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.contract_id == contract_id
            ).options(selectinload(ManagerObjectPermission.object))
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get permissions for contract {contract_id}: {e}")
            return []
    
    async def get_object_permissions(self, object_id: int) -> List[ManagerObjectPermission]:
        """Получение всех прав управляющих на объект."""
        try:
            query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.object_id == object_id
            ).options(selectinload(ManagerObjectPermission.contract))
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to get permissions for object {object_id}: {e}")
            return []
    
    async def has_permission(
        self, 
        contract_id: int, 
        object_id: int, 
        permission: str
    ) -> bool:
        """Проверка конкретного права управляющего на объект."""
        try:
            perm = await self.get_permission(contract_id, object_id)
            if not perm:
                return False
            
            permissions_dict = perm.get_permissions_dict()
            return permissions_dict.get(permission, False)
            
        except Exception as e:
            logger.error(f"Failed to check permission {permission} for contract {contract_id} on object {object_id}: {e}")
            return False
    
    async def can_view_object(self, contract_id: int, object_id: int) -> bool:
        """Проверка права просмотра объекта."""
        return await self.has_permission(contract_id, object_id, "can_view")
    
    async def can_edit_object(self, contract_id: int, object_id: int) -> bool:
        """Проверка права редактирования объекта."""
        return await self.has_permission(contract_id, object_id, "can_edit")
    
    async def can_delete_object(self, contract_id: int, object_id: int) -> bool:
        """Проверка права удаления объекта."""
        return await self.has_permission(contract_id, object_id, "can_delete")
    
    async def can_manage_employees(self, contract_id: int, object_id: int) -> bool:
        """Проверка права управления сотрудниками на объекте."""
        return await self.has_permission(contract_id, object_id, "can_manage_employees")
    
    async def can_view_finances(self, contract_id: int, object_id: int) -> bool:
        """Проверка права просмотра финансов по объекту."""
        return await self.has_permission(contract_id, object_id, "can_view_finances")
    
    async def can_edit_rates(self, contract_id: int, object_id: int) -> bool:
        """Проверка права редактирования ставок по объекту."""
        return await self.has_permission(contract_id, object_id, "can_edit_rates")
    
    async def can_edit_schedule(self, contract_id: int, object_id: int) -> bool:
        """Проверка права редактирования расписания объекта."""
        return await self.has_permission(contract_id, object_id, "can_edit_schedule")
    
    async def get_accessible_objects(self, contract_id: int) -> List[Object]:
        """Получение объектов, доступных управляющему."""
        try:
            # Получаем все права управляющего
            permissions = await self.get_contract_permissions(contract_id)
            
            # Фильтруем объекты, к которым есть хотя бы одно право
            accessible_objects = []
            for permission in permissions:
                if permission.has_any_permission():
                    accessible_objects.append(permission.object)
            
            return accessible_objects
            
        except Exception as e:
            logger.error(f"Failed to get accessible objects for contract {contract_id}: {e}")
            return []
    
    async def get_objects_with_permission(
        self, 
        contract_id: int, 
        permission: str
    ) -> List[Object]:
        """Получение объектов с конкретным правом."""
        try:
            permissions = await self.get_contract_permissions(contract_id)
            
            objects = []
            for perm in permissions:
                if perm.get_permissions_dict().get(permission, False):
                    objects.append(perm.object)
            
            return objects
            
        except Exception as e:
            logger.error(f"Failed to get objects with permission {permission} for contract {contract_id}: {e}")
            return []
    
    async def get_manager_contracts_for_user(self, user_id: int) -> List[Contract]:
        """Получение договоров управляющего для пользователя."""
        try:
            logger.info(f"Getting manager contracts for user {user_id}")
            
            query = select(Contract).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.is_manager == True,
                    Contract.is_active == True
                )
            )
            
            logger.info(f"Executing query: {query}")
            result = await self.session.execute(query)
            contracts = result.scalars().all()
            logger.info(f"Found {len(contracts)} manager contracts for user {user_id}")
            
            return contracts
            
        except Exception as e:
            logger.error(f"Failed to get manager contracts for user {user_id}: {e}", exc_info=True)
            return []
    
    async def get_manager_object_ids(self, telegram_id: int) -> List[int]:
        """Получить идентификаторы объектов, доступных менеджеру."""
        try:
            # Получаем внутренний ID пользователя
            user_query = select(User.id).where(User.telegram_id == telegram_id)
            user_result = await self.session.execute(user_query)
            user_id = user_result.scalar_one_or_none()
            if not user_id:
                return []

            # Получаем договоры управляющего
            contracts = await self.get_manager_contracts_for_user(user_id)
            object_ids: set[int] = set()
            for contract in contracts:
                permissions = await self.get_contract_permissions(contract.id)
                for perm in permissions:
                    permissions_dict = perm.get_permissions_dict()
                    if permissions_dict.get("can_view", False) or permissions_dict.get("can_edit_schedule", False):
                        object_ids.add(perm.object_id)
            return list(object_ids)
        except Exception as e:
            logger.error(f"Failed to get manager object ids for {telegram_id}: {e}")
            return []

    async def check_manager_object_access(self, telegram_id: int, object_id: int) -> bool:
        """Проверка доступа менеджера к объекту."""
        try:
            # Получаем внутренний ID пользователя
            user_query = select(User.id).where(User.telegram_id == telegram_id)
            user_result = await self.session.execute(user_query)
            user_id = user_result.scalar_one_or_none()
            if not user_id:
                return False

            # Получаем договоры управляющего
            contracts = await self.get_manager_contracts_for_user(user_id)
            for contract in contracts:
                permissions = await self.get_contract_permissions(contract.id)
                for perm in permissions:
                    if perm.object_id != object_id:
                        continue
                    permissions_dict = perm.get_permissions_dict()
                    if permissions_dict.get("can_view", False) or permissions_dict.get("can_edit_schedule", False):
                        return True
            return False
        except Exception as e:
            logger.error(
                f"Failed to check manager access for telegram_id {telegram_id} and object {object_id}: {e}"
            )
            return False


    async def get_user_accessible_objects(self, user_id: int) -> List[Object]:
        """Получение всех объектов, доступных пользователю как управляющему."""
        try:
            logger.info(f"Getting accessible objects for user {user_id}")
            
            # Получаем договоры управляющего
            manager_contracts = await self.get_manager_contracts_for_user(user_id)
            logger.info(f"Found {len(manager_contracts)} manager contracts for user {user_id}")
            
            accessible_objects = []
            for contract in manager_contracts:
                logger.info(f"Getting objects for contract {contract.id}")
                objects = await self.get_accessible_objects(contract.id)
                logger.info(f"Found {len(objects)} objects for contract {contract.id}")
                accessible_objects.extend(objects)
            
            # Убираем дубликаты
            unique_objects = list({obj.id: obj for obj in accessible_objects}.values())
            logger.info(f"Total unique accessible objects: {len(unique_objects)}")
            
            return unique_objects
            
        except Exception as e:
            logger.error(f"Failed to get accessible objects for user {user_id}: {e}", exc_info=True)
            return []
    
    async def bulk_create_permissions(
        self, 
        contract_id: int, 
        object_permissions: List[Dict[str, Any]]
    ) -> List[ManagerObjectPermission]:
        """Массовое создание прав на несколько объектов."""
        try:
            created_permissions = []
            
            for obj_perm in object_permissions:
                object_id = obj_perm.get("object_id")
                permissions = obj_perm.get("permissions", {})
                
                if object_id and permissions:
                    permission = await self.create_permission(contract_id, object_id, permissions)
                    if permission:
                        created_permissions.append(permission)
            
            logger.info(f"Bulk created {len(created_permissions)} manager permissions for contract {contract_id}")
            return created_permissions
            
        except Exception as e:
            logger.error(f"Failed to bulk create permissions for contract {contract_id}: {e}")
            return []
    
    async def sync_contract_permissions(self, contract_id: int) -> bool:
        """Синхронизация прав управляющего с объектами владельца."""
        try:
            # Получаем договор
            contract_query = select(Contract).where(Contract.id == contract_id)
            result = await self.session.execute(contract_query)
            contract = result.scalar_one_or_none()
            
            if not contract or not contract.is_manager:
                return False
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == contract.owner_id)
            result = await self.session.execute(objects_query)
            owner_objects = result.scalars().all()
            
            # Получаем существующие права
            existing_permissions = await self.get_contract_permissions(contract_id)
            existing_object_ids = {perm.object_id for perm in existing_permissions}
            
            # Создаем права для новых объектов (если есть общие права)
            if contract.manager_permissions:
                for obj in owner_objects:
                    if obj.id not in existing_object_ids:
                        await self.create_permission(contract_id, obj.id, contract.manager_permissions)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync contract permissions for contract {contract_id}: {e}")
            return False
