"""Роуты для работы с начислениями и выплатами."""

from datetime import date, timedelta, datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import get_current_user
from apps.web.dependencies import require_role
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


async def get_user_id_from_current_user(current_user, session: AsyncSession) -> Optional[int]:
    """Получает внутренний ID пользователя из current_user."""
    # current_user может быть dict (из JWT) или User объект (из dependencies)
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    elif isinstance(current_user, User):
        return current_user.id
    else:
        return None


@router.get("/payroll", response_class=HTMLResponse, name="owner_payroll_list")
async def owner_payroll_list(
    request: Request,
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session),
    employee_id: Optional[str] = Query(None),
    period_start: Optional[str] = Query(None),
    period_end: Optional[str] = Query(None)
):
    """Список всех начислений."""
    try:
        payroll_service = PayrollService(db)
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Фильтры по дате
        if not period_start:
            period_start = (date.today() - timedelta(days=30)).isoformat()
        if not period_end:
            period_end = date.today().isoformat()

        # Парсинг дат (валидация формата)
        try:
            period_start_date = date.fromisoformat(period_start)
            period_end_date = date.fromisoformat(period_end)
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат дат. Используйте YYYY-MM-DD")

        # Получить ВСЕХ сотрудников владельца (включая уволенных)
        # для возможности просмотра и создания начислений задним числом
        all_emps_query = select(User).join(Contract, Contract.employee_id == User.id).where(
            Contract.owner_id == owner_id
        ).distinct()
        all_emps_result = await db.execute(all_emps_query)
        employees_all = all_emps_result.scalars().all()

        # Сотрудники для фильтра: договор пересекается с выбранным периодом
        # Пересечение по интервалу [start_date, effective_end], где effective_end = COALESCE(date(end_date), termination_date, +inf)
        # Если end_date и termination_date NULL, считаем договор бессрочным
        employees_filter_query = select(User).join(Contract, Contract.employee_id == User.id).where(
            Contract.owner_id == owner_id,
            func.date(Contract.start_date) <= period_end_date,
            (
                (
                    (Contract.end_date.is_(None)) & (Contract.termination_date.is_(None))
                ) |
                (func.coalesce(func.date(Contract.end_date), Contract.termination_date) >= period_start_date)
            )
        ).distinct().order_by(User.last_name, User.first_name)
        employees_result = await db.execute(employees_filter_query)
        employees = employees_result.scalars().all()

        # Нормализация employee_id: пустое значение → None
        employee_id_int = None
        if employee_id is not None and str(employee_id).strip() != "":
            try:
                employee_id_int = int(employee_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="employee_id должен быть числом")
        
        # Получить начисления
        if employee_id_int:
            entries = await payroll_service.get_payroll_entries_by_employee(
                employee_id=employee_id_int,
                period_start=period_start_date,
                period_end=period_end_date,
                owner_id=owner_id  # Фильтровать по договорам владельца
            )
        else:
            # Получить начисления для всех сотрудников (включая неактивных)
            entries = []
            for emp in employees_all:
                emp_entries = await payroll_service.get_payroll_entries_by_employee(
                    employee_id=emp.id,
                    period_start=period_start_date,
                    period_end=period_end_date,
                    limit=50,
                    owner_id=owner_id  # Фильтровать по договорам владельца
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
                "selected_employee_id": employee_id_int,
                "period_start": period_start,
                "period_end": period_end
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading payroll list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.get("/payroll/report", response_class=HTMLResponse, name="owner_payroll_report")
async def owner_payroll_report(
    request: Request,
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session),
    period_start: str = None,
    period_end: str = None
):
    """Отчёт по начислениям с группировкой по объектам."""
    try:
        # Получить текущего пользователя из request
        current_user = await get_current_user(request)
        if not current_user:
            raise HTTPException(status_code=401, detail="Требуется авторизация")
        
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Парсинг дат
        if not period_start or not period_end:
            raise HTTPException(status_code=400, detail="Укажите период")
        
        period_start_date = date.fromisoformat(period_start)
        period_end_date = date.fromisoformat(period_end)
        
        # Получить все начисления за период
        from sqlalchemy.orm import selectinload
        
        entries_query = select(PayrollEntry).options(
            selectinload(PayrollEntry.employee),
            selectinload(PayrollEntry.object_),
            selectinload(PayrollEntry.contract)
        ).join(
            Contract, Contract.id == PayrollEntry.contract_id
        ).where(
            Contract.owner_id == owner_id,
            PayrollEntry.period_start >= period_start_date,
            PayrollEntry.period_end <= period_end_date
        ).order_by(PayrollEntry.object_id, PayrollEntry.employee_id)
        
        entries_result = await db.execute(entries_query)
        entries = list(entries_result.scalars().all())
        
        if not entries:
            return templates.TemplateResponse(
                "owner/payroll/report.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "period_start": period_start,
                    "period_end": period_end,
                    "report_data": None,
                    "error": "Нет начислений за выбранный период"
                }
            )
        
        # Группировка по сотрудникам: считаем на скольких объектах работал каждый
        employee_objects_count = {}
        for entry in entries:
            if entry.employee_id not in employee_objects_count:
                employee_objects_count[entry.employee_id] = set()
            employee_objects_count[entry.employee_id].add(entry.object_id)
        
        # Разделяем сотрудников: один объект vs несколько
        single_object_employees = {emp_id for emp_id, objs in employee_objects_count.items() if len(objs) == 1}
        multi_object_employees = {emp_id for emp_id, objs in employee_objects_count.items() if len(objs) > 1}
        
        # Группировка по объектам
        objects_data = {}
        multi_object_rows = []
        
        for entry in entries:
            # Получить данные о смене для подсчёта
            shifts_count = len(entry.calculation_details.get("shifts", [])) if entry.calculation_details else 0
            
            # Статус сотрудника на дату выплаты
            contract = entry.contract
            if contract.status == 'active':
                status = "Работает"
            elif contract.status == 'terminated':
                status = "Уволен"
            else:
                status = contract.status.capitalize()
            
            row_data = {
                "employee_id": entry.employee_id,
                "last_name": entry.employee.last_name or "",
                "first_name": entry.employee.first_name or "",
                "status": status,
                "shifts_count": shifts_count,
                "hours": float(entry.hours_worked or 0),
                "rate": float(entry.hourly_rate or 0),
                "bonus": float(entry.total_bonuses or 0),
                "penalty": float(entry.total_deductions or 0),
                "total": float(entry.net_amount or 0)
            }
            
            if entry.employee_id in multi_object_employees:
                # Сотрудник работал на нескольких объектах
                row_data["object_name"] = entry.object_.name if entry.object_ else "—"
                multi_object_rows.append(row_data)
            else:
                # Сотрудник работал на одном объекте
                object_id = entry.object_id
                if object_id not in objects_data:
                    objects_data[object_id] = {
                        "object_name": entry.object_.name if entry.object_ else f"Объект #{object_id}",
                        "rows": [],
                        "subtotal": 0
                    }
                
                objects_data[object_id]["rows"].append(row_data)
                objects_data[object_id]["subtotal"] += row_data["total"]
        
        # Сортировка объектов по имени
        objects_list = sorted(objects_data.values(), key=lambda x: x["object_name"])
        
        # Общий итог
        grand_total = sum(obj["subtotal"] for obj in objects_list) + sum(row["total"] for row in multi_object_rows)
        
        report_data = {
            "objects": objects_list,
            "multi_object_employees": sorted(multi_object_rows, key=lambda x: (x["last_name"], x["first_name"])),
            "grand_total": grand_total
        }
        
        # Формируем данные для отчёта по выплатам
        from domain.entities.employee_payment import EmployeePayment
        
        # Группируем начисления и выплаты по сотрудникам
        employee_payment_data = {}
        
        for entry in entries:
            emp_id = entry.employee_id
            if emp_id not in employee_payment_data:
                employee_payment_data[emp_id] = {
                    "employee_id": emp_id,
                    "last_name": entry.employee.last_name or "",
                    "first_name": entry.employee.first_name or "",
                    "gross_total": 0.0,
                    "net_total": 0.0,
                    "paid": 0.0,
                    "payment_methods": set()
                }
            
            employee_payment_data[emp_id]["gross_total"] += float(entry.gross_amount or 0)
            employee_payment_data[emp_id]["net_total"] += float(entry.net_amount or 0)
        
        # Получаем выплаты за период
        payments_query = select(EmployeePayment).join(
            PayrollEntry, EmployeePayment.payroll_entry_id == PayrollEntry.id
        ).join(
            Contract, Contract.id == PayrollEntry.contract_id
        ).where(
            Contract.owner_id == owner_id,
            PayrollEntry.period_start >= period_start_date,
            PayrollEntry.period_end <= period_end_date
        )
        
        payments_result = await db.execute(payments_query)
        payments = list(payments_result.scalars().all())
        
        for payment in payments:
            emp_id = payment.employee_id
            if emp_id in employee_payment_data:
                employee_payment_data[emp_id]["paid"] += float(payment.amount or 0)
                if payment.payment_method:
                    employee_payment_data[emp_id]["payment_methods"].add(payment.payment_method)
        
        # Рассчитываем остатки и форматируем способы оплаты
        employees_list = []
        total_gross = 0.0
        total_net = 0.0
        total_paid = 0.0
        total_remainder = 0.0
        
        for emp_data in employee_payment_data.values():
            remainder = emp_data["net_total"] - emp_data["paid"]
            emp_data["remainder"] = remainder
            emp_data["payment_methods"] = ", ".join(sorted(emp_data["payment_methods"])) if emp_data["payment_methods"] else ""
            
            employees_list.append(emp_data)
            total_gross += emp_data["gross_total"]
            total_net += emp_data["net_total"]
            total_paid += emp_data["paid"]
            total_remainder += remainder
        
        # Сортируем по фамилии
        employees_list.sort(key=lambda x: (x["last_name"], x["first_name"]))
        
        payments_data = {
            "employees": employees_list,
            "total_gross": total_gross,
            "total_net": total_net,
            "total_paid": total_paid,
            "total_remainder": total_remainder
        }
        
        return templates.TemplateResponse(
            "owner/payroll/report.html",
            {
                "request": request,
                "current_user": current_user,
                "period_start": period_start,
                "period_end": period_end,
                "report_data": report_data,
                "payments_data": payments_data
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating payroll report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка формирования отчёта: {str(e)}")


@router.get("/payroll/{entry_id}", response_class=HTMLResponse, name="owner_payroll_detail")
async def owner_payroll_detail(
    request: Request,
    entry_id: int,
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
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
        
        # Нормализовать timestamp в edit_history (конвертировать строки в datetime)
        # И загрузить информацию о пользователях
        from datetime import timezone
        user_ids_to_load = set()
        for adj in adjustments:
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
        for adj in adjustments:
            if adj.edit_history:
                for change in adj.edit_history:
                    uid = change.get('user_id')
                    if uid:
                        change['user_name'] = users_map.get(uid, f"ID: {uid}")
        
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
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session),
    deduction_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(...),
    adjustment_date: Optional[str] = Form(None)
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
        
        # Парсинг даты
        adjustment_date_obj = None
        if adjustment_date:
            try:
                adjustment_date_obj = date.fromisoformat(adjustment_date)
            except ValueError:
                pass  # Используем текущую дату
        
        # Добавить удержание через PayrollAdjustmentService
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=entry.employee_id,
            amount=-abs(Decimal(str(amount))),  # Отрицательное для удержания
            adjustment_type='manual_deduction',
            description=description,
            created_by=owner_id,
            object_id=entry.object_id,
            adjustment_date=adjustment_date_obj
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
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session),
    bonus_type: str = Form(...),
    amount: float = Form(...),
    description: str = Form(...),
    adjustment_date: Optional[str] = Form(None)
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
        
        # Парсинг даты
        adjustment_date_obj = None
        if adjustment_date:
            try:
                adjustment_date_obj = date.fromisoformat(adjustment_date)
            except ValueError:
                pass  # Используем текущую дату
        
        # Добавить доплату через PayrollAdjustmentService
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=entry.employee_id,
            amount=abs(Decimal(str(amount))),  # Положительное для бонуса
            adjustment_type='manual_bonus',
            description=description,
            created_by=owner_id,
            object_id=entry.object_id,
            adjustment_date=adjustment_date_obj
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
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
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
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
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
    current_user: dict = Depends(require_role(["owner", "superadmin"])),
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
        
        # Найти все активные payment_schedules (системные + кастомные владельца)
        # Логика такая же как в автоматическом пересчете - берем ВСЕ активные графики,
        # а объекты фильтруем по owner_id
        schedules_query = select(PaymentSchedule).where(
            PaymentSchedule.is_active == True
        )
        schedules_result = await db.execute(schedules_query)
        schedules = schedules_result.scalars().all()
        
        logger.info(f"Found {len(schedules)} active schedules total")
        
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
                        # Найти контракты:
                        # - активные
                        # - terminated + settlement_policy='schedule'
                        # - terminated + settlement_policy='termination_date' И конец платёжного периода <= termination_date
                        contracts_query = select(Contract).where(
                            and_(
                                Contract.allowed_objects.isnot(None),
                                cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj.id], JSONB)),
                                or_(
                                    Contract.status == 'active',
                                    and_(
                                        Contract.status == 'terminated',
                                        Contract.settlement_policy == 'schedule'
                                    ),
                                    and_(
                                        Contract.status == 'terminated',
                                        Contract.settlement_policy == 'termination_date',
                                        Contract.termination_date.isnot(None),
                                        func.date(period_end) <= Contract.termination_date
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
                                
                                # Проверить, существует ли уже начисление за этот период
                                existing_entry_query = select(PayrollEntry).where(
                                    PayrollEntry.employee_id == contract.employee_id,
                                    PayrollEntry.period_start == period_start,
                                    PayrollEntry.period_end == period_end,
                                    PayrollEntry.object_id == obj.id
                                )
                                existing_entry_result = await db.execute(existing_entry_query)
                                existing_entry = existing_entry_result.scalar_one_or_none()
                                
                                # КРИТИЧНО: найти ВСЕ корректировки для этого сотрудника за этот период
                                # 1. is_applied = false (обычные неприменённые)
                                # 2. is_applied = true AND payroll_entry_id IS NULL ("зависшие")
                                # 3. is_applied = true AND payroll_entry_id = existing_entry.id (УЖЕ привязанные к ЭТОМУ начислению, если оно существует)
                                
                                # Строим базовые условия для статуса применения
                                apply_status_conditions = [
                                    PayrollAdjustment.is_applied == False,
                                    and_(
                                        PayrollAdjustment.is_applied == True,
                                        PayrollAdjustment.payroll_entry_id.is_(None)
                                    )
                                ]
                                
                                # Если начисление уже существует - добавляем условие для его корректировок
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
                                        # Корректировки со сменой - фильтр по дате смены
                                        and_(
                                            PayrollAdjustment.shift_id.isnot(None),
                                            func.date(Shift.end_time) >= period_start,
                                            func.date(Shift.end_time) <= period_end
                                        ),
                                        # Корректировки БЕЗ смены:
                                        # - Если НЕ привязаны к начислению - по created_at
                                        # - Если УЖЕ привязаны к ЭТОМУ начислению - берём без фильтра по дате
                                        and_(
                                            PayrollAdjustment.shift_id.is_(None),
                                            or_(
                                                and_(
                                                    PayrollAdjustment.payroll_entry_id.is_(None),
                                                    func.date(PayrollAdjustment.created_at) >= period_start,
                                                    func.date(PayrollAdjustment.created_at) <= period_end
                                                ),
                                                # Только если existing_entry существует
                                                PayrollAdjustment.payroll_entry_id == existing_entry.id if existing_entry else False
                                            )
                                        )
                                    )
                                )
                                
                                all_result = await db.execute(all_adjustments_query)
                                all_adjustments = list(all_result.scalars().all())
                                
                                # Фильтруем по правилам:
                                # shift_base - только для текущего объекта
                                # Остальные - для всех объектов владельца
                                # РАЗДЕЛЯЕМ на уже применённые и новые
                                already_applied_adjustments = []  # Уже привязаны к ЭТОМУ начислению
                                new_adjustments = []  # Новые или "зависшие"
                                
                                for adj in all_adjustments:
                                    # Сбрасываем статус "зависших" корректировок
                                    if adj.is_applied and adj.payroll_entry_id is None:
                                        adj.is_applied = False
                                        adj.payroll_entry_id = None
                                    
                                    # Фильтр по объекту
                                    if adj.adjustment_type == 'shift_base':
                                        # shift_base - только для текущего объекта
                                        if adj.object_id != obj.id:
                                            continue
                                    
                                    # Разделяем на уже применённые и новые
                                    if existing_entry and adj.is_applied and adj.payroll_entry_id == existing_entry.id:
                                        already_applied_adjustments.append(adj)
                                    else:
                                        new_adjustments.append(adj)
                                
                                # Flush изменений статусов перед использованием
                                if new_adjustments:
                                    await db.flush()
                                
                                # Если нет ВООБЩЕ корректировок (ни новых, ни старых) - пропускаем
                                if not new_adjustments and not already_applied_adjustments:
                                    logger.debug(
                                        f"No adjustments found for employee",
                                        employee_id=contract.employee_id,
                                        object_id=obj.id
                                    )
                                    continue
                                
                                logger.info(
                                    f"Found adjustments for employee: {len(new_adjustments)} new, {len(already_applied_adjustments)} already applied",
                                    employee_id=contract.employee_id,
                                    new_types=[adj.adjustment_type for adj in new_adjustments],
                                    new_amounts=[float(adj.amount) for adj in new_adjustments]
                                )
                                
                                # ПЕРЕСЧИТЫВАЕМ начисление С НУЛЯ, используя ВСЕ корректировки (и старые, и новые)
                                all_relevant_adjustments = already_applied_adjustments + new_adjustments
                                
                                gross_amount = Decimal('0')
                                total_bonuses = Decimal('0')
                                total_deductions = Decimal('0')
                                total_hours = Decimal('0')
                                
                                for adj in all_relevant_adjustments:
                                    amount_decimal = Decimal(str(adj.amount))
                                    
                                    if adj.adjustment_type == 'shift_base':
                                        # Базовое начисление за смену
                                        gross_amount += amount_decimal
                                        # Извлекаем часы из details
                                        if adj.details and 'hours' in adj.details:
                                            total_hours += Decimal(str(adj.details['hours']))
                                    elif amount_decimal > 0:
                                        # Премии
                                        total_bonuses += amount_decimal
                                    else:
                                        # Штрафы
                                        total_deductions += abs(amount_decimal)
                                
                                avg_hourly_rate = gross_amount / total_hours if total_hours > 0 else Decimal('0')
                                net_amount = gross_amount + total_bonuses - total_deductions
                                
                                # Формируем calculation_details для протокола расчёта
                                calculation_details = {
                                    "created_by": "manual_recalculate",
                                    "created_at": target_date_obj.isoformat(),
                                    "shifts": [],
                                    "adjustments": []
                                }
                                
                                # Собираем детали смен из shift_base корректировок
                                shift_adjustments = [adj for adj in all_relevant_adjustments if adj.adjustment_type == 'shift_base']
                                if shift_adjustments:
                                    shift_ids = [adj.shift_id for adj in shift_adjustments if adj.shift_id]
                                    if shift_ids:
                                        shifts_query = select(Shift).where(Shift.id.in_(shift_ids))
                                        shifts_result = await db.execute(shifts_query)
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
                                    new_entry = PayrollEntry(
                                        employee_id=contract.employee_id,
                                        contract_id=contract.id,
                                        object_id=obj.id,
                                        period_start=period_start,
                                        period_end=period_end,
                                        gross_amount=float(gross_amount),
                                        total_bonuses=float(total_bonuses),
                                        total_deductions=float(total_deductions),
                                        net_amount=float(net_amount),
                                        hours_worked=float(total_hours),
                                        hourly_rate=float(avg_hourly_rate),
                                        calculation_details=calculation_details,
                                        created_by_id=owner_id
                                    )
                                    db.add(new_entry)
                                    await db.flush()  # Получаем ID нового начисления
                                    
                                    # Применяем корректировки к новому начислению
                                    if new_adjustments:
                                        new_adjustment_ids = [adj.id for adj in new_adjustments]
                                        applied_count = await adjustment_service.mark_adjustments_as_applied(
                                            adjustment_ids=new_adjustment_ids,
                                            payroll_entry_id=new_entry.id
                                        )
                                    else:
                                        applied_count = 0
                                    
                                    total_entries_created += 1
                                    total_adjustments_applied += applied_count
                                    
                                    logger.info(
                                        f"Created new payroll entry",
                                        payroll_entry_id=new_entry.id,
                                        employee_id=contract.employee_id,
                                        object_id=obj.id,
                                        gross_amount=float(gross_amount),
                                        net_amount=float(net_amount),
                                        adjustments_count=applied_count
                                    )
                                else:
                                    # ОБНОВЛЯЕМ существующее начисление - ВСЕ суммы
                                    existing_entry.gross_amount = float(gross_amount)
                                    existing_entry.total_bonuses = float(total_bonuses)
                                    existing_entry.total_deductions = float(total_deductions)
                                    existing_entry.net_amount = float(net_amount)
                                    existing_entry.hours_worked = float(total_hours)
                                    existing_entry.hourly_rate = float(avg_hourly_rate)
                                    existing_entry.calculation_details = calculation_details
                                    
                                    # Применяем ТОЛЬКО новые корректировки (if any)
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
                                        f"Updated existing payroll entry",
                                        payroll_entry_id=existing_entry.id,
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

