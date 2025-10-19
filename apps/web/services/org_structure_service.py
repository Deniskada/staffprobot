"""Сервис для работы с организационной структурой."""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from decimal import Decimal

from domain.entities.org_structure import OrgStructureUnit
from domain.entities.payment_system import PaymentSystem
from domain.entities.payment_schedule import PaymentSchedule
from core.logging.logger import logger


class OrgStructureService:
    """Сервис для управления организационной структурой."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_unit(
        self,
        owner_id: int,
        name: str,
        parent_id: Optional[int] = None,
        description: Optional[str] = None,
        organization_profile_id: Optional[int] = None,
        payment_system_id: Optional[int] = None,
        payment_schedule_id: Optional[int] = None,
        inherit_late_settings: bool = True,
        late_threshold_minutes: Optional[int] = None,
        late_penalty_per_minute: Optional[Decimal] = None,
        inherit_cancellation_settings: bool = True,
        cancellation_short_notice_hours: Optional[int] = None,
        cancellation_short_notice_fine: Optional[Decimal] = None,
        cancellation_invalid_reason_fine: Optional[Decimal] = None,
        telegram_report_chat_id: Optional[str] = None
    ) -> OrgStructureUnit:
        """
        Создать новое подразделение.
        
        Args:
            owner_id: ID владельца
            name: Название подразделения
            parent_id: ID родительского подразделения (None для корневого)
            description: Описание
            payment_system_id: ID системы оплаты (None для наследования)
            payment_schedule_id: ID графика выплат (None для наследования)
            inherit_late_settings: Наследовать настройки штрафов
            late_threshold_minutes: Допустимое опоздание
            late_penalty_per_minute: Стоимость минуты штрафа
            
        Returns:
            OrgStructureUnit: Созданное подразделение
            
        Raises:
            ValueError: Если parent_id указывает на несуществующее подразделение или создает цикл
        """
        try:
            # Валидация родителя
            if parent_id is not None:
                parent = await self.get_unit_by_id(parent_id)
                if not parent:
                    raise ValueError(f"Родительское подразделение {parent_id} не найдено")
                
                # Проверить, что parent принадлежит тому же владельцу
                if parent.owner_id != owner_id:
                    raise ValueError("Родительское подразделение принадлежит другому владельцу")
                
                # Рассчитать уровень
                level = parent.level + 1
            else:
                level = 0
            
            # Создать подразделение
            new_unit = OrgStructureUnit(
                owner_id=owner_id,
                parent_id=parent_id,
                name=name,
                description=description,
                organization_profile_id=organization_profile_id,
                payment_system_id=payment_system_id,
                payment_schedule_id=payment_schedule_id,
                inherit_late_settings=inherit_late_settings,
                late_threshold_minutes=late_threshold_minutes,
                late_penalty_per_minute=late_penalty_per_minute,
                inherit_cancellation_settings=inherit_cancellation_settings,
                cancellation_short_notice_hours=cancellation_short_notice_hours,
                cancellation_short_notice_fine=cancellation_short_notice_fine,
                cancellation_invalid_reason_fine=cancellation_invalid_reason_fine,
                telegram_report_chat_id=telegram_report_chat_id,
                level=level,
                is_active=True
            )
            
            self.db.add(new_unit)
            await self.db.commit()
            await self.db.refresh(new_unit)
            
            logger.info(
                "Org unit created",
                unit_id=new_unit.id,
                owner_id=owner_id,
                unit_name=name,
                parent_id=parent_id,
                unit_level=level
            )
            
            return new_unit
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating org unit: {e}", owner_id=owner_id, unit_name=name)
            raise
    
    async def get_unit_by_id(self, unit_id: int) -> Optional[OrgStructureUnit]:
        """
        Получить подразделение по ID.
        
        Args:
            unit_id: ID подразделения
            
        Returns:
            Optional[OrgStructureUnit]: Подразделение или None
        """
        query = select(OrgStructureUnit).options(
            selectinload(OrgStructureUnit.parent),
            selectinload(OrgStructureUnit.payment_system),
            selectinload(OrgStructureUnit.payment_schedule)
        ).where(OrgStructureUnit.id == unit_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_units_by_owner(
        self,
        owner_id: int,
        include_inactive: bool = False
    ) -> List[OrgStructureUnit]:
        """
        Получить все подразделения владельца.
        
        Args:
            owner_id: ID владельца
            include_inactive: Включать неактивные подразделения
            
        Returns:
            List[OrgStructureUnit]: Список подразделений
        """
        query = select(OrgStructureUnit).where(OrgStructureUnit.owner_id == owner_id)
        
        if not include_inactive:
            query = query.where(OrgStructureUnit.is_active == True)
        
        query = query.order_by(OrgStructureUnit.level, OrgStructureUnit.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_org_tree(self, owner_id: int) -> List[Dict[str, Any]]:
        """
        Получить древовидную структуру подразделений.
        
        Args:
            owner_id: ID владельца
            
        Returns:
            List[Dict]: Список корневых узлов с вложенными children
        """
        # Получить все подразделения владельца
        units = await self.get_units_by_owner(owner_id)
        
        # Построить дерево
        units_dict = {unit.id: {
            'id': unit.id,
            'name': unit.name,
            'description': unit.description,
            'parent_id': unit.parent_id,
            'level': unit.level,
            'payment_system_id': unit.payment_system_id,
            'payment_schedule_id': unit.payment_schedule_id,
            'inherit_late_settings': unit.inherit_late_settings,
            'late_threshold_minutes': unit.late_threshold_minutes,
            'late_penalty_per_minute': float(unit.late_penalty_per_minute) if unit.late_penalty_per_minute else None,
            'is_active': unit.is_active,
            'children': []
        } for unit in units}
        
        # Рассчитать эффективные (унаследованные) значения payment_system_id / payment_schedule_id
        for unit_id, data in units_dict.items():
            data['effective_payment_system_id'] = data['payment_system_id']
            data['effective_payment_schedule_id'] = data['payment_schedule_id']

        def resolve_effective(current_id: int) -> None:
            data = units_dict[current_id]
            # если оба значения заданы, ничего не делаем
            if data['effective_payment_system_id'] is not None and data['effective_payment_schedule_id'] is not None:
                return
            visited: set[int] = set()
            parent_id = data['parent_id']
            while parent_id is not None and parent_id in units_dict and parent_id not in visited:
                visited.add(parent_id)
                parent = units_dict[parent_id]
                if data['effective_payment_system_id'] is None:
                    data['effective_payment_system_id'] = parent.get('effective_payment_system_id')
                    if data['effective_payment_system_id'] is None:
                        data['effective_payment_system_id'] = parent.get('payment_system_id')
                if data['effective_payment_schedule_id'] is None:
                    data['effective_payment_schedule_id'] = parent.get('effective_payment_schedule_id')
                    if data['effective_payment_schedule_id'] is None:
                        data['effective_payment_schedule_id'] = parent.get('payment_schedule_id')
                parent_id = parent.get('parent_id')

        for uid in list(units_dict.keys()):
            resolve_effective(uid)

        # Построить иерархию
        tree = []
        for unit_id, unit_data in units_dict.items():
            if unit_data['parent_id'] is None:
                # Корневой узел
                tree.append(unit_data)
            else:
                # Дочерний узел
                parent_id = unit_data['parent_id']
                if parent_id in units_dict:
                    units_dict[parent_id]['children'].append(unit_data)
        
        return tree
    
    async def update_unit(
        self,
        unit_id: int,
        owner_id: int,
        data: Dict[str, Any]
    ) -> Optional[OrgStructureUnit]:
        """
        Обновить подразделение.
        
        Args:
            unit_id: ID подразделения
            owner_id: ID владельца (для проверки прав)
            data: Данные для обновления
            
        Returns:
            Optional[OrgStructureUnit]: Обновленное подразделение или None
        """
        try:
            unit = await self.get_unit_by_id(unit_id)
            if not unit or unit.owner_id != owner_id:
                return None
            
            # Обновить поля
            if 'name' in data:
                unit.name = data['name']
            if 'description' in data:
                unit.description = data['description']
            if 'organization_profile_id' in data:
                unit.organization_profile_id = data['organization_profile_id']
            if 'payment_system_id' in data:
                unit.payment_system_id = data['payment_system_id']
            if 'payment_schedule_id' in data:
                unit.payment_schedule_id = data['payment_schedule_id']
            if 'inherit_late_settings' in data:
                unit.inherit_late_settings = data['inherit_late_settings']
            if 'late_threshold_minutes' in data:
                unit.late_threshold_minutes = data['late_threshold_minutes']
            if 'late_penalty_per_minute' in data:
                unit.late_penalty_per_minute = data['late_penalty_per_minute']
            if 'inherit_cancellation_settings' in data:
                unit.inherit_cancellation_settings = data['inherit_cancellation_settings']
            if 'cancellation_short_notice_hours' in data:
                unit.cancellation_short_notice_hours = data['cancellation_short_notice_hours']
            if 'cancellation_short_notice_fine' in data:
                unit.cancellation_short_notice_fine = data['cancellation_short_notice_fine']
            if 'cancellation_invalid_reason_fine' in data:
                unit.cancellation_invalid_reason_fine = data['cancellation_invalid_reason_fine']
            if 'telegram_report_chat_id' in data:
                unit.telegram_report_chat_id = data['telegram_report_chat_id']
            if 'is_active' in data:
                unit.is_active = data['is_active']
            
            await self.db.commit()
            await self.db.refresh(unit)
            
            logger.info("Org unit updated", unit_id=unit_id, owner_id=owner_id)
            
            return unit
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating org unit: {e}", unit_id=unit_id)
            raise
    
    async def get_effective_organization_profile_id(self, unit_id: int) -> Optional[int]:
        """
        Получить эффективный organization_profile_id с учетом наследования.
        
        Если у подразделения не указан профиль - ищет в родительском дереве.
        
        Args:
            unit_id: ID подразделения
            
        Returns:
            Optional[int]: ID профиля организации или None
        """
        unit = await self.get_unit_by_id(unit_id)
        if not unit:
            return None
        
        # Если у текущего подразделения указан профиль - возвращаем его
        if unit.organization_profile_id:
            return unit.organization_profile_id
        
        # Если нет - ищем у родителя
        if unit.parent_id:
            return await self.get_effective_organization_profile_id(unit.parent_id)
        
        # Если дошли до корня и профиль не найден - возвращаем None
        # В этом случае нужно будет использовать профиль по умолчанию владельца
        return None
    
    async def delete_unit(self, unit_id: int, owner_id: int) -> bool:
        """
        Удалить подразделение (мягкое удаление - is_active = False).
        
        Args:
            unit_id: ID подразделения
            owner_id: ID владельца (для проверки прав)
            
        Returns:
            bool: True если успешно удалено
        """
        try:
            unit = await self.get_unit_by_id(unit_id)
            if not unit or unit.owner_id != owner_id:
                return False
            
            # Проверить, нет ли дочерних подразделений
            children_query = select(OrgStructureUnit).where(
                OrgStructureUnit.parent_id == unit_id,
                OrgStructureUnit.is_active == True
            )
            children_result = await self.db.execute(children_query)
            children = children_result.scalars().all()
            
            if children:
                raise ValueError(f"Невозможно удалить подразделение: есть {len(children)} дочерних подразделений")
            
            # Проверить, нет ли привязанных объектов
            from domain.entities.object import Object
            objects_query = select(Object).where(Object.org_unit_id == unit_id)
            objects_result = await self.db.execute(objects_query)
            objects = objects_result.scalars().all()
            
            if objects:
                raise ValueError(f"Невозможно удалить подразделение: к нему привязано {len(objects)} объектов")
            
            # Мягкое удаление
            unit.is_active = False
            await self.db.commit()
            
            logger.info("Org unit deleted", unit_id=unit_id, owner_id=owner_id)
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting org unit: {e}", unit_id=unit_id)
            raise
    
    async def move_unit(
        self,
        unit_id: int,
        new_parent_id: Optional[int],
        owner_id: int
    ) -> Optional[OrgStructureUnit]:
        """
        Переместить подразделение в другое родительское.
        
        Args:
            unit_id: ID перемещаемого подразделения
            new_parent_id: ID нового родителя (None для перемещения в корень)
            owner_id: ID владельца (для проверки прав)
            
        Returns:
            Optional[OrgStructureUnit]: Перемещенное подразделение или None
            
        Raises:
            ValueError: Если перемещение создает цикл
        """
        try:
            unit = await self.get_unit_by_id(unit_id)
            if not unit or unit.owner_id != owner_id:
                return None
            
            # Валидация нового родителя
            if new_parent_id is not None:
                new_parent = await self.get_unit_by_id(new_parent_id)
                if not new_parent:
                    raise ValueError(f"Новое родительское подразделение {new_parent_id} не найдено")
                
                if new_parent.owner_id != owner_id:
                    raise ValueError("Новое родительское подразделение принадлежит другому владельцу")
                
                # Проверить на циклическую ссылку
                if await self._would_create_cycle(unit_id, new_parent_id):
                    raise ValueError("Перемещение создаст циклическую ссылку")
                
                new_level = new_parent.level + 1
            else:
                new_level = 0
            
            # Переместить
            old_parent_id = unit.parent_id
            unit.parent_id = new_parent_id
            unit.level = new_level
            
            # Обновить уровни всех дочерних подразделений
            await self._update_children_levels(unit_id, new_level)
            
            await self.db.commit()
            await self.db.refresh(unit)
            
            logger.info(
                "Org unit moved",
                unit_id=unit_id,
                old_parent_id=old_parent_id,
                new_parent_id=new_parent_id,
                new_level=new_level
            )
            
            return unit
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error moving org unit: {e}", unit_id=unit_id)
            raise
    
    async def _would_create_cycle(self, unit_id: int, new_parent_id: int) -> bool:
        """
        Проверить, создаст ли перемещение циклическую ссылку.
        
        Циклическая ссылка возникает, если новый родитель является потомком перемещаемого узла.
        
        Args:
            unit_id: ID перемещаемого подразделения
            new_parent_id: ID нового родителя
            
        Returns:
            bool: True если создаст цикл
        """
        # Если пытаемся переместить узел в самого себя
        if unit_id == new_parent_id:
            return True
        
        # Получить всех потомков unit_id
        descendants = await self._get_all_descendants(unit_id)
        descendant_ids = [d.id for d in descendants]
        
        # Если new_parent_id среди потомков - будет цикл
        return new_parent_id in descendant_ids
    
    async def _get_all_descendants(self, unit_id: int) -> List[OrgStructureUnit]:
        """
        Получить всех потомков подразделения (рекурсивно).
        
        Args:
            unit_id: ID подразделения
            
        Returns:
            List[OrgStructureUnit]: Список всех потомков
        """
        # Получить прямых детей
        query = select(OrgStructureUnit).where(OrgStructureUnit.parent_id == unit_id)
        result = await self.db.execute(query)
        children = result.scalars().all()
        
        descendants = list(children)
        
        # Рекурсивно получить потомков каждого ребенка
        for child in children:
            child_descendants = await self._get_all_descendants(child.id)
            descendants.extend(child_descendants)
        
        return descendants
    
    async def _update_children_levels(self, unit_id: int, parent_level: int) -> None:
        """
        Рекурсивно обновить уровни всех дочерних подразделений.
        
        Args:
            unit_id: ID родительского подразделения
            parent_level: Уровень родителя
        """
        # Получить всех детей
        query = select(OrgStructureUnit).where(OrgStructureUnit.parent_id == unit_id)
        result = await self.db.execute(query)
        children = result.scalars().all()
        
        for child in children:
            child.level = parent_level + 1
            # Рекурсивно обновить уровни потомков
            await self._update_children_levels(child.id, child.level)
    
    async def get_inherited_payment_system(self, unit_id: int) -> Optional[PaymentSystem]:
        """
        Получить систему оплаты с учетом наследования.
        
        Args:
            unit_id: ID подразделения
            
        Returns:
            Optional[PaymentSystem]: Система оплаты или None
        """
        unit = await self.get_unit_by_id(unit_id)
        if not unit:
            return None
        
        system_id = unit.get_inherited_payment_system_id()
        if system_id is None:
            return None
        
        # Получить PaymentSystem
        query = select(PaymentSystem).where(PaymentSystem.id == system_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_inherited_payment_schedule(self, unit_id: int) -> Optional[PaymentSchedule]:
        """
        Получить график выплат с учетом наследования.
        
        Args:
            unit_id: ID подразделения
            
        Returns:
            Optional[PaymentSchedule]: График выплат или None
        """
        unit = await self.get_unit_by_id(unit_id)
        if not unit:
            return None
        
        schedule_id = unit.get_inherited_payment_schedule_id()
        if schedule_id is None:
            return None
        
        # Получить PaymentSchedule
        query = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_root_unit(self, owner_id: int) -> Optional[OrgStructureUnit]:
        """
        Получить корневое подразделение владельца.
        
        Args:
            owner_id: ID владельца
            
        Returns:
            Optional[OrgStructureUnit]: Корневое подразделение (parent_id=NULL) или None
        """
        query = select(OrgStructureUnit).where(
            OrgStructureUnit.owner_id == owner_id,
            OrgStructureUnit.parent_id == None,
            OrgStructureUnit.is_active == True
        ).order_by(OrgStructureUnit.id).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_units_count(self, owner_id: int) -> int:
        """
        Получить количество активных подразделений владельца.
        
        Args:
            owner_id: ID владельца
            
        Returns:
            int: Количество подразделений
        """
        from sqlalchemy import func
        
        query = select(func.count(OrgStructureUnit.id)).where(
            OrgStructureUnit.owner_id == owner_id,
            OrgStructureUnit.is_active == True
        )
        
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def validate_no_cycles(self, unit_id: int, parent_id: Optional[int]) -> bool:
        """
        Валидация отсутствия циклов при установке родителя.
        
        Args:
            unit_id: ID подразделения
            parent_id: Предполагаемый ID родителя
            
        Returns:
            bool: True если цикла нет
        """
        if parent_id is None:
            return True
        
        if unit_id == parent_id:
            return False
        
        return not await self._would_create_cycle(unit_id, parent_id)

