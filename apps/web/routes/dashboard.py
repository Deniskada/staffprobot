from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.auth.user_manager import UserManager
from apps.web.middleware.auth_middleware import require_owner_or_superadmin, get_current_user
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.contract import Contract

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")
user_manager = UserManager()


async def get_user_id_from_current_user(current_user, session: AsyncSession):
    """Возвращает внутренний ID пользователя по current_user.
    В JWT payload текущий user.id — это telegram_id, нужно маппить на User.id.
    """
    if isinstance(current_user, dict):
        telegram_id = current_user.get("id")
        if telegram_id is None:
            return None
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    return current_user.id


@router.get("/", response_class=HTMLResponse)
async def dashboard_index(request: Request):
    """Главная страница дашборда владельца"""
    # Получаем текущего пользователя
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Проверяем роль - перенаправляем в соответствующие разделы
    user_role = current_user.get("role", "employee") if isinstance(current_user, dict) else current_user.role
    if user_role == "superadmin":
        return RedirectResponse(url="/admin", status_code=302)
    elif user_role == "employee":
        return RedirectResponse(url="/employee", status_code=302)
    elif user_role == "owner":
        # Владельцы должны использовать новый интерфейс /owner
        return RedirectResponse(url="/owner", status_code=302)
    else:
        # Остальные роли - отказываем в доступе
        return RedirectResponse(url="/auth/login", status_code=302)
    
    async with get_async_session() as session:
        # Всегда используем внутренний user_id
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            # Нет пользователя в БД — отдаем пустые данные, чтобы не падать
            return templates.TemplateResponse("dashboard/index.html", {
                "request": request,
                "current_user": current_user,
                "metrics": {
                    "today": {"shifts": 0, "hours": 0, "payment": 0},
                    "week": {"shifts": 0, "hours": 0, "payment": 0},
                    "month": {"shifts": 0, "hours": 0, "payment": 0},
                    "planned": 0,
                    "active": 0,
                    "objects": 0,
                    "employees": 0,
                    "contracts": 0
                },
                "top_objects": [],
                "top_employees": [],
                "daily_stats": [],
                "upcoming_schedules": [],
                "active_shifts": []
            })
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Получаем сотрудников
        employees_query = select(User).where(User.role == "employee")
        employees_result = await session.execute(employees_query)
        employees = employees_result.scalars().all()
        
        # Получаем договоры
        contracts_query = select(Contract).where(Contract.owner_id == user_id)
        contracts_result = await session.execute(contracts_query)
        contracts = contracts_result.scalars().all()
        
        # Статистика за сегодня
        today = datetime.now().date()
        today_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                func.date(Shift.start_time) == today
            )
        )
        today_shifts_result = await session.execute(today_shifts_query)
        today_shifts = today_shifts_result.scalars().all()
        
        # Статистика за неделю
        week_ago = today - timedelta(days=7)
        week_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= week_ago
            )
        )
        week_shifts_result = await session.execute(week_shifts_query)
        week_shifts = week_shifts_result.scalars().all()
        
        # Статистика за месяц
        month_ago = today - timedelta(days=30)
        month_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= month_ago
            )
        )
        month_shifts_result = await session.execute(month_shifts_query)
        month_shifts = month_shifts_result.scalars().all()
        
        # Запланированные смены
        planned_schedules_query = select(ShiftSchedule).where(
            and_(
                ShiftSchedule.object_id.in_(object_ids),
                ShiftSchedule.status == "planned",
                ShiftSchedule.planned_start >= today
            )
        )
        planned_schedules_result = await session.execute(planned_schedules_query)
        planned_schedules = planned_schedules_result.scalars().all()
        
        # Активные смены
        active_shifts_query = select(Shift).options(
            selectinload(Shift.user),
            selectinload(Shift.object)
        ).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.status == "active"
            )
        )
        active_shifts_result = await session.execute(active_shifts_query)
        active_shifts = active_shifts_result.scalars().all()
        
        # Расчет метрик
        metrics = {
            "today": {
                "shifts": len(today_shifts),
                "hours": sum(s.total_hours or 0 for s in today_shifts if s.total_hours),
                "payment": sum(s.total_payment or 0 for s in today_shifts if s.total_payment)
            },
            "week": {
                "shifts": len(week_shifts),
                "hours": sum(s.total_hours or 0 for s in week_shifts if s.total_hours),
                "payment": sum(s.total_payment or 0 for s in week_shifts if s.total_payment)
            },
            "month": {
                "shifts": len(month_shifts),
                "hours": sum(s.total_hours or 0 for s in month_shifts if s.total_hours),
                "payment": sum(s.total_payment or 0 for s in month_shifts if s.total_payment)
            },
            "planned": len(planned_schedules),
            "active": len(active_shifts),
            "objects": len(objects),
            "employees": len(employees),
            "contracts": len(contracts)
        }
        
        # Топ объекты по активности
        object_stats = {}
        for shift in month_shifts:
            obj_id = shift.object_id
            if obj_id not in object_stats:
                object_stats[obj_id] = {
                    "object": next(obj for obj in objects if obj.id == obj_id),
                    "shifts": 0,
                    "hours": 0,
                    "payment": 0
                }
            object_stats[obj_id]["shifts"] += 1
            object_stats[obj_id]["hours"] += shift.total_hours or 0
            object_stats[obj_id]["payment"] += shift.total_payment or 0
        
        top_objects = sorted(
            object_stats.values(),
            key=lambda x: x["shifts"],
            reverse=True
        )[:5]
        
        # Топ сотрудники по активности (безопасный доступ)
        employee_stats = {}
        employees_by_id = {emp.id: emp for emp in employees}
        for shift in month_shifts:
            emp_id = shift.user_id
            employee_obj = employees_by_id.get(emp_id)
            if not employee_obj:
                # Пользователь не сотрудник или отсутствует — пропускаем
                continue
            if emp_id not in employee_stats:
                employee_stats[emp_id] = {
                    "employee": employee_obj,
                    "shifts": 0,
                    "hours": 0,
                    "payment": 0
                }
            employee_stats[emp_id]["shifts"] += 1
            employee_stats[emp_id]["hours"] += shift.total_hours or 0
            employee_stats[emp_id]["payment"] += shift.total_payment or 0
        
        top_employees = sorted(
            employee_stats.values(),
            key=lambda x: x["shifts"],
            reverse=True
        )[:5]
        
        # График активности по дням (последние 7 дней)
        daily_stats = []
        for i in range(7):
            day = today - timedelta(days=i)
            day_shifts_query = select(Shift).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    func.date(Shift.start_time) == day
                )
            )
            day_shifts_result = await session.execute(day_shifts_query)
            day_shifts = day_shifts_result.scalars().all()
            
            hours_sum = sum(s.total_hours or 0 for s in day_shifts if s.total_hours)
            payment_sum = sum(s.total_payment or 0 for s in day_shifts if s.total_payment)
            daily_stats.append({
                "date": day.strftime("%d.%m"),
                "shifts": int(len(day_shifts)),
                "hours": float(hours_sum) if hours_sum is not None else 0.0,
                "payment": float(payment_sum) if payment_sum is not None else 0.0
            })
        
        daily_stats.reverse()  # От старых к новым
        
        # Предстоящие смены (следующие 7 дней)
        next_week = today + timedelta(days=7)
        upcoming_schedules_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user)
        ).where(
            and_(
                ShiftSchedule.object_id.in_(object_ids),
                ShiftSchedule.status == "planned",
                ShiftSchedule.planned_start >= today,
                ShiftSchedule.planned_start <= next_week
            )
        ).order_by(ShiftSchedule.planned_start)
        
        upcoming_schedules_result = await session.execute(upcoming_schedules_query)
        upcoming_schedules = upcoming_schedules_result.scalars().all()
        
        return templates.TemplateResponse("dashboard/index.html", {
            "request": request,
            "current_user": current_user,
            "metrics": metrics,
            "top_objects": top_objects,
            "top_employees": top_employees,
            "daily_stats": daily_stats,
            "upcoming_schedules": upcoming_schedules,
            "active_shifts": active_shifts
        })


@router.get("/metrics")
async def dashboard_metrics(request: Request):
    """API для получения метрик дашборда"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Суперадмины не должны использовать метрики владельца
    user_role = current_user.get("role", "employee") if isinstance(current_user, dict) else current_user.role
    if user_role == "superadmin":
        return {"error": "Access denied for superadmin"}
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Статистика за последние 30 дней
        month_ago = datetime.now().date() - timedelta(days=30)
        shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= month_ago
            )
        )
        shifts_result = await session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        # Группировка по дням
        daily_data = {}
        for shift in shifts:
            day = shift.start_time.date()
            if day not in daily_data:
                daily_data[day] = {
                    "shifts": 0,
                    "hours": 0,
                    "payment": 0
                }
            daily_data[day]["shifts"] += 1
            daily_data[day]["hours"] += shift.total_hours or 0
            daily_data[day]["payment"] += shift.total_payment or 0
        
        # Подготовка данных для графика
        chart_data = []
        for i in range(30):
            day = month_ago + timedelta(days=i)
            data = daily_data.get(day, {"shifts": 0, "hours": 0, "payment": 0})
            chart_data.append({
                "date": day.strftime("%Y-%m-%d"),
                "shifts": data["shifts"],
                "hours": data["hours"],
                "payment": data["payment"]
            })
        
        return {
            "chart_data": chart_data,
            "total_shifts": int(len(shifts)),
            "total_hours": float(sum(s.total_hours or 0 for s in shifts if s.total_hours)),
            "total_payment": float(sum(s.total_payment or 0 for s in shifts if s.total_payment))
        }


@router.get("/alerts")
async def dashboard_alerts(request: Request):
    """API для получения уведомлений и предупреждений"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Суперадмины не должны использовать алерты владельца
    user_role = current_user.get("role", "employee") if isinstance(current_user, dict) else current_user.role
    if user_role == "superadmin":
        return {"alerts": [], "message": "Access denied for superadmin"}
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        alerts = []
        
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Проверка на длительные активные смены (более 12 часов)
        long_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.status == "active",
                Shift.start_time <= datetime.now() - timedelta(hours=12)
            )
        )
        long_shifts_result = await session.execute(long_shifts_query)
        long_shifts = long_shifts_result.scalars().all()
        
        for shift in long_shifts:
            alerts.append({
                "type": "warning",
                "title": "Длительная активная смена",
                "message": f"Смена на объекте '{shift.object.name}' активна более 12 часов",
                "shift_id": shift.id,
                "created_at": shift.start_time
            })
        
        # Проверка на отсутствие смен сегодня
        today = datetime.now().date()
        today_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                func.date(Shift.start_time) == today
            )
        )
        today_shifts_result = await session.execute(today_shifts_query)
        today_shifts = today_shifts_result.scalars().all()
        
        if not today_shifts:
            alerts.append({
                "type": "info",
                "title": "Нет смен сегодня",
                "message": "Сегодня еще не было ни одной смены",
                "created_at": datetime.now()
            })
        
        # Проверка на неоплаченные смены (старше 7 дней)
        week_ago = datetime.now() - timedelta(days=7)
        unpaid_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.status == "completed",
                Shift.end_time <= week_ago,
                or_(Shift.total_payment == 0, Shift.total_payment.is_(None))
            )
        )
        unpaid_shifts_result = await session.execute(unpaid_shifts_query)
        unpaid_shifts = unpaid_shifts_result.scalars().all()
        
        if unpaid_shifts:
            alerts.append({
                "type": "error",
                "title": "Неоплаченные смены",
                "message": f"Найдено {len(unpaid_shifts)} неоплаченных смен старше 7 дней",
                "count": len(unpaid_shifts),
                "created_at": datetime.now()
            })
        
        return {"alerts": alerts}


@router.get("/quick-stats")
async def quick_stats(request: Request):
    """API для быстрых статистик"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Суперадмины не должны использовать статистики владельца
    user_role = current_user.get("role", "employee") if isinstance(current_user, dict) else current_user.role
    if user_role == "superadmin":
        return {"error": "Access denied for superadmin"}
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Статистика за сегодня
        today = datetime.now().date()
        today_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                func.date(Shift.start_time) == today
            )
        )
        today_shifts_result = await session.execute(today_shifts_query)
        today_shifts = today_shifts_result.scalars().all()
        
        # Активные смены
        active_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.status == "active"
            )
        )
        active_shifts_result = await session.execute(active_shifts_query)
        active_shifts = active_shifts_result.scalars().all()
        
        # Запланированные смены на завтра
        tomorrow = today + timedelta(days=1)
        tomorrow_schedules_query = select(ShiftSchedule).where(
            and_(
                ShiftSchedule.object_id.in_(object_ids),
                ShiftSchedule.status == "planned",
                func.date(ShiftSchedule.planned_start) == tomorrow
            )
        )
        tomorrow_schedules_result = await session.execute(tomorrow_schedules_query)
        tomorrow_schedules = tomorrow_schedules_result.scalars().all()
        
        return {
            "today_shifts": int(len(today_shifts)),
            "active_shifts": int(len(active_shifts)),
            "tomorrow_schedules": int(len(tomorrow_schedules)),
            "total_objects": int(len(objects))
        }