"""Роуты для работы управляющих с начислениями и выплатами."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import date, datetime, timedelta
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
    object_id: Optional[str] = Query(None)  # Изменено на str для обработки пустых значений
):
    """Список начислений (только по доступным объектам)."""
    try:
        # Конвертация object_id в int, игнорируя пустые строки
        object_id_int = None
        if object_id and object_id.strip():
            try:
                object_id_int = int(object_id)
            except ValueError:
                pass
        
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
                        "current_user": current_user,
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
            # По умолчанию - последние 60 дней (чтобы показать хоть какие-то начисления)
            today = date.today()
            start_date = today - timedelta(days=60)
            end_date = today
        
        # Получить сотрудников с начислениями
        employees_data = []
        
        # Получить уникальных сотрудников из начислений за период
        from domain.entities.payroll_entry import PayrollEntry
        
        # Фильтр по объекту (если указан)
        if object_id_int and object_id_int in accessible_object_ids:
            object_filter = PayrollEntry.object_id == object_id_int
        else:
            object_filter = PayrollEntry.object_id.in_(accessible_object_ids)
        
        payroll_query = select(PayrollEntry).where(
            and_(
                PayrollEntry.period_start >= start_date,
                PayrollEntry.period_end <= end_date,
                object_filter  # Фильтр по доступным объектам
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
        
        logger.info(f"Manager payroll: found {len(employees_data)} employees, {len(accessible_objects)} accessible objects")
        
        # Получаем контекст управляющего
        from apps.web.routes.manager import get_manager_context
        manager_context = await get_manager_context(user_id, db)
        
        return templates.TemplateResponse(
            "manager/payroll/list.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Выплаты",
                "employees": employees_data,
                "accessible_objects": accessible_objects,
                "period_start": period_start or start_date.strftime("%Y-%m-%d"),
                "period_end": period_end or end_date.strftime("%Y-%m-%d"),
                "selected_object_id": object_id_int,
                **manager_context
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
        
        # Получить связанные adjustments
        from domain.entities.payroll_adjustment import PayrollAdjustment
        from sqlalchemy.orm import selectinload
        adjustments_query = select(PayrollAdjustment).where(
            PayrollAdjustment.payroll_entry_id == entry_id
        ).options(
            selectinload(PayrollAdjustment.creator),
            selectinload(PayrollAdjustment.updater)
        ).order_by(PayrollAdjustment.created_at)
        adjustments_result = await db.execute(adjustments_query)
        all_adjustments = adjustments_result.scalars().all()
        
        # Нормализовать timestamp в edit_history (конвертировать строки в datetime)
        from datetime import timezone
        for adj in all_adjustments:
            if adj.edit_history:
                for change in adj.edit_history:
                    if isinstance(change.get('timestamp'), str):
                        try:
                            dt = datetime.fromisoformat(change['timestamp'])
                            # Если datetime naive, делаем его UTC aware
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            change['timestamp'] = dt
                        except (ValueError, AttributeError):
                            pass  # Оставляем как есть если не удалось распарсить
        
        deductions = [adj for adj in all_adjustments if adj.amount < 0]
        bonuses = [adj for adj in all_adjustments if adj.amount > 0]
        
        # Получить список сотрудников с доступом к объектам управляющего
        permission_service = ManagerPermissionService(db)
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        accessible_object_ids = [obj.id for obj in accessible_objects]
        
        # Сотрудники с договорами на доступные объекты
        from domain.entities.contract import Contract
        from domain.entities.user import User
        from sqlalchemy.dialects.postgresql import JSONB
        from sqlalchemy import cast, or_
        
        employees_query = (
            select(User)
            .join(Contract, Contract.employee_id == User.id)
            .where(
                Contract.allowed_objects.isnot(None),
                or_(*[
                    cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj_id], JSONB))
                    for obj_id in accessible_object_ids
                ] if accessible_object_ids else [False])
            )
            .distinct()
        )
        employees_result = await db.execute(employees_query)
        employees = employees_result.scalars().all()
        
        # Получаем контекст управляющего
        from apps.web.routes.manager import get_manager_context
        manager_context = await get_manager_context(user_id, db)
        
        return templates.TemplateResponse(
            "manager/payroll/detail.html",
            {
                "request": request,
                "current_user": current_user,
                "title": f"Начисление #{entry_id}",
                "entry": entry,
                "deductions": deductions,
                "bonuses": bonuses,
                "is_manager": "manager" in user_roles and "owner" not in user_roles,
                "accessible_objects": accessible_objects,
                "employees": employees,
                **manager_context
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading payroll detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начисления: {str(e)}")


@router.post("/payroll/{entry_id}/add-adjustment", response_class=JSONResponse)
async def manager_add_adjustment_to_entry(
    entry_id: int,
    employee_id: int = Form(...),
    adjustment_type: str = Form(...),
    amount: Decimal = Form(...),
    description: str = Form(...),
    adjustment_date: Optional[str] = Form(None),
    object_id: Optional[int] = Form(None),
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session)
):
    """Добавить корректировку к начислению (сразу применённую)."""
    try:
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        from datetime import date
        
        if adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Неверный тип корректировки"}
            )
        
        # Парсинг даты
        adjustment_date_obj = None
        if adjustment_date:
            try:
                adjustment_date_obj = date.fromisoformat(adjustment_date)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Неверный формат даты"}
                )
        
        user_id = current_user.id
        
        # Проверить доступ к объекту (если указан)
        if object_id:
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому объекту"}
                )
        
        adjustment_service = PayrollAdjustmentService(db)
        
        # Создать корректировку
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=employee_id,
            amount=amount,
            adjustment_type=adjustment_type,
            description=description,
            created_by=user_id,
            object_id=object_id,
            shift_id=None,
            adjustment_date=adjustment_date_obj
        )
        
        # Сразу применить к начислению
        adjustment.payroll_entry_id = entry_id
        adjustment.is_applied = True
        
        await db.commit()
        
        logger.info(
            f"Adjustment added to entry by manager",
            adjustment_id=adjustment.id,
            entry_id=entry_id,
            employee_id=employee_id,
            type=adjustment_type,
            amount=float(amount),
            manager_id=user_id
        )
        
        return JSONResponse(content={
            "success": True,
            "adjustment_id": adjustment.id,
            "message": "Корректировка успешно добавлена к начислению"
        })
        
    except Exception as e:
        logger.error(f"Error adding adjustment to entry: {e}")
        await db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

