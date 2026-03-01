"""Сервис для работы с историей изменений договоров."""

from datetime import datetime, date
from typing import List, Dict, Any, Optional
from decimal import Decimal
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.contract_history import ContractHistory, ContractChangeType
from domain.entities.contract import Contract
from domain.entities.user import User
from core.logging.logger import logger


async def log_contract_event(
    session: AsyncSession,
    contract_id: int,
    change_type: str | ContractChangeType,
    changed_by: int | None = None,
    details: dict | None = None,
    metadata: dict | None = None,
) -> ContractHistory:
    """
    Упрощённый хелпер для логирования одного события договора.
    Записывает одну строку с field_name='event' и деталями в new_value.
    """
    change_type_val = change_type.value if isinstance(change_type, ContractChangeType) else change_type
    entry = ContractHistory(
        contract_id=contract_id,
        changed_by=changed_by,
        change_type=change_type_val,
        field_name="event",
        new_value=details,
        change_metadata=metadata,
    )
    session.add(entry)
    await session.flush()
    logger.info(
        "Contract event logged",
        contract_id=contract_id,
        change_type=change_type_val,
        changed_by=changed_by,
    )
    return entry


class ContractHistoryService:
    """Сервис для протоколирования и получения истории изменений договоров."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_contract_change(
        self,
        contract_id: int,
        changed_by: int,
        change_type: ContractChangeType,
        field_name: str,
        old_value: Any = None,
        new_value: Any = None,
        change_reason: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ContractHistory:
        """
        Записать изменение одного поля договора.
        
        Args:
            contract_id: ID договора
            changed_by: ID пользователя, который внес изменение
            change_type: Тип изменения (created, updated, status_changed)
            field_name: Название измененного поля
            old_value: Старое значение (будет сериализовано в JSONB)
            new_value: Новое значение (будет сериализовано в JSONB)
            change_reason: Причина изменения (опционально)
            effective_from: Дата начала действия (для будущих изменений)
            metadata: Дополнительные данные (IP, user agent, etc.)
            
        Returns:
            Созданная запись истории
        """
        # Сериализуем значения в JSON-совместимый формат
        old_value_json = self._serialize_value(old_value)
        new_value_json = self._serialize_value(new_value)
        
        # Преобразуем enum в строку
        change_type_value = change_type.value if isinstance(change_type, ContractChangeType) else change_type
        
        history_entry = ContractHistory(
            contract_id=contract_id,
            changed_by=changed_by,
            change_type=change_type_value,
            field_name=field_name,
            old_value=old_value_json,
            new_value=new_value_json,
            change_reason=change_reason,
            effective_from=effective_from,
            change_metadata=metadata
        )
        
        self.session.add(history_entry)
        await self.session.flush()
        
        logger.info(
            "Contract history entry created",
            contract_id=contract_id,
            field_name=field_name,
            change_type=change_type.value,
            changed_by=changed_by
        )
        
        return history_entry
    
    async def log_contract_changes(
        self,
        contract_id: int,
        changed_by: int,
        change_type: ContractChangeType,
        changes: Dict[str, Dict[str, Any]],
        change_reason: Optional[str] = None,
        effective_from: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ContractHistory]:
        """
        Записать множественные изменения договора (batch).
        
        Args:
            contract_id: ID договора
            changed_by: ID пользователя, который внес изменения
            change_type: Тип изменения
            changes: Словарь изменений {field_name: {'old': old_value, 'new': new_value}}
            change_reason: Причина изменения (опционально)
            effective_from: Дата начала действия
            metadata: Дополнительные данные
            
        Returns:
            Список созданных записей истории
        """
        history_entries = []
        
        for field_name, field_changes in changes.items():
            entry = await self.log_contract_change(
                contract_id=contract_id,
                changed_by=changed_by,
                change_type=change_type,
                field_name=field_name,
                old_value=field_changes.get('old'),
                new_value=field_changes.get('new'),
                change_reason=change_reason,
                effective_from=effective_from,
                metadata=metadata
            )
            history_entries.append(entry)
        
        logger.info(
            "Contract history batch created",
            contract_id=contract_id,
            fields_count=len(changes),
            change_type=change_type.value,
            changed_by=changed_by
        )
        
        return history_entries
    
    async def get_contract_history(
        self,
        contract_id: int,
        field_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ContractHistory]:
        """
        Получить историю изменений договора.
        
        Args:
            contract_id: ID договора
            field_name: Фильтр по полю (опционально)
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            
        Returns:
            Список записей истории, отсортированный по дате (новые первыми)
        """
        query = select(ContractHistory).where(
            ContractHistory.contract_id == contract_id
        ).options(
            selectinload(ContractHistory.changed_by_user)
        )
        
        if field_name:
            query = query.where(ContractHistory.field_name == field_name)
        
        query = query.order_by(desc(ContractHistory.changed_at)).limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        history_entries = list(result.scalars().all())
        
        # Загружаем пользователей отдельным запросом для избежания greenlet ошибок
        if history_entries:
            user_ids = {entry.changed_by for entry in history_entries if entry.changed_by}
            if user_ids:
                users_query = select(User).where(User.id.in_(user_ids))
                users_result = await self.session.execute(users_query)
                users = {user.id: user for user in users_result.scalars().all()}
                
                # Присваиваем пользователей к записям истории
                for entry in history_entries:
                    if entry.changed_by and entry.changed_by in users:
                        entry.changed_by_user = users[entry.changed_by]
        
        return history_entries
    
    async def get_field_history(
        self,
        contract_id: int,
        field_name: str
    ) -> List[ContractHistory]:
        """
        Получить историю изменений конкретного поля договора.
        
        Args:
            contract_id: ID договора
            field_name: Название поля
            
        Returns:
            Список записей истории для указанного поля
        """
        return await self.get_contract_history(contract_id, field_name=field_name)
    
    async def get_contract_snapshot(
        self,
        contract_id: int,
        target_date: date
    ) -> Dict[str, Any]:
        """
        Получить "снимок" договора на конкретную дату.
        
        Логика:
        1. Найти все изменения до указанной даты (включительно)
        2. Применить изменения в хронологическом порядке
        3. Вернуть итоговое состояние договора
        
        Args:
            contract_id: ID договора
            target_date: Дата, на которую нужен снимок
            
        Returns:
            Словарь с полями договора и их значениями на указанную дату
        """
        # Получаем текущее состояние договора (для проверки существования)
        contract_query = select(Contract).where(Contract.id == contract_id)
        contract_result = await self.session.execute(contract_query)
        contract = contract_result.scalar_one_or_none()
        
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")
        
        # Получаем все изменения до указанной даты (включительно)
        target_datetime = datetime.combine(target_date, datetime.min.time())
        history_query = select(ContractHistory).where(
            and_(
                ContractHistory.contract_id == contract_id,
                ContractHistory.changed_at <= target_datetime
            )
        ).options(
            selectinload(ContractHistory.changed_by_user)
        ).order_by(ContractHistory.changed_at)
        
        history_result = await self.session.execute(history_query)
        history_entries = list(history_result.scalars().all())
        
        # Начальное состояние - берем из записи "created" или используем значения по умолчанию
        snapshot = {
            'hourly_rate': None,
            'use_contract_rate': False,
            'payment_schedule_id': None,
            'inherit_payment_schedule': True,
            'payment_system_id': None,
            'use_contract_payment_system': False,
            'status': 'draft',
            'allowed_objects': [],
            'title': None,
            'template_id': None,
        }
        
        # Применяем изменения в хронологическом порядке (начиная с "created")
        for entry in history_entries:
            if entry.field_name in snapshot:
                # Десериализуем значение
                new_value = self._deserialize_value(entry.new_value)
                snapshot[entry.field_name] = new_value
        
        logger.debug(
            "Contract snapshot created",
            contract_id=contract_id,
            target_date=target_date.isoformat(),
            history_entries_count=len(history_entries)
        )
        
        return snapshot
    
    def _serialize_value(self, value: Any) -> Any:
        """
        Сериализовать значение для хранения в JSONB.
        
        Args:
            value: Значение для сериализации
            
        Returns:
            JSON-совместимое значение
        """
        if value is None:
            return None
        
        # Decimal -> float
        if isinstance(value, Decimal):
            return float(value)
        
        # datetime -> ISO string
        if isinstance(value, datetime):
            return value.isoformat()
        
        # date -> ISO string
        if isinstance(value, date):
            return value.isoformat()
        
        # list/dict уже JSON-совместимы
        if isinstance(value, (list, dict, str, int, float, bool)):
            return value
        
        # Остальные типы -> str
        return str(value)
    
    def _deserialize_value(self, value: Any) -> Any:
        """
        Десериализовать значение из JSONB.
        
        Args:
            value: Значение из JSONB
            
        Returns:
            Десериализованное значение
        """
        if value is None:
            return None
        
        # Если это строка в формате ISO datetime, пытаемся распарсить
        if isinstance(value, str):
            try:
                # Пробуем распарсить как datetime
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    # Пробуем распарсить как date
                    return date.fromisoformat(value)
                except (ValueError, AttributeError):
                    pass
        
        return value
