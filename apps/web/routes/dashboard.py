from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc

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
    """Главная страница дашборда - перенаправляет в соответствующий интерфейс"""
    # Получаем текущего пользователя
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    
    # Проверяем роли - перенаправляем в соответствующие разделы
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        # Получаем роли пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        
        if not user_obj:
            return RedirectResponse(url="/auth/login", status_code=302)
        
        # Определяем основной интерфейс по приоритету
        user_roles = user_obj.get_roles() if hasattr(user_obj, 'get_roles') else []
        
        if "superadmin" in user_roles:
            return RedirectResponse(url="/admin", status_code=302)
        elif "owner" in user_roles:
            return RedirectResponse(url="/owner", status_code=302)
        elif "manager" in user_roles:
            return RedirectResponse(url="/manager/dashboard", status_code=302)
        elif "employee" in user_roles or "applicant" in user_roles:
            return RedirectResponse(url="/employee", status_code=302)
        else:
            # Нет подходящих ролей - отказываем в доступе
            return RedirectResponse(url="/auth/login", status_code=302)


@router.get("/metrics")
async def dashboard_metrics(request: Request):
    """API для получения метрик дашборда"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return {"error": "User not found"}
        
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Получаем смены за последние 30 дней
        thirty_days_ago = datetime.now() - timedelta(days=30)
        shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= thirty_days_ago
            )
        ).order_by(desc(Shift.start_time))
        shifts_result = await session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        # Вычисляем метрики
        total_earnings = sum(shift.total_payment or 0 for shift in shifts)
        active_shifts = len([s for s in shifts if s.status == "active"])
        total_objects = len(objects)
        
        return {
            "total_earnings": total_earnings,
            "active_shifts": active_shifts,
            "total_objects": total_objects,
            "shifts_count": len(shifts)
        }


@router.get("/alerts")
async def dashboard_alerts(request: Request):
    """API для получения уведомлений дашборда"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return {"error": "User not found"}
        
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        alerts = []
        
        # Проверяем активные смены
        active_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.status == "active"
            )
        )
        active_shifts_result = await session.execute(active_shifts_query)
        active_shifts = active_shifts_result.scalars().all()
        
        for shift in active_shifts:
            # Проверяем, не превышено ли время работы
            if shift.end_time is None:
                hours_worked = (datetime.now() - shift.start_time).total_seconds() / 3600
                if hours_worked > 8:  # Более 8 часов
                    alerts.append({
                        "type": "warning",
                        "message": f"Смена на объекте {shift.object.name} длится более 8 часов",
                        "timestamp": shift.start_time
                    })
        
        return {"alerts": alerts}


@router.get("/quick-stats")
async def dashboard_quick_stats(request: Request):
    """API для получения быстрой статистики"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        if not user_id:
            return {"error": "User not found"}
        
        # Получаем объекты владельца
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        # Получаем смены за сегодня
        today = datetime.now().date()
        today_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                func.date(Shift.start_time) == today
            )
        )
        today_shifts_result = await session.execute(today_shifts_query)
        today_shifts = today_shifts_result.scalars().all()
        
        # Получаем смены за неделю
        week_ago = datetime.now() - timedelta(days=7)
        week_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= week_ago
            )
        )
        week_shifts_result = await session.execute(week_shifts_query)
        week_shifts = week_shifts_result.scalars().all()
        
        # Получаем смены за месяц
        month_ago = datetime.now() - timedelta(days=30)
        month_shifts_query = select(Shift).where(
            and_(
                Shift.object_id.in_(object_ids),
                Shift.start_time >= month_ago
            )
        )
        month_shifts_result = await session.execute(month_shifts_query)
        month_shifts = month_shifts_result.scalars().all()
        
        return {
            "today": {
                "shifts": len(today_shifts),
                "hours": sum((s.end_time - s.start_time).total_seconds() / 3600 if s.end_time else 0 for s in today_shifts),
                "payment": sum(s.total_payment or 0 for s in today_shifts)
            },
            "week": {
                "shifts": len(week_shifts),
                "hours": sum((s.end_time - s.start_time).total_seconds() / 3600 if s.end_time else 0 for s in week_shifts),
                "payment": sum(s.total_payment or 0 for s in week_shifts)
            },
            "month": {
                "shifts": len(month_shifts),
                "hours": sum((s.end_time - s.start_time).total_seconds() / 3600 if s.end_time else 0 for s in month_shifts),
                "payment": sum(s.total_payment or 0 for s in month_shifts)
            }
        }