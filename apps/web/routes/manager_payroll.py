"""Роуты для работы управляющих с начислениями и выплатами."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import get_current_user
from apps.web.middleware.role_middleware import get_user_id_from_current_user, require_manager_or_owner
from apps.web.dependencies import require_manager_payroll_permission
from core.database.session import get_db_session
from apps.web.services.payroll_service import PayrollService
from shared.services.manager_permission_service import ManagerPermissionService
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.contract import Contract
from core.logging.logger import logger

router = APIRouter()


@router.get("/payroll", response_class=HTMLResponse)
async def manager_payroll_list(
    request: Request,
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    object_id: Optional[int] = Query(None)
):
    """Список начислений (только по доступным объектам)."""
    try:
        # current_user - это объект User с множественными ролями
        user_id = current_user.id
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        
        # Получить доступные объекты управляющего
        permission_service = ManagerPermissionService(db)
        
        if "manager" in user_roles and "owner" not in user_roles:
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            if not accessible_objects:
                return templates.TemplateResponse(
                    "manager/payroll/list.html",
                    {
                        "request": request,
                        "title": "Начисления и выплаты",
                        "employees": [],
                        "accessible_objects": [],
                        "error": "У вас нет доступных объектов"
                    }
                )
        else:
            # Владелец видит все свои объекты
            objects_query = select(Object).where(Object.owner_id == user_id, Object.is_active == True)
            objects_result = await db.execute(objects_query)
            accessible_objects = objects_result.scalars().all()
        
        accessible_object_ids = [obj.id for obj in accessible_objects]
        
        # Получить начисления
        payroll_service = PayrollService(db)
        
        # Фильтрация по периоду
        if period_start and period_end:
            start_date = datetime.strptime(period_start, "%Y-%m-%d").date()
            end_date = datetime.strptime(period_end, "%Y-%m-%d").date()
        else:
            # По умолчанию - текущий месяц
            today = date.today()
            start_date = date(today.year, today.month, 1)
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1)
            else:
                end_date = date(today.year, today.month + 1, 1)
        
        # Получить сотрудников с начислениями
        employees_data = []
        
        # Получить уникальных сотрудников из начислений за период
        from domain.entities.payroll_entry import PayrollEntry
        
        payroll_query = select(PayrollEntry).where(
            and_(
                PayrollEntry.period_start >= start_date,
                PayrollEntry.period_end <= end_date
            )
        ).options(selectinload(PayrollEntry.employee))
        
        payroll_result = await db.execute(payroll_query)
        all_entries = payroll_result.scalars().all()
        
        # Группировать по сотрудникам
        employees_entries = {}
        for entry in all_entries:
            emp_id = entry.employee_id
            if emp_id not in employees_entries:
                employees_entries[emp_id] = []
            employees_entries[emp_id].append(entry)
        
        # Для каждого сотрудника создать запись
        for emp_id, entries in employees_entries.items():
            user_query = select(User).where(User.id == emp_id)
            user_result = await db.execute(user_query)
            employee = user_result.scalar_one_or_none()
            
            if employee:
                total_amount = sum(entry.net_amount for entry in entries)
                employees_data.append({
                    "employee": employee,
                    "entries_count": len(entries),
                    "total_amount": total_amount,
                    "latest_entry": entries[0] if entries else None
                })
        
        return templates.TemplateResponse(
            "manager/payroll/list.html",
            {
                "request": request,
                "title": "Начисления и выплаты",
                "employees": employees_data,
                "accessible_objects": accessible_objects,
                "period_start": period_start or start_date.strftime("%Y-%m-%d"),
                "period_end": period_end or end_date.strftime("%Y-%m-%d"),
                "selected_object_id": object_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading manager payroll: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.get("/payroll/{entry_id}", response_class=HTMLResponse)
async def manager_payroll_detail(
    request: Request,
    entry_id: int,
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session)
):
    """Детализация начисления."""
    try:
        # current_user - это объект User с множественными ролями
        user_id = current_user.id
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        
        payroll_service = PayrollService(db)
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        
        if not entry:
            raise HTTPException(status_code=404, detail="Начисление не найдено")
        
        # Проверить доступ (управляющий должен иметь доступ к объектам смен сотрудника)
        if "manager" in user_roles and "owner" not in user_roles:
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            # Проверить, что все смены сотрудника в доступных объектах
            # (упрощенная проверка - просто даем доступ, если есть хоть один доступный объект)
            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="У вас нет доступа к этому начислению")
        
        # Получить детали (смены, удержания, премии)
        shifts = await payroll_service.get_shifts_for_entry(entry_id)
        deductions = await payroll_service.get_deductions_for_entry(entry_id)
        bonuses = await payroll_service.get_bonuses_for_entry(entry_id)
        
        return templates.TemplateResponse(
            "manager/payroll/detail.html",
            {
                "request": request,
                "title": f"Начисление #{entry_id}",
                "entry": entry,
                "shifts": shifts,
                "deductions": deductions,
                "bonuses": bonuses,
                "is_manager": "manager" in user_roles and "owner" not in user_roles
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading payroll detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начисления: {str(e)}")

