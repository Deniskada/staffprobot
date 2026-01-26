"""
Роуты для интерфейса сотрудника (соискателя)
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Any, Optional
from collections import defaultdict
from calendar import monthrange
import logging
from io import BytesIO

from apps.web.dependencies import get_current_user_dependency
from core.database.session import get_db_session, get_async_session
from apps.web.middleware.role_middleware import require_employee_or_applicant
from domain.entities import User, Object, Application, Interview, ShiftSchedule, Shift, TimeSlot
from domain.entities.org_structure import OrgStructureUnit
from domain.entities.contract import Contract
from domain.entities.application import ApplicationStatus
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.employee_payment import EmployeePayment
from domain.entities.payment_schedule import PaymentSchedule
from apps.web.utils.timezone_utils import WebTimezoneHelper
from shared.services.role_based_login_service import RoleBasedLoginService
from shared.services.calendar_filter_service import CalendarFilterService
from shared.services.object_access_service import ObjectAccessService
from shared.models.calendar_data import TimeslotStatus
from shared.services.shift_history_service import ShiftHistoryService
from shared.services.shift_notification_service import ShiftNotificationService
from shared.services.cancellation_policy_service import CancellationPolicyService
from apps.web.utils.shift_history_utils import build_shift_history_items
from apps.web.utils.calendar_utils import create_calendar_grid
from openpyxl import Workbook

logger = logging.getLogger(__name__)
router = APIRouter()
from apps.web.jinja import templates

# Инициализируем помощник для работы с временными зонами
web_timezone_helper = WebTimezoneHelper()


async def load_employee_earnings(
    db: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    """Загружает завершенные смены, корректировки и данные по выплатам сотрудника."""

    # --- Смены -------------------------------------------------------------
    shift_query = (
        select(Shift, Object)
        .join(Object, Shift.object_id == Object.id)
        .where(
            Shift.user_id == user_id,
            Shift.status == "completed",
            func.date(Shift.start_time) >= start_date,
            func.date(Shift.start_time) <= end_date,
        )
        .order_by(Shift.start_time.desc())
    )

    shift_result = await db.execute(shift_query)
    shift_rows = shift_result.all()

    earnings: List[Dict[str, Any]] = []
    total_hours = 0.0
    total_amount = 0.0
    summary_by_object: Dict[int, Dict[str, Any]] = {}
    earliest_shift_date: Optional[date] = None

    for shift, obj in shift_rows:
        timezone_str = getattr(obj, "timezone", None) or "Europe/Moscow"
        date_label = web_timezone_helper.format_datetime_with_timezone(
            shift.start_time, timezone_str, "%d.%m.%Y"
        )
        start_label = web_timezone_helper.format_datetime_with_timezone(
            shift.start_time, timezone_str, "%H:%M"
        )
        end_label = (
            web_timezone_helper.format_datetime_with_timezone(
                shift.end_time, timezone_str, "%H:%M"
            )
            if shift.end_time
            else "—"
        )

        duration_hours = float(shift.total_hours or 0)
        if not duration_hours and shift.start_time and shift.end_time:
            seconds = max((shift.end_time - shift.start_time).total_seconds(), 0)
            duration_hours = round(seconds / 3600, 2)

        hourly_rate = float(shift.hourly_rate or obj.hourly_rate or 0)
        amount = float(shift.total_payment or (duration_hours * hourly_rate))

        total_hours += duration_hours
        total_amount += amount

        earnings.append(
            {
                "type": "shift",
                "shift_id": shift.id,
                "object_name": obj.name,
                "object_id": obj.id,
                "date_label": date_label,
                "start_label": start_label,
                "end_label": end_label,
                "duration_hours": duration_hours,
                "hourly_rate": hourly_rate,
                "amount": amount,
                "description": "",
                "payment_date": None,
                "payment_date_label": None,
            }
        )

        summary_entry = summary_by_object.setdefault(
            obj.id,
            {
                "object_name": obj.name,
                "hours": 0.0,
                "amount": 0.0,
                "shifts": 0,
                "object_id": obj.id,
            },
        )
        summary_entry["hours"] += duration_hours
        summary_entry["amount"] += amount
        summary_entry["shifts"] += 1

        if shift.start_time:
            shift_date = shift.start_time.date()
            if earliest_shift_date is None or shift_date < earliest_shift_date:
                earliest_shift_date = shift_date

    # --- Корректировки -----------------------------------------------------
    adjustments_query = (
        select(PayrollAdjustment)
        .where(
            PayrollAdjustment.employee_id == user_id,
            func.date(PayrollAdjustment.created_at) >= start_date,
            func.date(PayrollAdjustment.created_at) <= end_date,
        )
        .order_by(PayrollAdjustment.created_at)
    )

    adjustments_result = await db.execute(adjustments_query)
    adjustments = adjustments_result.scalars().all()

    for adj in adjustments:
        if adj.adjustment_type == "shift_base":
            # Базовая оплата уже учтена в сменах
            continue

        earnings.append(
            {
                "type": "adjustment",
                "adjustment_id": adj.id,
                "adjustment_type": adj.adjustment_type,
                "object_name": "-",
                "object_id": adj.object_id,
                "date_label": adj.created_at.strftime("%d.%m.%Y"),
                "start_label": "-",
                "end_label": "-",
                "duration_hours": 0.0,
                "hourly_rate": 0.0,
                "amount": float(adj.amount),
                "description": adj.get_type_label()
                + (f": {adj.description}" if adj.description else ""),
                "is_automatic": adj.adjustment_type
                in ["late_start", "task_bonus", "task_penalty"],
                "payment_date": None,
                "payment_date_label": None,
            }
        )
        total_amount += float(adj.amount)

    # --- Начисления и выплаты ----------------------------------------------
    payroll_entries_query = (
        select(PayrollEntry)
        .options(
            selectinload(PayrollEntry.payments),
            selectinload(PayrollEntry.object_).selectinload(Object.org_unit),
        )
        .where(
            PayrollEntry.employee_id == user_id,
            PayrollEntry.period_end >= start_date,
            PayrollEntry.period_end <= end_date,
        )
        .order_by(PayrollEntry.period_end)
    )

    payroll_entries_result = await db.execute(payroll_entries_query)
    payroll_entries = payroll_entries_result.scalars().all()

    earliest_entry_date: Optional[date] = None
    if payroll_entries:
        earliest_entry_date = min(entry.period_end for entry in payroll_entries if entry.period_end)

    payments_query = (
        select(EmployeePayment)
        .where(
            EmployeePayment.employee_id == user_id,
            EmployeePayment.payment_date >= start_date,
            EmployeePayment.payment_date <= end_date,
        )
        .order_by(EmployeePayment.payment_date)
    )
    payments_result = await db.execute(payments_query)
    payments = payments_result.scalars().all()

    payments_by_date: Dict[date, List[EmployeePayment]] = defaultdict(list)
    entry_payment_date_map: Dict[int, date] = {}
    payment_date_entries: Dict[date, set] = defaultdict(set)

    for payment in payments:
        if not payment.payment_date:
            continue
        payments_by_date[payment.payment_date].append(payment)
        payment_date_entries[payment.payment_date].add(payment.payroll_entry_id)
        entry_payment_date_map.setdefault(payment.payroll_entry_id, payment.payment_date)

    # Построение связей "смена/корректировка -> начисление"
    shift_to_entry: Dict[int, int] = {}
    adjustment_to_entry: Dict[int, int] = {}
    schedule_dates: set[date] = set()
    schedule_cache: Dict[int, PaymentSchedule] = {}

    async def get_schedule_for_object(object_entity: Optional[Object]) -> Optional[PaymentSchedule]:
        """Получить график выплат для объекта с безопасной обработкой lazy loading."""
        if object_entity is None:
            return None
        
        try:
            # Получаем schedule_id безопасным способом через SQL запрос, если нужно
            schedule_id = None
            
            # Сначала проверяем payment_schedule_id объекта
            if object_entity.payment_schedule_id is not None:
                schedule_id = object_entity.payment_schedule_id
            elif object_entity.org_unit is not None:
                # Используем SQL запрос для получения schedule_id с учетом наследования
                org_unit = object_entity.org_unit
                
                # Рекурсивно ищем schedule_id в цепочке предков через SQL
                current_unit_id = org_unit.id
                max_depth = 10  # Защита от бесконечной рекурсии
                depth = 0
                
                while current_unit_id and depth < max_depth:
                    unit_query = select(OrgStructureUnit).where(OrgStructureUnit.id == current_unit_id)
                    unit_result = await db.execute(unit_query)
                    unit = unit_result.scalar_one_or_none()
                    
                    if not unit:
                        break
                    
                    if unit.payment_schedule_id is not None:
                        schedule_id = unit.payment_schedule_id
                        break
                    
                    current_unit_id = unit.parent_id
                    depth += 1
        except Exception as e:
            logger.warning(
                f"Error getting payment schedule for object {object_entity.id if object_entity else None}",
                error=str(e),
                exc_info=True
            )
            return None
        
        if not schedule_id:
            return None
        
        if schedule_id not in schedule_cache:
            schedule_query = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
            schedule_result = await db.execute(schedule_query)
            schedule_cache[schedule_id] = schedule_result.scalar_one_or_none()
        return schedule_cache.get(schedule_id)

    for entry in payroll_entries:
        details = entry.calculation_details or {}
        for shift_info in details.get("shifts", []):
            shift_id = shift_info.get("shift_id")
            if shift_id:
                shift_to_entry[shift_id] = entry.id
        for adj_info in details.get("adjustments", []):
            adj_id = adj_info.get("adjustment_id")
            if adj_id:
                adjustment_to_entry[adj_id] = entry.id

        schedule = await get_schedule_for_object(entry.object_)
        if schedule:
            schedule_dates.update(
                generate_payment_schedule_dates(schedule, start_date, end_date)
            )

    # Проставляем даты выплат в записях заработка
    for row in earnings:
        payment_date: Optional[date] = None
        if row["type"] == "shift":
            entry_id = shift_to_entry.get(row["shift_id"])
            if entry_id:
                payment_date = entry_payment_date_map.get(entry_id)
        elif row["type"] == "adjustment":
            entry_id = adjustment_to_entry.get(row.get("adjustment_id"))
            if entry_id:
                payment_date = entry_payment_date_map.get(entry_id)

        if payment_date:
            row["payment_date"] = payment_date.isoformat()
            row["payment_date_label"] = payment_date.strftime("%d.%m.%Y")

    # Сортировка записей по дате (в формате dd.mm.YYYY нужно преобразовать назад)
    def parse_date_label(label: str) -> datetime:
        return datetime.strptime(label, "%d.%m.%Y")

    earnings.sort(key=lambda item: parse_date_label(item["date_label"]), reverse=True)

    summary_list = sorted(
        summary_by_object.values(), key=lambda item: item["amount"], reverse=True
    )

    # Календарь выплат (объединяем даты из графиков и фактические выплаты)
    all_payment_dates = set(payments_by_date.keys()) | schedule_dates
    payment_rows = build_employee_payment_rows(
        all_payment_dates,
        payments_by_date,
        payment_date_entries,
    )

    return {
        "earnings": earnings,
        "total_hours": total_hours,
        "total_amount": total_amount,
        "summary_by_object": summary_list,
        "payment_rows": payment_rows,
        "earliest_shift_date": earliest_shift_date,
        "earliest_payroll_entry_date": earliest_entry_date,
    }


def generate_payment_schedule_dates(
    schedule: PaymentSchedule, start_date: date, end_date: date
) -> List[date]:
    """Возвращает даты выплат по графику в интервале [start_date; end_date]."""
    if start_date > end_date:
        return []

    dates: List[date] = []
    frequency = (schedule.frequency or "").lower()

    if frequency == "daily":
        current = start_date
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)

    elif frequency in {"weekly", "biweekly"}:
        step = 7 if frequency == "weekly" else 14
        payment_day = schedule.payment_day or 1
        target_weekday = (payment_day - 1) % 7
        current = start_date
        offset = (target_weekday - current.weekday()) % 7
        current = current + timedelta(days=offset)
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=step)

    elif frequency == "monthly":
        period = schedule.payment_period or {}
        payments_cfg = period.get("payments", [])

        if payments_cfg:
            for cfg in payments_cfg:
                next_payment_str = cfg.get("next_payment_date")
                if not next_payment_str:
                    continue
                try:
                    base_date = date.fromisoformat(next_payment_str)
                except ValueError:
                    continue

                current = base_date
                while current < start_date:
                    current = add_months(current, 1)
                while current <= end_date:
                    dates.append(current)
                    current = add_months(current, 1)
        else:
            payment_day = schedule.payment_day or 1
            current = date(start_date.year, start_date.month, 1)
            while current <= end_date:
                day = min(payment_day, monthrange(current.year, current.month)[1])
                payment_date = date(current.year, current.month, day)
                if start_date <= payment_date <= end_date:
                    dates.append(payment_date)
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)

    return sorted(set(dates))


def add_months(base_date: date, months: int) -> date:
    """Возвращает дату, смещённую на указанное количество месяцев."""
    month = base_date.month - 1 + months
    year = base_date.year + month // 12
    month = month % 12 + 1
    day = min(base_date.day, monthrange(year, month)[1])
    return date(year, month, day)


def build_employee_payment_rows(
    all_dates: set,
    payments_by_date: Dict[date, List[EmployeePayment]],
    payment_date_entries: Dict[date, set],
) -> List[Dict[str, Any]]:
    """Формирует строки таблицы «Даты выплат»."""
    rows: List[Dict[str, Any]] = []

    for payment_date in sorted(all_dates):
        date_payments = payments_by_date.get(payment_date, [])
        amount = sum(float(payment.amount or 0) for payment in date_payments) if date_payments else None

        completed_at_values: List[date] = []
        for payment in date_payments:
            if payment.status == "completed" and payment.completed_at:
                if isinstance(payment.completed_at, datetime):
                    completed_at_values.append(payment.completed_at.date())
                else:
                    completed_at_values.append(payment.completed_at)

        completed_at_label = (
            max(completed_at_values).strftime("%d.%m.%Y") if completed_at_values else None
        )

        if not date_payments:
            status = "scheduled"
        else:
            statuses = {payment.status for payment in date_payments if payment.status}
            if statuses == {"completed"}:
                status = "completed"
            elif "pending" in statuses:
                status = "pending"
            elif "failed" in statuses:
                status = "failed"
            else:
                status = statuses.pop()

        rows.append(
            {
                "date": payment_date,
                "date_iso": payment_date.isoformat(),
                "date_label": payment_date.strftime("%d.%m.%Y"),
                "amount": amount,
                "completed_at": completed_at_label,
                "status": status,
                "has_related_entries": bool(payment_date_entries.get(payment_date)),
            }
        )

    return rows


async def get_user_id_from_current_user(current_user, session):
    """Получает внутренний ID пользователя из current_user"""
    if isinstance(current_user, dict):
        # current_user - это словарь из JWT payload
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        # current_user - это объект User
        return current_user.id

async def get_available_interfaces_for_user(current_user, db):
    """Получает доступные интерфейсы для пользователя"""
    user_id = await get_user_id_from_current_user(current_user, db)
    login_service = RoleBasedLoginService(db)
    return await login_service.get_available_interfaces(user_id)


@router.get("/earnings", response_class=HTMLResponse)
async def employee_earnings(
    request: Request,
    year: Optional[int] = Query(None, description="Год для отображения начислений"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница заработка сотрудника."""

    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    today = datetime.utcnow().date()
    selected_year = year or today.year
    try:
        selected_year = int(selected_year)
    except (TypeError, ValueError):
        selected_year = today.year

    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)

    earnings_payload = await load_employee_earnings(db, user_id, year_start, year_end)

    earliest_candidates = [
        candidate
        for candidate in (
            earnings_payload.get("earliest_shift_date"),
            earnings_payload.get("earliest_payroll_entry_date"),
        )
        if candidate is not None
    ]
    first_year = min(candidate.year for candidate in earliest_candidates) if earliest_candidates else selected_year
    if first_year > selected_year:
        first_year = selected_year
    available_years = list(range(first_year, today.year + 1))

    available_interfaces = await get_available_interfaces_for_user(current_user, db)
    applications_count_result = await db.execute(
        select(func.count(Application.id)).where(Application.applicant_id == user_id)
    )
    applications_count = applications_count_result.scalar() or 0

    return templates.TemplateResponse(
        "employee/earnings.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "selected_year": selected_year,
            "year_start": year_start,
            "year_end": year_end,
            "available_years": available_years,
            "earnings": earnings_payload["earnings"],
            "total_hours": earnings_payload["total_hours"],
            "total_amount": earnings_payload["total_amount"],
            "summary_by_object": earnings_payload["summary_by_object"],
            "payment_rows": earnings_payload["payment_rows"],
        },
    )


@router.get("/earnings/export")
async def employee_earnings_export(
    year: Optional[int] = Query(None, description="Год для экспорта"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Экспорт заработка в Excel."""

    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    today = datetime.utcnow().date()
    selected_year = year or today.year
    try:
        selected_year = int(selected_year)
    except (TypeError, ValueError):
        selected_year = today.year

    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)

    earnings_payload = await load_employee_earnings(db, user_id, year_start, year_end)

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Сводка"
    summary_sheet.append(["Год", f"{selected_year}"])
    summary_sheet.append(["Всего записей", len(earnings_payload["earnings"])])
    summary_sheet.append(["Общее число часов", earnings_payload["total_hours"]])
    summary_sheet.append(["Заработано, ₽", earnings_payload["total_amount"]])
    summary_sheet.append([])
    summary_sheet.append(["Объект", "Смен", "Часы", "Сумма, ₽"])

    for item in earnings_payload["summary_by_object"]:
        summary_sheet.append([
            item["object_name"],
            item["shifts"],
            round(item["hours"], 2),
            round(item["amount"], 2),
        ])

    detail_sheet = workbook.create_sheet("Начисления")
    detail_sheet.append([
        "Дата",
        "Тип",
        "Описание",
        "Объект",
        "Часы",
        "Ставка, ₽",
        "Сумма, ₽",
        "Дата выплаты",
    ])

    for row in earnings_payload["earnings"]:
        if row["type"] == "shift":
            row_type = "Смена"
        elif row["type"] == "adjustment":
            row_type = "Корректировка"
        else:
            row_type = row.get("type", "Запись")
        detail_sheet.append([
            row["date_label"],
            row_type,
            row.get("description", "Смена на объекте" if row["type"] == "shift" else "-"),
            row["object_name"],
            round(row["duration_hours"], 2) if row["type"] == "shift" else "-",
            round(row["hourly_rate"], 2) if row["type"] == "shift" else "-",
            round(row["amount"], 2),
            row.get("payment_date_label") or "-",
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"earnings_{selected_year}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return StreamingResponse(buffer, media_type=headers["Content-Type"], headers=headers)

@router.get("/", response_class=HTMLResponse)
async def employee_index(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Главная страница сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0
        
        # Получаем статистику
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        interviews_count = await db.execute(
            select(func.count(Interview.id)).where(
                    and_(
                    Interview.applicant_id == user_id,
                    Interview.status.in_(['SCHEDULED', 'PENDING'])
                )
            )
        )
        interviews_count = interviews_count.scalar() or 0
        
        available_objects_count = await db.execute(
            select(func.count(Object.id)).where(Object.available_for_applicants == True)
        )
        available_objects_count = available_objects_count.scalar() or 0
        
        history_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        history_count = history_count.scalar() or 0
        
        # Получаем последние заявки
        recent_applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(
            Application.applicant_id == user_id
        ).order_by(Application.created_at.desc()).limit(5)
        
        recent_applications_result = await db.execute(recent_applications_query)
        recent_applications = []
        for row in recent_applications_result:
            recent_applications.append({
                'id': row.Application.id,
                'object_name': row.object_name,
                'status': row.Application.status,
                'created_at': row.Application.created_at
            })
        
        # Получаем ближайшие собеседования
        upcoming_interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(
            and_(
                Interview.applicant_id == user_id,
                Interview.scheduled_at >= datetime.now(),
                Interview.status.in_(['SCHEDULED', 'PENDING'])
            )
        ).order_by(Interview.scheduled_at.asc()).limit(5)
        
        upcoming_interviews_result = await db.execute(upcoming_interviews_query)
        upcoming_interviews = []
        for row in upcoming_interviews_result:
            upcoming_interviews.append({
                'id': row.Interview.id,
                'object_name': row.object_name,
                'scheduled_at': row.Interview.scheduled_at,
                'type': row.Interview.type
            })
        
        # Всего заработано
        from sqlalchemy import func as _func
        total_earned = (await db.execute(
            select(_func.coalesce(_func.sum(Shift.total_payment), 0)).where(
                Shift.user_id == user_id,
                Shift.status == 'completed'
            )
        )).scalar() or 0

        return templates.TemplateResponse("employee/index.html", {
            "request": request,
            "current_user": current_user,
            "current_date": datetime.now(),
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "available_objects_count": available_objects_count,
            "history_count": history_count,
            "total_earned": float(total_earned),
            "recent_applications": recent_applications,
            "upcoming_interviews": upcoming_interviews,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {e}")

@router.get("/objects", response_class=HTMLResponse)
async def employee_objects(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница поиска работы"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Получаем доступные объекты
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = []
        
        for obj in objects_result.scalars():
            # Парсим координаты из формата "lat,lon"
            lat, lon = obj.coordinates.split(',') if obj.coordinates else (0, 0)
            
            objects.append({
                'id': obj.id,
                'name': obj.name,
                'address': obj.address or '',
                'latitude': float(lat),
                'longitude': float(lon),
                'opening_time': str(obj.opening_time),
                'closing_time': str(obj.closing_time),
                'hourly_rate': float(obj.hourly_rate),
                'work_conditions': obj.work_conditions or 'Стандартные условия работы',
                'shift_tasks': obj.shift_tasks or ['Выполнение основных обязанностей']
            })
        
        # Получаем ключ API Яндекс Карт
        import os
        yandex_maps_api_key = os.getenv("YANDEX_MAPS_API_KEY", "")
        
        return templates.TemplateResponse("employee/objects.html", {
        "request": request,
        "current_user": current_user,
        "yandex_maps_api_key": yandex_maps_api_key,
            "objects": objects,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки объектов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки объектов: {e}")

@router.get("/api/objects")
async def employee_api_objects(
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """API для получения объектов для карты"""
    try:
        logger.info(f"API objects called, current_user: {type(current_user)}")
        
        if isinstance(current_user, RedirectResponse):
            logger.info("Redirecting to login")
            return current_user
        
        # Проверяем кэш (публичные объекты - общий кэш)
        from core.cache.redis_cache import cache
        cache_key = "api_objects:employee_public"
        cached_data = await cache.get(cache_key, serialize="json")
        if cached_data:
            logger.info("Employee objects API: cache HIT for public objects")
            return cached_data
        
        logger.info("Employee objects API: cache MISS")
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            logger.error("User not found")
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        logger.info(f"User ID: {user_id}")
        
        # Получаем доступные объекты
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = []
        
        # Получаем рейтинги для всех объектов
        from shared.services.rating_service import RatingService
        rating_service = RatingService(db)
        
        for obj in objects_result.scalars():
            # Парсим координаты из формата "lat,lon"
            lat, lon = obj.coordinates.split(',') if obj.coordinates else (0, 0)
            
            # Получаем рейтинг объекта
            rating = await rating_service.get_rating('object', obj.id)
            if not rating:
                rating = await rating_service.get_or_create_rating('object', obj.id)
            
            # Форматируем звездный рейтинг
            star_info = rating_service.get_star_rating(float(rating.average_rating))
            
            objects.append({
                'id': obj.id,
                'name': obj.name,
                'address': obj.address or '',
                'latitude': float(lat),
                'longitude': float(lon),
                'opening_time': str(obj.opening_time),
                'closing_time': str(obj.closing_time),
                'hourly_rate': float(obj.hourly_rate),
                'work_conditions': obj.work_conditions or 'Стандартные условия работы',
                'shift_tasks': obj.shift_tasks or ['Выполнение основных обязанностей'],
                'rating': {
                    'average_rating': float(rating.average_rating),
                    'total_reviews': rating.total_reviews,
                    'stars': star_info
                }
            })
        
        logger.info(f"Found {len(objects)} objects")
        response_data = {"objects": objects}
        
        # Сохраняем в кэш (TTL 5 минут для публичных объектов)
        await cache.set(cache_key, response_data, ttl=300, serialize="json")
        logger.info(f"Employee objects API: cached {len(objects)} public objects")
        
        return response_data
        
    except Exception as e:
        logger.error(f"Ошибка загрузки объектов API: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки объектов: {e}")

@router.get("/applications", response_class=HTMLResponse)
async def employee_applications(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница заявок сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Получаем заявки
        applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(Application.applicant_id == user_id).order_by(Application.created_at.desc())
        
        applications_result = await db.execute(applications_query)
        applications = []
        for row in applications_result:
            applications.append({
                'id': row.Application.id,
                'object_id': row.Application.object_id,
                'object_name': row.object_name,
                'status': row.Application.status.value.lower(),
                'message': row.Application.message,
                'preferred_schedule': row.Application.preferred_schedule,
                'created_at': row.Application.created_at,
                'interview_scheduled_at': row.Application.interview_scheduled_at,
                'interview_type': row.Application.interview_type,
                'interview_result': row.Application.interview_result
            })
        
        # Статистика заявок
        applications_stats = {
            'pending': len([a for a in applications if a['status'] == 'pending']),
            'approved': len([a for a in applications if a['status'] == 'approved']),
            'rejected': len([a for a in applications if a['status'] == 'rejected']),
            'interview': len([a for a in applications if a['status'] == 'interview'])
        }
        
        # Получаем объекты для фильтра
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = [{'id': obj.id, 'name': obj.name} for obj in objects_result.scalars()]
        
        return templates.TemplateResponse("employee/applications.html", {
            "request": request,
            "current_user": current_user,
            "applications": applications,
            "applications_stats": applications_stats,
            "objects": objects,
            "applications_count": applications_count,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки заявок: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки заявок: {e}")

@router.post("/api/applications")
async def employee_create_application(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        form_data = await request.form()
        object_id = form_data.get("object_id")
        message = form_data.get("message", "").strip()

        if not object_id:
            raise HTTPException(status_code=400, detail="Не указан объект")

        object_query = select(Object).where(and_(Object.id == int(object_id), Object.available_for_applicants == True))
        obj_result = await db.execute(object_query)
        obj = obj_result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден или недоступен")

        existing_query = select(Application).where(and_(
            Application.applicant_id == user_id,
            Application.object_id == int(object_id),
            Application.status.in_([ApplicationStatus.PENDING, ApplicationStatus.APPROVED, ApplicationStatus.INTERVIEW])
        ))
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="У вас уже есть активная заявка на этот объект")

        application = Application(
            applicant_id=user_id,
            object_id=int(object_id),
            message=message,
            status=ApplicationStatus.PENDING
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)

        # Отправляем уведомления через асинхронную команду  
        try:
            logger.info(f"=== Начинаем отправку уведомлений ===")
            from core.database.session import get_sync_session
            from shared.services.notification_service import NotificationService
            from core.config.settings import settings
            from domain.entities.user import User
            
            # Получаем синхронную сессию для NotificationService
            session_factory = get_sync_session
            with session_factory() as session:
                logger.info(f"Sending notification to owner_id={obj.owner_id}, application_id={application.id}")
                
                telegram_token = settings.telegram_bot_token
                logger.info(f"Telegram token получен: {telegram_token[:10]}...")
                
                notification_service = NotificationService(
                    session=session,
                    telegram_token=telegram_token
                )
                
                # Получаем информацию о пользователе для имени в уведомлении
                user_query = select(User).where(User.id == user_id)
                user_result = session.execute(user_query)
                applicant_user = user_result.scalar_one_or_none()
                
                applicant_name = "Пользователь"
                if applicant_user:
                    if applicant_user.first_name or applicant_user.last_name:
                        parts = []
                        if applicant_user.first_name:
                            parts.append(applicant_user.first_name.strip())
                        if applicant_user.last_name:
                            parts.append(applicant_user.last_name.strip())
                        applicant_name = " ".join(parts) if parts else applicant_user.username
                    elif applicant_user.username:
                        applicant_name = applicant_user.username
                
                # Уведомляем владельца конкретного объекта
                owner_id = obj.owner_id
                logger.info(f"Creating notification for owner user_id={owner_id}, for application_id={application.id}")
                
                notification_payload = {
                    "application_id": application.id,
                    "applicant_name": applicant_name,
                    "object_name": obj.name,
                    "message": message
                }
                
                logger.info(f"Notification payload: {notification_payload}")
                
                # Создаем уведомления для владельца  
                try:
                    notifications = notification_service.create(
                        [owner_id],
                        "application_created",
                        notification_payload,
                        send_telegram=True
                    )
                    logger.info(f"Notification created: {len(notifications)} notifications")
                    session.commit()
                    logger.info(f"Notifications committed to database successfully")
                except Exception as service_error:
                    logger.error(f"Error in notification service create: {service_error}")
                    raise service_error
                    
        except Exception as notification_error:
            logger.error(f"Ошибка отправки уведомлений: {notification_error}")
            # Не прерываем выполнение основной операции

        return {"id": application.id, "status": application.status.value, "message": "Заявка успешно создана"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Ошибка создания заявки: {exc}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания заявки: {exc}")

@router.get("/api/applications/{application_id}")
async def employee_application_details_api(
    application_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Необходима авторизация")

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    query = select(Application, Object.name.label("object_name")).join(Object).where(
        and_(Application.id == application_id, Application.applicant_id == user_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    application = row.Application
    return {
        "id": application.id,
        "object_id": application.object_id,
        "object_name": row.object_name,
        "status": application.status.value.lower(),
        "message": application.message,
        "preferred_schedule": application.preferred_schedule,
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "interview_scheduled_at": application.interview_scheduled_at.isoformat() if application.interview_scheduled_at else None,
        "interview_type": application.interview_type,
        "interview_result": application.interview_result
    }


@router.get("/api/applications/{application_id}/interview")
async def employee_application_interview_api(
    application_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Необходима авторизация")

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    query = select(Application, Object.name.label("object_name"), Object.address.label("object_address"))\
        .join(Object).where(and_(Application.id == application_id, Application.applicant_id == user_id))
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Заявка или собеседование не найдены")

    application = row.Application
    if application.status != ApplicationStatus.INTERVIEW:
        raise HTTPException(status_code=404, detail="Собеседование не назначено")

    return {
        "application_id": application.id,
        "object_name": row.object_name,
        "location": row.object_address,
        "scheduled_at": application.interview_scheduled_at.isoformat() if application.interview_scheduled_at else None,
        "type": application.interview_type,
        "notes": application.interview_result,
        "contact_person": None,
        "contact_phone": None
    }

@router.get("/calendar", response_class=HTMLResponse)
async def employee_calendar(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Календарь сотрудника (общий календарь объектов/смен)."""
    try:
        from datetime import date
        import json

        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        user_obj = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user_obj:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        employee_display_name = (f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip()
                                 or user_obj.username
                                 or f"ID {user_obj.id}")

        available_interfaces = await get_available_interfaces_for_user(current_user, db)

        # Текущая дата по умолчанию
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        # Получаем объекты, доступные сотруднику через ObjectAccessService
        from sqlalchemy.orm import selectinload
        from domain.entities.contract import Contract
        from domain.entities.object import Object
        from domain.entities.time_slot import TimeSlot
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift import Shift

        # Получаем доступные объекты через ObjectAccessService
        telegram_id = current_user.get("telegram_id") or current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "telegram_id", None)
        if not telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        access_service = ObjectAccessService(db)
        accessible_objects = await access_service.get_accessible_objects(telegram_id, "employee")
        all_object_ids = [obj["id"] for obj in accessible_objects]

        # Опциональная фильтрация по выбранному объекту (только для данных календаря)
        object_ids = all_object_ids.copy()  # Для данных календаря
        if object_id and object_id in all_object_ids:
            object_ids = [object_id]  # Фильтруем данные календаря

        # Карта объектов и список для фильтра (ВСЕГДА все доступные объекты)
        objects_map = {}
        objects_list = []  # Список объектов для фильтра (все доступные)
        if all_object_ids:
            objs_q = select(Object).where(Object.id.in_(all_object_ids))
            objs = (await db.execute(objs_q)).scalars().all()
            objects_map = {o.id: o for o in objs}
            # Преобразуем в список словарей для шаблона (ВСЕ доступные объекты)
            objects_list = [{"id": o.id, "name": o.name} for o in objs]

        # Тайм-слоты с текущего месяца до конца года (как у владельца)
        timeslots_data = []
        if object_ids:
            start_date = date(year, month, 1)
            end_date = date(year, 12, 31)

            ts_q = select(TimeSlot).options(selectinload(TimeSlot.object)).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= start_date,
                    TimeSlot.slot_date < end_date,
                    TimeSlot.is_active == True,
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)

            timeslots = (await db.execute(ts_q)).scalars().all()
            for slot in timeslots:
                obj = objects_map.get(slot.object_id)
                if not obj:
                    continue
                timeslots_data.append({
                    "id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": obj.name,
                    "date": slot.slot_date,  # date object, not isoformat
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate) if obj.hourly_rate else 0,
                    "max_employees": slot.max_employees or 1,
                    "is_active": slot.is_active,
                    "notes": slot.notes or "",
                })

        # Смены за месяц (запланированные и фактические)
        shifts_data = []
        if object_ids:
            start_date = date(year, month, 1)
            end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

            # Запланированные
            sched_q = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.object_id.in_(object_ids),
                    ShiftSchedule.planned_start >= start_date,
                    ShiftSchedule.planned_start < end_date,
                )
            ).order_by(ShiftSchedule.planned_start)
            scheduled = (await db.execute(sched_q)).scalars().all()

            # Фактические
            act_q = select(Shift).options(selectinload(Shift.user)).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time < end_date,
                )
            ).order_by(Shift.start_time)
            actual = (await db.execute(act_q)).scalars().all()

            # Преобразуем (запланированные)
            # Загрузим пользователей для отображения имени
            user_ids = list({s.user_id for s in scheduled if s.user_id})
            users_map = {}
            if user_ids:
                users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
                users_map = {u.id: u for u in users_res.scalars().all()}

            for s in scheduled:
                obj = objects_map.get(s.object_id)
                if not obj:
                    continue
                emp = users_map.get(s.user_id)
                emp_name = (f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else None)
                shifts_data.append({
                    "id": f"schedule_{s.id}",
                    "object_id": s.object_id,
                    "object_name": obj.name,
                    "date": s.planned_start.date(),  # date object, not isoformat
                    "start_time": web_timezone_helper.format_time_with_timezone(s.planned_start, obj.timezone if obj else 'Europe/Moscow'),
                    "end_time": web_timezone_helper.format_time_with_timezone(s.planned_end, obj.timezone if obj else 'Europe/Moscow'),
                    "status": s.status,
                    "time_slot_id": s.time_slot_id,
                    "employee_name": emp_name,
                    "notes": s.notes or "",
                })

            # Преобразуем (фактические)
            act_user_ids = list({sh.user_id for sh in actual if sh.user_id})
            act_users_map = {}
            if act_user_ids:
                act_users_res = await db.execute(select(User).where(User.id.in_(act_user_ids)))
                act_users_map = {u.id: u for u in act_users_res.scalars().all()}

            for sh in actual:
                obj = objects_map.get(sh.object_id)
                if not obj:
                    continue
                emp = act_users_map.get(sh.user_id)
                emp_name = (f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else None)
                shifts_data.append({
                    "id": sh.id,
                    "object_id": sh.object_id,
                    "object_name": obj.name,
                    "date": sh.start_time.date(),  # date object, not isoformat
                    "start_time": web_timezone_helper.format_time_with_timezone(sh.start_time, obj.timezone if obj else 'Europe/Moscow'),
                    "end_time": web_timezone_helper.format_time_with_timezone(sh.end_time, obj.timezone if obj else 'Europe/Moscow') if sh.end_time else None,
                    "status": sh.status,
                    "time_slot_id": sh.time_slot_id,
                    "employee_name": emp_name,
                    "notes": sh.notes or "",
                })

        # Сетка календаря
        calendar_weeks = create_calendar_grid(year, month, timeslots_data, shifts_data)

        # JSON для шаблона
        def _serialize(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            from datetime import datetime as _dt
            if isinstance(obj, _dt):
                return obj.isoformat()
            raise TypeError(str(type(obj)))

        calendar_weeks_json = json.dumps(calendar_weeks, default=_serialize)

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0

        # Заголовок месяца
        RU_MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        title = f"{RU_MONTHS[month]} {year}"

        return templates.TemplateResponse("employee/calendar.html", {
            "request": request,
            "current_user": current_user,
            "title": title,
            "calendar_title": title,
            "year": year,
            "month": month,
            "current_date": today,
            "calendar_weeks": calendar_weeks,
            "calendar_weeks_json": calendar_weeks_json,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "show_today_button": True,
            "current_employee_id": user_id,
            "current_employee_name": employee_display_name,
            "objects": objects_list,
            "selected_object_id": object_id,
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки календаря: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки календаря: {e}")


@router.get("/calendar/api/objects")
async def employee_calendar_api_objects(
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """API для получения объектов календаря сотрудника - только объекты, где у сотрудника есть контракт."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Проверяем кэш
        from core.cache.redis_cache import cache
        cache_key = f"api_objects:employee_{user_id}"
        cached_data = await cache.get(cache_key, serialize="json")
        if cached_data:
            logger.info(f"Employee calendar objects API: cache HIT for user {user_id}")
            return cached_data
        
        logger.info(f"Employee calendar objects API: cache MISS for user {user_id}")

        # Получаем объекты, где у сотрудника есть активный контракт
        from domain.entities.contract import Contract
        contracts_query = select(Contract).where(
            Contract.employee_id == user_id,
            Contract.status == "active"
        )
        contracts_result = await db.execute(contracts_query)
        contracts = contracts_result.scalars().all()
        
        object_ids = [contract.object_id for contract in contracts]
        
        if not object_ids:
            return []
        
        # Получаем объекты по ID
        objects_query = select(Object).where(Object.id.in_(object_ids))
        objects_result = await db.execute(objects_query)
        objects = objects_result.scalars().all()
        
        objects_data = [{
            "id": obj.id,
            "name": obj.name,
            "address": obj.address,
            "hourly_rate": float(obj.hourly_rate) if obj.hourly_rate else 0.0,
            "opening_time": obj.opening_time.strftime("%H:%M") if obj.opening_time else "09:00",
            "closing_time": obj.closing_time.strftime("%H:%M") if obj.closing_time else "18:00"
        } for obj in objects]
        
        # Сохраняем в кэш (TTL 2 минуты)
        await cache.set(cache_key, objects_data, ttl=120, serialize="json")
        logger.info(f"Employee calendar objects API: cached {len(objects_data)} objects")
        
        return objects_data
        
    except Exception as e:
        logger.error(f"Error getting employee calendar objects: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения объектов календаря")


@router.get("/api/calendar/employees-for-object/{object_id}")
async def employee_calendar_employees_for_object(
    object_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Возвращает текущего сотрудника, если у него есть доступ к объекту."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        if isinstance(current_user, dict):
            telegram_id = current_user.get("telegram_id") or current_user.get("id")
        else:
            telegram_id = getattr(current_user, "telegram_id", None)

        if not telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        access_service = ObjectAccessService(db)
        accessible_objects = await access_service.get_accessible_objects(telegram_id, "employee")
        accessible_object_ids = {obj["id"] for obj in accessible_objects}

        if object_id not in accessible_object_ids:
            return []

        user_obj = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user_obj:
            return []

        display_name = (f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip()
                        or user_obj.username
                        or f"ID {user_obj.id}")

        return [{
            "id": int(user_obj.id),
            "name": display_name
        }]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee list for object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения сотрудников для объекта")


@router.get("/calendar/api/timeslot/{timeslot_id}")
async def employee_calendar_timeslot_detail(
    timeslot_id: int,
    current_user: dict = Depends(require_employee_or_applicant)
):
    """Детали тайм-слота для модалки быстрого планирования сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")

            if isinstance(current_user, dict):
                telegram_id = current_user.get("telegram_id") or current_user.get("id")
            else:
                telegram_id = getattr(current_user, "telegram_id", None)

            if not telegram_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")

            access_service = ObjectAccessService(db)
            accessible_objects = await access_service.get_accessible_objects(telegram_id, "employee")
            accessible_object_ids = {obj["id"] for obj in accessible_objects}

            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступных объектов")

            slot = (await db.execute(
                select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id)
            )).scalar_one_or_none()

            if not slot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден")

            if slot.object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к тайм-слоту")

            tz_name = slot.object.timezone if slot.object and slot.object.timezone else 'Europe/Moscow'

            scheduled_query = select(ShiftSchedule).options(selectinload(ShiftSchedule.user)).where(
                and_(
                    ShiftSchedule.time_slot_id == timeslot_id,
                    ShiftSchedule.status.in_(["planned", "confirmed"])
                )
            ).order_by(ShiftSchedule.planned_start)
            scheduled_rows = (await db.execute(scheduled_query)).scalars().all()

            scheduled = [
                {
                    "id": sched.id,
                    "user_id": sched.user_id,
                    "user_name": f"{sched.user.first_name or ''} {sched.user.last_name or ''}".strip() if sched.user else None,
                    "status": sched.status,
                    "start_time": web_timezone_helper.format_datetime_with_timezone(sched.planned_start, tz_name, "%H:%M") if sched.planned_start else None,
                    "end_time": web_timezone_helper.format_datetime_with_timezone(sched.planned_end, tz_name, "%H:%M") if sched.planned_end else None,
                    "planned_start": sched.planned_start.isoformat() if sched.planned_start else None,
                    "planned_end": sched.planned_end.isoformat() if sched.planned_end else None,
                }
                for sched in scheduled_rows
            ]

            linked_shifts_query = select(Shift).options(selectinload(Shift.user)).where(
                Shift.time_slot_id == timeslot_id
            ).order_by(Shift.start_time)
            linked_shifts = (await db.execute(linked_shifts_query)).scalars().all()

            day_start = datetime.combine(slot.slot_date, time.min)
            day_end = datetime.combine(slot.slot_date, time.max)
            overlap_query = select(Shift).options(selectinload(Shift.user)).where(
                and_(
                    Shift.object_id == slot.object_id,
                    Shift.start_time >= day_start,
                    Shift.start_time <= day_end
                )
            ).order_by(Shift.start_time)
            potential_overlaps = (await db.execute(overlap_query)).scalars().all()

            linked_ids = {shift.id for shift in linked_shifts}

            def overlaps_timeslot(shift: Shift) -> bool:
                shift_start = shift.start_time.time()
                shift_end = shift.end_time.time() if shift.end_time else None
                if not shift_end:
                    return shift_start < slot.end_time
                return shift_start < slot.end_time and slot.start_time < shift_end

            combined_shifts = linked_shifts + [
                shift for shift in potential_overlaps
                if shift.id not in linked_ids and overlaps_timeslot(shift)
            ]

            actual = [
                {
                    "id": shift.id,
                    "user_id": shift.user_id,
                    "user_name": f"{shift.user.first_name or ''} {shift.user.last_name or ''}".strip() if shift.user else None,
                    "status": shift.status,
                    "start_time": web_timezone_helper.format_datetime_with_timezone(shift.start_time, tz_name, "%H:%M") if shift.start_time else None,
                    "end_time": web_timezone_helper.format_datetime_with_timezone(shift.end_time, tz_name, "%H:%M") if shift.end_time else None,
                }
                for shift in combined_shifts
            ]

            return {
                "slot": {
                    "id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": slot.object.name if slot.object else None,
                    "date": slot.slot_date.strftime("%Y-%m-%d"),
                    "start_time": slot.start_time.strftime("%H:%M") if slot.start_time else None,
                    "end_time": slot.end_time.strftime("%H:%M") if slot.end_time else None,
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else None,
                    "max_employees": slot.max_employees or 1,
                    "is_active": slot.is_active,
                    "notes": slot.notes or "",
                },
                "scheduled": scheduled,
                "actual": actual
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee timeslot detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")


@router.get("/notifications/center", response_class=HTMLResponse)
async def employee_notifications_center(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Центр уведомлений для сотрудника.
    """
    # Получаем user_id (функция определена выше в этом файле)
    user_id = await get_user_id_from_current_user(current_user, db)
    
    # Определяем доступные интерфейсы на основе ролей пользователя
    available_interfaces = []
    user_roles = current_user.get("roles", []) if isinstance(current_user, dict) else []
    
    if "admin" in user_roles:
        available_interfaces.append({"title": "Администратор", "url": "/admin"})
    if "owner" in user_roles:
        available_interfaces.append({"title": "Владелец", "url": "/owner"})
    if "manager" in user_roles:
        available_interfaces.append({"title": "Управляющий", "url": "/manager"})
    if "employee" in user_roles or current_user.get("role") == "employee":
        available_interfaces.append({"title": "Сотрудник", "url": "/employee"})
    if not available_interfaces:  # Если нет ролей, значит соискатель
        available_interfaces.append({"title": "Соискатель", "url": "/employee"})
    
    # Подсчет заявок для навигации
    applications_count = await db.execute(
        select(func.count(Application.id)).where(Application.applicant_id == user_id)
    )
    applications_count = applications_count.scalar() or 0
    
    return templates.TemplateResponse(
        "employee/notifications/center.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
        }
    )


@router.get("/api/employees")
async def employee_api_employees(
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Возвращает только текущего сотрудника для панели сотрудников."""
    import time
    start_time = time.time()
    
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        # Быстрая проверка кэша ДО любых операций с БД
        # Используем telegram_id из JWT токена (доступен в current_user)
        user_telegram_id = current_user.get("telegram_id") or current_user.get("id") if isinstance(current_user, dict) else getattr(current_user, "telegram_id", None)
        
        if user_telegram_id:
            from core.cache.redis_cache import cache
            cache_start = time.time()
            cache_key = f"api_employees:employee_tg_{user_telegram_id}"
            cached_data = await cache.get(cache_key, serialize="json")
            cache_time = (time.time() - cache_start) * 1000
            
            if cached_data:
                total_time = (time.time() - start_time) * 1000
                logger.info(f"Employee employees API: cache HIT for telegram_id {user_telegram_id}, cache_time={cache_time:.2f}ms, total_time={total_time:.2f}ms")
                return cached_data

        # current_user теперь объект User, а не словарь
        if isinstance(current_user, dict):
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        else:
            # current_user - это объект User
            user = current_user
        
        if not user:
            return []

        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or f"ID {user.id}"
        employee_data = [{
            "id": int(user.id),
            "name": str(name),
            "role": "employee",
            "is_active": bool(user.is_active),
            "telegram_id": int(user.telegram_id) if user.telegram_id else None,
            # для dnd назначения самим сотрудником на слот
            "draggable": True,
        }]
        
        # Сохраняем в кэш (TTL 2 минуты) с ключом по telegram_id
        from core.cache.redis_cache import cache
        cache_key = f"api_employees:employee_tg_{user.telegram_id}"
        await cache.set(cache_key, employee_data, ttl=120, serialize="json")
        total_time = (time.time() - start_time) * 1000
        logger.info(f"Employee employees API: cache MISS, cached for user {user.id}, total_time={total_time:.2f}ms")
        
        return employee_data
    except Exception as e:
        logger.error(f"Ошибка загрузки сотрудника: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников")


def _create_calendar_grid_employee(
    year: int,
    month: int,
    timeslots: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]] | None = None,
) -> List[List[Dict[str, Any]]]:
    """Создает календарную сетку для сотрудника (показываем все активные тайм‑слоты и все смены, кроме отмененных)."""
    import calendar as _cal
    from datetime import date, timedelta

    if shifts is None:
        shifts = []

    first_day = date(year, month, 1)
    last_day = date(year, month, _cal.monthrange(year, month)[1])
    
    # Находим понедельник для начала календаря
    today = date.today()
    if today.year == year and today.month == month:
        # Если смотрим текущий месяц - начинаем за 2 недели до текущей
        current_monday = today - timedelta(days=today.weekday())
        first_monday = current_monday - timedelta(weeks=2)
    else:
        # Для других месяцев - начинаем с первого понедельника месяца
        first_monday = first_day - timedelta(days=first_day.weekday())

    calendar_grid: List[List[Dict[str, Any]]] = []
    current_date = first_monday

    for _ in range(6):
        week_data: List[Dict[str, Any]] = []
        for _d in range(7):
            current_date_str = current_date.isoformat()

            # Смены за день
            all_day_shifts = [s for s in shifts if s.get("date") == current_date_str]
            day_shifts = [s for s in all_day_shifts if s.get("status") != "cancelled"]

            # Тайм-слоты за день
            day_timeslots = []
            for slot in timeslots:
                if slot.get("date") == current_date_str and slot.get("is_active", True):
                    slot_with_status = slot.copy()
                    slot_with_status["status"] = "available"
                    day_timeslots.append(slot_with_status)

            week_data.append({
                "date": current_date,
                "day": current_date.day,
                "is_current_month": current_date.month == month,
                "is_other_month": current_date.month != month,
                "is_today": current_date == date.today(),
                "timeslots": day_timeslots,
                "timeslots_count": len(day_timeslots),
                "shifts": day_shifts,
                "shifts_count": len(day_shifts),
            })

            current_date += timedelta(days=1)

        calendar_grid.append(week_data)

    return calendar_grid


@router.get("/shifts", response_class=HTMLResponse)
async def employee_shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр: active, planned, completed, cancelled"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Табличный список смен сотрудника (по аналогии с владельцем)."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        # Фильтр периода
        from datetime import datetime as _dt, time as _time
        df = _dt.strptime(date_from, "%Y-%m-%d") if date_from else None
        dt = _dt.strptime(date_to, "%Y-%m-%d") if date_to else None

        # Фактические смены
        from sqlalchemy import select, desc, and_
        shifts_q = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.user)
        ).where(Shift.user_id == user_id)
        if df:
            shifts_q = shifts_q.where(Shift.start_time >= df)
        if dt:
            shifts_q = shifts_q.where(Shift.start_time <= dt)

        # Запланированные смены
        schedules_q = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user)
        ).where(ShiftSchedule.user_id == user_id)
        if df:
            schedules_q = schedules_q.where(ShiftSchedule.planned_start >= df)
        if dt:
            schedules_q = schedules_q.where(ShiftSchedule.planned_start <= dt)

        # Получение
        shifts = (await db.execute(shifts_q.order_by(desc(Shift.created_at)))).scalars().all()
        schedules = (await db.execute(schedules_q.order_by(desc(ShiftSchedule.created_at)))).scalars().all()

        # Форматирование
        all_shifts = []
        for s in shifts:
            all_shifts.append({
                'id': s.id,
                'type': 'shift',
                'object_name': s.object.name if s.object else '-',
                'user_name': f"{s.user.first_name} {s.user.last_name or ''}".strip() if s.user else '-',
                'start_time': web_timezone_helper.format_datetime_with_timezone(s.start_time, s.object.timezone if s.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if s.start_time else '-',
                'end_time': web_timezone_helper.format_datetime_with_timezone(s.end_time, s.object.timezone if s.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if s.end_time else '-',
                'status': s.status,
                'total_hours': float(s.total_hours) if s.total_hours else None,
                'total_payment': float(s.total_payment) if s.total_payment else None,
            })
        for sc in schedules:
            all_shifts.append({
                'id': sc.id,
                'type': 'schedule',
                'object_name': sc.object.name if sc.object else '-',
                'user_name': f"{sc.user.first_name} {sc.user.last_name or ''}".strip() if sc.user else '-',
                'start_time': web_timezone_helper.format_datetime_with_timezone(sc.planned_start, sc.object.timezone if sc.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if sc.planned_start else '-',
                'end_time': web_timezone_helper.format_datetime_with_timezone(sc.planned_end, sc.object.timezone if sc.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if sc.planned_end else '-',
                'status': sc.status,
                'total_hours': None,
                'total_payment': None,
            })

        # Фильтр статуса
        if status:
            if status == 'planned':
                all_shifts = [x for x in all_shifts if x['type'] == 'schedule']
            else:
                all_shifts = [x for x in all_shifts if x['status'] == status]

        # Сортировка и пагинация
        all_shifts.sort(key=lambda x: x['start_time'] or '', reverse=True)
        total = len(all_shifts)
        start_i = (page - 1) * per_page
        end_i = start_i + per_page
        page_shifts = all_shifts[start_i:end_i]

        # Интерфейсы
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Подсчет заявок для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0

        return templates.TemplateResponse("employee/shifts/list.html", {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "shifts": page_shifts,
            "stats": {
                "total": total,
                "active": len([s for s in all_shifts if s['status'] == 'active']),
                "planned": len([s for s in all_shifts if s['type'] == 'schedule']),
                "completed": len([s for s in all_shifts if s['status'] == 'completed'])
            },
            "filters": {"status": status, "date_from": date_from, "date_to": date_to},
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1)//per_page}
        })
    except Exception as e:
        logger.error(f"Error loading employee shifts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки смен сотрудника")

@router.get("/profile", response_class=HTMLResponse)
async def employee_profile(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница профиля сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем данные пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Статистика профиля
        logger.info(f"Getting applications count for user_id: {user_id}")
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        logger.info(f"Applications count: {applications_count}")
        
        interviews_count = await db.execute(
            select(func.count(Interview.id)).where(Interview.applicant_id == user_id)
        )
        interviews_count = interviews_count.scalar() or 0
        
        successful_count = await db.execute(
            select(func.count(Application.id)).where(
                and_(Application.applicant_id == user_id, Application.status == 'APPROVED')
            )
        )
        successful_count = successful_count.scalar() or 0
        
        in_progress_count = await db.execute(
            select(func.count(Application.id)).where(
                and_(Application.applicant_id == user_id, Application.status == 'PENDING')
            )
        )
        in_progress_count = in_progress_count.scalar() or 0
        
        logger.info(f"Creating profile_stats with applications_count: {applications_count}")
        profile_stats = {
            'applications': applications_count,
            'interviews': interviews_count,
            'successful': successful_count,
            'in_progress': in_progress_count
        }
        logger.info(f"Profile stats created: {profile_stats}")
        
        # Категории работы
        work_categories = [
            "Уборка и санитария",
            "Обслуживание клиентов", 
            "Безопасность",
            "Техническое обслуживание",
            "Административные задачи",
            "Продажи и маркетинг",
            "Складские операции",
            "Специализированные задачи"
        ]
        
        return templates.TemplateResponse("employee/profile.html", {
            "request": request,
            "current_user": user,
            "user": user,
            "profile_stats": profile_stats,
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "work_categories": work_categories,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки профиля: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки профиля: {e}")


@router.post("/profile")
async def employee_profile_update(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление профиля сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные из формы
        try:
            # Попробуем получить JSON данные
            json_data = await request.json()
            logger.info(f"Received JSON data: {json_data}")
            form_data = json_data
        except:
            # Если не JSON, то form data
            form_data = await request.form()
            logger.info(f"Received form data: {dict(form_data)}")
        
        # Получаем пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Обновляем поля с правильной кодировкой
        if 'first_name' in form_data:
            user.first_name = form_data['first_name']
            logger.info(f"Updated first_name: {user.first_name}")
        if 'last_name' in form_data:
            user.last_name = form_data['last_name']
            logger.info(f"Updated last_name: {user.last_name}")
        if 'phone' in form_data:
            user.phone = form_data['phone']
            logger.info(f"Updated phone: {user.phone}")
        if 'email' in form_data:
            user.email = form_data['email'] or None
            logger.info(f"Updated email: {user.email}")
        if 'birth_date' in form_data:
            birth_date_str = form_data['birth_date']
            if birth_date_str:
                try:
                    from datetime import datetime
                    user.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                    logger.info(f"Updated birth_date: {user.birth_date}")
                except ValueError:
                    logger.error(f"Invalid birth_date format: {birth_date_str}")
            else:
                user.birth_date = None
        if 'work_experience' in form_data:
            user.work_experience = form_data['work_experience']
        if 'education' in form_data:
            user.education = form_data['education']
        if 'skills' in form_data:
            user.skills = form_data['skills']
        if 'about' in form_data:
            user.about = form_data['about']
        if 'preferred_schedule' in form_data:
            user.preferred_schedule = form_data['preferred_schedule']
        if 'min_salary' in form_data:
            min_salary_str = form_data['min_salary']
            if min_salary_str and min_salary_str.isdigit():
                user.min_salary = int(min_salary_str)
                logger.info(f"Updated min_salary: {user.min_salary}")
            else:
                user.min_salary = None
        if 'availability_notes' in form_data:
            user.availability_notes = form_data['availability_notes']
        if 'preferred_work_types' in form_data:
            # Для чекбоксов form_data может быть списком или строкой
            work_types = form_data.get('preferred_work_types')
            if isinstance(work_types, list):
                user.preferred_work_types = work_types
            elif isinstance(work_types, str):
                user.preferred_work_types = [work_types]
            else:
                user.preferred_work_types = []
            logger.info(f"Updated preferred_work_types: {user.preferred_work_types}")
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Profile updated for user {user_id}")
        
        result = {"success": True, "message": "Профиль успешно обновлен"}
        logger.info(f"Returning result: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления профиля")


@router.post("/api/profile/avatar")
async def employee_upload_avatar(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Загрузка фото профиля сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Пользователь не авторизован")
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем файл из формы
        form = await request.form()
        avatar_file = form.get("avatar")
        
        if not avatar_file:
            raise HTTPException(status_code=400, detail="Файл не предоставлен")
        
        # Проверяем тип файла
        if not hasattr(avatar_file, 'content_type') or not avatar_file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
        
        # Проверяем размер (максимум 5MB)
        file_content = await avatar_file.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Размер файла не должен превышать 5MB")
        
        # Получаем пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Загружаем файл в хранилище
        from shared.services.media_storage import get_media_storage_client
        storage_client = get_media_storage_client()
        
        # Определяем имя файла
        file_name = avatar_file.filename or f"avatar_{user_id}.jpg"
        folder = f"profiles/{user_id}"
        
        # Загружаем
        media_file = await storage_client.upload(
            file_content=file_content,
            file_name=file_name,
            content_type=avatar_file.content_type,
            folder=folder,
            metadata={"user_id": user_id, "type": "avatar"}
        )
        
        # Получаем URL
        avatar_url = await storage_client.get_url(media_file.key, expires_in=31536000)  # 1 год
        
        # Сохраняем URL в профиле
        user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Avatar uploaded: user_id={user_id}, avatar_url={avatar_url}, storage_key={media_file.key}")
        
        return JSONResponse(content={
            "success": True,
            "avatar_url": avatar_url,
            "message": "Фото профиля успешно загружено"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error uploading avatar: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки фото: {str(e)}")


@router.get("/history", response_class=HTMLResponse)
async def employee_history(
    request: Request,
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница истории активности: заявки, собеседования, смены."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Период
        from datetime import datetime as _dt
        df = _dt.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        dt = _dt.strptime(date_to, "%Y-%m-%d").date() if date_to else None

        # Получаем историю событий
        history_events = []
        
        # Заявки
        applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(Application.applicant_id == user_id).order_by(Application.created_at.desc())
        
        applications_result = await db.execute(applications_query)
        for row in applications_result:
            history_events.append({
                'id': row.Application.id,
                'type': 'application',
                'title': f'Подана заявка на работу',
                'description': f'Заявка на объект "{row.object_name}"',
                'object_name': row.object_name,
                'status': row.Application.status,
                'created_at': row.Application.created_at,
                'start': row.Application.created_at,
                'end': None
            })
        
        # Собеседования
        interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(Interview.applicant_id == user_id)
        if df:
            interviews_query = interviews_query.where(Interview.scheduled_at >= df)
        if dt:
            # включительно конец дня
            from datetime import datetime, time
            interviews_query = interviews_query.where(Interview.scheduled_at <= datetime.combine(dt, time.max))
        interviews_query = interviews_query.order_by(Interview.scheduled_at.desc())
        
        interviews_result = await db.execute(interviews_query)
        for row in interviews_result:
            history_events.append({
                'id': row.Interview.id,
                'type': 'interview',
                'title': f'Собеседование',
                'description': f'Собеседование на объекте "{row.object_name}"',
                'object_name': row.object_name,
                'status': row.Interview.status,
                'created_at': row.Interview.scheduled_at,
                'start': row.Interview.scheduled_at,
                'end': None
            })
        
        # Смены сотрудника: запланированные (расписание), фактические (смены)
        # Запланированные
        sched_q = select(ShiftSchedule, Object.name.label('object_name')).join(
            Object, ShiftSchedule.object_id == Object.id
        ).where(ShiftSchedule.user_id == user_id)
        if df:
            sched_q = sched_q.where(ShiftSchedule.planned_start >= df)
        if dt:
            from datetime import datetime, time
            sched_q = sched_q.where(ShiftSchedule.planned_start <= datetime.combine(dt, time.max))
        sched_q = sched_q.order_by(ShiftSchedule.planned_start.desc())

        sched_res = await db.execute(sched_q)
        for row in sched_res:
            history_events.append({
                'id': row.ShiftSchedule.id,
                'type': 'planned_shift',
                'title': 'Запланирована смена',
                'description': f"Объект \"{row.object_name}\"",
                'object_name': row.object_name,
                'status': row.ShiftSchedule.status,
                'created_at': row.ShiftSchedule.planned_start,
                'start': row.ShiftSchedule.planned_start,
                'end': row.ShiftSchedule.planned_end,
                'is_cancellable': row.ShiftSchedule.status == 'planned'
            })

        # Фактические (активные/завершенные/отмененные)
        shift_q = select(Shift, Object.name.label('object_name')).join(
            Object, Shift.object_id == Object.id
        ).where(Shift.user_id == user_id)
        if df:
            shift_q = shift_q.where(Shift.start_time >= df)
        if dt:
            from datetime import datetime, time
            shift_q = shift_q.where(Shift.start_time <= datetime.combine(dt, time.max))
        shift_q = shift_q.order_by(Shift.start_time.desc())

        shift_res = await db.execute(shift_q)
        # Подсчет заработка по завершенным сменам
        total_earned_period = 0.0
        for row in shift_res:
            earned = None
            if row.Shift.status == 'completed':
                if row.Shift.total_payment:
                    earned = float(row.Shift.total_payment)
                elif row.Shift.start_time and row.Shift.end_time and row.Shift.hourly_rate:
                    duration = (row.Shift.end_time - row.Shift.start_time).total_seconds() / 3600.0
                    earned = float(row.Shift.hourly_rate) * max(0.0, duration)
                if earned:
                    total_earned_period += earned

            history_events.append({
                'id': row.Shift.id,
                'type': 'shift',
                'title': 'Смена',
                'description': f"Объект \"{row.object_name}\"",
                'object_name': row.object_name,
                'status': row.Shift.status,
                'created_at': row.Shift.start_time,
                'start': row.Shift.start_time,
                'end': row.Shift.end_time,
                'earned': earned
            })

        # Сортируем по дате
        history_events.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Статистика
        stats = {
            'total_applications': len([e for e in history_events if e['type'] == 'application']),
            'total_interviews': len([e for e in history_events if e['type'] == 'interview']),
            'total_shifts': len([e for e in history_events if e['type'] in ('shift', 'planned_shift')]),
            'completed_shifts': len([e for e in history_events if e.get('status') == 'completed']),
            'planned_shifts': len([e for e in history_events if e['type'] == 'planned_shift' and e.get('status') == 'planned']),
            'cancelled_shifts': len([e for e in history_events if e.get('status') == 'cancelled']),
            'earned_period': round(total_earned_period, 2),
            'success_rate': 0
        }
        
        successful_applications = len([e for e in history_events if e['type'] == 'application' and e['status'] == 'APPROVED'])
        if stats['total_applications'] > 0:
            stats['success_rate'] = round((successful_applications / stats['total_applications']) * 100)
        
        return templates.TemplateResponse("employee/history.html", {
        "request": request,
        "current_user": current_user,
            "history_events": history_events,
            "stats": stats,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "date_from": date_from,
            "date_to": date_to
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки истории: {e}")


@router.get("/api/calendar/data")
async def employee_calendar_api_data(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    object_ids: Optional[str] = Query(None, description="ID объектов через запятую"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Новый универсальный API для получения данных календаря сотрудника.
    Использует CalendarFilterService для правильной фильтрации смен.
    """
    try:
        # Генерируем ключ кэша
        import hashlib
        user_id = current_user.get("telegram_id") or current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        cache_key_data = f"calendar_api_employee:{user_id}:{start_date}:{end_date}:{object_ids or 'all'}"
        cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
        
        # Проверяем кэш
        from core.cache.redis_cache import cache
        cached_response = await cache.get(f"api_response:{cache_key}", serialize="json")
        if cached_response:
            logger.info(f"Employee calendar API: cache HIT for {start_date} to {end_date}")
            return cached_response
        
        logger.info(f"Employee calendar API: cache MISS for {start_date} to {end_date}, object_ids={object_ids}")
        logger.info(f"Current user type: {type(current_user)}, value: {current_user}")
        
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Парсим фильтр объектов
        object_filter = None
        if object_ids:
            try:
                object_filter = [int(obj_id.strip()) for obj_id in object_ids.split(",") if obj_id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ID объектов")
        
        # Получаем роль пользователя и telegram_id
        if isinstance(current_user, dict):
            user_role = current_user.get("role", "employee")
            user_telegram_id = current_user.get("telegram_id") or current_user.get("id")
        else:
            # current_user - это объект User
            user_role = getattr(current_user, "role", "employee")
            user_telegram_id = getattr(current_user, "telegram_id", None)
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные календаря через универсальный сервис
        calendar_service = CalendarFilterService(db)
        calendar_data = await calendar_service.get_calendar_data(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj,
            object_filter=object_filter
        )
        
        # Преобразуем в формат, совместимый с существующим JavaScript
        timeslots_data = []
        for ts in calendar_data.timeslots:
            if ts.status == TimeslotStatus.HIDDEN:
                continue
            timeslots_data.append({
                "id": ts.id,
                "object_id": ts.object_id,
                "object_name": ts.object_name,
                "date": ts.date.isoformat(),
                "start_time": ts.start_time.strftime("%H:%M"),
                "end_time": ts.end_time.strftime("%H:%M"),
                "hourly_rate": ts.hourly_rate,
                "max_employees": ts.max_employees,
                "current_employees": ts.current_employees,
                "available_slots": ts.available_slots,
                "occupied_minutes": ts.occupied_minutes,
                "free_minutes": ts.free_minutes,
                "occupancy_ratio": ts.occupancy_ratio,
                "status": ts.status.value,
                "status_label": ts.status_label,
                "is_active": ts.is_active,
                "notes": ts.notes,
                "work_conditions": ts.work_conditions,
                "shift_tasks": ts.shift_tasks,
                "coordinates": ts.coordinates,
                "can_edit": ts.can_edit,
                "can_plan": ts.can_plan,
                "can_view": ts.can_view
            })
        
        shifts_data = []
        for s in calendar_data.shifts:
            # Получаем часовой пояс объекта
            object_timezone = s.timezone if hasattr(s, 'timezone') and s.timezone else 'Europe/Moscow'
            import pytz
            tz = pytz.timezone(object_timezone)
            
            # Конвертируем время в локальное время объекта
            def convert_to_local_time(utc_time):
                if utc_time:
                    # Если время уже имеет timezone info, конвертируем
                    if utc_time.tzinfo:
                        return utc_time.astimezone(tz).replace(tzinfo=None)
                    else:
                        # Если время naive, считаем его UTC и конвертируем
                        utc_aware = pytz.UTC.localize(utc_time)
                        return utc_aware.astimezone(tz).replace(tzinfo=None)
                return None
            
            shifts_data.append({
                "id": s.id,
                "user_id": s.user_id,
                "user_name": s.user_name,
                "object_id": s.object_id,
                "object_name": s.object_name,
                "time_slot_id": s.time_slot_id,
                "start_time": convert_to_local_time(s.start_time).isoformat() if s.start_time else None,
                "end_time": convert_to_local_time(s.end_time).isoformat() if s.end_time else None,
                "planned_start": convert_to_local_time(s.planned_start).isoformat() if s.planned_start else None,
                "planned_end": convert_to_local_time(s.planned_end).isoformat() if s.planned_end else None,
                "shift_type": s.shift_type.value,
                "status": s.status.value,
                "hourly_rate": s.hourly_rate,
                "total_hours": s.total_hours,
                "total_payment": s.total_payment,
                "notes": s.notes,
                "is_planned": s.is_planned,
                "schedule_id": s.schedule_id,
                "actual_shift_id": s.actual_shift_id,
                "start_coordinates": s.start_coordinates,
                "end_coordinates": s.end_coordinates,
                "can_edit": s.can_edit,
                "can_cancel": s.can_cancel,
                "can_view": s.can_view
            })
        
        response_data = {
            "timeslots": timeslots_data,
            "shifts": shifts_data,
            "metadata": {
                "date_range_start": calendar_data.date_range_start.isoformat(),
                "date_range_end": calendar_data.date_range_end.isoformat(),
                "user_role": calendar_data.user_role,
                "total_timeslots": calendar_data.total_timeslots,
                "total_shifts": calendar_data.total_shifts,
                "planned_shifts": calendar_data.planned_shifts,
                "active_shifts": calendar_data.active_shifts,
                "completed_shifts": calendar_data.completed_shifts,
                "accessible_objects": calendar_data.accessible_objects
            }
        }
        
        # Сохраняем в кэш (TTL 2 минуты)
        await cache.set(f"api_response:{cache_key}", response_data, ttl=120, serialize="json")
        logger.info(f"Employee calendar API: response cached")
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee calendar data: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail="Ошибка получения данных календаря")


@router.get("/shifts/plan", response_class=HTMLResponse)
async def employee_shifts_plan(
    request: Request,
    object_id: Optional[int] = Query(None, description="ID объекта для предзаполнения"),
    return_to: Optional[str] = Query(None, description="URL возврата после планирования"),
    employee_id: Optional[int] = Query(None, description="ID сотрудника (игнорируется, используется текущий пользователь)"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница планирования смен для сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        if isinstance(current_user, dict):
            telegram_id = current_user.get("telegram_id") or current_user.get("id")
        else:
            telegram_id = getattr(current_user, "telegram_id", None)

        if not telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        access_service = ObjectAccessService(db)
        accessible_objects = await access_service.get_accessible_objects(telegram_id, "employee")
        objects_list = [{"id": obj["id"], "name": obj.get("name", f"Объект {obj['id']}")} for obj in accessible_objects]

        selected_object_id = None
        if object_id:
            if any(obj["id"] == object_id for obj in objects_list):
                selected_object_id = object_id

        user_obj = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user_obj:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        employee_display_name = (f"{user_obj.first_name or ''} {user_obj.last_name or ''}".strip()
                                 or user_obj.username
                                 or f"ID {user_obj.id}")

        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0

        login_service = RoleBasedLoginService(db)
        available_interfaces = await login_service.get_available_interfaces(user_id)

        return templates.TemplateResponse("employee/shifts/plan.html", {
            "request": request,
            "current_user": current_user,
            "objects": objects_list,
            "selected_object_id": selected_object_id,
            "return_to": return_to or "/employee/calendar",
            "preselected_employee_id": user_id,
            "current_employee_name": employee_display_name,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading employee shifts plan page: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки страницы планирования")


@router.get("/shifts/{shift_id}", response_class=HTMLResponse)
async def employee_shift_detail(
    request: Request, 
    shift_id: str,  # Поддержка префикса schedule_
    shift_type: Optional[str] = Query("shift"),
    current_user: dict = Depends(require_employee_or_applicant),
):
    """Детали смены сотрудника"""
    try:
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        # Определяем тип смены по ID
        if shift_id.startswith('schedule_'):
            actual_shift_id = int(shift_id.replace('schedule_', ''))
            actual_shift_type = "schedule"
        else:
            actual_shift_id = int(shift_id)
            actual_shift_type = shift_type or "shift"
        
        async with get_async_session() as db:
            # Получаем внутренний ID пользователя
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты сотрудника через контракты
            from shared.services.object_access_service import ObjectAccessService
            object_access_service = ObjectAccessService(db)
            
            # Получаем telegram_id для ObjectAccessService
            if isinstance(current_user, dict):
                telegram_id = current_user.get("telegram_id") or current_user.get("id")
            else:
                telegram_id = getattr(current_user, "telegram_id", None)
            
            accessible_objects = await object_access_service.get_accessible_objects(telegram_id, "employee")
            accessible_object_ids = [obj["id"] for obj in accessible_objects]
            
            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объектам")
            
            shift_data = None
            history_items: List[Dict[str, Any]] = []
            timezone = "Europe/Moscow"
            
            # Импортируем select для запросов
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            
            history_entries: List = []
            if actual_shift_type == "schedule":
                # Запланированная смена
                query = select(ShiftSchedule).options(
                    selectinload(ShiftSchedule.object),
                    selectinload(ShiftSchedule.user)
                ).where(ShiftSchedule.id == actual_shift_id)
                
                result = await db.execute(query)
                schedule = result.scalar_one_or_none()
                
                if not schedule:
                    raise HTTPException(status_code=404, detail="Запланированная смена не найдена")
                
                # Проверяем доступ к объекту
                if schedule.object_id not in accessible_object_ids:
                    raise HTTPException(status_code=403, detail="Нет доступа к объекту")
                
                shift_data = {
                    "id": f"schedule_{schedule.id}",
                    "type": "schedule",
                    "user_name": f"{schedule.user.first_name or ''} {schedule.user.last_name or ''}".strip(),
                    "object_name": schedule.object.name,
                    "object_address": schedule.object.address,
                    "planned_start": schedule.planned_start,
                    "planned_end": schedule.planned_end,
                    "status": schedule.status,
                    "hourly_rate": schedule.hourly_rate,
                    "notes": schedule.notes,
                    "created_at": schedule.created_at,
                    "updated_at": schedule.updated_at
                }
                history_service = ShiftHistoryService(db)
                schedule_history = await history_service.fetch_history(schedule_id=actual_shift_id)
                history_entries = list(schedule_history)
                if schedule.object and getattr(schedule.object, "timezone", None):
                    timezone = schedule.object.timezone
                if getattr(schedule, "actual_shifts", None):
                    for actual in schedule.actual_shifts:
                        history_entries.extend(
                            await history_service.fetch_history(shift_id=actual.id)
                        )
            else:
                # Фактическая смена
                query = select(Shift).options(
                    selectinload(Shift.object),
                    selectinload(Shift.user)
                ).where(Shift.id == actual_shift_id)
                
                result = await db.execute(query)
                shift = result.scalar_one_or_none()
                
                if not shift:
                    raise HTTPException(status_code=404, detail="Смена не найдена")
                
                # Проверяем доступ к объекту
                if shift.object_id not in accessible_object_ids:
                    raise HTTPException(status_code=403, detail="Нет доступа к объекту")
                
                shift_data = {
                    "id": shift.id,
                    "type": "shift",
                    "user_name": f"{shift.user.first_name or ''} {shift.user.last_name or ''}".strip(),
                    "object_name": shift.object.name,
                    "object_address": shift.object.address,
                    "start_time": shift.start_time,
                    "end_time": shift.end_time,
                    "status": shift.status,
                    "hourly_rate": shift.hourly_rate,
                    "total_hours": shift.total_hours,
                    "total_payment": shift.total_payment,
                    "notes": shift.notes,
                    "start_coordinates": shift.start_coordinates,
                    "end_coordinates": shift.end_coordinates,
                    "created_at": shift.created_at,
                    "updated_at": shift.updated_at
                }
                history_service = ShiftHistoryService(db)
                shift_history = await history_service.fetch_history(shift_id=actual_shift_id)
                history_entries = list(shift_history)
                if shift.object and getattr(shift.object, "timezone", None):
                    timezone = shift.object.timezone
                schedule_id = getattr(shift, "schedule_id", None)
                if schedule_id:
                    history_entries.extend(
                        await history_service.fetch_history(schedule_id=schedule_id)
                    )
            
            # Получаем доступные интерфейсы
            available_interfaces = await get_available_interfaces_for_user(current_user, db)

            actor_ids = {entry.actor_id for entry in history_entries if entry.actor_id}
            actor_names: Dict[int, str] = {}
            if actor_ids:
                users_result = await db.execute(
                    select(User.id, User.first_name, User.last_name).where(User.id.in_(actor_ids))
                )
                for row in users_result.all():
                    full_name = " ".join(filter(None, [row.last_name, row.first_name])).strip()
                    actor_names[row.id] = full_name or f"ID {row.id}"

            reason_titles: Dict[str, str] = {}
            owner_id = None
            if actual_shift_type == "schedule":
                owner_id = schedule.object.owner_id if schedule.object else None  # type: ignore
            else:
                owner_id = shift.object.owner_id if shift.object else None  # type: ignore

            if owner_id:
                reasons = await CancellationPolicyService.get_owner_reasons(
                    db,
                    owner_id,
                    only_visible=False,
                    only_active=True,
                )
                reason_titles = {reason.code: reason.title for reason in reasons}

            history_items = build_shift_history_items(
                history_entries,
                timezone=timezone,
                actor_names=actor_names,
                reason_titles=reason_titles,
            )
            
            return templates.TemplateResponse("employee/shifts/detail.html", {
                "request": request,
                "current_user": current_user,
                "shift": shift_data,
                "available_interfaces": available_interfaces,
                "history_items": history_items,
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in employee shift detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей смены")


@router.get("/timeslots/{timeslot_id}", response_class=HTMLResponse)
async def employee_timeslot_detail(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали тайм-слота сотрудника"""
    try:
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        # Получаем внутренний ID пользователя
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=400, detail="Пользователь не найден")
        
        # Получаем доступные объекты сотрудника через контракты
        from shared.services.object_access_service import ObjectAccessService
        object_access_service = ObjectAccessService(db)
        
        # Получаем telegram_id для ObjectAccessService
        if isinstance(current_user, dict):
            telegram_id = current_user.get("telegram_id") or current_user.get("id")
        else:
            telegram_id = getattr(current_user, "telegram_id", None)
        
        accessible_objects = await object_access_service.get_accessible_objects(telegram_id, "employee")
        accessible_object_ids = [obj["id"] for obj in accessible_objects]
        
        if not accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к объектам")
        
        # Получаем тайм-слот
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        timeslot_query = select(TimeSlot).options(
            selectinload(TimeSlot.object)
        ).where(TimeSlot.id == timeslot_id)
        
        timeslot_result = await db.execute(timeslot_query)
        timeslot = timeslot_result.scalar_one_or_none()
        
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Проверяем доступ к объекту
        if timeslot.object_id not in accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к объекту")
        
        # Получаем связанные смены и расписания
        from sqlalchemy import and_
        # Запланированные смены (исключаем отмененные)
        scheduled_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.user)
        ).where(
            and_(
                ShiftSchedule.time_slot_id == timeslot_id,
                ShiftSchedule.status != "cancelled"
            )
        )
        
        scheduled_result = await db.execute(scheduled_query)
        scheduled_shifts = scheduled_result.scalars().all()
        
        # Фактические смены
        actual_query = select(Shift).options(
            selectinload(Shift.user)
        ).where(Shift.time_slot_id == timeslot_id)
        
        actual_result = await db.execute(actual_query)
        actual_shifts = actual_result.scalars().all()
        
        # Получаем доступные интерфейсы
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        return templates.TemplateResponse("employee/timeslots/detail.html", {
            "request": request,
            "current_user": current_user,
            "timeslot": timeslot,
            "scheduled_shifts": scheduled_shifts,
            "actual_shifts": actual_shifts,
            "available_interfaces": available_interfaces
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in employee timeslot detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")


@router.post("/api/calendar/plan-shift")
async def employee_plan_shift(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """API: сотрудник планирует смену для себя на тайм-слот."""
    logger.info("Employee plan shift endpoint called")
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        data = await request.json()
        timeslot_id = data.get('timeslot_id')
        employee_id = data.get('employee_id')
        
        if not timeslot_id:
            raise HTTPException(status_code=400, detail="Не указан ID тайм-слота")
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Проверяем что сотрудник планирует смену только для себя
        if int(employee_id) != int(user_id):
            raise HTTPException(status_code=403, detail="Можно планировать смену только для себя")
        
        # Получаем тайм-слот
        timeslot = (await db.execute(select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id))).scalar_one_or_none()
        
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Проверяем, является ли пользователь владельцем объекта
        from domain.entities.user import User
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        is_owner = False
        if user_obj and user_obj.role == 'owner':
            # Проверяем, что объект принадлежит владельцу
            object_query = select(Object).where(Object.id == timeslot.object_id)
            object_result = await db.execute(object_query)
            obj = object_result.scalar_one_or_none()
            if obj and obj.owner_id == user_id:
                is_owner = True
        
        has_access = False
        employee_contract = None  # Договор сотрудника с доступом к объекту
        
        if is_owner:
            # Владелец может планировать себя на свои объекты
            has_access = True
        else:
            # Проверяем что у сотрудника есть активный договор с доступом к этому объекту
            contracts = (await db.execute(
                select(Contract).where(
                    and_(
                        Contract.employee_id == user_id,
                        Contract.is_active == True,
                        Contract.status == 'active'
                    )
                )
            )).scalars().all()
            
            import json as _json
            for contract in contracts:
                if not contract.allowed_objects:
                    continue
                # Нормализуем список разрешённых объектов к списку целых чисел
                raw_allowed = (
                    contract.allowed_objects
                    if isinstance(contract.allowed_objects, list)
                    else _json.loads(contract.allowed_objects)
                )
                try:
                    allowed_ids = {int(x) for x in raw_allowed}
                except Exception:
                    # Фолбэк на случай неожиданных типов в списке
                    allowed_ids = set()
                    for x in raw_allowed:
                        try:
                            allowed_ids.add(int(x))
                        except Exception:
                            continue

                if int(timeslot.object_id) in allowed_ids:
                    has_access = True
                    employee_contract = contract  # Сохраняем договор для определения ставки
                    break
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Нет доступа к объекту")
        
        slot_start_time = timeslot.start_time
        slot_end_time = timeslot.end_time
        if slot_start_time is None or slot_end_time is None:
            raise HTTPException(status_code=400, detail="У тайм-слота не указано время работы")

        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')

        if start_time_str:
            try:
                custom_start_time = datetime.strptime(start_time_str, "%H:%M").time()
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат времени начала (используйте ЧЧ:ММ)")
        else:
            custom_start_time = slot_start_time

        if end_time_str:
            try:
                custom_end_time = datetime.strptime(end_time_str, "%H:%M").time()
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат времени окончания (используйте ЧЧ:ММ)")
        else:
            custom_end_time = slot_end_time

        if custom_start_time >= custom_end_time:
            raise HTTPException(status_code=400, detail="Время окончания должно быть позже времени начала")

        if custom_start_time < slot_start_time or custom_end_time > slot_end_time:
            raise HTTPException(
                status_code=400,
                detail=f"Смена должна укладываться в границы тайм-слота: {slot_start_time.strftime('%H:%M')} - {slot_end_time.strftime('%H:%M')}"
            )

        import pytz
        object_timezone = timeslot.object.timezone if timeslot.object and timeslot.object.timezone else 'Europe/Moscow'
        tz = pytz.timezone(object_timezone)
        
        slot_datetime_naive = datetime.combine(timeslot.slot_date, custom_start_time)
        end_datetime_naive = datetime.combine(timeslot.slot_date, custom_end_time)

        slot_datetime = tz.localize(slot_datetime_naive).astimezone(pytz.UTC)
        end_datetime = tz.localize(end_datetime_naive).astimezone(pytz.UTC)

        # Проверяем, что сотрудник не занят в это время на других сменах
        overlapping_query = select(ShiftSchedule).where(
            ShiftSchedule.user_id == user_id,
            ShiftSchedule.status.in_(["planned", "confirmed"]),
            ShiftSchedule.planned_start < end_datetime,
            ShiftSchedule.planned_end > slot_datetime
        )
        overlapping_existing = (await db.execute(overlapping_query)).scalars().all()
        if overlapping_existing:
            raise HTTPException(status_code=400, detail="У вас уже запланирована смена в это время")

        # Проверяем лимит по количеству сотрудников в тайм-слоте для выбранного интервала
        timeslot_schedules_query = select(ShiftSchedule).where(
            ShiftSchedule.time_slot_id == timeslot_id,
            ShiftSchedule.status.in_(["planned", "confirmed"])
        )
        current_slot_schedules = (await db.execute(timeslot_schedules_query)).scalars().all()

        def to_utc(value: datetime) -> datetime:
            if value is None:
                return None
            if value.tzinfo is None:
                return pytz.UTC.localize(value)
            return value.astimezone(pytz.UTC)

        overlapping_slot_schedules = [
            sched for sched in current_slot_schedules
            if not (to_utc(sched.planned_end) <= slot_datetime or to_utc(sched.planned_start) >= end_datetime)
        ]

        max_employees = timeslot.max_employees or 1
        if len(overlapping_slot_schedules) >= max_employees:
            raise HTTPException(status_code=400, detail="На выбранное время нет свободных мест в тайм-слоте")

        # Определяем ставку с учетом флага use_contract_rate
        effective_rate = None
        if employee_contract:
            # Используем метод модели Contract для определения эффективной ставки
            timeslot_rate = float(timeslot.hourly_rate) if timeslot.hourly_rate else None
            object_rate = float(timeslot.object.hourly_rate) if timeslot.object and timeslot.object.hourly_rate else None
            effective_rate = employee_contract.get_effective_hourly_rate(
                timeslot_rate=timeslot_rate,
                object_rate=object_rate
            )
        else:
            # Фолбэк для случаев без договора: тайм-слот > объект
            effective_rate = float(timeslot.hourly_rate) if timeslot.hourly_rate else float(timeslot.object.hourly_rate) if timeslot.object else 0
        
        shift_schedule = ShiftSchedule(
            user_id=user_id,
            object_id=timeslot.object_id,
            time_slot_id=timeslot_id,
            planned_start=slot_datetime,
            planned_end=end_datetime,
            status='planned',
            hourly_rate=effective_rate,
            notes=''
        )
        
        db.add(shift_schedule)
        await db.flush()

        actor_role = "owner" if is_owner else "employee"
        history_service = ShiftHistoryService(db)
        await history_service.log_event(
            operation="schedule_plan",
            source="web",
            actor_id=user_id,
            actor_role=actor_role,
            schedule_id=shift_schedule.id,
            old_status=None,
            new_status="planned",
            payload={
                "object_id": timeslot.object_id,
                "time_slot_id": timeslot_id,
                "employee_id": user_id,
                "planned_start": slot_datetime.isoformat(),
                "planned_end": end_datetime.isoformat(),
                "origin": "employee_calendar",
            },
        )
        await db.commit()
        await db.refresh(shift_schedule)
        
        if actor_role == "employee":
            try:
                await ShiftNotificationService().notify_schedule_planned(
                    schedule_id=shift_schedule.id,
                    actor_role="employee",
                    planner_id=user_id,
                )
            except Exception as notification_error:
                logger.warning(
                    "Failed to send employee schedule planned notification",
                    error=str(notification_error),
                    schedule_id=shift_schedule.id,
                )
        
        # Очищаем кэш календаря для немедленного отображения
        from core.cache.redis_cache import cache
        await cache.clear_pattern("calendar_shifts:*")
        await cache.clear_pattern("api_response:*")
        logger.info(f"Calendar cache cleared after planning shift {shift_schedule.id}")
        
        logger.info(f"Employee {user_id} successfully planned shift {shift_schedule.id} for timeslot {timeslot_id}")
        return {
            "success": True,
            "message": "Смена успешно запланирована",
            "shift_id": shift_schedule.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error planning shift for employee: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка планирования смены: {str(e)}")


@router.post("/api/calendar/check-availability")
async def employee_check_availability(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Проверка доступности сотрудника при планировании через страницу сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        payload = await request.json()
        timeslot_id = payload.get('timeslot_id')
        employee_id = payload.get('employee_id')

        if not timeslot_id or employee_id is None:
            raise HTTPException(status_code=400, detail="Не указан тайм-слот или сотрудник")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        # Проверяем, что сотрудник планирует только для себя
        if int(employee_id) != int(user_id):
            return {"available": False, "message": "Нельзя планировать смены для другого сотрудника"}

        # Проверяем существование тайм-слота и доступ к объекту
        timeslot = (await db.execute(select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id))).scalar_one_or_none()
        if not timeslot:
            return {"available": False, "message": "Тайм-слот не найден"}

        if timeslot.object is None:
            return {"available": False, "message": "Объект тайм-слота не найден"}

        # Проверяем доступ к объекту через ObjectAccessService
        if isinstance(current_user, dict):
            telegram_id = current_user.get("telegram_id") or current_user.get("id")
        else:
            telegram_id = getattr(current_user, "telegram_id", None)

        if not telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        access_service = ObjectAccessService(db)
        accessible_objects = await access_service.get_accessible_objects(telegram_id, "employee")
        accessible_object_ids = {obj["id"] for obj in accessible_objects}

        if timeslot.object_id not in accessible_object_ids:
            return {"available": False, "message": "У вас нет доступа к объекту тайм-слота"}

        return {"available": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking employee availability: {e}")
        raise HTTPException(status_code=500, detail="Ошибка проверки доступности сотрудника")


@router.post("/api/shifts/cancel")
async def employee_cancel_planned_shift(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant)
):
    """Отмена запланированной смены сотрудником (смена в ShiftSchedule)."""
    try:
        data = await request.json()
        schedule_id = data.get('schedule_id')
        if not schedule_id:
            raise HTTPException(status_code=400, detail="Не указан ID запланированной смены")

        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")

            # Найдем запланированную смену и проверим владельца
            from sqlalchemy import select
            schedule = (await db.execute(select(ShiftSchedule).where(ShiftSchedule.id == schedule_id))).scalar_one_or_none()
            if not schedule:
                raise HTTPException(status_code=404, detail="Запланированная смена не найдена")
            if int(schedule.user_id) != int(user_id):
                raise HTTPException(status_code=403, detail="Нельзя отменить чужую смену")
            if schedule.status != 'planned':
                raise HTTPException(status_code=400, detail="Можно отменять только запланированные смены")

            schedule.status = 'cancelled'
            await db.commit()
            from core.cache.redis_cache import cache
            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling planned shift: {e}")
        raise HTTPException(status_code=500, detail="Ошибка отмены смены")