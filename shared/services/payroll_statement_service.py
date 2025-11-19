"""Сервис формирования расчётных листов для сотрудников."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging.logger import logger
from domain.entities.contract import Contract
from domain.entities.employee_payment import EmployeePayment
from domain.entities.object import Object
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_statement_log import PayrollStatementLog
from domain.entities.payment_schedule import PaymentSchedule
from domain.entities.org_structure import OrgStructureUnit
from domain.entities.user import User
from shared.services.payroll_generation_service import PayrollGenerationService, PayrollGenerationResult
from shared.services.payment_schedule_service import get_payment_period_for_date
from apps.web.services.payroll_service import PayrollService


@dataclass
class StatementEntry:
    entry: PayrollEntry
    adjustments: List[PayrollAdjustment]
    payments: List[EmployeePayment]
    paid_amount: Decimal


@dataclass
class StatementTotals:
    gross: Decimal
    bonuses: Decimal
    deductions: Decimal
    net: Decimal
    paid: Decimal

    @property
    def balance(self) -> Decimal:
        return self.net - self.paid


class PayrollStatementService:
    """Подготавливает расчётный лист и гарантирует наличие всех начислений."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.generation_service = PayrollGenerationService(session)
        self.payroll_service = PayrollService(session)

    async def generate_statement(
        self,
        *,
        employee_id: int,
        requested_by_id: int,
        requested_role: str,
        owner_id: Optional[int] = None,
        accessible_object_ids: Optional[Set[int]] = None,
        ensure_entries: bool = True,
        log_result: bool = True,
    ) -> Dict[str, any]:
        employee = await self._get_employee(employee_id)

        contracts = await self._load_contracts(
            employee_id=employee_id,
            owner_id=owner_id,
            accessible_object_ids=accessible_object_ids,
        )
        if not contracts:
            raise ValueError("Нет доступных договоров для сотрудника")

        objects_map = await self._load_objects_for_contracts(contracts, accessible_object_ids)
        if not objects_map:
            raise ValueError("Нет доступных объектов для расчётного листа")

        org_units_cache = await self._build_org_unit_cache(objects_map.values())
        schedule_map = await self._load_payment_schedules(objects_map.values(), org_units_cache)

        entries = await self._load_entries(employee_id, owner_id, objects_map.keys())
        adjustments = await self._load_adjustments(employee_id, objects_map.keys())

        range_start, range_end = self._detect_range(adjustments, entries)

        if ensure_entries:
            await self._ensure_entries(
                contracts=contracts,
                objects_map=objects_map,
                schedule_map=schedule_map,
                org_units_cache=org_units_cache,
                range_start=range_start,
                range_end=range_end,
                calculation_date=date.today(),
                created_by_id=requested_by_id,
                source="payroll_statement",
                restrict_employee_id=employee_id,
            )
            entries = await self._load_entries(employee_id, owner_id, objects_map.keys())
            adjustments = await self._load_adjustments(employee_id, objects_map.keys())
        payments = await self._load_payments([entry.id for entry in entries])

        entry_blocks = self._build_statement_entries(entries, adjustments, payments)
        totals = self._calculate_totals(entry_blocks)
        pending_adjustments = await self._load_pending_adjustments(employee_id, objects_map.keys())

        log_record: Optional[PayrollStatementLog] = None
        if log_result:
            log_record = PayrollStatementLog(
                employee_id=employee_id,
                owner_id=owner_id,
                requested_by=requested_by_id,
                requested_role=requested_role,
                period_start=range_start,
                period_end=range_end,
                total_net=totals.net,
                total_paid=totals.paid,
                balance=totals.balance,
                extra_data={
                    "entries": len(entry_blocks),
                    "pending_adjustments": len(pending_adjustments),
                },
            )
            self.session.add(log_record)
            await self.session.flush()

            logger.info(
                "Payroll statement generated",
                employee_id=employee_id,
                range_start=range_start.isoformat(),
                range_end=range_end.isoformat(),
                total_net=float(totals.net),
                total_paid=float(totals.paid),
                balance=float(totals.balance),
            )

        return {
            "employee": employee,
            "range_start": range_start,
            "range_end": range_end,
            "entries": entry_blocks,
            "totals": totals,
            "pending_adjustments": pending_adjustments,
            "log_record": log_record,
        }

    async def _get_employee(self, employee_id: int) -> User:
        query = select(User).where(User.id == employee_id)
        result = await self.session.execute(query)
        employee = result.scalar_one_or_none()
        if not employee:
            raise ValueError(f"Сотрудник {employee_id} не найден")
        return employee

    async def _load_contracts(
        self,
        *,
        employee_id: int,
        owner_id: Optional[int],
        accessible_object_ids: Optional[Set[int]],
    ) -> List[Contract]:
        query = select(Contract).where(Contract.employee_id == employee_id)
        if owner_id:
            query = query.where(Contract.owner_id == owner_id)
        query = query.options(selectinload(Contract.owner))
        result = await self.session.execute(query)
        contracts = result.scalars().all()

        filtered: List[Contract] = []
        for contract in contracts:
            object_ids = self._normalize_allowed_objects(contract.allowed_objects)
            if accessible_object_ids is not None:
                object_ids = [obj_id for obj_id in object_ids if obj_id in accessible_object_ids]
            if object_ids:
                contract.__dict__["_allowed_object_ids"] = object_ids  # cache for later use
                filtered.append(contract)

        return filtered

    async def _load_objects_for_contracts(
        self,
        contracts: Sequence[Contract],
        accessible_object_ids: Optional[Set[int]],
    ) -> Dict[int, Object]:
        object_ids: Set[int] = set()
        for contract in contracts:
            object_ids.update(contract.__dict__.get("_allowed_object_ids", []))

        if accessible_object_ids is not None:
            object_ids &= accessible_object_ids

        if not object_ids:
            return {}

        query = (
            select(Object)
            .where(Object.id.in_(list(object_ids)))
            .options(selectinload(Object.org_unit), selectinload(Object.payment_schedule))
        )
        result = await self.session.execute(query)
        objects = result.scalars().all()

        objects_map = {obj.id: obj for obj in objects}

        # Удостоверимся, что в каждом контракте остались только реально существующие объекты
        for contract in contracts:
            allowed_ids = contract.__dict__.get("_allowed_object_ids", [])
            contract.__dict__["_allowed_object_ids"] = [obj_id for obj_id in allowed_ids if obj_id in objects_map]

        return objects_map

    async def _build_org_unit_cache(
        self,
        objects: Sequence[Object],
    ) -> Dict[int, OrgStructureUnit]:
        """Загружает все подразделения и их родителей, чтобы избежать ленивых загрузок."""
        pending_ids: Set[int] = {
            obj.org_unit_id for obj in objects if getattr(obj, "org_unit_id", None)
        }
        cache: Dict[int, OrgStructureUnit] = {}

        while pending_ids:
            ids_to_load = pending_ids - cache.keys()
            if not ids_to_load:
                break
            query = select(OrgStructureUnit).where(OrgStructureUnit.id.in_(list(ids_to_load)))
            result = await self.session.execute(query)
            units = result.scalars().all()
            pending_ids = set()
            for unit in units:
                cache[unit.id] = unit
                if unit.parent_id and unit.parent_id not in cache:
                    pending_ids.add(unit.parent_id)

        return cache

    def _resolve_payment_schedule_id(
        self,
        obj: Object,
        org_units_cache: Dict[int, OrgStructureUnit],
    ) -> Optional[int]:
        """Определяет график выплат для объекта, используя кеш подразделений."""
        if obj.payment_schedule_id is not None:
            return obj.payment_schedule_id

        current_id = getattr(obj, "org_unit_id", None)
        visited: Set[int] = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            unit = org_units_cache.get(current_id)
            if not unit:
                break
            if unit.payment_schedule_id is not None:
                return unit.payment_schedule_id
            current_id = unit.parent_id

        return None

    async def _load_payment_schedules(
        self,
        objects: Sequence[Object],
        org_units_cache: Dict[int, OrgStructureUnit],
    ) -> Dict[int, PaymentSchedule]:
        schedule_ids: Set[int] = set()
        for obj in objects:
            schedule_id = self._resolve_payment_schedule_id(obj, org_units_cache)
            if schedule_id:
                schedule_ids.add(schedule_id)

        if not schedule_ids:
            return {}

        query = select(PaymentSchedule).where(PaymentSchedule.id.in_(list(schedule_ids)))
        result = await self.session.execute(query)
        schedules = result.scalars().all()

        return {schedule.id: schedule for schedule in schedules}

    async def _load_entries(
        self,
        employee_id: int,
        owner_id: Optional[int],
        object_ids: Set[int],
    ) -> List[PayrollEntry]:
        query = select(PayrollEntry).where(PayrollEntry.employee_id == employee_id)
        if object_ids:
            query = query.where(PayrollEntry.object_id.in_(list(object_ids)))
        if owner_id:
            query = query.join(Contract, PayrollEntry.contract_id == Contract.id).where(Contract.owner_id == owner_id)
        query = query.options(
            selectinload(PayrollEntry.object_),
            selectinload(PayrollEntry.adjustments),
            selectinload(PayrollEntry.payments),
        ).order_by(PayrollEntry.period_start, PayrollEntry.period_end, PayrollEntry.id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _load_adjustments(
        self,
        employee_id: int,
        object_ids: Set[int],
    ) -> List[PayrollAdjustment]:
        query = select(PayrollAdjustment).where(PayrollAdjustment.employee_id == employee_id)
        if object_ids:
            query = query.where(
                or_(
                    PayrollAdjustment.object_id.is_(None),
                    PayrollAdjustment.object_id.in_(list(object_ids)),
                )
            )
        query = query.options(selectinload(PayrollAdjustment.shift)).order_by(PayrollAdjustment.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _load_payments(self, entry_ids: List[int]) -> List[EmployeePayment]:
        if not entry_ids:
            return []
        query = select(EmployeePayment).where(EmployeePayment.payroll_entry_id.in_(entry_ids))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _load_pending_adjustments(
        self,
        employee_id: int,
        object_ids: Set[int],
    ) -> List[PayrollAdjustment]:
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.employee_id == employee_id,
            PayrollAdjustment.is_applied == False,  # noqa: E712
        )
        if object_ids:
            query = query.where(
                or_(
                    PayrollAdjustment.object_id.is_(None),
                    PayrollAdjustment.object_id.in_(list(object_ids)),
                )
            )
        query = query.order_by(PayrollAdjustment.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    def _detect_range(
        self,
        adjustments: Sequence[PayrollAdjustment],
        entries: Sequence[PayrollEntry],
    ) -> Tuple[date, date]:
        dates: List[date] = []

        for adj in adjustments:
            dates.append(self._get_adjustment_effective_date(adj))

        for entry in entries:
            dates.append(entry.period_start)
            dates.append(entry.period_end)

        if not dates:
            today = date.today()
            return today, today

        return min(dates), max(dates)

    async def _ensure_entries(
        self,
        *,
        contracts: Sequence[Contract],
        objects_map: Dict[int, Object],
        schedule_map: Dict[int, PaymentSchedule],
        org_units_cache: Dict[int, OrgStructureUnit],
        range_start: date,
        range_end: date,
        calculation_date: date,
        created_by_id: int,
        source: str,
        restrict_employee_id: int,
    ) -> None:
        contract_map: Dict[int, List[Contract]] = {}
        for contract in contracts:
            allowed_ids = contract.__dict__.get("_allowed_object_ids", [])
            for obj_id in allowed_ids:
                contract_map.setdefault(obj_id, []).append(contract)

        for object_id, contract_list in contract_map.items():
            obj = objects_map.get(object_id)
            if not obj:
                continue
            schedule_id = self._resolve_payment_schedule_id(obj, org_units_cache)
            if not schedule_id:
                continue

            schedule = schedule_map.get(schedule_id)
            if not schedule:
                continue

            periods = await self._collect_periods(schedule, range_start, range_end)
            if not periods:
                continue

            for period_start, period_end in periods:
                for contract in contract_list:
                    result = await self.generation_service.process_contract_period(
                        contract=contract,
                        obj=obj,
                        period_start=period_start,
                        period_end=period_end,
                        calculation_date=calculation_date,
                        created_by_id=created_by_id,
                        source=source,
                        restrict_employee_id=restrict_employee_id,
                    )
                    if result.created_entries or result.updated_entries or result.applied_adjustments:
                        logger.info(
                            "Payroll entry ensured for statement",
                            employee_id=contract.employee_id,
                            object_id=obj.id,
                            period_start=period_start.isoformat(),
                            period_end=period_end.isoformat(),
                            entries_created=result.created_entries,
                            entries_updated=result.updated_entries,
                            adjustments_applied=result.applied_adjustments,
                        )

    async def _collect_periods(
        self,
        schedule: PaymentSchedule,
        start_date: date,
        end_date: date,
    ) -> List[Tuple[date, date]]:
        """Возвращает список периодов для графика, перекрывающих диапазон."""
        periods: List[Tuple[date, date]] = []
        seen: Set[Tuple[date, date]] = set()

        scan_start = start_date - timedelta(days=90)
        scan_end = end_date + timedelta(days=30)
        current = scan_start

        while current <= scan_end:
            period = await get_payment_period_for_date(schedule, current)
            if period:
                key = (period["period_start"], period["period_end"])
                if (
                    key not in seen
                    and key[1] >= start_date
                    and key[0] <= end_date
                ):
                    seen.add(key)
                    periods.append(key)
            current += timedelta(days=1)

        periods.sort(key=lambda rng: (rng[0], rng[1]))
        return periods

    def _build_statement_entries(
        self,
        entries: Sequence[PayrollEntry],
        adjustments: Sequence[PayrollAdjustment],
        payments: Sequence[EmployeePayment],
    ) -> List[StatementEntry]:
        adjustments_map: Dict[int, List[PayrollAdjustment]] = {}
        for adj in adjustments:
            if adj.payroll_entry_id is None:
                continue
            adjustments_map.setdefault(adj.payroll_entry_id, []).append(adj)

        payments_map: Dict[int, List[EmployeePayment]] = {}
        for payment in payments:
            payments_map.setdefault(payment.payroll_entry_id, []).append(payment)

        statement_entries: List[StatementEntry] = []
        for entry in entries:
            entry_adjustments = adjustments_map.get(entry.id, [])
            entry_payments = payments_map.get(entry.id, [])

            paid_amount = sum(
                Decimal(str(payment.amount))
                for payment in entry_payments
                if payment.status == "completed"
            )

            statement_entries.append(
                StatementEntry(
                    entry=entry,
                    adjustments=entry_adjustments,
                    payments=entry_payments,
                    paid_amount=paid_amount,
                )
            )

        return statement_entries

    def _calculate_totals(self, entries: Sequence[StatementEntry]) -> StatementTotals:
        gross = Decimal("0")
        bonuses = Decimal("0")
        deductions = Decimal("0")
        net = Decimal("0")
        paid = Decimal("0")

        for block in entries:
            gross += Decimal(str(block.entry.gross_amount or 0))
            bonuses += Decimal(str(block.entry.total_bonuses or 0))
            deductions += Decimal(str(block.entry.total_deductions or 0))
            net += Decimal(str(block.entry.net_amount or 0))
            paid += block.paid_amount

        return StatementTotals(
            gross=gross,
            bonuses=bonuses,
            deductions=deductions,
            net=net,
            paid=paid,
        )

    def _get_adjustment_effective_date(self, adjustment: PayrollAdjustment) -> date:
        if adjustment.shift and adjustment.shift.end_time:
            return adjustment.shift.end_time.date()
        return adjustment.created_at.date() if isinstance(adjustment.created_at, datetime) else date.today()

    def _normalize_allowed_objects(self, allowed_objects) -> List[int]:
        if not allowed_objects:
            return []
        if isinstance(allowed_objects, list):
            raw_values = allowed_objects
        else:
            import json

            try:
                parsed = json.loads(allowed_objects)
                raw_values = parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError, json.JSONDecodeError):
                raw_values = []

        normalized: List[int] = []
        for value in raw_values:
            try:
                normalized.append(int(value))
            except (TypeError, ValueError):
                continue
        return normalized

