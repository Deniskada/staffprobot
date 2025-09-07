"""Сервис для управления договорами."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_
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
        name: str,
        content: str,
        description: Optional[str] = None,
        version: str = "1.0",
        created_by: int = None
    ) -> ContractTemplate:
        """Создание шаблона договора."""
        async with get_async_session() as session:
            template = ContractTemplate(
                name=name,
                description=description,
                content=content,
                version=version,
                created_by=created_by
            )
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            logger.info(f"Created contract template: {template.id} - {name}")
            return template
    
    async def get_contract_templates(self, active_only: bool = True) -> List[ContractTemplate]:
        """Получение списка шаблонов договоров."""
        async with get_async_session() as session:
            query = select(ContractTemplate)
            if active_only:
                query = query.where(ContractTemplate.is_active == True)
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
        owner_id: int,
        contract_data: Dict[str, Any]
    ) -> Optional[Contract]:
        """Создание договора с сотрудником."""
        async with get_async_session() as session:
            # Находим сотрудника по ID
            employee_query = select(User).where(User.id == contract_data["employee_id"])
            employee_result = await session.execute(employee_query)
            employee = employee_result.scalar_one_or_none()
            
            if not employee:
                raise ValueError(f"Сотрудник с ID {contract_data['employee_id']} не найден")
            
            # Генерируем номер договора
            contract_number = await self._generate_contract_number(owner_id)
            
            # Создаем договор
            contract = Contract(
                contract_number=contract_number,
                owner_id=owner_id,
                employee_id=employee.id,
                template_id=contract_data.get("template_id"),
                title=contract_data["title"],
                content=contract_data["content"],
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
    
    async def get_owner_objects(self, owner_id: int) -> List[Object]:
        """Получение объектов владельца."""
        async with get_async_session() as session:
            query = select(Object).where(
                and_(
                    Object.owner_id == owner_id,
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
