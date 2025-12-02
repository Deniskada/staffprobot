"""Celery задачи для автоматического создания начислений по графику выплат."""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict, Any
import asyncio

from core.celery.celery_app import celery_app
from core.database.session import get_async_session
from core.logging.logger import logger
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from domain.entities.payment_schedule import PaymentSchedule
from domain.entities.object import Object
from domain.entities.contract import Contract
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.org_structure import OrgStructureUnit
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.payment_schedule_service import get_payment_period_for_date
from shared.services.contract_helper import get_inherited_payment_schedule_id


@celery_app.task(name="create_payroll_entries_by_schedule")
def create_payroll_entries_by_schedule(target_date: str = None):
    """
    Автоматически создает начисления (payroll_entries) по графикам выплат.
    
    Запускается ежедневно в 01:00.
    
    Args:
        target_date: Опциональная дата в формате YYYY-MM-DD. Если не указана, используется сегодняшняя дата.
    
    Логика:
    1. Находит все payment_schedules, у которых дата выплаты = сегодня
    2. Для каждого графика находит все объекты с этим payment_schedule_id
    3. Для каждого объекта находит активных сотрудников (contracts)
    4. Для каждого сотрудника:
       - Определяет период выплаты из schedule (period_start, period_end)
       - Получает все is_applied=FALSE adjustments за период
       - Создает PayrollEntry
       - Проставляет payroll_entry_id и is_applied=TRUE у adjustments
    """
    
    async def process():
        try:
            if target_date:
                today = date.fromisoformat(target_date)
            else:
                today = date.today()
            logger.info(f"Starting payroll entries creation for {today}")
            
            async with get_async_session() as session:
                # 1. Найти все schedules с датой выплаты сегодня
                schedules_query = select(PaymentSchedule).where(
                    PaymentSchedule.is_active == True   # Только активные графики
                )
                schedules_result = await session.execute(schedules_query)
                schedules = schedules_result.scalars().all()
                
                logger.info(f"Found {len(schedules)} active payment schedules to check")
                
                total_entries_created = 0
                total_entries_updated = 0
                total_adjustments_applied = 0
                errors = []
                
                for schedule in schedules:
                    try:
                        # Проверяем, есть ли выплата сегодня для этого графика
                        logger.info(
                            "Schedule check",
                            schedule_id=schedule.id,
                            schedule_name=schedule.name,
                            frequency=schedule.frequency,
                            payment_day=schedule.payment_day,
                            period_cfg=schedule.payment_period,
                            today=today.isoformat()
                        )

                        payment_period = await get_payment_period_for_date(schedule, today)
                        
                        if not payment_period:
                            logger.info(
                                "Skip schedule: not a payment day",
                                schedule_id=schedule.id
                            )
                            continue
                        
                        period_start = payment_period['period_start']
                        period_end = payment_period['period_end']

                        if period_start > period_end:
                            logger.warning(
                                "Invalid period (start > end)",
                                schedule_id=schedule.id,
                                period_start=period_start.isoformat(),
                                period_end=period_end.isoformat()
                            )
                            continue
                        
                        logger.info(
                            f"Processing schedule {schedule.id}: {schedule.name}",
                            period_start=period_start.isoformat(),
                            period_end=period_end.isoformat()
                        )
                        
                        # 2. Найти все объекты с этим payment_schedule_id
                        # Учитываем как прямую привязку, так и наследование от подразделения
                        
                        # Функция для рекурсивного поиска всех потомков подразделения
                        async def get_all_descendant_unit_ids(unit_id: int) -> List[int]:
                            """Рекурсивно найти все дочерние подразделения"""
                            result = [unit_id]
                            children_query = select(OrgStructureUnit.id).where(
                                OrgStructureUnit.parent_id == unit_id,
                                OrgStructureUnit.is_active == True
                            )
                            children_result = await session.execute(children_query)
                            children_ids = [row[0] for row in children_result.all()]
                            
                            for child_id in children_ids:
                                result.extend(await get_all_descendant_unit_ids(child_id))
                            
                            return result
                        
                        # Найти подразделения, использующие этот график (с учетом наследования)
                        units_with_schedule = []
                        
                        # Найти все подразделения владельца (если owner_id указан) или все подразделения
                        if schedule.owner_id:
                            all_units_query = select(OrgStructureUnit).options(
                                selectinload(OrgStructureUnit.parent)
                            ).where(
                                OrgStructureUnit.owner_id == schedule.owner_id,
                                OrgStructureUnit.is_active == True
                            )
                        else:
                            all_units_query = select(OrgStructureUnit).options(
                                selectinload(OrgStructureUnit.parent)
                            ).where(
                                OrgStructureUnit.is_active == True
                            )
                        
                        all_units_result = await session.execute(all_units_query)
                        all_units = all_units_result.scalars().all()
                        
                        # Проверить каждое подразделение
                        for unit in all_units:
                            # Проверить, использует ли подразделение этот график (с учетом наследования)
                            inherited_schedule_id = unit.get_inherited_payment_schedule_id()
                            if inherited_schedule_id == schedule.id:
                                # Добавить само подразделение и все его дочерние подразделения
                                unit_ids = await get_all_descendant_unit_ids(unit.id)
                                units_with_schedule.extend(unit_ids)
                        
                        # Убрать дубликаты
                        units_with_schedule = list(set(units_with_schedule))
                        
                        # Найти объекты:
                        # - с прямой привязкой к графику ИЛИ
                        # - принадлежащие подразделению с этим графиком (с учетом дочерних)
                        if units_with_schedule:
                            objects_query = select(Object).where(
                                Object.is_active == True,
                                or_(
                                    Object.payment_schedule_id == schedule.id,
                                    Object.org_unit_id.in_(units_with_schedule)
                                )
                            )
                        else:
                            # Если нет подразделений с этим графиком, искать только объекты с прямой привязкой
                            objects_query = select(Object).where(
                                Object.is_active == True,
                                Object.payment_schedule_id == schedule.id
                            )
                        
                        objects_result = await session.execute(objects_query)
                        objects = objects_result.scalars().all()
                        
                        logger.info(f"Found {len(objects)} objects for schedule {schedule.id}")
                        
                        # НОВАЯ ЛОГИКА: Найти всех владельцев объектов
                        owner_ids = list(set([obj.owner_id for obj in objects if obj.owner_id]))
                        logger.info(f"Processing {len(owner_ids)} owner(s) for schedule {schedule.id}")
                        
                        # Для каждого владельца найти все активные договоры
                        for owner_id in owner_ids:
                            try:
                                # Найти все активные (или terminated/schedule) договоры владельца
                                contracts_query = select(Contract).where(
                                    and_(
                                        Contract.owner_id == owner_id,
                                        or_(
                                            Contract.status == 'active',
                                            and_(
                                                Contract.status == 'terminated',
                                                Contract.settlement_policy == 'schedule'
                                            )
                                        )
                                    )
                                )
                                contracts_result = await session.execute(contracts_query)
                                all_contracts = contracts_result.scalars().all()
                                
                                logger.debug(f"Found {len(all_contracts)} total contracts for owner {owner_id}")
                                
                                # Для каждого договора проверить график и обработать корректировки
                                for contract in all_contracts:
                                    try:
                                        # НОВАЯ ЛОГИКА: Проверить график выплат контракта
                                        effective_payment_schedule_id = None
                                        
                                        if contract.inherit_payment_schedule:
                                            # Наследуем от подразделения
                                            effective_payment_schedule_id = await get_inherited_payment_schedule_id(contract, session)
                                            logger.debug(
                                                f"Contract {contract.id} inherits payment schedule from org unit",
                                                inherited_schedule_id=effective_payment_schedule_id
                                            )
                                        else:
                                            # Используем явно указанный график (ПРИОРИТЕТ!)
                                            effective_payment_schedule_id = contract.payment_schedule_id
                                            logger.debug(
                                                f"Contract {contract.id} has explicit payment schedule",
                                                schedule_id=effective_payment_schedule_id
                                            )
                                        
                                        # Проверяем, совпадает ли график контракта с текущим графиком
                                        if effective_payment_schedule_id and effective_payment_schedule_id != schedule.id:
                                            logger.debug(
                                                f"Skip contract {contract.id}: different payment schedule",
                                                contract_schedule=effective_payment_schedule_id,
                                                current_schedule=schedule.id
                                            )
                                            continue
                                        
                                        # Если у контракта нет графика (ни явного, ни наследуемого) - пропускаем
                                        if not effective_payment_schedule_id:
                                            logger.debug(
                                                f"Skip contract {contract.id}: no payment schedule"
                                            )
                                            continue
                                        
                                        adjustment_service = PayrollAdjustmentService(session)
                                        
                                        # Найти ВСЕ корректировки сотрудника за период (без фильтра по объектам!)
                                        from domain.entities.shift import Shift
                                        from sqlalchemy import func
                                        
                                        # Простой запрос: все неприменённые корректировки за период
                                        all_adjustments_query = select(PayrollAdjustment).outerjoin(
                                            Shift, PayrollAdjustment.shift_id == Shift.id
                                        ).where(
                                            PayrollAdjustment.employee_id == contract.employee_id,
                                            PayrollAdjustment.is_applied == False,
                                            or_(
                                                and_(
                                                    PayrollAdjustment.shift_id.isnot(None),
                                                    func.date(Shift.end_time) >= period_start,
                                                    func.date(Shift.end_time) <= period_end
                                                ),
                                                and_(
                                                    PayrollAdjustment.shift_id.is_(None),
                                                    func.date(PayrollAdjustment.created_at) >= period_start,
                                                    func.date(PayrollAdjustment.created_at) <= period_end
                                                )
                                            )
                                        )
                                        
                                        all_result = await session.execute(all_adjustments_query)
                                        all_adjustments = list(all_result.scalars().all())
                                        
                                        if not all_adjustments:
                                            logger.debug(
                                                f"No unapplied adjustments for employee {contract.employee_id}"
                                            )
                                            continue
                                        
                                        # Группируем корректировки по object_id
                                        from collections import defaultdict
                                        adjustments_by_object = defaultdict(list)
                                        for adj in all_adjustments:
                                            adjustments_by_object[adj.object_id].append(adj)
                                        
                                        logger.info(
                                            f"Employee {contract.employee_id}: {len(all_adjustments)} adjustments grouped into {len(adjustments_by_object)} objects"
                                        )
                                        
                                        # Обрабатываем корректировки для КАЖДОГО объекта
                                        for obj_id, object_adjustments in adjustments_by_object.items():
                                            try:
                                                # Проверить, существует ли уже начисление за этот период и объект
                                                existing_entry_query = select(PayrollEntry).where(
                                                    PayrollEntry.employee_id == contract.employee_id,
                                                    PayrollEntry.period_start == period_start,
                                                    PayrollEntry.period_end == period_end,
                                                    PayrollEntry.object_id == obj_id
                                                )
                                                existing_entry_result = await session.execute(existing_entry_query)
                                                existing_entry = existing_entry_result.scalar_one_or_none()
                                                
                                                # Все корректировки для этого объекта - новые (т.к. фильтр is_applied=false)
                                                new_adjustments = object_adjustments
                                                
                                                # Пропускаем если нет корректировок
                                                if not new_adjustments:
                                                    continue
                                        
                                                # ПЕРЕСЧИТЫВАЕМ с использованием ВСЕХ корректировок
                                                all_relevant_adjustments = new_adjustments
                                        
                                                gross_amount = Decimal('0.00')
                                                total_bonuses = Decimal('0.00')
                                                total_deductions = Decimal('0.00')
                                                total_hours = Decimal('0.00')
                                                
                                                for adj in all_relevant_adjustments:
                                                    amount_decimal = Decimal(str(adj.amount))
                                                    
                                                    if adj.adjustment_type == 'shift_base':
                                                        gross_amount += amount_decimal
                                                        # Извлекаем часы из details корректировки
                                                        if adj.details and 'hours' in adj.details:
                                                            total_hours += Decimal(str(adj.details['hours']))
                                                    elif amount_decimal > 0:
                                                        total_bonuses += amount_decimal
                                                    else:
                                                        total_deductions += abs(amount_decimal)
                                        
                                                avg_hourly_rate = gross_amount / total_hours if total_hours > 0 else Decimal('0')
                                                net_amount = gross_amount + total_bonuses - total_deductions
                                                
                                                # Формируем calculation_details для протокола расчёта
                                                calculation_details = {
                                                    "created_by": "celery_schedule",
                                                    "created_at": today.isoformat(),
                                                    "shifts": [],
                                                    "adjustments": []
                                                }
                                                
                                                # Собираем детали смен
                                                shift_base_adjustments = [adj for adj in all_relevant_adjustments if adj.adjustment_type == 'shift_base']
                                                if shift_base_adjustments:
                                                    shift_ids = [adj.shift_id for adj in shift_base_adjustments if adj.shift_id]
                                                    if shift_ids:
                                                        shifts_query = select(Shift).where(Shift.id.in_(shift_ids))
                                                        shifts_result = await session.execute(shifts_query)
                                                        shifts = shifts_result.scalars().all()
                                                        for shift in shifts:
                                                            shift_hours = Decimal(str(shift.total_hours)) if shift.total_hours else Decimal('0')
                                                            shift_rate = Decimal(str(shift.hourly_rate)) if shift.hourly_rate else Decimal('0')
                                                            shift_payment = shift_hours * shift_rate
                                                            
                                                            calculation_details["shifts"].append({
                                                                "shift_id": shift.id,
                                                                "date": shift.start_time.date().isoformat() if shift.start_time else None,
                                                                "hours": float(shift_hours),
                                                                "rate": float(shift_rate),
                                                                "amount": float(shift_payment)
                                                            })
                                                
                                                # Собираем детали всех корректировок
                                                for adj in all_relevant_adjustments:
                                                    calculation_details["adjustments"].append({
                                                        "adjustment_id": adj.id,
                                                        "type": adj.adjustment_type,
                                                        "amount": float(adj.amount),
                                                        "description": adj.description or "",
                                                        "shift_id": adj.shift_id
                                                    })
                                        
                                                # Если начисления не существует - СОЗДАЁМ новое
                                                if not existing_entry:
                                                    payroll_entry = PayrollEntry(
                                                        employee_id=contract.employee_id,
                                                        contract_id=contract.id,
                                                        object_id=obj_id,
                                                        period_start=period_start,
                                                        period_end=period_end,
                                                        hours_worked=float(total_hours),
                                                        hourly_rate=float(avg_hourly_rate),
                                                        gross_amount=float(gross_amount),
                                                        total_bonuses=float(total_bonuses),
                                                        total_deductions=float(total_deductions),
                                                        net_amount=float(net_amount),
                                                        calculation_details=calculation_details
                                                    )
                                                    
                                                    session.add(payroll_entry)
                                                    await session.flush()
                                                    
                                                    # Применяем ТОЛЬКО новые корректировки
                                                    if new_adjustments:
                                                        new_adjustment_ids = [adj.id for adj in new_adjustments]
                                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                                            adjustment_ids=new_adjustment_ids,
                                                            payroll_entry_id=payroll_entry.id
                                                        )
                                                    else:
                                                        applied_count = 0
                                                    
                                                    total_entries_created += 1
                                                    total_adjustments_applied += applied_count
                                                    
                                                    logger.info(
                                                        f"Created payroll entry",
                                                        payroll_entry_id=payroll_entry.id,
                                                        employee_id=contract.employee_id,
                                                        object_id=obj_id,
                                                        gross_amount=float(gross_amount),
                                                        net_amount=float(net_amount),
                                                        adjustments_count=applied_count
                                                    )
                                                else:
                                                    # ОБНОВЛЯЕМ существующее начисление
                                                    existing_entry.gross_amount = float(gross_amount)
                                                    existing_entry.total_bonuses = float(total_bonuses)
                                                    existing_entry.total_deductions = float(total_deductions)
                                                    existing_entry.net_amount = float(net_amount)
                                                    existing_entry.hours_worked = float(total_hours)
                                                    existing_entry.hourly_rate = float(avg_hourly_rate)
                                                    existing_entry.calculation_details = calculation_details
                                                    
                                                    # Применяем ТОЛЬКО новые корректировки
                                                    if new_adjustments:
                                                        new_adjustment_ids = [adj.id for adj in new_adjustments]
                                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                                            adjustment_ids=new_adjustment_ids,
                                                            payroll_entry_id=existing_entry.id
                                                        )
                                                    else:
                                                        applied_count = 0
                                                    
                                                    total_entries_updated += 1
                                                    total_adjustments_applied += applied_count
                                                    
                                                    logger.info(
                                                        f"Updated payroll entry",
                                                        payroll_entry_id=existing_entry.id,
                                                        employee_id=contract.employee_id,
                                                        object_id=obj_id,
                                                        adjustments_count=applied_count
                                                    )
                                            except Exception as e:
                                                logger.error(
                                                    f"Error processing object {obj_id} for contract {contract.id}",
                                                    employee_id=contract.employee_id,
                                                    object_id=obj_id,
                                                    error=str(e),
                                                    exc_info=True
                                                )
                                                errors.append({
                                                    "contract_id": contract.id,
                                                    "employee_id": contract.employee_id,
                                                    "object_id": obj_id,
                                                    "error": str(e)
                                                })
                                                continue
                                    except Exception as e:
                                        logger.error(
                                            f"Error processing contract {contract.id}",
                                            error=str(e),
                                            exc_info=True
                                        )
                                        errors.append({
                                            "contract_id": contract.id,
                                            "employee_id": contract.employee_id,
                                            "error": str(e)
                                        })
                                        continue
                            except Exception as e:
                                logger.error(
                                    f"Error processing owner {owner_id}",
                                    error=str(e),
                                    exc_info=True
                                )
                                errors.append({
                                    "owner_id": owner_id,
                                    "error": str(e)
                                })
                                continue
                        
                        # ===== ОБРАБОТКА ИНДИВИДУАЛЬНЫХ ГРАФИКОВ СОТРУДНИКОВ =====
                        # Найти все contracts с payment_schedule_id=schedule.id и inherit_payment_schedule=false
                        # (не привязанные ни к одному объекту с этим графиком)
                        individual_contracts_query = select(Contract).where(
                            Contract.payment_schedule_id == schedule.id,
                            Contract.inherit_payment_schedule == False,
                            or_(
                                Contract.status == 'active',
                                and_(
                                    Contract.status == 'terminated',
                                    Contract.settlement_policy == 'schedule'
                                )
                            )
                        )
                        individual_contracts_result = await session.execute(individual_contracts_query)
                        individual_contracts = individual_contracts_result.scalars().all()
                        
                        logger.info(f"Found {len(individual_contracts)} contracts with individual schedule {schedule.id}")
                        
                        for contract in individual_contracts:
                            try:
                                # Используем первый объект из allowed_objects
                                if not contract.allowed_objects or len(contract.allowed_objects) == 0:
                                    logger.warning(f"Contract {contract.id} has no allowed_objects, skipping")
                                    continue
                                
                                first_object_id = contract.allowed_objects[0]
                                
                                # Загрузить объект
                                obj_result = await session.execute(
                                    select(Object).where(Object.id == first_object_id)
                                )
                                obj = obj_result.scalar_one_or_none()
                                
                                if not obj:
                                    logger.warning(f"Object {first_object_id} not found for contract {contract.id}")
                                    continue
                                
                                adjustment_service = PayrollAdjustmentService(session)
                                
                                # Проверить, существует ли уже начисление за этот период
                                existing_entry_query = select(PayrollEntry).where(
                                    PayrollEntry.employee_id == contract.employee_id,
                                    PayrollEntry.period_start == period_start,
                                    PayrollEntry.period_end == period_end,
                                    PayrollEntry.object_id == obj.id
                                )
                                existing_entry_result = await session.execute(existing_entry_query)
                                existing_entry = existing_entry_result.scalar_one_or_none()
                                
                                # РАСШИРЕННЫЙ фильтр корректировок
                                from domain.entities.shift import Shift
                                from sqlalchemy import func
                                
                                apply_status_conditions = [
                                    PayrollAdjustment.is_applied == False,
                                    and_(
                                        PayrollAdjustment.is_applied == True,
                                        PayrollAdjustment.payroll_entry_id.is_(None)
                                    )
                                ]
                                
                                if existing_entry:
                                    apply_status_conditions.append(
                                        and_(
                                            PayrollAdjustment.is_applied == True,
                                            PayrollAdjustment.payroll_entry_id == existing_entry.id
                                        )
                                    )
                                
                                all_adjustments_query = select(PayrollAdjustment).outerjoin(
                                    Shift, PayrollAdjustment.shift_id == Shift.id
                                ).where(
                                    PayrollAdjustment.employee_id == contract.employee_id,
                                    or_(*apply_status_conditions),
                                    or_(
                                        and_(
                                            PayrollAdjustment.shift_id.isnot(None),
                                            func.date(Shift.end_time) >= period_start,
                                            func.date(Shift.end_time) <= period_end
                                        ),
                                        and_(
                                            PayrollAdjustment.shift_id.is_(None),
                                            or_(
                                                and_(
                                                    PayrollAdjustment.payroll_entry_id.is_(None),
                                                    func.date(PayrollAdjustment.created_at) >= period_start,
                                                    func.date(PayrollAdjustment.created_at) <= period_end
                                                ),
                                                PayrollAdjustment.payroll_entry_id == existing_entry.id if existing_entry else False
                                            )
                                        )
                                    )
                                )
                                
                                all_result = await session.execute(all_adjustments_query)
                                all_adjustments = list(all_result.scalars().all())
                                
                                # Фильтруем и разделяем корректировки
                                already_applied_adjustments = []
                                new_adjustments = []
                                
                                for adj in all_adjustments:
                                    # Сбрасываем статус "зависших"
                                    if adj.is_applied and adj.payroll_entry_id is None:
                                        adj.is_applied = False
                                        adj.payroll_entry_id = None
                                    
                                    # Фильтр по объекту
                                    if adj.adjustment_type == 'shift_base':
                                        if adj.object_id != obj.id:
                                            continue
                                    
                                    # Разделяем
                                    if existing_entry and adj.is_applied and adj.payroll_entry_id == existing_entry.id:
                                        already_applied_adjustments.append(adj)
                                    else:
                                        new_adjustments.append(adj)
                                
                                # Flush изменений
                                if new_adjustments:
                                    await session.flush()
                                
                                # Пропускаем если нет корректировок
                                if not new_adjustments and not already_applied_adjustments:
                                    logger.debug(
                                        f"No adjustments for individual contract employee",
                                        employee_id=contract.employee_id,
                                        object_id=obj.id
                                    )
                                    continue
                                
                                # ПЕРЕСЧИТЫВАЕМ с использованием ВСЕХ корректировок
                                all_relevant_adjustments = already_applied_adjustments + new_adjustments
                                
                                gross_amount = Decimal('0.00')
                                total_bonuses = Decimal('0.00')
                                total_deductions = Decimal('0.00')
                                total_hours = Decimal('0.00')
                                
                                for adj in all_relevant_adjustments:
                                    amount = Decimal(str(adj.amount))
                                    
                                    if adj.adjustment_type == 'shift_base':
                                        gross_amount += amount
                                        # Извлекаем часы из details если есть
                                        if adj.details and 'hours' in adj.details:
                                            hours = Decimal(str(adj.details['hours']))
                                            total_hours += hours
                                    elif adj.adjustment_type in ['task_bonus', 'manual_bonus', 'incident_refund']:
                                        total_bonuses += amount
                                    elif adj.adjustment_type in ['task_penalty', 'manual_deduction', 'incident_deduction', 'late_start']:
                                        total_deductions += abs(amount)
                                
                                net_amount = gross_amount + total_bonuses - total_deductions
                                avg_hourly_rate = (gross_amount / total_hours) if total_hours > 0 else Decimal('0.00')
                                
                                calculation_details = {
                                    "adjustments": [
                                        {
                                            "id": adj.id,
                                            "type": adj.adjustment_type,
                                            "amount": float(adj.amount),
                                            "description": adj.description
                                        }
                                        for adj in all_relevant_adjustments
                                    ]
                                }
                                
                                if not existing_entry:
                                    # СОЗДАЁМ новое начисление
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
                                        calculation_details=calculation_details
                                    )
                                    
                                    session.add(payroll_entry)
                                    await session.flush()
                                    
                                    # Применяем ТОЛЬКО новые корректировки
                                    if new_adjustments:
                                        new_adjustment_ids = [adj.id for adj in new_adjustments]
                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                            adjustment_ids=new_adjustment_ids,
                                            payroll_entry_id=payroll_entry.id
                                        )
                                    else:
                                        applied_count = 0
                                    
                                    total_entries_created += 1
                                    total_adjustments_applied += applied_count
                                    
                                    logger.info(
                                        f"Created payroll entry for individual schedule contract",
                                        payroll_entry_id=payroll_entry.id,
                                        employee_id=contract.employee_id,
                                        object_id=obj.id,
                                        schedule_id=schedule.id,
                                        gross_amount=float(gross_amount),
                                        net_amount=float(net_amount),
                                        adjustments_count=applied_count
                                    )
                                else:
                                    # ОБНОВЛЯЕМ существующее начисление
                                    existing_entry.gross_amount = float(gross_amount)
                                    existing_entry.total_bonuses = float(total_bonuses)
                                    existing_entry.total_deductions = float(total_deductions)
                                    existing_entry.net_amount = float(net_amount)
                                    existing_entry.hours_worked = float(total_hours)
                                    existing_entry.hourly_rate = float(avg_hourly_rate)
                                    existing_entry.calculation_details = calculation_details
                                    
                                    # Применяем ТОЛЬКО новые корректировки
                                    if new_adjustments:
                                        new_adjustment_ids = [adj.id for adj in new_adjustments]
                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                            adjustment_ids=new_adjustment_ids,
                                            payroll_entry_id=existing_entry.id
                                        )
                                    else:
                                        applied_count = 0
                                    
                                    total_entries_updated += 1
                                    total_adjustments_applied += applied_count
                                    
                                    logger.info(
                                        f"Updated payroll entry for individual schedule contract",
                                        payroll_entry_id=existing_entry.id,
                                        employee_id=contract.employee_id,
                                        object_id=obj.id,
                                        schedule_id=schedule.id,
                                        gross_amount=float(gross_amount),
                                        net_amount=float(net_amount),
                                        adjustments_count=applied_count
                                    )
                                
                            except Exception as e:
                                error_msg = f"Error creating payroll entry for individual contract {contract.id}: {e}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                continue
                        
                    except Exception as e:
                        error_msg = f"Error processing schedule {schedule.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Сохраняем все изменения
                await session.commit()
                
                logger.info(
                    f"Payroll entries creation completed",
                    entries_created=total_entries_created,
                    entries_updated=total_entries_updated,
                    adjustments_applied=total_adjustments_applied,
                    errors_count=len(errors)
                )
                
                return {
                    'success': True,
                    'date': today.isoformat(),
                    'entries_created': total_entries_created,
                    'entries_updated': total_entries_updated,
                    'adjustments_applied': total_adjustments_applied,
                    'errors': errors
                }
                
        except Exception as e:
            logger.error(f"Critical error in payroll entries task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())




@celery_app.task(name="create_final_settlements_by_termination_date")
def create_final_settlements_by_termination_date():
    """
    Создаёт финальные расчёты для сотрудников в дату увольнения.
    
    Запускается ежедневно в 01:05.
    
    Логика:
    1. Находит все договоры с termination_date = сегодня и settlement_policy = 'termination_date'
    2. Для каждого договора:
       - Получает все неприменённые adjustments до даты увольнения (включительно)
       - Создаёт PayrollEntry
       - Проставляет payroll_entry_id и is_applied=TRUE у adjustments
    """
    
    async def process():
        try:
            today = date.today()
            logger.info(f"Starting final settlements for termination_date={today}")
            
            async with get_async_session() as session:
                # 1. Найти все контракты с termination_date=сегодня и settlement_policy='termination_date'
                contracts_query = select(Contract).where(
                    Contract.status == 'terminated',
                    Contract.settlement_policy == 'termination_date',
                    Contract.termination_date == today
                )
                contracts_result = await session.execute(contracts_query)
                contracts = contracts_result.scalars().all()
                
                logger.info(f"Found {len(contracts)} contracts for final settlement")
                
                total_entries_created = 0
                total_adjustments_applied = 0
                errors = []
                
                for contract in contracts:
                    try:
                        # 2. Получить все неприменённые adjustments до даты увольнения
                        adjustment_service = PayrollAdjustmentService(session)
                        adjustments = await adjustment_service.get_unapplied_adjustments_until(
                            employee_id=contract.employee_id,
                            until_date=today
                        )
                        
                        if not adjustments:
                            logger.debug(
                                f"No adjustments for final settlement",
                                employee_id=contract.employee_id,
                                termination_date=today
                            )
                            continue
                        
                        # Рассчитать итоговые суммы и часы
                        gross_amount = Decimal('0.00')
                        total_bonuses = Decimal('0.00')
                        total_deductions = Decimal('0.00')
                        total_hours = Decimal('0.00')
                        avg_hourly_rate = Decimal('0.00')
                        
                        shift_adjustments = []
                        for adj in adjustments:
                            amount_decimal = Decimal(str(adj.amount))
                            
                            if adj.adjustment_type == 'shift_base':
                                gross_amount += amount_decimal
                                shift_adjustments.append(adj)
                            elif amount_decimal > 0:
                                total_bonuses += amount_decimal
                            else:
                                total_deductions += abs(amount_decimal)
                        
                        # Получить часы и ставку из смен
                        if shift_adjustments:
                            from domain.entities.shift import Shift
                            shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]
                            if shift_ids:
                                shifts_result = await session.execute(
                                    select(Shift).where(Shift.id.in_(shift_ids))
                                )
                                shifts = shifts_result.scalars().all()
                                for shift in shifts:
                                    if shift.total_hours:
                                        total_hours += Decimal(str(shift.total_hours))
                                    if shift.hourly_rate:
                                        avg_hourly_rate = Decimal(str(shift.hourly_rate))
                        
                        # Если нет часов, попытаться рассчитать
                        if total_hours == 0 and gross_amount > 0 and avg_hourly_rate > 0:
                            total_hours = gross_amount / avg_hourly_rate
                        
                        # Получить object_id из первого adjustment с object_id
                        object_id = next((adj.object_id for adj in adjustments if adj.object_id), None)
                        
                        # Если всё ещё нет ставки, взять из объекта
                        if avg_hourly_rate == 0 and object_id:
                            obj_result = await session.execute(
                                select(Object).where(Object.id == object_id)
                            )
                            obj = obj_result.scalar_one_or_none()
                            if obj and obj.hourly_rate:
                                avg_hourly_rate = Decimal(str(obj.hourly_rate))
                        
                        net_amount = gross_amount + total_bonuses - total_deductions
                        
                        # Создать PayrollEntry
                        payroll_entry = PayrollEntry(
                            employee_id=contract.employee_id,
                            contract_id=contract.id,
                            object_id=object_id,
                            period_start=None,  # Для финрасчёта период не указываем
                            period_end=today,
                            hours_worked=float(total_hours),
                            hourly_rate=float(avg_hourly_rate) if avg_hourly_rate else 0.0,
                            gross_amount=float(gross_amount),
                            total_bonuses=float(total_bonuses),
                            total_deductions=float(total_deductions),
                            net_amount=float(net_amount)
                        )
                        
                        session.add(payroll_entry)
                        await session.flush()
                        
                        # Отметить adjustments как применённые
                        adjustment_ids = [adj.id for adj in adjustments]
                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                            adjustment_ids=adjustment_ids,
                            payroll_entry_id=payroll_entry.id
                        )
                        
                        total_entries_created += 1
                        total_adjustments_applied += applied_count
                        
                        logger.info(
                            f"Created final settlement entry",
                            payroll_entry_id=payroll_entry.id,
                            employee_id=contract.employee_id,
                            termination_date=today,
                            gross_amount=float(gross_amount),
                            net_amount=float(net_amount),
                            adjustments_count=applied_count
                        )
                        
                    except Exception as e:
                        error_msg = f"Error creating final settlement for contract {contract.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
                
                # Сохраняем все изменения
                await session.commit()
                
                logger.info(
                    f"Final settlements completed",
                    entries_created=total_entries_created,
                    adjustments_applied=total_adjustments_applied,
                    errors_count=len(errors)
                )
                
                return {
                    'success': True,
                    'date': today.isoformat(),
                    'entries_created': total_entries_created,
                    'adjustments_applied': total_adjustments_applied,
                    'errors': errors
                }
                
        except Exception as e:
            logger.error(f"Critical error in final settlements task: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # Запускаем async функцию в event loop
    return asyncio.run(process())
