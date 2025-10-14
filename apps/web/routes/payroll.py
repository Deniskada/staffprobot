"""Роуты для работы с начислениями и выплатами."""

from datetime import date, timedelta, datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import get_current_user, require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_employee_or_applicant
from core.database.session import get_db_session
from core.logging.logger import logger
from apps.web.services.payroll_service import PayrollService
from domain.entities.user import User
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.contract import Contract

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
        adjustments_query = select(PayrollAdjustment).where(
            PayrollAdjustment.payroll_entry_id == entry_id
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
        
        # Пересчитать суммы в entry
        entry.total_deductions = float(entry.total_deductions) + abs(float(amount))
        entry.net_amount = entry.gross_amount + entry.total_bonuses - entry.total_deductions
        
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
        
        # Пересчитать суммы в entry
        entry.total_bonuses = float(entry.total_bonuses) + abs(float(amount))
        entry.net_amount = entry.gross_amount + entry.total_bonuses - entry.total_deductions
        
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

