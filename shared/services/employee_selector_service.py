"""Сервис для выборки сотрудников по объектам/владельцам с группировкой."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.user import User


class EmployeeSelectorService:
    """Универсальный сервис для получения сотрудников по объектам/владельцам."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_employees_for_owner(
        self,
        owner_id: int,
        object_id: Optional[int] = None,
    ) -> Dict[str, List[Dict[str, Optional[str]]]]:
        """
        Вернуть сотрудников владельца, сгруппированных по активным и расторгнутым договорам.

        Args:
            owner_id: ID владельца.
            object_id: ID объекта. Если задан, отбираются только сотрудники, у которых в договорах есть доступ к объекту.

        Returns:
            Словарь с ключами active / former (списки сотрудников).
        """
        contracts = await self._load_contracts(owner_id, object_id)
        return self._group_employees(contracts, object_id)

    async def get_employees_for_object(
        self,
        object_id: int
    ) -> Tuple[Optional[int], Dict[str, List[Dict[str, Optional[str]]]]]:
        """
        Вернуть владельца и сотрудников для конкретного объекта.

        Args:
            object_id: ID объекта.

        Returns:
            Кортеж (owner_id, сгруппированные сотрудники). Если объект не найден — (None, пустые списки).
        """
        obj = await self.session.get(Object, object_id)
        if not obj or not getattr(obj, "owner_id", None):
            return None, {"active": [], "former": []}

        grouped = await self.get_employees_for_owner(obj.owner_id, object_id=object_id)
        return obj.owner_id, grouped

    async def _load_contracts(
        self,
        owner_id: int,
        object_id: Optional[int]
    ) -> List[Contract]:
        """Получить контракты владельца (с optional фильтром по объекту) вместе с сотрудниками."""
        contracts_query = (
            select(Contract)
            .options(selectinload(Contract.employee))
            .where(Contract.owner_id == owner_id)
        )
        result = await self.session.execute(contracts_query)
        contracts = list(result.scalars().all())

        if object_id is None:
            return contracts

        filtered_contracts: List[Contract] = []
        for contract in contracts:
            allowed_objects = contract.allowed_objects
            if allowed_objects is None:
                # Нет ограничения по объектам — считаем, что договор распространяется на все объекты владельца
                filtered_contracts.append(contract)
                continue

            if isinstance(allowed_objects, str):
                try:
                    allowed_objects = json.loads(allowed_objects)
                except json.JSONDecodeError:
                    allowed_objects = []

            if isinstance(allowed_objects, list) and object_id in allowed_objects:
                filtered_contracts.append(contract)

        return filtered_contracts

    def _group_employees(
        self,
        contracts: List[Contract],
        object_id: Optional[int]
    ) -> Dict[str, List[Dict[str, Optional[str]]]]:
        """
        Разделить сотрудников на активных и бывших.

        Args:
            contracts: список договоров владельца (уже отфильтрованных по объекту при необходимости).
            object_id: объект, для которого строится список (используется только для журналирования/расширения в будущем).

        Returns:
            Словарь {"active": [...], "former": [...]} с сотрудниками.
        """
        employees_map: Dict[int, Dict[str, object]] = {}

        for contract in contracts:
            employee: Optional[User] = contract.employee
            if not employee:
                continue

            emp_record = employees_map.setdefault(
                employee.id,
                {
                    "employee": employee,
                    "has_active": False,
                    "has_inactive": False,
                },
            )

            is_active_contract = bool(contract.is_active and contract.status == "active")
            if is_active_contract:
                emp_record["has_active"] = True
            else:
                emp_record["has_inactive"] = True

        active_employees: List[Dict[str, Optional[str]]] = []
        former_employees: List[Dict[str, Optional[str]]] = []

        for record in employees_map.values():
            employee: User = record["employee"]  # type: ignore[assignment]
            item = {
                "id": int(employee.id),
                "first_name": employee.first_name or "",
                "last_name": employee.last_name or "",
                "middle_name": getattr(employee, "patronymic", "") or "",
                "is_active": bool(record["has_active"]),
            }

            if record["has_active"]:
                active_employees.append(item)
            elif record["has_inactive"]:
                former_employees.append(item)

        def sort_key(emp: Dict[str, Optional[str]]):
            return (
                (emp["last_name"] or "").lower(),
                (emp["first_name"] or "").lower(),
                emp["id"],
            )

        active_employees.sort(key=sort_key)
        former_employees.sort(key=sort_key)

        return {"active": active_employees, "former": former_employees}

