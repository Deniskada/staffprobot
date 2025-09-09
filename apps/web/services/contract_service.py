"""Сервис для управления договорами."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from domain.entities.contract import Contract, ContractTemplate, ContractVersion
from domain.entities.user import User
from domain.entities.object import Object
from core.logging.logger import logger


class ContractService:
    """Сервис для управления договорами."""
    
    async def create_contract_template(
        self,
        template_data: Dict[str, Any]
    ) -> Optional[ContractTemplate]:
        """Создание шаблона договора."""
        async with get_async_session() as session:
            # Находим пользователя по telegram_id
            user_query = select(User).where(User.telegram_id == template_data["created_by"])
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise ValueError(f"Пользователь с Telegram ID {template_data['created_by']} не найден")
            
            template = ContractTemplate(
                name=template_data["name"],
                description=template_data.get("description", ""),
                content=template_data["content"],
                version=template_data.get("version", "1.0"),
                created_by=user.id,  # Используем id из БД
                is_public=bool(template_data.get("is_public", False)),
                fields_schema=template_data.get("fields_schema")
            )
            
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            logger.info(f"Created contract template: {template.id} - {template_data['name']}")
            return template
    
    async def get_contract_templates(self) -> List[ContractTemplate]:
        """Получение списка шаблонов договоров."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(ContractTemplate.is_active == True)
            query = query.order_by(ContractTemplate.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_contract_templates_for_user(self, user_id: int) -> List[ContractTemplate]:
        """Получение списка шаблонов договоров для пользователя (свои + публичные)."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(
                (ContractTemplate.created_by == user_id) | 
                (ContractTemplate.is_public == True)
            ).where(ContractTemplate.is_active == True)
            query = query.order_by(ContractTemplate.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_contract_template(self, template_id: int) -> Optional[ContractTemplate]:
        """Получение шаблона договора по ID."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(ContractTemplate.id == template_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def create_contract(
        self,
        owner_telegram_id: int,
        contract_data: Dict[str, Any]
    ) -> Optional[Contract]:
        """Создание договора с сотрудником."""
        async with get_async_session() as session:
            # Находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                raise ValueError(f"Владелец с Telegram ID {owner_telegram_id} не найден")
            
            # Находим сотрудника по telegram_id
            employee_query = select(User).where(User.telegram_id == contract_data["employee_telegram_id"])
            employee_result = await session.execute(employee_query)
            employee = employee_result.scalar_one_or_none()
            
            if not employee:
                raise ValueError(f"Сотрудник с Telegram ID {contract_data['employee_telegram_id']} не найден")
            
            # Генерируем номер договора
            contract_number = await self._generate_contract_number(owner.id)
            
            # Генерируем контент из шаблона, если нужно
            content = contract_data.get("content")
            values = contract_data.get("values", {})
            
            if contract_data.get("template_id") and values:
                # Получаем шаблон
                template_query = select(ContractTemplate).where(ContractTemplate.id == contract_data["template_id"])
                template_result = await session.execute(template_query)
                template = template_result.scalar_one_or_none()
                
                if template and template.content and not content:
                    # Генерируем контент из шаблона
                    content = await self._generate_content_from_template(template.content, values, owner, employee)
            
            # Создаем договор
            contract = Contract(
                contract_number=contract_number,
                owner_id=owner.id,
                employee_id=employee.id,
                template_id=contract_data.get("template_id"),
                title=contract_data["title"],
                content=content,
                values=values if values else None,
                hourly_rate=contract_data.get("hourly_rate"),
                start_date=contract_data["start_date"],
                end_date=contract_data.get("end_date"),
                allowed_objects=contract_data.get("allowed_objects", [])
            )
            
            session.add(contract)
            await session.commit()
            await session.refresh(contract)
            
            logger.info(f"Created contract: {contract.id} - {contract_number}")
            return contract
    
    async def get_owner_contracts(self, owner_id: int, active_only: bool = True) -> List[Contract]:
        """Получение договоров владельца."""
        async with get_async_session() as session:
            query = select(Contract).where(Contract.owner_id == owner_id)
            if active_only:
                query = query.where(Contract.is_active == True)
            
            query = query.options(
                selectinload(Contract.employee),
                selectinload(Contract.template)
            ).order_by(Contract.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_employee_contracts(self, employee_id: int, active_only: bool = True) -> List[Contract]:
        """Получение договоров сотрудника."""
        async with get_async_session() as session:
            query = select(Contract).where(Contract.employee_id == employee_id)
            if active_only:
                query = query.where(Contract.is_active == True)
            
            query = query.options(
                selectinload(Contract.owner),
                selectinload(Contract.template)
            ).order_by(Contract.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_contract(self, contract_id: int) -> Optional[Contract]:
        """Получение договора по ID."""
        async with get_async_session() as session:
            query = select(Contract).where(Contract.id == contract_id)
            query = query.options(
                selectinload(Contract.owner),
                selectinload(Contract.employee),
                selectinload(Contract.template)
            )
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def update_contract(
        self,
        contract_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        hourly_rate: Optional[int] = None,
        end_date: Optional[datetime] = None,
        allowed_objects: Optional[List[int]] = None
    ) -> Optional[Contract]:
        """Обновление договора."""
        async with get_async_session() as session:
            query = select(Contract).where(Contract.id == contract_id)
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return None
            
            # Сохраняем версию перед изменением
            if content and content != contract.content:
                await self._create_contract_version(
                    contract_id, 
                    contract.content, 
                    "Обновление содержания договора",
                    contract.owner_id
                )
            
            # Обновляем поля
            if title is not None:
                contract.title = title
            if content is not None:
                contract.content = content
            if hourly_rate is not None:
                contract.hourly_rate = hourly_rate
            if end_date is not None:
                contract.end_date = end_date
            if allowed_objects is not None:
                contract.allowed_objects = allowed_objects
            
            contract.updated_at = datetime.now()
            await session.commit()
            await session.refresh(contract)
            
            logger.info(f"Updated contract: {contract.id}")
            return contract
    
    async def terminate_contract(self, contract_id: int, reason: str = None) -> bool:
        """Расторжение договора."""
        async with get_async_session() as session:
            query = select(Contract).where(Contract.id == contract_id)
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            contract.status = "terminated"
            contract.is_active = False
            contract.terminated_at = datetime.now()
            
            # Создаем версию с причиной расторжения
            await self._create_contract_version(
                contract_id,
                contract.content,
                f"Договор расторгнут. Причина: {reason or 'Не указана'}",
                contract.owner_id
            )
            
            await session.commit()
            
            logger.info(f"Terminated contract: {contract.id}")
            return True
    
    async def get_contract_employees(self, owner_id: int) -> List[Dict[str, Any]]:
        """Получение списка сотрудников владельца с информацией о договорах."""
        async with get_async_session() as session:
            # Получаем всех сотрудников, с которыми есть договоры
            query = select(Contract).where(
                and_(
                    Contract.owner_id == owner_id,
                    Contract.is_active == True
                )
            ).options(
                selectinload(Contract.employee)
            )
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            # Группируем по сотрудникам
            employees = {}
            for contract in contracts:
                employee = contract.employee
                if employee.id not in employees:
                    employees[employee.id] = {
                        'id': employee.id,
                        'telegram_id': employee.telegram_id,
                        'first_name': employee.first_name,
                        'last_name': employee.last_name,
                        'username': employee.username,
                        'contracts': []
                    }
                
                employees[employee.id]['contracts'].append({
                    'id': contract.id,
                    'contract_number': contract.contract_number,
                    'title': contract.title,
                    'status': contract.status,
                    'hourly_rate': contract.hourly_rate,
                    'start_date': contract.start_date,
                    'end_date': contract.end_date,
                    'allowed_objects': contract.allowed_objects or []
                })
            
            return list(employees.values())
    
    async def get_contract_employees_by_telegram_id(self, owner_telegram_id: int) -> List[Dict[str, Any]]:
        """Получение списка сотрудников владельца по telegram_id."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return []
            
            # Получаем всех сотрудников, с которыми есть активные договоры
            query = select(Contract).where(
                and_(
                    Contract.owner_id == owner.id,
                    Contract.status == 'active',
                    Contract.is_active == True
                )
            ).options(
                selectinload(Contract.employee)
            )
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            # Получаем информацию об объектах владельца
            objects_query = select(Object).where(
                and_(
                    Object.owner_id == owner.id,
                    Object.is_active == True
                )
            )
            objects_result = await session.execute(objects_query)
            objects = {obj.id: obj for obj in objects_result.scalars().all()}
            
            # Группируем по сотрудникам
            employees = {}
            for contract in contracts:
                employee = contract.employee
                if employee.id not in employees:
                    employees[employee.id] = {
                        'id': employee.id,
                        'telegram_id': employee.telegram_id,
                        'first_name': employee.first_name,
                        'last_name': employee.last_name,
                        'username': employee.username,
                        'contracts': [],
                        'accessible_objects': set()  # Объекты, к которым есть доступ
                    }
                
                # Определяем доступные объекты для этого договора
                contract_objects = []
                if contract.allowed_objects:
                    # Если указаны конкретные объекты
                    for obj_id in contract.allowed_objects:
                        if obj_id in objects:
                            obj = objects[obj_id]
                            contract_objects.append({
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address
                            })
                            employees[employee.id]['accessible_objects'].add(obj.id)
                else:
                    # Если не указаны - доступ ко всем объектам
                    contract_objects = [
                        {
                            'id': obj.id,
                            'name': obj.name,
                            'address': obj.address
                        } for obj in objects.values()
                    ]
                    for obj in objects.values():
                        employees[employee.id]['accessible_objects'].add(obj.id)
                
                employees[employee.id]['contracts'].append({
                    'id': contract.id,
                    'contract_number': contract.contract_number,
                    'title': contract.title,
                    'status': contract.status,
                    'is_active': contract.is_active,
                    'hourly_rate': contract.hourly_rate,
                    'start_date': contract.start_date,
                    'end_date': contract.end_date,
                    'allowed_objects': contract.allowed_objects or [],
                    'allowed_objects_info': contract_objects
                })
            
            # Преобразуем set в list для JSON сериализации
            for employee in employees.values():
                employee['accessible_objects'] = [
                    {
                        'id': obj_id,
                        'name': objects[obj_id].name,
                        'address': objects[obj_id].address
                    } for obj_id in employee['accessible_objects'] if obj_id in objects
                ]
            
            return list(employees.values())
    
    async def get_all_contract_employees_by_telegram_id(self, owner_telegram_id: int) -> List[Dict[str, Any]]:
        """Получение всех сотрудников владельца (включая бывших) по telegram_id."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return []
            
            # Получаем всех сотрудников, с которыми есть договоры (включая неактивные)
            query = select(Contract).where(
                Contract.owner_id == owner.id
            ).options(
                selectinload(Contract.employee)
            )
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            # Получаем информацию об объектах владельца
            objects_query = select(Object).where(
                and_(
                    Object.owner_id == owner.id,
                    Object.is_active == True
                )
            )
            objects_result = await session.execute(objects_query)
            objects = {obj.id: obj for obj in objects_result.scalars().all()}
            
            # Группируем по сотрудникам
            employees = {}
            for contract in contracts:
                employee = contract.employee
                if employee.id not in employees:
                    employees[employee.id] = {
                        'id': employee.id,
                        'telegram_id': employee.telegram_id,
                        'first_name': employee.first_name,
                        'last_name': employee.last_name,
                        'username': employee.username,
                        'created_at': employee.created_at,
                        'contracts': [],
                        'accessible_objects': set()  # Объекты, к которым есть доступ
                    }
                
                # Определяем доступные объекты для этого договора (только для активных)
                contract_objects = []
                if contract.status == 'active' and contract.is_active:
                    if contract.allowed_objects:
                        # Если указаны конкретные объекты
                        for obj_id in contract.allowed_objects:
                            if obj_id in objects:
                                obj = objects[obj_id]
                                contract_objects.append({
                                    'id': obj.id,
                                    'name': obj.name,
                                    'address': obj.address
                                })
                                employees[employee.id]['accessible_objects'].add(obj.id)
                    else:
                        # Если не указаны - доступ ко всем объектам
                        contract_objects = [
                            {
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address
                            } for obj in objects.values()
                        ]
                        for obj in objects.values():
                            employees[employee.id]['accessible_objects'].add(obj.id)
                
                employees[employee.id]['contracts'].append({
                    'id': contract.id,
                    'contract_number': contract.contract_number,
                    'title': contract.title,
                    'status': contract.status,
                    'hourly_rate': contract.hourly_rate,
                    'start_date': contract.start_date,
                    'end_date': contract.end_date,
                    'allowed_objects': contract.allowed_objects or [],
                    'allowed_objects_info': contract_objects,
                    'is_active': contract.is_active
                })
            
            # Преобразуем set в list для JSON сериализации
            for employee in employees.values():
                employee['accessible_objects'] = [
                    {
                        'id': obj_id,
                        'name': objects[obj_id].name,
                        'address': objects[obj_id].address
                    } for obj_id in employee['accessible_objects'] if obj_id in objects
                ]
            
            return list(employees.values())
    
    async def get_available_objects_for_contract(self, owner_id: int) -> List[Object]:
        """Получение доступных объектов для назначения в договор."""
        async with get_async_session() as session:
            query = select(Object).where(
                and_(
                    Object.owner_id == owner_id,
                    Object.is_active == True
                )
            ).order_by(Object.name)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def _generate_contract_number(self, owner_id: int) -> str:
        """Генерация уникального номера договора."""
        async with get_async_session() as session:
            # Получаем количество договоров владельца
            query = select(Contract).where(Contract.owner_id == owner_id)
            result = await session.execute(query)
            contracts_count = len(result.scalars().all())
            
            # Генерируем номер: OWNER_ID-YYYY-NNNNNN
            year = datetime.now().year
            number = f"{owner_id:03d}-{year}-{contracts_count + 1:06d}"
            
            # Проверяем уникальность
            existing_query = select(Contract).where(Contract.contract_number == number)
            existing_result = await session.execute(existing_query)
            if existing_result.scalar_one_or_none():
                # Если номер уже существует, добавляем суффикс
                counter = 1
                while True:
                    new_number = f"{number}-{counter}"
                    check_query = select(Contract).where(Contract.contract_number == new_number)
                    check_result = await session.execute(check_query)
                    if not check_result.scalar_one_or_none():
                        return new_number
                    counter += 1
            
            return number
    
    async def _create_contract_version(
        self,
        contract_id: int,
        content: str,
        changes_description: str,
        created_by: int
    ) -> ContractVersion:
        """Создание версии договора."""
        async with get_async_session() as session:
            # Получаем последнюю версию
            query = select(ContractVersion).where(ContractVersion.contract_id == contract_id)
            query = query.order_by(ContractVersion.created_at.desc())
            result = await session.execute(query)
            last_version = result.scalar_one_or_none()
            
            # Генерируем номер версии
            if last_version:
                version_parts = last_version.version_number.split('.')
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                version_number = '.'.join(version_parts)
            else:
                version_number = "1.0"
            
            version = ContractVersion(
                contract_id=contract_id,
                version_number=version_number,
                content=content,
                changes_description=changes_description,
                created_by=created_by
            )
            
            session.add(version)
            await session.commit()
            await session.refresh(version)
            
            return version
    
    async def get_available_employees(self, owner_id: int) -> List[Dict[str, Any]]:
        """Получение доступных сотрудников для создания договора."""
        async with get_async_session() as session:
            # Получаем всех пользователей с ролью employee
            query = select(User).where(
                and_(
                    User.role == "employee",
                    User.is_active == True
                )
            ).order_by(User.first_name, User.last_name)
            
            result = await session.execute(query)
            employees = result.scalars().all()
            
            return [
                {
                    "id": emp.id,
                    "telegram_id": emp.telegram_id,
                    "first_name": emp.first_name,
                    "last_name": emp.last_name,
                    "username": emp.username,
                    "display_name": f"{emp.first_name} {emp.last_name or ''}".strip() or emp.username or f"ID: {emp.telegram_id}"
                }
                for emp in employees
            ]
    
    async def get_owner_objects(self, owner_telegram_id: int) -> List[Object]:
        """Получение объектов владельца по telegram_id."""
        async with get_async_session() as session:
            # Сначала находим пользователя по telegram_id
            user_query = select(User).where(User.telegram_id == owner_telegram_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return []
            
            # Теперь ищем объекты по owner_id из базы данных
            query = select(Object).where(
                and_(
                    Object.owner_id == user.id,
                    Object.is_active == True
                )
            ).order_by(Object.name)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_contract_templates(self) -> List[ContractTemplate]:
        """Получение шаблонов договоров."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(ContractTemplate.is_active == True)
            query = query.order_by(ContractTemplate.created_at.desc())
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_contract_template(self, template_id: int) -> Optional[ContractTemplate]:
        """Получение шаблона договора по ID."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(
                and_(
                    ContractTemplate.id == template_id,
                    ContractTemplate.is_active == True
                )
            )
            
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
    async def update_contract_template(self, template_id: int, template_data: Dict[str, Any]) -> bool:
        """Обновление шаблона договора."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(
                and_(
                    ContractTemplate.id == template_id,
                    ContractTemplate.is_active == True
                )
            )
            
            result = await session.execute(query)
            template = result.scalar_one_or_none()
            
            if not template:
                return False
            
            # Обновляем поля
            template.name = template_data["name"]
            template.description = template_data.get("description", "")
            template.content = template_data["content"]
            template.version = template_data["version"]
            # Новые поля
            template.is_public = bool(template_data.get("is_public", False))
            template.fields_schema = template_data.get("fields_schema")
            
            await session.commit()
            
            logger.info(f"Updated template: {template.id}")
            return True
    
    async def delete_contract_template(self, template_id: int) -> bool:
        """Удаление шаблона договора (мягкое удаление)."""
        async with get_async_session() as session:
            query = select(ContractTemplate).where(
                and_(
                    ContractTemplate.id == template_id,
                    ContractTemplate.is_active == True
                )
            )
            
            result = await session.execute(query)
            template = result.scalar_one_or_none()
            
            if not template:
                return False
            
            # Мягкое удаление
            template.is_active = False
            await session.commit()
            
            logger.info(f"Deleted template: {template.id}")
            return True
    
    async def get_employee_by_id(self, employee_id: int, owner_id: int) -> Optional[Dict[str, Any]]:
        """Получение сотрудника по ID с проверкой прав владельца."""
        async with get_async_session() as session:
            # Проверяем, что у владельца есть договор с этим сотрудником
            query = select(Contract).where(
                and_(
                    Contract.owner_id == owner_id,
                    Contract.employee_id == employee_id,
                    Contract.is_active == True
                )
            ).options(selectinload(Contract.employee))
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            if not contracts:
                return None
            
            employee = contracts[0].employee
            return {
                "id": employee.id,
                "telegram_id": employee.telegram_id,
                "first_name": employee.first_name,
                "last_name": employee.last_name,
                "username": employee.username,
                "contracts": [
                    {
                        "id": contract.id,
                        "contract_number": contract.contract_number,
                        "title": contract.title,
                        "status": contract.status,
                        "hourly_rate": contract.hourly_rate,
                        "start_date": contract.start_date,
                        "end_date": contract.end_date,
                        "allowed_objects": contract.allowed_objects or []
                    }
                    for contract in contracts
                ]
            }
    
    async def get_employee_by_telegram_id(self, employee_id: int, owner_telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о сотруднике по telegram_id владельца."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return None
            
            # Получаем сотрудника с договорами (включая неактивные)
            query = select(Contract).where(
                and_(
                    Contract.employee_id == employee_id,
                    Contract.owner_id == owner.id
                )
            ).options(
                selectinload(Contract.employee)
            )
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
            if not contracts:
                return None
            
            # Берем первого сотрудника (все договоры с одним сотрудником)
            employee = contracts[0].employee
            
            # Получаем информацию об объектах
            objects_info = {}
            if contracts:
                object_ids = set()
                for contract in contracts:
                    if contract.allowed_objects:
                        object_ids.update(contract.allowed_objects)
                
                if object_ids:
                    objects_query = select(Object).where(Object.id.in_(object_ids))
                    objects_result = await session.execute(objects_query)
                    objects = objects_result.scalars().all()
                    objects_info = {obj.id: obj for obj in objects}
            
            return {
                'id': employee.id,
                'telegram_id': employee.telegram_id,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'username': employee.username,
                'created_at': employee.created_at,
                'contracts': [{
                    'id': contract.id,
                    'contract_number': contract.contract_number,
                    'title': contract.title,
                    'status': contract.status,
                    'hourly_rate': contract.hourly_rate,
                    'start_date': contract.start_date,
                    'end_date': contract.end_date,
                    'allowed_objects': contract.allowed_objects or [],
                    'is_active': contract.is_active,
                    'allowed_objects_info': [objects_info.get(obj_id) for obj_id in (contract.allowed_objects or []) if objects_info.get(obj_id)]
                } for contract in contracts]
            }
    
    async def get_contract_by_id(self, contract_id: int, owner_id: int) -> Optional[Dict[str, Any]]:
        """Получение договора по ID с проверкой прав владельца."""
        async with get_async_session() as session:
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner_id
                )
            ).options(
                selectinload(Contract.employee),
                selectinload(Contract.template)
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return None
            
            return {
                "id": contract.id,
                "contract_number": contract.contract_number,
                "title": contract.title,
                "content": contract.content,
                "status": contract.status,
                "hourly_rate": contract.hourly_rate,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "allowed_objects": contract.allowed_objects or [],
                "employee": {
                    "id": contract.employee.id,
                    "telegram_id": contract.employee.telegram_id,
                    "first_name": contract.employee.first_name,
                    "last_name": contract.employee.last_name,
                    "username": contract.employee.username
                },
                "template": {
                    "id": contract.template.id,
                    "name": contract.template.name
                } if contract.template else None
            }
    
    async def get_contract_by_telegram_id(self, contract_id: int, owner_telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение договора по ID с проверкой прав владельца по telegram_id."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return None
            
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner.id,
                    Contract.is_active == True
                )
            ).options(
                selectinload(Contract.employee),
                selectinload(Contract.template)
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return None
            
            # Получаем информацию об объектах
            allowed_objects_info = []
            if contract.allowed_objects:
                objects_query = select(Object).where(Object.id.in_(contract.allowed_objects))
                objects_result = await session.execute(objects_query)
                objects = objects_result.scalars().all()
                allowed_objects_info = [
                    {"id": obj.id, "name": obj.name, "address": obj.address}
                    for obj in objects
                ]
            
            return {
                "id": contract.id,
                "contract_number": contract.contract_number,
                "title": contract.title,
                "content": contract.content,
                "hourly_rate": contract.hourly_rate,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "status": contract.status,
                "allowed_objects": contract.allowed_objects or [],
                "allowed_objects_info": allowed_objects_info,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "signed_at": contract.signed_at,
                "terminated_at": contract.terminated_at,
                "owner": {
                    "id": owner.id,
                    "telegram_id": owner.telegram_id,
                    "first_name": owner.first_name,
                    "last_name": owner.last_name,
                    "username": owner.username
                },
                "employee": {
                    "id": contract.employee.id,
                    "telegram_id": contract.employee.telegram_id,
                    "first_name": contract.employee.first_name,
                    "last_name": contract.employee.last_name,
                    "username": contract.employee.username
                },
                "template": {
                    "id": contract.template.id,
                    "name": contract.template.name,
                    "version": contract.template.version
                } if contract.template else None
            }
    
    async def update_contract_by_telegram_id(
        self, 
        contract_id: int, 
        owner_telegram_id: int, 
        contract_data: Dict[str, Any]
    ) -> bool:
        """Обновление договора по telegram_id владельца."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return False
            
            # Получаем договор
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner.id,
                    Contract.is_active == True
                )
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            # Обновляем поля
            contract.title = contract_data["title"]
            contract.content = contract_data["content"]
            contract.hourly_rate = contract_data.get("hourly_rate")
            contract.start_date = contract_data["start_date"]
            contract.end_date = contract_data.get("end_date")
            contract.template_id = contract_data.get("template_id")
            contract.allowed_objects = contract_data.get("allowed_objects", [])
            
            await session.commit()
            
            logger.info(f"Updated contract: {contract.id}")
            return True
    
    async def update_contract(self, contract_id: int, owner_id: int, contract_data: Dict[str, Any]) -> bool:
        """Обновление договора."""
        async with get_async_session() as session:
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner_id
                )
            )
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            # Сохраняем версию перед изменением
            if "content" in contract_data and contract_data["content"] != contract.content:
                await self._create_contract_version(
                    contract_id, 
                    contract.content, 
                    "Обновление содержания договора",
                    owner_id
                )
            
            # Обновляем поля
            if "title" in contract_data:
                contract.title = contract_data["title"]
            if "content" in contract_data:
                contract.content = contract_data["content"]
            if "hourly_rate" in contract_data:
                contract.hourly_rate = contract_data["hourly_rate"]
            if "start_date" in contract_data:
                contract.start_date = contract_data["start_date"]
            if "end_date" in contract_data:
                contract.end_date = contract_data["end_date"]
            if "allowed_objects" in contract_data:
                contract.allowed_objects = contract_data["allowed_objects"]
            
            contract.updated_at = datetime.now()
            await session.commit()
            
            logger.info(f"Updated contract: {contract.id}")
            return True
    
    async def terminate_contract(self, contract_id: int, owner_id: int, reason: str) -> bool:
        """Расторжение договора."""
        async with get_async_session() as session:
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner_id
                )
            )
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            contract.status = "terminated"
            contract.is_active = False
            contract.terminated_at = datetime.now()
            
            # Создаем версию с причиной расторжения
            await self._create_contract_version(
                contract_id,
                contract.content,
                f"Договор расторгнут. Причина: {reason}",
                owner_id
            )
            
            await session.commit()
            
            logger.info(f"Terminated contract: {contract.id}")
            return True

    async def activate_contract_by_telegram_id(self, contract_id: int, owner_telegram_id: int) -> bool:
        """Активация договора по telegram_id владельца."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return False
            
            # Получаем договор
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner.id,
                    Contract.status == "draft"
                )
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            # Активируем договор
            contract.status = "active"
            contract.is_active = True
            contract.signed_at = func.now()
            
            await session.commit()
            
            logger.info(f"Activated contract: {contract.id}")
            return True

    async def terminate_contract_by_telegram_id(self, contract_id: int, owner_telegram_id: int, reason: str = None) -> bool:
        """Расторжение договора по telegram_id владельца."""
        async with get_async_session() as session:
            # Сначала находим владельца по telegram_id
            owner_query = select(User).where(User.telegram_id == owner_telegram_id)
            owner_result = await session.execute(owner_query)
            owner = owner_result.scalar_one_or_none()
            
            if not owner:
                return False
            
            # Получаем договор
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id == owner.id,
                    Contract.is_active == True
                )
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            # Расторгаем договор
            contract.status = "terminated"
            contract.terminated_at = datetime.utcnow()
            contract.is_active = False
            
            # Создаем версию с причиной расторжения
            await self._create_contract_version(
                contract_id,
                contract.content,
                f"Договор расторгнут. Причина: {reason}" if reason else "Договор расторгнут",
                owner.id
            )
            
            await session.commit()
            
            logger.info(f"Terminated contract: {contract.id} by owner telegram_id: {owner_telegram_id}")
            return True
    
    async def _generate_content_from_template(
        self, 
        template_content: str, 
        values: Dict[str, Any], 
        owner: User, 
        employee: User
    ) -> str:
        """Генерация контента договора из шаблона с подстановкой значений."""
        try:
            from jinja2 import Template
            
            # Создаем контекст для подстановки
            context = {
                # Базовые поля владельца
                'owner_name': owner.first_name or '',
                'owner_last_name': owner.last_name or '',
                'owner_telegram_id': owner.telegram_id,
                
                # Базовые поля сотрудника
                'employee_name': employee.first_name or '',
                'employee_last_name': employee.last_name or '',
                'employee_telegram_id': employee.telegram_id,
                
                # Текущая дата
                'current_date': datetime.now().strftime("%d.%m.%Y"),
                
                # Динамические поля из формы
                **values
            }
            
            # Создаем шаблон Jinja2
            jinja_template = Template(template_content)
            
            # Генерируем контент
            generated_content = jinja_template.render(context)
            
            return generated_content
            
        except Exception as e:
            logger.error(f"Error generating content from template: {e}")
            # Возвращаем исходный шаблон в случае ошибки
            return template_content
