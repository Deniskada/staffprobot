"""
Сервис для проверки прав на создание отзывов.
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
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
            
            # 3. Проверяем, что договор завершен или активен
            if contract.status not in ['active', 'completed']:
                return {
                    "can_create": False,
                    "reason": "Отзыв можно оставить только по завершенному или активному договору"
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
                    # Для отзыва о сотруднике - берем employee_id из договора
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
                
                elif target_type == 'object':
                    # Для отзыва об объекте - получаем объекты по договору
                    # Любой участник договора может оставлять отзыв об объектах
                    objects = await self._get_objects_by_contract(contract)
                    print(f"DEBUG: Contract {contract.id} has {len(objects)} objects")
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
                            print(f"DEBUG: Added object {obj.id} ({obj.name}) to available targets")
            
            return available_targets
            
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
                # Любой участник договора может оставлять отзыв об объекте
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking target permissions: {e}")
            return False
