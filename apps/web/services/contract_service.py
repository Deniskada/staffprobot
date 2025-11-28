"""Сервис для управления договорами."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.contract import Contract, ContractTemplate, ContractVersion
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from shared.services.role_service import RoleService
from shared.services.manager_permission_service import ManagerPermissionService
from shared.services.shift_history_service import ShiftHistoryService
from shared.services.shift_status_sync_service import ShiftStatusSyncService
from core.logging.logger import logger
from core.cache.redis_cache import cached
from core.cache.cache_service import CacheService


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
            
            # Если пришла явная схема полей, используем её; иначе генерируем из контента
            explicit_schema: Optional[List[Dict[str, Any]]] = template_data.get("fields_schema")
            fields_schema = explicit_schema if explicit_schema else self._extract_fields_schema_from_content(template_data["content"])
            
            template = ContractTemplate(
                name=template_data["name"],
                description=template_data.get("description", ""),
                content=template_data["content"],
                version=template_data.get("version", "1.0"),
                created_by=user.id,  # Используем id из БД
                is_public=bool(template_data.get("is_public", False)),
                fields_schema=fields_schema
            )
            
            session.add(template)
            await session.commit()
            await session.refresh(template)
            
            logger.info(f"Created contract template: {template.id} - {template_data['name']}")
            return template
    
    def _extract_fields_schema_from_content(self, content: str) -> List[Dict[str, Any]]:
        """Извлекает схему полей из контента шаблона на основе найденных тегов."""
        import re
        
        # Находим все теги в формате {{ tag_name }} с сохранением порядка
        tags = re.findall(r'\{\{\s*(\w+)\s*\}\}', content)
        
        # Убираем дубликаты, но СОХРАНЯЕМ ПОРЯДОК появления в тексте
        seen = set()
        ordered_tags = []
        for tag in tags:
            if tag not in seen:
                ordered_tags.append(tag)
                seen.add(tag)
        
        # Убираем системные теги
        system_tags = ['owner_name', 'owner_last_name', 'current_date']
        user_tags = [tag for tag in ordered_tags if tag not in system_tags]
        
        # Создаем схему полей
        fields_schema = []
        
        tag_mapping = {
            'employee_name': {'label': 'ФИО сотрудника', 'type': 'text', 'required': True},
            'birth_date': {'label': 'Дата рождения', 'type': 'date', 'required': True},
            'inn': {'label': 'ИНН', 'type': 'text', 'required': False},
            'snils': {'label': 'СНИЛС', 'type': 'text', 'required': False},
            'passport_series': {'label': 'Серия паспорта', 'type': 'text', 'required': True},
            'passport_number': {'label': 'Номер паспорта', 'type': 'text', 'required': True},
            'passport_issuer': {'label': 'Кем выдан паспорт', 'type': 'text', 'required': False},
            'passport_date': {'label': 'Дата выдачи паспорта', 'type': 'date', 'required': False},
            'email': {'label': 'Email', 'type': 'email', 'required': False},
        }
        
        for tag in user_tags:
            if tag in tag_mapping:
                field_config = tag_mapping[tag].copy()
                field_config['key'] = tag
                fields_schema.append(field_config)
            else:
                # Для неизвестных тегов создаем базовое поле
                fields_schema.append({
                    'key': tag,
                    'label': tag.replace('_', ' ').title(),
                    'type': 'text',
                    'required': False
                })
        
        logger.info(f"Extracted fields schema: {fields_schema}")
        return fields_schema
    
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
            
            # Проверяем пересечение объектов в активных договорах (опционально)
            # Пока разрешаем создание нескольких договоров с одним сотрудником
            # TODO: В будущем можно добавить проверку пересечения объектов
            
            # Валидация обязательных полей
            use_contract_rate = contract_data.get("use_contract_rate", False)
            use_contract_payment_system = contract_data.get("use_contract_payment_system", False)
            hourly_rate = contract_data.get("hourly_rate")
            
            # Если включен флаг use_contract_rate, hourly_rate обязателен
            if use_contract_rate and not hourly_rate:
                raise ValueError("При использовании ставки договора необходимо указать почасовую ставку")
            
            # Если включен флаг use_contract_payment_system, payment_system_id обязателен
            if use_contract_payment_system and not contract_data.get("payment_system_id"):
                raise ValueError("При использовании системы оплаты договора необходимо указать систему оплаты")
            
            if not hourly_rate:
                # Пытаемся получить ставку из объекта
                if contract_data.get("allowed_objects"):
                    # Получаем ставку из первого объекта
                    from domain.entities.object import Object
                    object_query = select(Object).where(Object.id == contract_data["allowed_objects"][0])
                    object_result = await session.execute(object_query)
                    object_entity = object_result.scalar_one_or_none()
                    
                    if object_entity and object_entity.hourly_rate:
                        hourly_rate = float(object_entity.hourly_rate)
                        logger.info(f"Автоматически установлена ставка {hourly_rate} руб/час из объекта {object_entity.id}")
                    else:
                        raise ValueError("Часовая ставка обязательна. Укажите ставку в договоре или выберите объект с установленной ставкой.")
                else:
                    raise ValueError("Часовая ставка обязательна. Укажите ставку в договоре или выберите объект с установленной ставкой.")
            
            if hourly_rate <= 0:
                raise ValueError("Ставка должна быть больше 0")
            
            # Получаем название договора (теперь обязательное поле)
            title = contract_data.get("title")
            if not title or title.strip() == "":
                raise ValueError("Название договора обязательно")
            
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
            
            # Парсим даты если они переданы как строки
            from datetime import date
            start_date = contract_data["start_date"]
            if isinstance(start_date, str):
                start_date = date.fromisoformat(start_date)
            
            end_date = contract_data.get("end_date")
            if end_date and isinstance(end_date, str):
                end_date = date.fromisoformat(end_date)
            
            # Создаем договор
            contract = Contract(
                contract_number=contract_number,
                owner_id=owner.id,
                employee_id=employee.id,
                template_id=contract_data.get("template_id"),
                title=title,
                content=content,
                values=values if values else None,
                hourly_rate=hourly_rate,
                use_contract_rate=use_contract_rate,
                payment_system_id=contract_data.get("payment_system_id", 1),  # По умолчанию simple_hourly
                use_contract_payment_system=use_contract_payment_system,
                start_date=start_date,
                end_date=end_date,
                allowed_objects=contract_data.get("allowed_objects", []),
                is_manager=contract_data.get("is_manager", False),
                manager_permissions=contract_data.get("manager_permissions"),
                status="active"  # Устанавливаем активный статус по умолчанию
            )
            
            session.add(contract)
            await session.commit()
            await session.refresh(contract)
            
            # Автоматически назначаем роли
            role_service = RoleService(session)
            await role_service.assign_employee_role(employee.id)
            
            # Если это договор управляющего, назначаем роль управляющего
            if contract.is_manager:
                await role_service.assign_manager_role(employee.id)
                
                # Создаем права на объекты, если указаны
                if contract.manager_permissions and contract.allowed_objects:
                    permission_service = ManagerPermissionService(session)
                    for object_id in contract.allowed_objects:
                        await permission_service.create_permission(
                            contract.id, 
                            object_id, 
                            contract.manager_permissions
                        )
            
            logger.info(f"Created contract: {contract.id} - {contract_number}")
            
            # Инвалидация кэша сотрудника и владельца
            await CacheService.invalidate_user_cache(employee.id)
            await CacheService.invalidate_user_cache(owner.id)
            
            # Инвалидация API кэшей
            from core.cache.redis_cache import cache
            await cache.clear_pattern("api_employees:*")
            await cache.clear_pattern("api_objects:*")
            
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
                
                # Если это договор управляющего, обновляем права на объекты
                if contract.is_manager:
                    permission_service = ManagerPermissionService(session)
                    # Удаляем старые права
                    old_permissions = await permission_service.get_contract_permissions(contract.id)
                    for permission in old_permissions:
                        await permission_service.delete_permission(permission.id)
                    
                    # Создаем новые права
                    if contract.manager_permissions and allowed_objects:
                        for object_id in allowed_objects:
                            await permission_service.create_permission(
                                contract.id, 
                                object_id, 
                                contract.manager_permissions
                            )
            
            contract.updated_at = datetime.now()
            await session.commit()
            await session.refresh(contract)
            
            logger.info(f"Updated contract: {contract.id}")
            
            # Инвалидация кэша сотрудника и владельца
            await CacheService.invalidate_user_cache(contract.employee_id)
            await CacheService.invalidate_user_cache(contract.owner_id)
            
            return contract
    
    
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
    
    @cached(ttl=timedelta(minutes=15), key_prefix="contract_employees")
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
                    # Если указаны конкретные объекты - доступ только к ним
                    for obj_id in contract.allowed_objects:
                        if obj_id in objects:
                            obj = objects[obj_id]
                            contract_objects.append({
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address
                            })
                            employees[employee.id]['accessible_objects'].add(obj.id)
                # Если allowed_objects пустой - нет доступа к объектам (не добавляем ничего)
                
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
    
    @cached(ttl=timedelta(minutes=15), key_prefix="all_contract_employees")
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
                        # Если указаны конкретные объекты - доступ только к ним
                        for obj_id in contract.allowed_objects:
                            if obj_id in objects:
                                obj = objects[obj_id]
                                contract_objects.append({
                                    'id': obj.id,
                                    'name': obj.name,
                                    'address': obj.address
                                })
                                employees[employee.id]['accessible_objects'].add(obj.id)
                    # Если allowed_objects пустой - нет доступа к объектам (не добавляем ничего)
                
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
        try:
            logger.info(f"=== CREATING CONTRACT VERSION ===")
            logger.info(f"Parameters: contract_id={contract_id}, content_length={len(content) if content else 0}, changes_description='{changes_description}', created_by={created_by}")
            
            async with get_async_session() as session:
                logger.info(f"Step 1: Getting last version for contract {contract_id}")
                # Получаем последнюю версию
                query = select(ContractVersion).where(ContractVersion.contract_id == contract_id)
                query = query.order_by(ContractVersion.created_at.desc())
                result = await session.execute(query)
                last_version = result.scalar_one_or_none()
                logger.info(f"Step 1 SUCCESS: Last version found: {last_version.version_number if last_version else 'None'}")
                
                logger.info(f"Step 2: Generating version number")
                # Генерируем номер версии
                if last_version:
                    version_parts = last_version.version_number.split('.')
                    version_parts[-1] = str(int(version_parts[-1]) + 1)
                    version_number = '.'.join(version_parts)
                else:
                    version_number = "1.0"
                logger.info(f"Step 2 SUCCESS: Generated version number: {version_number}")
                
                logger.info(f"Step 3: Creating ContractVersion object")
                version = ContractVersion(
                    contract_id=contract_id,
                    version_number=version_number,
                    content=content or "",
                    changes_description=changes_description,
                    created_by=created_by
                )
                logger.info(f"Step 3 SUCCESS: ContractVersion object created")
            
                logger.info(f"Step 4: Adding version to session and committing")
                session.add(version)
                await session.commit()
                await session.refresh(version)
                logger.info(f"Step 4 SUCCESS: Version committed to database")
                
                logger.info(f"=== CONTRACT VERSION CREATED SUCCESSFULLY ===")
                logger.info(f"Version ID: {version.id}, Version Number: {version.version_number}")
                return version
                
        except Exception as e:
            logger.error(f"=== CONTRACT VERSION CREATION FAILED ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            raise e
    
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
    
    @cached(ttl=timedelta(minutes=15), key_prefix="owner_objects")
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
            template.is_public = bool(template_data.get("is_public", False))
            # Если пришла явная схема полей, используем её; иначе генерируем из нового контента
            explicit_schema: Optional[List[Dict[str, Any]]] = template_data.get("fields_schema")
            template.fields_schema = explicit_schema if explicit_schema else self._extract_fields_schema_from_content(template_data["content"])
            
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
                "created_at": employee.created_at,
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
    
    async def get_employee_by_id(self, employee_id: int, owner_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о сотруднике по внутреннему user_id.
        
        Args:
            employee_id: внутренний user_id сотрудника (НЕ telegram_id)
            owner_id: внутренний user_id владельца (НЕ telegram_id)
        
        Returns:
            Dict с информацией о сотруднике и его договорах или None
        """
        async with get_async_session() as session:
            # Получаем сотрудника с договорами (включая неактивные) по внутренним IDs
            query = select(Contract).where(
                and_(
                    Contract.employee_id == employee_id,
                    Contract.owner_id == owner_id
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
            
            # Собираем все уникальные объекты, к которым есть доступ
            accessible_objects = []
            accessible_object_ids = set()
            
            for contract in contracts:
                # Только из активных договоров
                if contract.is_active and contract.allowed_objects:
                    for obj_id in contract.allowed_objects:
                        if obj_id in objects_info and obj_id not in accessible_object_ids:
                            obj = objects_info[obj_id]
                            accessible_objects.append({
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address
                            })
                            accessible_object_ids.add(obj_id)
            
            return {
                'id': employee.id,
                'telegram_id': employee.telegram_id,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'username': employee.username,
                'phone': employee.phone,
                'email': employee.email,
                'birth_date': employee.birth_date,
                'work_experience': employee.work_experience,
                'education': employee.education,
                'skills': employee.skills,
                'about': employee.about,
                'preferred_schedule': employee.preferred_schedule,
                'min_salary': employee.min_salary,
                'availability_notes': employee.availability_notes,
                'is_active': employee.is_active,
                'created_at': employee.created_at,
                'accessible_objects': accessible_objects,
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
                    'is_manager': contract.is_manager,
                    'manager_permissions': contract.manager_permissions,
                    'allowed_objects_info': [objects_info.get(obj_id) for obj_id in (contract.allowed_objects or []) if objects_info.get(obj_id)]
                } for contract in contracts]
            }
    
    async def get_employee_by_id(self, employee_id: int, manager_telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о сотруднике по внутреннему ID (для управляющих)."""
        async with get_async_session() as session:
            # Сначала находим управляющего по telegram_id
            manager_query = select(User).where(User.telegram_id == manager_telegram_id)
            manager_result = await session.execute(manager_query)
            manager = manager_result.scalar_one_or_none()
            
            if not manager:
                return None
            
            # Получаем сотрудника по внутреннему ID
            employee_query = select(User).where(User.id == employee_id)
            employee_result = await session.execute(employee_query)
            employee = employee_result.scalar_one_or_none()
            
            if not employee:
                return None
            
            # Для управляющего получаем договоры, где он имеет права доступа
            # Это могут быть договоры, где управляющий является владельцем ИЛИ имеет права управляющего
            from shared.services.manager_permission_service import ManagerPermissionService
            permission_service = ManagerPermissionService(session)
            accessible_objects = await permission_service.get_user_accessible_objects(manager.id)
            
            if not accessible_objects:
                return None
            
            # Получаем ID владельцев объектов, к которым есть доступ
            owner_ids = [obj.owner_id for obj in accessible_objects]
            
            # Получаем договоры с этим сотрудником от владельцев, к объектам которых есть доступ
            query = select(Contract).where(
                and_(
                    Contract.employee_id == employee_id,
                    Contract.owner_id.in_(owner_ids),
                    Contract.is_active == True  # Только активные договоры
                )
            ).options(
                selectinload(Contract.employee)
            )
            
            result = await session.execute(query)
            contracts = result.scalars().all()
            
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
            
            # Собираем все уникальные объекты, к которым есть доступ
            accessible_objects = []
            accessible_object_ids = set()
            
            for contract in contracts:
                # Только из активных договоров
                if contract.is_active and contract.allowed_objects:
                    for obj_id in contract.allowed_objects:
                        if obj_id in objects_info and obj_id not in accessible_object_ids:
                            obj = objects_info[obj_id]
                            accessible_objects.append({
                                'id': obj.id,
                                'name': obj.name,
                                'address': obj.address
                            })
                            accessible_object_ids.add(obj_id)
            
            return {
                'id': employee.id,
                'telegram_id': employee.telegram_id,
                'first_name': employee.first_name,
                'last_name': employee.last_name,
                'username': employee.username,
                'phone': employee.phone,
                'email': employee.email,
                'birth_date': employee.birth_date,
                'work_experience': employee.work_experience,
                'education': employee.education,
                'skills': employee.skills,
                'about': employee.about,
                'preferred_schedule': employee.preferred_schedule,
                'min_salary': employee.min_salary,
                'availability_notes': employee.availability_notes,
                'is_active': employee.is_active,
                'created_at': employee.created_at,
                'accessible_objects': accessible_objects,
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
                    'is_manager': contract.is_manager,
                    'manager_permissions': contract.manager_permissions,
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
                    Contract.owner_id == owner.id
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
                "use_contract_rate": contract.use_contract_rate,
                "payment_system_id": contract.payment_system_id,
                "use_contract_payment_system": contract.use_contract_payment_system,
                "start_date": contract.start_date,
                "end_date": contract.end_date,
                "status": contract.status,
                "is_manager": contract.is_manager,
                "manager_permissions": contract.manager_permissions,
                "allowed_objects": contract.allowed_objects or [],
                "allowed_objects_info": allowed_objects_info,
                "created_at": contract.created_at,
                "updated_at": contract.updated_at,
                "signed_at": contract.signed_at,
                "terminated_at": contract.terminated_at,
                "termination_date": contract.termination_date,
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
    
    async def get_contract_by_id_for_manager(self, contract_id: int, manager_telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получение договора по ID для управляющего с проверкой прав доступа."""
        async with get_async_session() as session:
            # Сначала находим управляющего по telegram_id
            manager_query = select(User).where(User.telegram_id == manager_telegram_id)
            manager_result = await session.execute(manager_query)
            manager = manager_result.scalar_one_or_none()
            
            if not manager:
                return None
            
            # Проверяем права доступа управляющего
            from shared.services.manager_permission_service import ManagerPermissionService
            permission_service = ManagerPermissionService(session)
            accessible_objects = await permission_service.get_user_accessible_objects(manager.id)
            
            if not accessible_objects:
                return None
            
            # Получаем ID владельцев объектов, к которым есть доступ
            owner_ids = [obj.owner_id for obj in accessible_objects]
            
            # Получаем договор, если владелец входит в список доступных
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id.in_(owner_ids)
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
                    "phone": contract.employee.phone,
                    "email": contract.employee.email
                }
            }
    
    async def update_contract_for_manager(self, contract_id: int, manager_telegram_id: int, update_data: Dict[str, Any]) -> bool:
        """Обновление договора управляющим с проверкой прав доступа."""
        async with get_async_session() as session:
            # Сначала находим управляющего по telegram_id
            manager_query = select(User).where(User.telegram_id == manager_telegram_id)
            manager_result = await session.execute(manager_query)
            manager = manager_result.scalar_one_or_none()
            
            if not manager:
                return False
            
            # Проверяем права доступа управляющего
            from shared.services.manager_permission_service import ManagerPermissionService
            permission_service = ManagerPermissionService(session)
            accessible_objects = await permission_service.get_user_accessible_objects(manager.id)
            
            if not accessible_objects:
                return False
            
            # Получаем ID владельцев объектов, к которым есть доступ
            owner_ids = [obj.owner_id for obj in accessible_objects]
            
            # Получаем договор, если владелец входит в список доступных
            query = select(Contract).where(
                and_(
                    Contract.id == contract_id,
                    Contract.owner_id.in_(owner_ids)
                )
            )
            
            result = await session.execute(query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                return False
            
            # Обновляем поля договора
            if "title" in update_data:
                contract.title = update_data["title"]
            if "hourly_rate" in update_data:
                contract.hourly_rate = update_data["hourly_rate"]
            if "start_date" in update_data:
                contract.start_date = update_data["start_date"]
            if "end_date" in update_data:
                contract.end_date = update_data["end_date"]
            if "status" in update_data:
                contract.status = update_data["status"]
            if "content" in update_data:
                contract.content = update_data["content"]
            if "allowed_objects" in update_data:
                contract.allowed_objects = update_data["allowed_objects"]
            if "is_manager" in update_data:
                contract.is_manager = update_data["is_manager"]
            if "manager_permissions" in update_data:
                contract.manager_permissions = update_data["manager_permissions"]
            
            session.add(contract)
            await session.commit()
            return True
    
    async def get_contract_by_id_and_owner_telegram_id(self, contract_id: int, owner_telegram_id: int) -> Optional[Contract]:
        """Получение ORM объекта договора по ID с проверкой прав владельца по telegram_id."""
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
            
            return contract
    
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
            
            # Обновляем поля управляющего, если они переданы
            if "is_manager" in contract_data:
                contract.is_manager = contract_data["is_manager"]
            if "manager_permissions" in contract_data:
                contract.manager_permissions = contract_data["manager_permissions"]
            
            # Если это договор управляющего, обновляем права на объекты
            if contract.is_manager:
                permission_service = ManagerPermissionService(session)
                # Удаляем старые права
                old_permissions = await permission_service.get_contract_permissions(contract.id)
                for permission in old_permissions:
                    await permission_service.delete_permission(permission.id)
                
                # Создаем новые права
                if contract.manager_permissions and contract.allowed_objects:
                    for object_id in contract.allowed_objects:
                        await permission_service.create_permission(
                            contract.id, 
                            object_id, 
                            contract.manager_permissions
                        )
            
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
            
            # Сохраняем старый статус для проверки изменений
            old_status = contract.status
            old_is_active = contract.is_active
            old_is_manager = contract.is_manager
            
            # Валидация use_contract_rate + hourly_rate
            if "use_contract_rate" in contract_data:
                use_contract_rate = contract_data["use_contract_rate"]
                hourly_rate_value = contract_data.get("hourly_rate", contract.hourly_rate)
                
                if use_contract_rate and not hourly_rate_value:
                    raise ValueError("При использовании ставки договора необходимо указать почасовую ставку")
            
            # Валидация use_contract_payment_system + payment_system_id
            if "use_contract_payment_system" in contract_data:
                use_contract_payment_system = contract_data["use_contract_payment_system"]
                payment_system_id_value = contract_data.get("payment_system_id", contract.payment_system_id)
                
                if use_contract_payment_system and not payment_system_id_value:
                    raise ValueError("При использовании системы оплаты договора необходимо указать систему оплаты")
            
            # Обновляем поля
            if "title" in contract_data:
                contract.title = contract_data["title"]
            if "content" in contract_data:
                contract.content = contract_data["content"]
            if "hourly_rate" in contract_data:
                contract.hourly_rate = contract_data["hourly_rate"]
            if "use_contract_rate" in contract_data:
                contract.use_contract_rate = contract_data["use_contract_rate"]
            if "payment_system_id" in contract_data:
                contract.payment_system_id = contract_data["payment_system_id"]
            if "use_contract_payment_system" in contract_data:
                contract.use_contract_payment_system = contract_data["use_contract_payment_system"]
            if "start_date" in contract_data:
                contract.start_date = contract_data["start_date"]
            if "end_date" in contract_data:
                contract.end_date = contract_data["end_date"]
            if "allowed_objects" in contract_data:
                logger.info(f"Updating contract {contract.id} allowed_objects from {contract.allowed_objects} to {contract_data['allowed_objects']}")
                contract.allowed_objects = contract_data["allowed_objects"]
                
                # Обновляем права на объекты для всех типов договоров
                if contract.is_manager:
                    # Для управляющих используем ManagerPermissionService
                    permission_service = ManagerPermissionService(session)
                    # Удаляем старые права
                    old_permissions = await permission_service.get_contract_permissions(contract.id)
                    for permission in old_permissions:
                        await permission_service.delete_permission(permission.id)
                    
                    # Создаем новые права
                    if contract.manager_permissions and contract.allowed_objects:
                        for object_id in contract.allowed_objects:
                            await permission_service.create_permission(
                                contract.id, 
                                object_id, 
                                contract.manager_permissions
                            )
                else:
                    # Для обычных сотрудников права на объекты хранятся в allowed_objects
                    # Дополнительных действий не требуется, так как права проверяются по allowed_objects
                    pass
            if "status" in contract_data:
                contract.status = contract_data["status"]
            if "is_active" in contract_data:
                contract.is_active = contract_data["is_active"]
            if "is_manager" in contract_data:
                contract.is_manager = contract_data["is_manager"]
                
                # Если изменился статус управляющего, обновляем роли и права
                if old_is_manager != contract.is_manager:
                    role_service = RoleService(session)
                    
                    if contract.is_manager:
                        # Стал управляющим - добавляем роль
                        await role_service.assign_manager_role(contract.employee_id)
                        logger.info(f"Assigned manager role to user {contract.employee_id} (contract {contract.id})")
                    else:
                        # Перестал быть управляющим - удаляем права на объекты
                        permission_service = ManagerPermissionService(session)
                        old_permissions = await permission_service.get_contract_permissions(contract.id)
                        for permission in old_permissions:
                            await permission_service.delete_permission(permission.id)
                        logger.info(f"Deleted {len(old_permissions)} manager permissions for contract {contract.id}")
                        
                        # Проверяем, есть ли у пользователя другие активные договоры с is_manager=True
                        other_manager_contracts_query = select(Contract).where(
                            and_(
                                Contract.employee_id == contract.employee_id,
                                Contract.id != contract.id,
                                Contract.is_manager == True,
                                Contract.is_active == True,
                                Contract.status == 'active'
                            )
                        )
                        other_manager_contracts_result = await session.execute(other_manager_contracts_query)
                        other_manager_contracts = other_manager_contracts_result.scalars().all()
                        
                        if not other_manager_contracts:
                            # Нет других активных договоров с is_manager=True - удаляем роль
                            await role_service.remove_manager_role(contract.employee_id)
                            logger.info(f"Removed manager role from user {contract.employee_id} (no other manager contracts)")
                        else:
                            logger.info(f"User {contract.employee_id} still has {len(other_manager_contracts)} other manager contracts")
            
            if "manager_permissions" in contract_data:
                contract.manager_permissions = contract_data["manager_permissions"]
                
                # Если изменились права управляющего, обновляем права на объекты
                if contract.is_manager and contract.allowed_objects:
                    permission_service = ManagerPermissionService(session)
                    # Удаляем старые права
                    old_permissions = await permission_service.get_contract_permissions(contract.id)
                    for permission in old_permissions:
                        await permission_service.delete_permission(permission.id)
                    
                    # Создаем новые права
                    if contract.manager_permissions:
                        for object_id in contract.allowed_objects:
                            await permission_service.create_permission(
                                contract.id, 
                                object_id, 
                                contract.manager_permissions
                            )
            
            contract.updated_at = datetime.now()
            await session.commit()
            # Обновляем роли сотрудника при изменении статуса договора
            if (old_status != contract.status or old_is_active != contract.is_active):
                if contract.status == "active" and contract.is_active:
                    # Договор стал активным - добавляем роль employee
                    await self._update_employee_role(session, contract.employee_id)
                else:
                    # Договор стал неактивным - проверяем, есть ли другие активные договоры
                    await self._check_and_update_employee_role(session, contract.employee_id)
            
            logger.info(f"Updated contract: {contract.id}")
            return True
    
    async def terminate_contract(
        self,
        contract_id: int,
        owner_id: int,
        reason: str,
        termination_date: Optional[date] = None,
        settlement_policy: str = "schedule",
        terminated_by_type: str = "owner"
    ) -> bool:
        """
        Расторжение договора.
        
        Args:
            contract_id: ID договора
            owner_id: ID владельца
            reason: Причина расторжения (может содержать [category] prefix)
            termination_date: Дата увольнения (optional)
            settlement_policy: Политика финального расчёта ('schedule' | 'termination_date')
            terminated_by_type: Тип расторгающего ('owner' | 'manager' | 'system')
        """
        try:
            logger.info(f"=== STARTING CONTRACT TERMINATION ===")
            logger.info(f"Parameters: contract_id={contract_id}, owner_id={owner_id}, reason='{reason}', termination_date={termination_date}, settlement_policy={settlement_policy}")
            
            async with get_async_session() as session:
                logger.info(f"Step 1: Searching for contract {contract_id} for owner {owner_id}")
                query = select(Contract).where(
                    and_(
                        Contract.id == contract_id,
                        Contract.owner_id == owner_id
                    )
                )
                result = await session.execute(query)
                contract = result.scalar_one_or_none()
                
                if not contract:
                    logger.error(f"Step 1 FAILED: Contract {contract_id} not found for owner {owner_id}")
                    return False
                
                logger.info(f"Step 1 SUCCESS: Found contract: id={contract.id}, status={contract.status}, is_active={contract.is_active}, employee_id={contract.employee_id}")
                
                logger.info(f"Step 2: Updating contract status to terminated")
                terminated_at_now = datetime.now()
                contract.status = "terminated"
                contract.is_active = False
                contract.terminated_at = terminated_at_now
                contract.termination_date = termination_date
                contract.settlement_policy = settlement_policy
                logger.info(f"Step 2 SUCCESS: Contract status updated with termination_date={termination_date}, settlement_policy={settlement_policy}")
                
                # Step 2.5: Создать запись о расторжении для аналитики
                logger.info(f"Step 2.5: Creating termination record for analytics")
                try:
                    from domain.entities.contract_termination import ContractTermination
                    
                    # Парсим категорию из reason если есть формат [category]
                    reason_category = "other"
                    reason_text = reason
                    if reason.startswith("[") and "]" in reason:
                        end_bracket = reason.index("]")
                        reason_category = reason[1:end_bracket]
                        reason_text = reason[end_bracket + 1:].strip()
                    
                    termination_record = ContractTermination(
                        contract_id=contract_id,
                        employee_id=contract.employee_id,
                        owner_id=contract.owner_id,
                        terminated_by_id=owner_id,
                        terminated_by_type=terminated_by_type,
                        reason_category=reason_category,
                        reason=reason_text,
                        termination_date=termination_date,
                        settlement_policy=settlement_policy,
                        terminated_at=terminated_at_now
                    )
                    session.add(termination_record)
                    logger.info(f"Step 2.5 SUCCESS: Termination record created")
                except Exception as term_error:
                    logger.error(f"Step 2.5 WARNING: Error creating termination record: {term_error}")
                    # Не прерываем расторжение из-за ошибки создания записи
                
                logger.info(f"Step 3: Creating contract version with reason: '{reason}'")
                try:
                    await self._create_contract_version(
                        contract_id,
                        contract.content,
                        f"Договор расторгнут. Причина: {reason}",
                        owner_id
                    )
                    logger.info(f"Step 3 SUCCESS: Contract version created")
                except Exception as version_error:
                    logger.error(f"Step 3 FAILED: Error creating contract version: {version_error}")
                    raise version_error
                
                logger.info(f"Step 4: Cancelling planned shifts on lost objects")
                try:
                    cancelled_shifts_count = await self._cancel_shifts_on_contract_termination(
                        session, contract, reason
                    )
                    logger.info(f"Step 4 SUCCESS: Cancelled {cancelled_shifts_count} shifts")
                except Exception as cancel_error:
                    logger.error(f"Step 4 FAILED: Error cancelling shifts: {cancel_error}")
                    # Не прерываем, договор уже расторгнут
                
                # Step 4.5: Отменить все плановые смены после termination_date
                if termination_date:
                    logger.info(f"Step 4.5: Cancelling all planned shifts after termination_date={termination_date}")
                    try:
                        cancelled_after_date_count = await self._cancel_shifts_after_termination_date(
                            session, contract.employee_id, termination_date, reason, contract.id, owner_id
                        )
                        logger.info(f"Step 4.5 SUCCESS: Cancelled {cancelled_after_date_count} shifts after termination date")
                    except Exception as cancel_date_error:
                        logger.error(f"Step 4.5 FAILED: Error cancelling shifts after termination date: {cancel_date_error}")
                        # Не прерываем, договор уже расторгнут
                
                logger.info(f"Step 5: Committing all changes to database")
                try:
                    await session.commit()
                    logger.info(f"Step 5 SUCCESS: All changes committed")
                except Exception as commit_error:
                    logger.error(f"Step 5 FAILED: Error committing changes: {commit_error}")
                    raise commit_error
                
                logger.info(f"Step 6: Checking and updating employee role for user {contract.employee_id}")
                try:
                    await self._check_and_update_employee_role(session, contract.employee_id)
                    logger.info(f"Step 6 SUCCESS: Employee role updated")
                except Exception as role_error:
                    logger.error(f"Step 6 FAILED: Error updating employee role: {role_error}")
                    # Не прерываем выполнение, так как договор уже расторгнут
                
                logger.info(f"=== CONTRACT TERMINATION COMPLETED SUCCESSFULLY ===")
                logger.info(f"Contract {contract.id} terminated successfully")
                return True
        
                
        except Exception as e:
            logger.error(f"=== CONTRACT TERMINATION FAILED ===")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(f"Full traceback:", exc_info=True)
            return False

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
            
            # Обновляем роли сотрудника при активации договора
            await self._update_employee_role(session, contract.employee_id)
            
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
            
            # Автоотмена запланированных смен на недоступные объекты
            cancelled_shifts_count = await self._cancel_shifts_on_contract_termination(
                session, contract, reason
            )
            
            await session.commit()
            
            logger.info(f"Terminated contract: {contract.id}, cancelled {cancelled_shifts_count} shifts")
            
            # Проверяем, есть ли у сотрудника другие активные договоры
            await self._check_and_update_employee_role(session, contract.employee_id)
            
            logger.info(f"Terminated contract: {contract.id} by owner telegram_id: {owner_telegram_id}")
            return True
    
    async def _cancel_shifts_on_contract_termination(
        self, 
        session, 
        terminated_contract: Contract, 
        reason: str
    ) -> int:
        """
        Отменить запланированные смены на объекты, к которым сотрудник потерял доступ.
        
        Args:
            session: Сессия БД
            terminated_contract: Расторгаемый договор
            reason: Причина расторжения
            
        Returns:
            int: Количество отмененных смен
        """
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift_cancellation import ShiftCancellation
        from datetime import datetime, timezone as dt_timezone
        
        try:
            employee_id = terminated_contract.employee_id
            terminated_allowed_objects = set(terminated_contract.allowed_objects or [])
            
            # Получаем все остальные активные договоры сотрудника
            active_contracts_query = select(Contract).where(
                and_(
                    Contract.employee_id == employee_id,
                    Contract.id != terminated_contract.id,
                    Contract.is_active == True,
                    Contract.status == "active"
                )
            )
            active_contracts_result = await session.execute(active_contracts_query)
            active_contracts = active_contracts_result.scalars().all()
            
            # Собираем объекты из остальных договоров
            remaining_objects = set()
            for contract in active_contracts:
                if contract.allowed_objects:
                    remaining_objects.update(contract.allowed_objects)
            
            # Вычисляем объекты, к которым утрачен доступ
            lost_objects = terminated_allowed_objects - remaining_objects
            
            if not lost_objects:
                logger.info(f"No lost objects for employee {employee_id}, all objects available in other contracts")
                return 0
            
            logger.info(f"Employee {employee_id} lost access to objects: {lost_objects}")
            
            # Находим запланированные смены на эти объекты
            now_utc = datetime.now(dt_timezone.utc)
            shifts_query = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.user_id == employee_id,
                    ShiftSchedule.status == 'planned',
                    ShiftSchedule.object_id.in_(list(lost_objects)),
                    ShiftSchedule.planned_start > now_utc
                )
            )
            shifts_result = await session.execute(shifts_query)
            shifts_to_cancel = shifts_result.scalars().all()
            
            history_service = ShiftHistoryService(session)
            sync_service = ShiftStatusSyncService(session)
            cancelled_count = 0
            for shift in shifts_to_cancel:
                # Отменяем смену
                previous_status = shift.status
                shift.status = 'cancelled'
                payload = {
                    "reason_code": "contract_termination",
                    "notes": reason,
                    "contract_id": terminated_contract.id,
                    "object_id": shift.object_id,
                    "origin": "contract_service",
                }
                await history_service.log_event(
                    operation="schedule_cancel",
                    source="system",
                    actor_id=terminated_contract.owner_id,
                    actor_role="system",
                    schedule_id=shift.id,
                    shift_id=None,
                    old_status=previous_status,
                    new_status='cancelled',
                    payload=payload,
                )
                await sync_service.cancel_linked_shifts(
                    shift,
                    actor_id=terminated_contract.owner_id,
                    actor_role="system",
                    source="system",
                    payload=payload,
                )
                
                # Создаем запись о отмене
                cancellation = ShiftCancellation(
                    shift_schedule_id=shift.id,
                    employee_id=employee_id,
                    object_id=shift.object_id,
                    cancelled_by_id=terminated_contract.owner_id,
                    cancelled_by_type='system',
                    cancellation_reason='contract_termination',
                    reason_notes=f"Расторгнут договор №{terminated_contract.contract_number}. Причина: {reason}",
                    contract_id=terminated_contract.id,
                    hours_before_shift=None,  # Не применяем штрафы при автоотмене
                    fine_amount=None,
                    fine_reason=None,
                    fine_applied=False
                )
                session.add(cancellation)
                cancelled_count += 1
            
            logger.info(f"Cancelled {cancelled_count} shifts for employee {employee_id} on lost objects")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling shifts on contract termination: {e}")
            # Не прерываем расторжение договора из-за ошибки отмены смен
            return 0
    
    async def _cancel_shifts_after_termination_date(
        self,
        session,
        employee_id: int,
        termination_date: date,
        reason: str,
        contract_id: int,
        cancelled_by_id: int
    ) -> int:
        """
        Отменить все плановые смены после даты увольнения.
        
        Args:
            session: Сессия БД
            employee_id: ID сотрудника
            termination_date: Дата увольнения
            reason: Причина расторжения
            contract_id: ID расторгаемого договора
            cancelled_by_id: ID пользователя, расторгающего договор
            
        Returns:
            int: Количество отмененных смен
        """
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift_cancellation import ShiftCancellation
        from datetime import datetime, timezone as dt_timezone
        
        try:
            # Находим все плановые смены после termination_date
            # Конвертируем termination_date в datetime для сравнения с planned_start
            termination_datetime = datetime.combine(termination_date, datetime.min.time())
            termination_datetime_utc = termination_datetime.replace(tzinfo=dt_timezone.utc)
            
            shifts_query = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.user_id == employee_id,
                    ShiftSchedule.status == 'planned',
                    func.date(ShiftSchedule.planned_start) > termination_date
                )
            )
            shifts_result = await session.execute(shifts_query)
            shifts_to_cancel = shifts_result.scalars().all()
            
            history_service = ShiftHistoryService(session)
            sync_service = ShiftStatusSyncService(session)
            cancelled_count = 0
            for shift in shifts_to_cancel:
                # Отменяем смену
                previous_status = shift.status
                shift.status = 'cancelled'
                payload = {
                    "reason_code": "contract_termination",
                    "notes": reason,
                    "contract_id": contract_id,
                    "object_id": shift.object_id,
                    "origin": "contract_service",
                }
                await history_service.log_event(
                    operation="schedule_cancel",
                    source="system",
                    actor_id=cancelled_by_id,
                    actor_role="system",
                    schedule_id=shift.id,
                    shift_id=None,
                    old_status=previous_status,
                    new_status='cancelled',
                    payload=payload,
                )
                await sync_service.cancel_linked_shifts(
                    shift,
                    actor_id=cancelled_by_id,
                    actor_role="system",
                    source="system",
                    payload=payload,
                )
                
                # Создаем запись о отмене
                cancellation = ShiftCancellation(
                    shift_schedule_id=shift.id,
                    employee_id=employee_id,
                    object_id=shift.object_id,
                    cancelled_by_id=cancelled_by_id,
                    cancelled_by_type='system',
                    cancellation_reason='contract_termination',
                    reason_notes=f"Расторгнут договор (дата увольнения: {termination_date}). Причина: {reason}",
                    contract_id=contract_id,
                    hours_before_shift=None,  # Не применяем штрафы при автоотмене
                    fine_amount=None,
                    fine_reason=None,
                    fine_applied=False
                )
                session.add(cancellation)
                cancelled_count += 1
            
            logger.info(f"Cancelled {cancelled_count} planned shifts for employee {employee_id} after termination_date={termination_date}")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling shifts after termination date: {e}")
            # Не прерываем расторжение договора из-за ошибки отмены смен
            return 0
    
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
    
    async def _update_employee_role(self, session, employee_id: int) -> None:
        """Обновление роли сотрудника на 'employee'."""
        try:
            # Получаем пользователя
            user_query = select(User).where(User.id == employee_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User with id {employee_id} not found")
                return
            
            # Обновляем роль
            user.role = "employee"
            
            # Обновляем массив ролей, если он существует
            if hasattr(user, 'roles') and user.roles:
                if "employee" not in user.roles:
                    user.roles.append("employee")
            else:
                # Если поле roles не существует, создаем его
                user.roles = ["applicant", "employee"]
            
            await session.commit()
            logger.info(f"Updated user {employee_id} role to employee")
            
        except Exception as e:
            logger.error(f"Error updating employee role for user {employee_id}: {e}")
            # Не поднимаем исключение, чтобы не сломать создание договора
    
    async def _check_and_update_employee_role(self, session, employee_id: int) -> None:
        """Проверка и обновление роли сотрудника при расторжении договора."""
        try:
            # Проверяем, есть ли у сотрудника другие активные договоры
            active_contracts_query = select(Contract).where(
                and_(
                    Contract.employee_id == employee_id,
                    Contract.is_active == True,
                    Contract.status == "active"
                )
            )
            active_contracts_result = await session.execute(active_contracts_query)
            active_contracts = active_contracts_result.scalars().all()
            
            # Получаем пользователя
            user_query = select(User).where(User.id == employee_id)
            user_result = await session.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User with id {employee_id} not found")
                return
            
            # Если нет активных договоров, убираем роль employee и делаем пользователя неактивным
            if not active_contracts:
                if user.role == "employee":
                    user.role = "applicant"
                
                # Обновляем массив ролей
                if hasattr(user, 'roles') and user.roles and "employee" in user.roles:
                    user.roles.remove("employee")
                    if not user.roles:  # Если массив стал пустым
                        user.roles = ["applicant"]
                
                # Делаем пользователя неактивным
                user.is_active = False
                
                await session.commit()
                logger.info(f"Removed employee role from user {employee_id} and marked as inactive - no active contracts")
            else:
                logger.info(f"User {employee_id} still has {len(active_contracts)} active contracts")
            
        except Exception as e:
            logger.error(f"Error checking employee role for user {employee_id}: {e}")
            # Не поднимаем исключение, чтобы не сломать расторжение договора
