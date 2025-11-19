"""Роуты для работы управляющих с начислениями и выплатами."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib.parse import quote

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import get_current_user
from apps.web.middleware.role_middleware import get_user_id_from_current_user, require_manager_or_owner
from apps.web.dependencies import require_manager_payroll_permission
from core.database.session import get_db_session
from apps.web.services.payroll_service import PayrollService
from apps.web.services.payroll_statement_exporter import build_statement_workbook
from shared.services.manager_permission_service import ManagerPermissionService
from shared.services.payroll_statement_service import PayrollStatementService
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.contract import Contract
from domain.entities.payroll_entry import PayrollEntry
from core.logging.logger import logger
from apps.web.routes.manager import get_manager_context

router = APIRouter()


@router.get("/payroll", response_class=HTMLResponse)
async def manager_payroll_list(
    request: Request,
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None),
    object_id: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    show_inactive: bool = Query(False),
):
    """Сводка начислений по сотрудникам с фильтрами и пагинацией."""
    try:
        # Парсинг фильтров
        object_id_int: Optional[int] = None
        if object_id and object_id.strip():
            try:
                object_id_int = int(object_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="object_id должен быть числом")

        try:
            if period_end:
                period_end_date = date.fromisoformat(period_end)
            else:
                period_end_date = date.today()

            if period_start:
                period_start_date = date.fromisoformat(period_start)
            else:
                period_start_date = period_end_date - timedelta(days=60)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат дат. Используйте YYYY-MM-DD")

        if period_start_date > period_end_date:
            raise HTTPException(status_code=400, detail="Дата начала периода не может быть позже даты окончания")

        sort_field = (sort or "latest_period").lower()
        if sort_field not in {"latest_period", "employee", "entries_count", "total_amount"}:
            sort_field = "latest_period"
        sort_order = order.lower() if order else "desc"
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        user_id = current_user.id
        user_roles = current_user.get_roles() if hasattr(current_user, "get_roles") else current_user.roles
        if isinstance(user_roles, str):
            user_roles = [user_roles]
        user_roles = user_roles or []
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(db)

        if is_manager_only:
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            if not accessible_objects:
                manager_context = await get_manager_context(user_id, db)
                return templates.TemplateResponse(
                    "manager/payroll/list.html",
                    {
                        "request": request,
                        "current_user": current_user,
                        "title": "Начисления и выплаты",
                        "summary_rows": [],
                        "accessible_objects": [],
                        "filters": {
                            "object_id": None,
                            "period_start": period_start_date.isoformat(),
                            "period_end": period_end_date.isoformat(),
                            "show_inactive": show_inactive,
                        },
                        "sort": {"field": sort_field, "order": sort_order},
                        "pagination": {"page": page, "per_page": per_page, "total": 0, "pages": 0},
                        "show_inactive": show_inactive,
                        "error": "У вас нет доступных объектов",
                        **manager_context,
                    },
                )
            accessible_object_ids = [obj.id for obj in accessible_objects]
            active_employee_ids = set(await permission_service.get_user_accessible_employee_ids(user_id))
        else:
            objects_query = (
                select(Object)
                .where(Object.owner_id == user_id, Object.is_active == True)
                .order_by(Object.name)
            )
            objects_result = await db.execute(objects_query)
            accessible_objects = objects_result.scalars().all()
            accessible_object_ids = [obj.id for obj in accessible_objects]

            active_contracts_query = select(Contract.employee_id).where(
                Contract.owner_id == user_id,
                Contract.is_active == True,
            )
            active_contracts_result = await db.execute(active_contracts_query)
            active_employee_ids = set(active_contracts_result.scalars().all())

        if object_id_int and object_id_int not in accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к указанному объекту")

        filters_dict = {
            "object_id": object_id_int,
            "period_start": period_start_date.isoformat(),
            "period_end": period_end_date.isoformat(),
            "show_inactive": show_inactive,
        }

        # Загрузка начислений
        entries_query = (
            select(PayrollEntry)
            .where(
                PayrollEntry.period_start >= period_start_date,
                PayrollEntry.period_end <= period_end_date,
            )
            .options(selectinload(PayrollEntry.employee))
        )

        if accessible_object_ids:
            entries_query = entries_query.where(PayrollEntry.object_id.in_(accessible_object_ids))

        if object_id_int:
            entries_query = entries_query.where(PayrollEntry.object_id == object_id_int)

        entries_result = await db.execute(entries_query)
        entries = entries_result.scalars().all()

        summary_map: Dict[int, Dict[str, Any]] = {}
        employee_objs_map: Dict[int, User] = {}

        for entry in entries:
            if entry.employee_id is None:
                continue

            emp_id = int(entry.employee_id)
            if emp_id not in summary_map:
                summary_map[emp_id] = {
                    "employee_id": emp_id,
                    "employee": None,
                    "entries_count": 0,
                    "total_amount": 0.0,
                    "latest_entry": None,
                    "latest_entry_id": None,
                    "is_active": False,
                }

            row = summary_map[emp_id]
            row["entries_count"] += 1
            row["total_amount"] += float(entry.net_amount or 0)

            if row["latest_entry"] is None or (entry.id and entry.id > (row["latest_entry_id"] or 0)):
                row["latest_entry"] = entry
                row["latest_entry_id"] = entry.id

            if entry.employee:
                employee_objs_map[emp_id] = entry.employee

        # Добавляем сотрудников с активными договорами (даже без начислений)
        for emp_id in active_employee_ids:
            if emp_id not in summary_map:
                summary_map[emp_id] = {
                    "employee_id": emp_id,
                    "employee": None,
                    "entries_count": 0,
                    "total_amount": 0.0,
                    "latest_entry": None,
                    "latest_entry_id": None,
                    "is_active": True,
                }

        missing_employee_ids = [emp_id for emp_id in summary_map.keys() if emp_id not in employee_objs_map]
        if missing_employee_ids:
            users_query = select(User).where(User.id.in_(missing_employee_ids))
            users_result = await db.execute(users_query)
            for user in users_result.scalars().all():
                employee_objs_map[user.id] = user

        summary_rows: List[Dict[str, Any]] = []
        for emp_id, row in summary_map.items():
            employee = employee_objs_map.get(emp_id)
            row["employee"] = employee
            row["is_active"] = emp_id in active_employee_ids
            row["total_amount"] = float(row["total_amount"])
            summary_rows.append(row)

        if not show_inactive:
            summary_rows = [row for row in summary_rows if row["is_active"]]

        # Сортировка
        def sort_key(row: Dict[str, Any]):
            if sort_field == "employee":
                employee = row.get("employee")
                last_name = (employee.last_name if employee else "") or ""
                first_name = (employee.first_name if employee else "") or ""
                return (last_name.lower(), first_name.lower(), row["employee_id"])
            if sort_field == "entries_count":
                return (row["entries_count"], row["employee_id"])
            if sort_field == "total_amount":
                return (row["total_amount"], row["employee_id"])

            latest_entry = row.get("latest_entry")
            if latest_entry:
                return (latest_entry.period_end or date.min, latest_entry.id or 0)
            return (date.min, row["employee_id"])

        summary_rows.sort(key=sort_key, reverse=(sort_order == "desc"))

        total_rows = len(summary_rows)
        total_pages = (total_rows + per_page - 1) // per_page if total_rows else 0
        if total_pages and page > total_pages:
            page = total_pages
        if page < 1:
            page = 1

        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_rows = summary_rows[start_idx:end_idx]

        pagination_info = {
            "page": page,
            "per_page": per_page,
            "total": total_rows,
            "pages": total_pages,
        }

        manager_context = await get_manager_context(user_id, db)

        return templates.TemplateResponse(
            "manager/payroll/list.html",
            {
                "request": request,
                "current_user": current_user,
                "title": "Начисления и выплаты",
                "summary_rows": paginated_rows,
                "accessible_objects": accessible_objects,
                "filters": filters_dict,
                "sort": {"field": sort_field, "order": sort_order},
                "pagination": pagination_info,
                "show_inactive": show_inactive,
                "has_rows": total_rows > 0,
                **manager_context,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading manager payroll: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.get(
    "/payroll/statement/{employee_id}",
    response_class=HTMLResponse,
    name="manager_payroll_statement",
)
async def manager_payroll_statement(
    request: Request,
    employee_id: int,
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session),
):
    """Расчётный лист для управляющего (по доступным объектам)."""
    permission_service = ManagerPermissionService(db)
    statement_service = PayrollStatementService(db)
    try:
        user_id = current_user.id
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        accessible_object_ids = {obj.id for obj in accessible_objects}
        if not accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступных объектов")

        statement = await statement_service.generate_statement(
            employee_id=employee_id,
            requested_by_id=user_id,
            requested_role="manager",
            accessible_object_ids=accessible_object_ids,
        )
        await db.commit()

        manager_context = await get_manager_context(user_id, db)
        return templates.TemplateResponse(
            "manager/payroll/statement.html",
            {
                "request": request,
                "current_user": current_user,
                "statement": statement,
                "accessible_objects": accessible_objects,
                **manager_context,
            },
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error generating manager payroll statement: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Не удалось сформировать расчётный лист")


@router.get(
    "/payroll/statement/{employee_id}/export",
    name="manager_payroll_statement_export",
)
async def manager_payroll_statement_export(
    request: Request,
    employee_id: int,
    current_user = Depends(require_manager_payroll_permission),
    db: AsyncSession = Depends(get_db_session),
):
    """Экспорт расчётного листа управляющего в Excel."""
    permission_service = ManagerPermissionService(db)
    statement_service = PayrollStatementService(db)
    try:
        user_id = current_user.id
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        accessible_object_ids = {obj.id for obj in accessible_objects}
        if not accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступных объектов")

        statement = await statement_service.generate_statement(
            employee_id=employee_id,
            requested_by_id=user_id,
            requested_role="manager",
            accessible_object_ids=accessible_object_ids,
            log_result=False,
        )
        await db.commit()

        content = build_statement_workbook(statement)
        employee = statement["employee"]
        # Используем только ASCII для имени файла, чтобы избежать проблем с кодировкой
        safe_name = (employee.last_name or "employee").encode("ascii", "ignore").decode("ascii") or "employee"
        filename = f"manager_payroll_statement_{safe_name}_{employee_id}.xlsx"
        # Кодируем имя файла для Content-Disposition заголовка
        encoded_filename = quote(filename, safe="")
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{encoded_filename}"'},
        )
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error exporting manager payroll statement: {e}")
        raise HTTPException(status_code=500, detail="Не удалось выгрузить отчёт")


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
        
        permission_service = ManagerPermissionService(db)
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        if is_manager_only:
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        else:
            objects_query = select(Object).where(Object.owner_id == user_id, Object.is_active == True)
            objects_result = await db.execute(objects_query)
            accessible_objects = objects_result.scalars().all()

        accessible_object_ids = [obj.id for obj in accessible_objects]

        if is_manager_only:
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(
                user_id, include_inactive=True
            )
            if entry.object_id and entry.object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="У вас нет доступа к этому начислению")
            if entry.employee_id not in accessible_employee_ids:
                raise HTTPException(status_code=403, detail="У вас нет доступа к этому сотруднику")
        else:
            accessible_employee_ids = None
        
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
        # И загрузить информацию о пользователях
        from datetime import timezone
        user_ids_to_load = set()
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
                    
                    # Собираем ID пользователей для загрузки
                    if change.get('user_id'):
                        user_ids_to_load.add(change['user_id'])
        
        # Загрузить пользователей
        users_map = {}
        if user_ids_to_load:
            users_query = select(User).where(User.id.in_(list(user_ids_to_load)))
            users_result = await db.execute(users_query)
            users_list = users_result.scalars().all()
            users_map = {u.id: f"{u.last_name} {u.first_name}" for u in users_list}
        
        # Добавить user_name в edit_history
        for adj in all_adjustments:
            if adj.edit_history:
                for change in adj.edit_history:
                    uid = change.get('user_id')
                    if uid:
                        change['user_name'] = users_map.get(uid, f"ID: {uid}")
        
        deductions = [adj for adj in all_adjustments if adj.amount < 0]
        bonuses = [adj for adj in all_adjustments if adj.amount > 0]
        
        # Выплаты по начислению
        from domain.entities.employee_payment import EmployeePayment

        payments_query = select(EmployeePayment).where(
            EmployeePayment.payroll_entry_id == entry_id
        ).order_by(EmployeePayment.payment_date)
        payments_result = await db.execute(payments_query)
        payments = payments_result.scalars().all()
        has_payments = len(payments) > 0

        # Список начислений сотрудника
        employee_entries = await payroll_service.get_payroll_entries_by_employee(
            employee_id=entry.employee_id,
            limit=500
        )
        if is_manager_only and accessible_object_ids:
            employee_entries = [
                e for e in employee_entries
                if e.object_id in accessible_object_ids
            ]
        employee_entries.sort(key=lambda e: (e.period_end, e.id), reverse=True)

        # Сотрудники для выпадающего списка (для модалок)
        if is_manager_only:
            if accessible_employee_ids:
                employees_query = (
                    select(User)
                    .where(User.id.in_(accessible_employee_ids))
                    .order_by(User.last_name, User.first_name)
                )
                employees_result = await db.execute(employees_query)
                employees = employees_result.scalars().all()
            else:
                employees = []
        else:
            employees_query = (
                select(User)
                .join(Contract, Contract.employee_id == User.id)
                .where(Contract.owner_id == user_id, Contract.is_active == True)
                .distinct()
                .order_by(User.last_name, User.first_name)
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
                "employee_entries": employee_entries,
                "payments": payments,
                "has_payments": has_payments,
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
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(db)
        accessible_object_ids: List[int] = []
        accessible_employee_ids: List[int] = []

        if is_manager_only:
            accessible_object_ids = await permission_service.get_user_accessible_object_ids(user_id)
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(user_id)
            if not accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к объектам"}
                )
        else:
            accessible_employee_ids = None

        payroll_service = PayrollService(db)
        entry = await payroll_service.get_payroll_entry_by_id(entry_id)
        if not entry:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Начисление не найдено"}
            )

        if employee_id != entry.employee_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Сотрудник не соответствует начислению"}
            )

        if is_manager_only:
            if entry.object_id and entry.object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому начислению"}
                )
            if employee_id not in accessible_employee_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому сотруднику"}
                )
            if object_id and object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому объекту"}
                )

        # Если объект не указан, подставляем из начисления
        if not object_id and entry.object_id:
            object_id = entry.object_id
        
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

