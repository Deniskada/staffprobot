"""Роуты для работы с начислениями и выплатами."""

from datetime import date, timedelta, datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import get_current_user, require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.database.session import get_db_session
from core.logging.logger import logger
from apps.web.services.payroll_service import PayrollService
from domain.entities.user import User
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.contract import Contract
from domain.entities.shift import Shift
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.payment_schedule import PaymentSchedule
from domain.entities.object import Object
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import cast

router = APIRouter()


async def get_user_id_from_current_user(current_user: dict, session: AsyncSession) -> Optional[int]:
    """Получает внутренний ID пользователя из current_user (JWT payload)."""
    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    user_query = select(User).where(User.telegram_id == telegram_id)
    user_result = await session.execute(user_query)
    user_obj = user_result.scalar_one_or_none()
    return user_obj.id if user_obj else None


@router.get("/payroll", response_class=HTMLResponse, name="owner_payroll_list")
async def owner_payroll_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    employee_id: Optional[int] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
):
    """Список всех начислений."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Получить всех сотрудников владельца
        query = select(User).join(Contract, Contract.employee_id == User.id).where(
            Contract.owner_id == owner_id,
            Contract.status == 'active'
        ).distinct()
        result = await db.execute(query)
        employees = result.scalars().all()
        
        # Фильтры по дате
        if not period_start:
            period_start = (date.today() - timedelta(days=30)).isoformat()
        if not period_end:
            period_end = date.today().isoformat()
        
        # Получить начисления
        if employee_id:
            entries = await payroll_service.get_payroll_entries_by_employee(
                employee_id=employee_id,
                period_start=date.fromisoformat(period_start),
                period_end=date.fromisoformat(period_end)
            )
        else:
            # Получить начисления для всех сотрудников
            entries = []
            for emp in employees:
                emp_entries = await payroll_service.get_payroll_entries_by_employee(
                    employee_id=emp.id,
                    period_start=date.fromisoformat(period_start),
                    period_end=date.fromisoformat(period_end),
                    limit=50
                )
                entries.extend(emp_entries)
            
            # Сортировать по дате
            entries.sort(key=lambda e: e.period_end, reverse=True)
        
        return templates.TemplateResponse(
            "owner/payroll/list.html",
            {
                "request": request,
                "current_user": current_user,
                "entries": entries,
                "employees": employees,
                "selected_employee_id": employee_id,
                "period_start": period_start,
                "period_end": period_end
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading payroll list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.get("/payroll/{entry_id}", response_class=HTMLResponse, name="owner_payroll_detail")
async def owner_payroll_detail(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детальная страница начисления."""
    try:
        payroll_service = PayrollService(db)
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ: владелец должен быть owner этого сотрудника
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == owner_id
        )
        result = await db.execute(query)
        owner_contracts = result.scalars().all()
        
        if not owner_contracts:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Получить связанные adjustments (для старого шаблона - как deductions, bonuses)
        from domain.entities.payroll_adjustment import PayrollAdjustment
        from sqlalchemy.orm import selectinload
        adjustments_query = select(PayrollAdjustment).where(
            PayrollAdjustment.payroll_entry_id == entry_id
        ).options(
            selectinload(PayrollAdjustment.creator),
            selectinload(PayrollAdjustment.updater)
        ).order_by(PayrollAdjustment.created_at)
        adjustments_result = await db.execute(adjustments_query)
        adjustments = adjustments_result.scalars().all()
        
        # Разделить на deductions и bonuses для совместимости со старым шаблоном
        deductions = [adj for adj in adjustments if float(adj.amount) < 0]
        bonuses = [adj for adj in adjustments if float(adj.amount) > 0 and adj.adjustment_type != 'shift_base']
        
        # Получить выплаты (payments)
        from domain.entities.employee_payment import EmployeePayment
        payments_query = select(EmployeePayment).where(
            EmployeePayment.payroll_entry_id == entry_id
        ).order_by(EmployeePayment.payment_date)
        payments_result = await db.execute(payments_query)
        payments = payments_result.scalars().all()
        
        return templates.TemplateResponse(
            "owner/payroll/detail.html",
            {
                "request": request,
                "current_user": current_user,
                "entry": entry,
                "deductions": deductions,
                "bonuses": bonuses,
                "payments": payments,
                "today": date.today()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading payroll detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начисления: {str(e)}")


@router.post("/payroll/{entry_id}/add-deduction", name="owner_payroll_add_deduction")
async def owner_payroll_add_deduction(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    deduction_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(...)
):
    """Добавить удержание к начислению."""
    try:
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        
        payroll_service = PayrollService(db)
        adjustment_service = PayrollAdjustmentService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == owner_id
        )
        result = await db.execute(query)
        owner_contracts = result.scalars().all()
        
        if not owner_contracts:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Добавить удержание через PayrollAdjustmentService
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=entry.employee_id,
            amount=-abs(Decimal(str(amount))),  # Отрицательное для удержания
            adjustment_type='manual_deduction',
            description=description,
            created_by=owner_id,
            object_id=entry.object_id
        )
        
        # Привязать к payroll_entry
        adjustment.payroll_entry_id = entry_id
        adjustment.is_applied = True
        
        # Пересчитать суммы в entry (все в Decimal)
        entry.total_deductions = Decimal(str(entry.total_deductions)) + abs(Decimal(str(amount)))
        entry.net_amount = Decimal(str(entry.gross_amount)) + Decimal(str(entry.total_bonuses)) - Decimal(str(entry.total_deductions))
        
        await db.commit()
        
        logger.info(
            f"Deduction added by owner",
            entry_id=entry_id,
            amount=amount,
            type=deduction_type
        )
        
        return RedirectResponse(
            url=f"/owner/payroll/{entry_id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding deduction: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка добавления удержания: {str(e)}")


@router.post("/payroll/{entry_id}/add-bonus", name="owner_payroll_add_bonus")
async def owner_payroll_add_bonus(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    bonus_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(...)
):
    """Добавить доплату к начислению."""
    try:
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        
        payroll_service = PayrollService(db)
        adjustment_service = PayrollAdjustmentService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == owner_id
        )
        result = await db.execute(query)
        owner_contracts = result.scalars().all()
        
        if not owner_contracts:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Добавить доплату через PayrollAdjustmentService
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=entry.employee_id,
            amount=abs(Decimal(str(amount))),  # Положительное для бонуса
            adjustment_type='manual_bonus',
            description=description,
            created_by=owner_id,
            object_id=entry.object_id
        )
        
        # Привязать к payroll_entry
        adjustment.payroll_entry_id = entry_id
        adjustment.is_applied = True
        
        # Пересчитать суммы в entry (все в Decimal)
        entry.total_bonuses = Decimal(str(entry.total_bonuses)) + abs(Decimal(str(amount)))
        entry.net_amount = Decimal(str(entry.gross_amount)) + Decimal(str(entry.total_bonuses)) - Decimal(str(entry.total_deductions))
        
        await db.commit()
        
        logger.info(
            f"Bonus added by owner",
            entry_id=entry_id,
            amount=amount,
            type=bonus_type
        )
        
        return RedirectResponse(
            url=f"/owner/payroll/{entry_id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding bonus: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка добавления доплаты: {str(e)}")


@router.post("/payroll/{entry_id}/payments/{payment_id}/complete", name="owner_payment_complete")
async def complete_payment(
    request: Request,
    entry_id: int,
    payment_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    confirmation_code: Optional[str] = Form(None)
):
    """Подтвердить выплату."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ к entry
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == owner_id
        )
        result = await db.execute(query)
        owner_contracts = result.scalars().all()
        
        if not owner_contracts:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Подтвердить выплату
        await payroll_service.mark_payment_completed(
            payment_id=payment_id,
            confirmation_code=confirmation_code
        )
        
        logger.info(
            f"Payment completed by owner",
            payment_id=payment_id,
            entry_id=entry_id,
            confirmation_code=confirmation_code
        )
        
        return RedirectResponse(
            url=f"/owner/payroll/{entry_id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing payment: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка подтверждения выплаты: {str(e)}")


@router.post("/payroll/{entry_id}/create-payment", name="owner_payroll_create_payment")
async def owner_payroll_create_payment(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    amount: float = Form(...),
    payment_date: str = Form(...),
    payment_method: str = Form(...),
    notes: Optional[str] = Form(None)
):
    """Создать выплату для начисления."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == owner_id
        )
        result = await db.execute(query)
        owner_contracts = result.scalars().all()
        
        if not owner_contracts:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Создать выплату
        await payroll_service.create_payment(
            payroll_entry_id=entry_id,
            amount=Decimal(str(amount)),
            payment_date=date.fromisoformat(payment_date),
            payment_method=payment_method,
            created_by_id=owner_id,
            notes=notes
        )
        
        logger.info(
            f"Payment created by owner",
            entry_id=entry_id,
            amount=amount,
            method=payment_method
        )
        
        return RedirectResponse(
            url=f"/owner/payroll/{entry_id}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания выплаты: {str(e)}")


@router.post("/payroll/manual-recalculate", response_class=JSONResponse, name="owner_payroll_manual_recalculate")
async def owner_payroll_manual_recalculate(
    request: Request,
    target_date: str = Form(...),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Ручной запуск пересчёта выплат на указанную дату (идемпотентно)."""
    try:
        # Парсинг даты
        try:
            target_date_obj = date.fromisoformat(target_date)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Неверный формат даты"}
            )
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Пользователь не найден"}
            )
        
        logger.info(
            f"Manual payroll recalculation started",
            owner_id=owner_id,
            target_date=target_date_obj.isoformat()
        )
        
        # Импорт функции для расчёта периода
        from core.celery.tasks.payroll_tasks import _get_payment_period_for_date
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        
        # Найти все активные payment_schedules владельца
        schedules_query = select(PaymentSchedule).where(
            PaymentSchedule.owner_id == owner_id,
            PaymentSchedule.is_active == True
        )
        schedules_result = await db.execute(schedules_query)
        schedules = schedules_result.scalars().all()
        
        logger.info(f"Found {len(schedules)} active schedules for owner {owner_id}")
        
        total_entries_created = 0
        total_entries_updated = 0
        total_adjustments_applied = 0
        errors = []
        
        for schedule in schedules:
            try:
                # Проверяем, является ли target_date днём выплаты
                payment_period = await _get_payment_period_for_date(schedule, target_date_obj)
                
                if not payment_period:
                    logger.debug(
                        f"Skip schedule {schedule.id}: target date is not a payment day",
                        schedule_id=schedule.id,
                        target_date=target_date_obj.isoformat()
                    )
                    continue
                
                period_start = payment_period['period_start']
                period_end = payment_period['period_end']
                
                logger.info(
                    f"Manual recalculation for schedule {schedule.id}: {schedule.name}",
                    period_start=period_start.isoformat(),
                    period_end=period_end.isoformat()
                )
                
                # Найти все объекты владельца
                objects_query = select(Object).where(
                    Object.is_active == True,
                    Object.owner_id == owner_id
                )
                objects_result = await db.execute(objects_query)
                objects = objects_result.scalars().all()
                
                logger.info(f"Found {len(objects)} objects for owner {owner_id}")
                
                for obj in objects:
                    try:
                        # Найти контракты
                        contracts_query = select(Contract).where(
                            and_(
                                Contract.allowed_objects.isnot(None),
                                cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj.id], JSONB)),
                                or_(
                                    and_(Contract.status == 'active', Contract.is_active == True),
                                    and_(
                                        Contract.status == 'terminated',
                                        Contract.settlement_policy == 'schedule'
                                    )
                                )
                            )
                        )
                        contracts_result = await db.execute(contracts_query)
                        contracts = contracts_result.scalars().all()
                        
                        logger.debug(f"Found {len(contracts)} contracts for object {obj.id}")
                        
                        for contract in contracts:
                            try:
                                adjustment_service = PayrollAdjustmentService(db)
                                
                                # Получить неприменённые adjustments за период
                                adjustments = await adjustment_service.get_unapplied_adjustments(
                                    employee_id=contract.employee_id,
                                    period_start=period_start,
                                    period_end=period_end
                                )
                                
                                if not adjustments:
                                    logger.debug(
                                        f"No unapplied adjustments for employee",
                                        employee_id=contract.employee_id,
                                        period_start=period_start,
                                        period_end=period_end
                                    )
                                    continue
                                
                                # Проверить, существует ли уже начисление за этот период
                                existing_entry_query = select(PayrollEntry).where(
                                    PayrollEntry.employee_id == contract.employee_id,
                                    PayrollEntry.period_start == period_start,
                                    PayrollEntry.period_end == period_end,
                                    PayrollEntry.object_id == obj.id
                                )
                                existing_entry_result = await db.execute(existing_entry_query)
                                existing_entry = existing_entry_result.scalar_one_or_none()
                                
                                # Рассчитать суммы
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
                                    shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]
                                    if shift_ids:
                                        shifts_result = await db.execute(
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
                                
                                # Если всё ещё нет ставки, взять из объекта
                                if avg_hourly_rate == 0:
                                    avg_hourly_rate = Decimal(str(obj.hourly_rate)) if obj.hourly_rate else Decimal('200.00')
                                
                                net_amount = gross_amount + total_bonuses - total_deductions
                                
                                if existing_entry:
                                    # ОБНОВЛЯЕМ существующее начисление
                                    # Сначала сбросим все старые adjustments этого entry
                                    old_adjustments_query = select(PayrollAdjustment).where(
                                        PayrollAdjustment.payroll_entry_id == existing_entry.id,
                                        PayrollAdjustment.is_applied == True
                                    )
                                    old_adjustments_result = await db.execute(old_adjustments_query)
                                    old_adjustments = old_adjustments_result.scalars().all()
                                    
                                    for old_adj in old_adjustments:
                                        old_adj.payroll_entry_id = None
                                        old_adj.is_applied = False
                                    
                                    # Обновляем суммы в entry
                                    existing_entry.hours_worked = float(total_hours)
                                    existing_entry.hourly_rate = float(avg_hourly_rate)
                                    existing_entry.gross_amount = float(gross_amount)
                                    existing_entry.total_bonuses = float(total_bonuses)
                                    existing_entry.total_deductions = float(total_deductions)
                                    existing_entry.net_amount = float(net_amount)
                                    
                                    # Применяем adjustments заново
                                    adjustment_ids = [adj.id for adj in adjustments]
                                    applied_count = await adjustment_service.mark_adjustments_as_applied(
                                        adjustment_ids=adjustment_ids,
                                        payroll_entry_id=existing_entry.id
                                    )
                                    
                                    total_entries_updated += 1
                                    total_adjustments_applied += applied_count
                                    
                                    logger.info(
                                        f"Updated existing payroll entry",
                                        payroll_entry_id=existing_entry.id,
                                        employee_id=contract.employee_id,
                                        adjustments_count=applied_count
                                    )
                                    
                                else:
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
                                        created_by_id=owner_id
                                    )
                                    
                                    db.add(payroll_entry)
                                    await db.flush()
                                    
                                    # Применяем adjustments
                                    adjustment_ids = [adj.id for adj in adjustments]
                                    applied_count = await adjustment_service.mark_adjustments_as_applied(
                                        adjustment_ids=adjustment_ids,
                                        payroll_entry_id=payroll_entry.id
                                    )
                                    
                                    total_entries_created += 1
                                    total_adjustments_applied += applied_count
                                    
                                    logger.info(
                                        f"Created new payroll entry",
                                        payroll_entry_id=payroll_entry.id,
                                        employee_id=contract.employee_id,
                                        adjustments_count=applied_count
                                    )
                                
                            except Exception as e:
                                error_msg = f"Error processing contract {contract.id}: {e}"
                                logger.error(error_msg)
                                errors.append(error_msg)
                                continue
                    
                    except Exception as e:
                        error_msg = f"Error processing object {obj.id}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        continue
            
            except Exception as e:
                error_msg = f"Error processing schedule {schedule.id}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Commit всех изменений
        await db.commit()
        
        logger.info(
            f"Manual payroll recalculation completed",
            owner_id=owner_id,
            target_date=target_date_obj.isoformat(),
            entries_created=total_entries_created,
            entries_updated=total_entries_updated,
            adjustments_applied=total_adjustments_applied,
            errors_count=len(errors)
        )
        
        return JSONResponse(content={
            "success": True,
            "target_date": target_date_obj.isoformat(),
            "entries_created": total_entries_created,
            "entries_updated": total_entries_updated,
            "adjustments_applied": total_adjustments_applied,
            "errors": errors
        })
        
    except Exception as e:
        logger.error(f"Error in manual payroll recalculation: {e}")
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ==================== EMPLOYEE ROUTES ====================


@router.get("/employee/payroll", response_class=HTMLResponse, name="employee_payroll_list")
async def employee_payroll_list(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session),
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
):
    """Список начислений для сотрудника."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID сотрудника
        employee_id = await get_user_id_from_current_user(current_user, db)
        if not employee_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Фильтры по дате
        if not period_start:
            period_start = (date.today() - timedelta(days=90)).isoformat()
        if not period_end:
            period_end = date.today().isoformat()
        
        # Получить начисления текущего сотрудника
        entries = await payroll_service.get_payroll_entries_by_employee(
            employee_id=employee_id,
            period_start=date.fromisoformat(period_start),
            period_end=date.fromisoformat(period_end)
        )
        
        # Рассчитать сводку
        summary = await payroll_service.get_employee_payroll_summary(
            employee_id=employee_id,
            period_start=date.fromisoformat(period_start),
            period_end=date.fromisoformat(period_end)
        )
        
        return templates.TemplateResponse(
            "employee/payroll/list.html",
            {
                "request": request,
                "current_user": current_user,
                "entries": entries,
                "summary": summary,
                "period_start": period_start,
                "period_end": period_end
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading employee payroll list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.get("/employee/payroll/{entry_id}", response_class=HTMLResponse, name="employee_payroll_detail")
async def employee_payroll_detail(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Детальная страница начисления для сотрудника."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID сотрудника
        employee_id = await get_user_id_from_current_user(current_user, db)
        if not employee_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        # Проверить доступ: сотрудник может видеть только свои начисления
        if entry.employee_id != employee_id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        return templates.TemplateResponse(
            "employee/payroll/detail.html",
            {
                "request": request,
                "current_user": current_user,
                "entry": entry
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading employee payroll detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начисления: {str(e)}")

