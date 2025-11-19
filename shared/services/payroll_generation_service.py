"""Сервис для генерации/обновления начислений по периодам."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, List, Tuple

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging.logger import logger
from domain.entities.contract import Contract
from domain.entities.object import Object
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.shift import Shift
from shared.services.payroll_adjustment_service import PayrollAdjustmentService


@dataclass
class PayrollGenerationResult:
    created_entries: int = 0
    updated_entries: int = 0
    applied_adjustments: int = 0


class PayrollGenerationService:
    """Сервис, который пересчитывает начисления для заданного периода."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.adjustment_service = PayrollAdjustmentService(session)

    async def process_contract_period(
        self,
        *,
        contract: Contract,
        obj: Object,
        period_start: date,
        period_end: date,
        calculation_date: date,
        created_by_id: int,
        source: str,
        restrict_employee_id: Optional[int] = None,
    ) -> PayrollGenerationResult:
        """
        Создаёт/обновляет начисление для сотрудника по конкретному объекту и периоду.

        Args:
            contract: Договор сотрудника
            obj: Объект, для которого выполняется расчёт
            period_start: Начало периода
            period_end: Конец периода
            calculation_date: Дата расчёта (используется в calculation_details)
            created_by_id: Кто инициировал расчёт
            source: Источник (manual_recalculate, statement и т.д.)
            restrict_employee_id: Если указан, обрабатываем только этого сотрудника
        """

        if restrict_employee_id is not None and contract.employee_id != restrict_employee_id:
            return PayrollGenerationResult()

        # Проверяем политику расчётов у terminated контрактов
        if contract.status == "terminated":
            if contract.settlement_policy == "termination_date":
                if not contract.termination_date or period_end > contract.termination_date:
                    return PayrollGenerationResult()
            elif contract.settlement_policy not in {"schedule", "termination_date"}:
                return PayrollGenerationResult()

        # Проверяем, покрывает ли договор данный объект
        allowed_object_ids = self._normalize_allowed_objects(contract.allowed_objects)
        if obj.id not in allowed_object_ids:
            return PayrollGenerationResult()

        existing_entry_query = select(PayrollEntry).where(
            PayrollEntry.employee_id == contract.employee_id,
            PayrollEntry.period_start == period_start,
            PayrollEntry.period_end == period_end,
            PayrollEntry.object_id == obj.id,
        )
        existing_entry_result = await self.session.execute(existing_entry_query)
        existing_entry = existing_entry_result.scalar_one_or_none()

        all_adjustments = await self._fetch_period_adjustments(
            employee_id=contract.employee_id,
            object_id=obj.id,
            period_start=period_start,
            period_end=period_end,
            existing_entry=existing_entry,
        )

        if not all_adjustments:
            return PayrollGenerationResult()

        (
            already_applied_adjustments,
            new_adjustments,
        ) = self._split_adjustments(all_adjustments, existing_entry)

        if new_adjustments:
            await self.session.flush()

        if not already_applied_adjustments and not new_adjustments:
            return PayrollGenerationResult()

        all_relevant_adjustments = already_applied_adjustments + new_adjustments

        gross_amount, total_bonuses, total_deductions, total_hours = self._calculate_totals(
            all_relevant_adjustments
        )
        avg_hourly_rate = gross_amount / total_hours if total_hours > 0 else Decimal("0")
        net_amount = gross_amount + total_bonuses - total_deductions

        calculation_details = await self._build_calculation_details(
            adjustments=all_relevant_adjustments,
            source=source,
            calculation_date=calculation_date,
        )

        outcome = PayrollGenerationResult()

        if not existing_entry:
            payroll_entry = PayrollEntry(
                employee_id=contract.employee_id,
                contract_id=contract.id,
                object_id=obj.id,
                period_start=period_start,
                period_end=period_end,
                hours_worked=float(total_hours),
                hourly_rate=float(avg_hourly_rate),
                gross_amount=float(gross_amount),
                total_bonuses=float(total_bonuses),
                total_deductions=float(total_deductions),
                net_amount=float(net_amount),
                calculation_details=calculation_details,
                created_by_id=created_by_id,
            )
            self.session.add(payroll_entry)
            await self.session.flush()

            if new_adjustments:
                applied_count = await self.adjustment_service.mark_adjustments_as_applied(
                    adjustment_ids=[adj.id for adj in new_adjustments],
                    payroll_entry_id=payroll_entry.id,
                )
            else:
                applied_count = 0

            outcome.created_entries += 1
            outcome.applied_adjustments += applied_count

            logger.info(
                "Payroll entry created via generation service",
                entry_id=payroll_entry.id,
                employee_id=contract.employee_id,
                object_id=obj.id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
                net_amount=float(net_amount),
                source=source,
            )
        else:
            existing_entry.gross_amount = float(gross_amount)
            existing_entry.total_bonuses = float(total_bonuses)
            existing_entry.total_deductions = float(total_deductions)
            existing_entry.net_amount = float(net_amount)
            existing_entry.hours_worked = float(total_hours)
            existing_entry.hourly_rate = float(avg_hourly_rate)
            existing_entry.calculation_details = calculation_details

            if new_adjustments:
                applied_count = await self.adjustment_service.mark_adjustments_as_applied(
                    adjustment_ids=[adj.id for adj in new_adjustments],
                    payroll_entry_id=existing_entry.id,
                )
            else:
                applied_count = 0

            outcome.updated_entries += 1
            outcome.applied_adjustments += applied_count

            logger.info(
                "Payroll entry updated via generation service",
                entry_id=existing_entry.id,
                employee_id=contract.employee_id,
                object_id=obj.id,
                period_start=period_start.isoformat(),
                period_end=period_end.isoformat(),
                net_amount=float(net_amount),
                source=source,
            )

        return outcome

    async def _fetch_period_adjustments(
        self,
        *,
        employee_id: int,
        object_id: int,
        period_start: date,
        period_end: date,
        existing_entry: Optional[PayrollEntry],
    ) -> List[PayrollAdjustment]:
        """Загружает коррекции для периода (по логике manual_recalculate)."""

        apply_status_conditions = [
            PayrollAdjustment.is_applied == False,
            and_(
                PayrollAdjustment.is_applied == True,
                PayrollAdjustment.payroll_entry_id.is_(None),
            ),
        ]

        if existing_entry:
            apply_status_conditions.append(
                and_(
                    PayrollAdjustment.is_applied == True,
                    PayrollAdjustment.payroll_entry_id == existing_entry.id,
                )
            )

        query = (
            select(PayrollAdjustment)
            .outerjoin(Shift, PayrollAdjustment.shift_id == Shift.id)
            .where(
                PayrollAdjustment.employee_id == employee_id,
                or_(*apply_status_conditions),
                or_(
                    and_(
                        PayrollAdjustment.shift_id.isnot(None),
                        func.date(Shift.end_time) >= period_start,
                        func.date(Shift.end_time) <= period_end,
                    ),
                    and_(
                        PayrollAdjustment.shift_id.is_(None),
                        or_(
                            and_(
                                PayrollAdjustment.payroll_entry_id.is_(None),
                                func.date(PayrollAdjustment.created_at) >= period_start,
                                func.date(PayrollAdjustment.created_at) <= period_end,
                            ),
                            PayrollAdjustment.payroll_entry_id == existing_entry.id
                            if existing_entry
                            else False,
                        ),
                    ),
                ),
            )
            .options(selectinload(PayrollAdjustment.shift))
        )

        result = await self.session.execute(query)
        adjustments: List[PayrollAdjustment] = list(result.scalars().all())

        filtered: List[PayrollAdjustment] = []
        for adj in adjustments:
            if adj.adjustment_type == "shift_base" and adj.object_id != object_id:
                continue
            filtered.append(adj)

        return filtered

    def _split_adjustments(
        self,
        adjustments: List[PayrollAdjustment],
        existing_entry: Optional[PayrollEntry],
    ) -> Tuple[List[PayrollAdjustment], List[PayrollAdjustment]]:
        already_applied: List[PayrollAdjustment] = []
        new_adjustments: List[PayrollAdjustment] = []

        for adj in adjustments:
            if adj.is_applied and adj.payroll_entry_id is None:
                adj.is_applied = False
                adj.payroll_entry_id = None

            if existing_entry and adj.is_applied and adj.payroll_entry_id == existing_entry.id:
                already_applied.append(adj)
            else:
                new_adjustments.append(adj)

        return already_applied, new_adjustments

    def _calculate_totals(
        self,
        adjustments: List[PayrollAdjustment],
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        gross_amount = Decimal("0")
        total_bonuses = Decimal("0")
        total_deductions = Decimal("0")
        total_hours = Decimal("0")

        for adj in adjustments:
            amount_decimal = Decimal(str(adj.amount))

            if adj.adjustment_type == "shift_base":
                gross_amount += amount_decimal
                if adj.details and "hours" in adj.details:
                    total_hours += Decimal(str(adj.details["hours"]))
            elif amount_decimal > 0:
                total_bonuses += amount_decimal
            else:
                total_deductions += abs(amount_decimal)

        return gross_amount, total_bonuses, total_deductions, total_hours

    async def _build_calculation_details(
        self,
        *,
        adjustments: List[PayrollAdjustment],
        source: str,
        calculation_date: date,
    ) -> dict:
        details = {
            "created_by": source,
            "created_at": calculation_date.isoformat(),
            "shifts": [],
            "adjustments": [],
        }

        shift_adjustments = [adj for adj in adjustments if adj.adjustment_type == "shift_base"]
        shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]

        if shift_ids:
            shifts_query = select(Shift).where(Shift.id.in_(shift_ids))
            shifts_result = await self.session.execute(shifts_query)
            shifts = shifts_result.scalars().all()

            for shift in shifts:
                shift_hours = Decimal(str(shift.total_hours)) if shift.total_hours else Decimal("0")
                shift_rate = Decimal(str(shift.hourly_rate)) if shift.hourly_rate else Decimal("0")
                shift_payment = shift_hours * shift_rate
                details["shifts"].append(
                    {
                        "shift_id": shift.id,
                        "date": shift.start_time.date().isoformat() if shift.start_time else None,
                        "hours": float(shift_hours),
                        "rate": float(shift_rate),
                        "amount": float(shift_payment),
                    }
                )

        for adj in adjustments:
            details["adjustments"].append(
                {
                    "adjustment_id": adj.id,
                    "type": adj.adjustment_type,
                    "amount": float(adj.amount),
                    "description": adj.description or "",
                    "shift_id": adj.shift_id,
                }
            )

        return details

    @staticmethod
    def _normalize_allowed_objects(allowed_objects) -> List[int]:
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

