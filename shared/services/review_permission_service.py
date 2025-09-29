"""
Сервис для проверки прав на создание отзывов.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from core.logging.logger import logger
from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.review import Review


class ReviewPermissionService:
    """Сервис для проверки прав на создание отзывов."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def can_create_review(
        self, 
        user_id: int, 
        target_type: str, 
        target_id: int, 
        contract_id: int
    ) -> Dict[str, Any]:
        """
        Проверка прав на создание отзыва.
        
        Args:
            user_id: ID пользователя (внутренний)
            target_type: Тип цели ('employee' или 'object')
            target_id: ID цели
            contract_id: ID договора
            
        Returns:
            Dict с результатом проверки
        """
        try:
            # 1. Проверяем существование договора
            contract = await self._get_contract(contract_id)
            if not contract:
                return {
                    "can_create": False,
                    "reason": "Договор не найден"
                }
            
            # 2. Проверяем, что пользователь участвует в договоре
            if user_id not in [contract.owner_id, contract.employee_id]:
                return {
                    "can_create": False,
                    "reason": "Пользователь не участвует в данном договоре"
                }
            
            # 3. Проверяем, что договор завершен, активен или расторгнут
            if contract.status not in ['active', 'completed', 'terminated']:
                return {
                    "can_create": False,
                    "reason": "Отзыв можно оставить только по завершенному, активному или расторгнутому договору"
                }
            
            # 4. Проверяем связь цели с договором
            if not await self._is_target_linked_to_contract(target_type, target_id, contract):
                return {
                    "can_create": False,
                    "reason": f"Цель {target_type} #{target_id} не связана с данным договором"
                }
            
            # 5. Проверяем, что пользователь еще не оставлял отзыв по этому договору
            existing_review = await self._get_existing_review(user_id, contract_id, target_type, target_id)
            if existing_review:
                return {
                    "can_create": False,
                    "reason": "Отзыв по данному договору уже оставлен",
                    "existing_review_id": existing_review.id
                }
            
            # 6. Проверяем права на создание отзыва по типу цели
            if not await self._check_target_permissions(user_id, target_type, target_id, contract):
                return {
                    "can_create": False,
                    "reason": f"Нет прав на создание отзыва о {target_type}"
                }
            
            return {
                "can_create": True,
                "reason": "Все проверки пройдены"
            }
            
        except Exception as e:
            logger.error(f"Error checking review creation permissions: {e}")
            return {
                "can_create": False,
                "reason": "Ошибка проверки прав"
            }
    
    async def get_available_targets_for_review(
        self, 
        user_id: int, 
        target_type: str
    ) -> List[Dict[str, Any]]:
        """
        Получение доступных целей для создания отзыва.
        
        Args:
            user_id: ID пользователя (внутренний)
            target_type: Тип цели ('employee' или 'object')
            
        Returns:
            List доступных целей
        """
        try:
            print(f"DEBUG: get_available_targets_for_review called with user_id={user_id}, target_type={target_type}")
            
            # Получаем пользователя для проверки ролей
            user = await self._get_user(user_id)
            if not user:
                print(f"DEBUG: User {user_id} not found")
                return []
            
            print(f"DEBUG: User roles: {user.get_roles()}")
            
            # Получаем договоры пользователя (все статусы)
            contracts_query = select(Contract).where(
                or_(
                    Contract.owner_id == user_id,
                    Contract.employee_id == user_id
                )
            )
            
            result = await self.db.execute(contracts_query)
            contracts = result.scalars().all()
            
            print(f"DEBUG: Found {len(contracts)} contracts for user {user_id}")
            
            available_targets = []
            
            for contract in contracts:
                if target_type == 'employee':
                    # Для отзыва о сотруднике - владельцы и управляющие
                    if contract.owner_id == user_id:  # Владелец договора
                        if contract.employee_id != user_id:  # Не оставляем отзыв о себе
                            employee = await self._get_user(contract.employee_id)
                            if employee:
                                # Проверяем, что отзыв еще не оставлен
                                existing_review = await self._get_existing_review(
                                    user_id, contract.id, target_type, contract.employee_id
                                )
                                if not existing_review:
                                    available_targets.append({
                                        "id": contract.employee_id,
                                        "name": f"{employee.first_name} {employee.last_name}",
                                        "contract_id": contract.id,
                                        "contract_number": contract.contract_number,
                                        "contract_title": contract.title
                                    })
                                    print(f"DEBUG: Added owner employee {contract.employee_id} ({employee.first_name} {employee.last_name}) to available targets")
                
                elif target_type == 'object':
                    # Для отзыва об объекте - сотрудники и владельцы
                    if contract.employee_id == user_id:  # Сотрудник договора
                        # Для сотрудника показываем объекты владельца договора
                        objects = await self._get_objects_by_owner(contract.owner_id)
                        print(f"DEBUG: Contract {contract.id} owner {contract.owner_id} has {len(objects)} objects")
                        for obj in objects:
                            # Проверяем, что отзыв еще не оставлен
                            existing_review = await self._get_existing_review(
                                user_id, contract.id, target_type, obj.id
                            )
                            if not existing_review:
                                available_targets.append({
                                    "id": obj.id,
                                    "name": obj.name,
                                    "address": obj.address,
                                    "contract_id": contract.id,
                                    "contract_number": contract.contract_number,
                                    "contract_title": contract.title
                                })
                                print(f"DEBUG: Added employee object {obj.id} ({obj.name}) to available targets")
                    
                    elif contract.owner_id == user_id:  # Владелец договора
                        # Для владельца показываем его объекты
                        objects = await self._get_objects_by_owner(contract.owner_id)
                        print(f"DEBUG: Owner contract {contract.id} has {len(objects)} objects")
                        for obj in objects:
                            # Проверяем, что отзыв еще не оставлен
                            existing_review = await self._get_existing_review(
                                user_id, contract.id, target_type, obj.id
                            )
                            if not existing_review:
                                available_targets.append({
                                    "id": obj.id,
                                    "name": obj.name,
                                    "address": obj.address,
                                    "contract_id": contract.id,
                                    "contract_number": contract.contract_number,
                                    "contract_title": contract.title
                                })
                                print(f"DEBUG: Added owner object {obj.id} ({obj.name}) to available targets")
            
            # Дополнительная логика для управляющих
            if user.is_manager():
                if target_type == 'object':
                    print(f"DEBUG: User is manager, checking manager permissions for objects")
                    manager_objects = await self._get_objects_for_manager(user_id)
                    for obj in manager_objects:
                        # Проверяем, что отзыв еще не оставлен (без привязки к договору)
                        existing_review = await self._get_existing_review_for_manager(
                            user_id, target_type, obj.id
                        )
                        if not existing_review:
                            available_targets.append({
                                "id": obj.id,
                                "name": obj.name,
                                "address": obj.address,
                                "contract_id": None,  # Нет привязки к договору
                                "contract_number": "Управляющий",
                                "contract_title": "Права управляющего"
                            })
                            print(f"DEBUG: Added manager object {obj.id} ({obj.name}) to available targets")
                
                elif target_type == 'employee':
                    print(f"DEBUG: User is manager, checking manager permissions for employees")
                    manager_employees = await self._get_employees_for_manager(user_id)
                    for employee in manager_employees:
                        # Проверяем, что отзыв еще не оставлен (без привязки к договору)
                        existing_review = await self._get_existing_review_for_manager(
                            user_id, target_type, employee.id
                        )
                        if not existing_review:
                            available_targets.append({
                                "id": employee.id,
                                "name": f"{employee.first_name} {employee.last_name}",
                                "contract_id": None,  # Нет привязки к договору
                                "contract_number": "Управляющий",
                                "contract_title": "Права управляющего"
                            })
                            print(f"DEBUG: Added manager employee {employee.id} ({employee.first_name} {employee.last_name}) to available targets")
            
            # Убираем дубликаты по id
            seen_ids = set()
            unique_targets = []
            for target in available_targets:
                if target["id"] not in seen_ids:
                    seen_ids.add(target["id"])
                    unique_targets.append(target)
            
            return unique_targets
            
        except Exception as e:
            logger.error(f"Error getting available targets for review: {e}")
            return []
    
    async def _get_contract(self, contract_id: int) -> Optional[Contract]:
        """Получение договора по ID."""
        try:
            query = select(Contract).where(Contract.id == contract_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting contract {contract_id}: {e}")
            return None
    
    async def _get_user(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def _get_objects_by_contract(self, contract: Contract) -> List[Object]:
        """Получение объектов по договору."""
        try:
            if not contract.allowed_objects:
                return []
            
            # Получаем объекты по ID из allowed_objects
            objects_query = select(Object).where(Object.id.in_(contract.allowed_objects))
            result = await self.db.execute(objects_query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting objects by contract: {e}")
            return []
    
    async def _get_objects_by_owner(self, owner_id: int) -> List[Object]:
        """Получение объектов по владельцу."""
        try:
            objects_query = select(Object).where(Object.owner_id == owner_id)
            result = await self.db.execute(objects_query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting objects by owner {owner_id}: {e}")
            return []
    
    async def _is_target_linked_to_contract(
        self, 
        target_type: str, 
        target_id: int, 
        contract: Contract
    ) -> bool:
        """Проверка связи цели с договором."""
        try:
            if target_type == 'employee':
                return contract.employee_id == target_id
            elif target_type == 'object':
                # TODO: Реализовать проверку связи объекта с договором
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking target link to contract: {e}")
            return False
    
    async def _get_existing_review(
        self, 
        user_id: int, 
        contract_id: int, 
        target_type: str, 
        target_id: int
    ) -> Optional[Review]:
        """Получение существующего отзыва."""
        try:
            query = select(Review).where(
                and_(
                    Review.reviewer_id == user_id,
                    Review.contract_id == contract_id,
                    Review.target_type == target_type,
                    Review.target_id == target_id
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting existing review: {e}")
            return None
    
    async def _check_target_permissions(
        self, 
        user_id: int, 
        target_type: str, 
        target_id: int, 
        contract: Contract
    ) -> bool:
        """Проверка прав на создание отзыва по типу цели."""
        try:
            if target_type == 'employee':
                # Владелец может оставлять отзыв о сотруднике
                return contract.owner_id == user_id
            elif target_type == 'object':
                # Сотрудник может оставлять отзыв об объекте
                return contract.employee_id == user_id
            return False
        except Exception as e:
            logger.error(f"Error checking target permissions: {e}")
            return False
    
    async def _get_objects_for_manager(self, user_id: int) -> List[Object]:
        """Получение объектов для управляющего через ManagerObjectPermission."""
        try:
            from domain.entities.manager_object_permission import ManagerObjectPermission
            
            # Получаем все права управляющего на объекты
            permissions_query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.contract_id.in_(
                    select(Contract.id).where(
                        or_(
                            Contract.owner_id == user_id,
                            Contract.employee_id == user_id
                        )
                    )
                )
            ).options(selectinload(ManagerObjectPermission.object))
            
            result = await self.db.execute(permissions_query)
            permissions = result.scalars().all()
            
            # Извлекаем объекты из прав
            objects = []
            for permission in permissions:
                if permission.object and permission.has_any_permission():
                    objects.append(permission.object)
            
            return objects
        except Exception as e:
            logger.error(f"Error getting objects for manager: {e}")
            return []
    
    async def _get_existing_review_for_manager(
        self, 
        user_id: int, 
        target_type: str, 
        target_id: int
    ) -> Optional[Review]:
        """Получение существующего отзыва для управляющего (без привязки к договору)."""
        try:
            query = select(Review).where(
                and_(
                    Review.reviewer_id == user_id,
                    Review.target_type == target_type,
                    Review.target_id == target_id,
                    Review.contract_id.is_(None)  # Отзыв без привязки к договору
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting existing review for manager: {e}")
            return None
    
    async def _get_employees_for_manager(self, user_id: int) -> List[User]:
        """Получение сотрудников для управляющего через объекты, к которым у него есть доступ."""
        try:
            from domain.entities.manager_object_permission import ManagerObjectPermission
            
            # 1. Находим объекты, к которым у управляющего есть доступ
            permissions_query = select(ManagerObjectPermission).where(
                ManagerObjectPermission.contract_id.in_(
                    select(Contract.id).where(
                        or_(
                            Contract.owner_id == user_id,
                            Contract.employee_id == user_id
                        )
                    )
                )
            ).options(selectinload(ManagerObjectPermission.object))
            
            result = await self.db.execute(permissions_query)
            permissions = result.scalars().all()
            
            # Получаем ID объектов, к которым есть доступ
            accessible_object_ids = set()
            for permission in permissions:
                if permission.object and permission.has_any_permission():
                    accessible_object_ids.add(permission.object.id)
            
            print(f"DEBUG: Manager {user_id} has access to objects: {list(accessible_object_ids)}")
            
            if not accessible_object_ids:
                return []
            
            # 2. Находим договоры, которые дают доступ к этим объектам
            # Поскольку allowed_objects - это JSON, используем простую проверку
            contracts_query = select(Contract)
            result = await self.db.execute(contracts_query)
            all_contracts = result.scalars().all()
            
            # Фильтруем договоры, которые содержат нужные объекты
            contracts = []
            for contract in all_contracts:
                if contract.allowed_objects:
                    # Проверяем пересечение массивов
                    contract_objects = set(contract.allowed_objects)
                    if contract_objects.intersection(accessible_object_ids):
                        contracts.append(contract)
            
            print(f"DEBUG: Found {len(contracts)} contracts with access to these objects")
            
            # 3. Извлекаем сотрудников из этих договоров
            employees = []
            for contract in contracts:
                if contract.employee_id != user_id:  # Не включаем самого себя
                    employee = await self._get_user(contract.employee_id)
                    if employee and employee not in employees:
                        employees.append(employee)
                        print(f"DEBUG: Added employee {employee.id} ({employee.first_name} {employee.last_name}) from contract {contract.id}")
            
            return employees
        except Exception as e:
            logger.error(f"Error getting employees for manager: {e}")
            return []
