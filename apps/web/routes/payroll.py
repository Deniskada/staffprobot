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
        
        # Получить всех сотрудников владельца
        query = select(User).join(Contract).where(
            Contract.owner_id == current_user['id'],
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
        
        # Проверить доступ: владелец должен быть owner этого сотрудника
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == current_user['id']
        )
        result = await db.execute(query)
        owner_contract = result.scalar_one_or_none()
        
        if not owner_contract:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        return templates.TemplateResponse(
            "owner/payroll/detail.html",
            {
                "request": request,
                "current_user": current_user,
                "entry": entry
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
        payroll_service = PayrollService(db)
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == current_user['id']
        )
        result = await db.execute(query)
        owner_contract = result.scalar_one_or_none()
        
        if not owner_contract:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Добавить удержание
        await payroll_service.add_deduction(
            payroll_entry_id=entry_id,
            deduction_type=deduction_type,
            amount=Decimal(str(amount)),
            description=description,
            is_automatic=False,
            created_by_id=current_user['id']
        )
        
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
        payroll_service = PayrollService(db)
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == current_user['id']
        )
        result = await db.execute(query)
        owner_contract = result.scalar_one_or_none()
        
        if not owner_contract:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Добавить доплату
        await payroll_service.add_bonus(
            payroll_entry_id=entry_id,
            bonus_type=bonus_type,
            amount=Decimal(str(amount)),
            description=description,
            created_by_id=current_user['id']
        )
        
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
        
        # Проверить доступ
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        query = select(Contract).where(
            Contract.employee_id == entry.employee_id,
            Contract.owner_id == current_user['id']
        )
        result = await db.execute(query)
        owner_contract = result.scalar_one_or_none()
        
        if not owner_contract:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Создать выплату
        await payroll_service.create_payment(
            payroll_entry_id=entry_id,
            amount=Decimal(str(amount)),
            payment_date=date.fromisoformat(payment_date),
            payment_method=payment_method,
            created_by_id=current_user['id'],
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
        
        # Фильтры по дате
        if not period_start:
            period_start = (date.today() - timedelta(days=90)).isoformat()
        if not period_end:
            period_end = date.today().isoformat()
        
        # Получить начисления текущего сотрудника
        entries = await payroll_service.get_payroll_entries_by_employee(
            employee_id=current_user['id'],
            period_start=date.fromisoformat(period_start),
            period_end=date.fromisoformat(period_end)
        )
        
        # Рассчитать сводку
        summary = await payroll_service.get_employee_payroll_summary(
            employee_id=current_user['id'],
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
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        # Проверить доступ: сотрудник может видеть только свои начисления
        if entry.employee_id != current_user['id']:
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

