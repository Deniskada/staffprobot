"""
Роуты для сотрудников
URL-префикс: /employee/*
"""

from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import get_current_user
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from domain.entities.shift import Shift
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


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


@router.get("/", response_class=HTMLResponse, name="employee_dashboard")
async def employee_dashboard(request: Request):
    """Дашборд сотрудника"""
    # Проверяем авторизацию и роль сотрудника
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            
            # Получаем статистику сотрудника
            # Смены, в которых участвовал сотрудник
            shifts_count = await session.execute(
                select(func.count(Shift.id)).where(Shift.user_id == user_id)
            )
            total_shifts = shifts_count.scalar()
            
            # Активные смены сотрудника
            active_shifts_count = await session.execute(
                select(func.count(Shift.id)).where(
                    and_(
                        Shift.user_id == user_id,
                        Shift.status == 'active'
                    )
                )
            )
            active_shifts = active_shifts_count.scalar()
            
            # Заработок за текущий месяц
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_earnings_result = await session.execute(
                select(func.sum(Shift.total_payment)).where(
                    and_(
                        Shift.user_id == user_id,
                        Shift.status == 'completed',
                        Shift.created_at >= current_month_start
                    )
                )
            )
            monthly_earnings = monthly_earnings_result.scalar() or 0
            
            # Последние смены
            recent_shifts_result = await session.execute(
                select(Shift).options(selectinload(Shift.object))
                .where(Shift.user_id == user_id)
                .order_by(desc(Shift.created_at)).limit(5)
            )
            recent_shifts = recent_shifts_result.scalars().all()
        
        stats = {
            'total_shifts': total_shifts,
            'active_shifts': active_shifts,
            'monthly_earnings': float(monthly_earnings),
        }

        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        async with get_async_session() as session:
            login_service = RoleBasedLoginService(session)
            available_interfaces = await login_service.get_available_interfaces(user_id)
        
        return templates.TemplateResponse("employee/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Дашборд сотрудника",
            "stats": stats,
            "recent_shifts": recent_shifts,
            "available_interfaces": available_interfaces,
        })
    except Exception as e:
        logger.error(f"Error loading employee dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/dashboard", response_class=HTMLResponse)
async def employee_dashboard_redirect(request: Request):
    """Редирект с /employee/dashboard на /employee/"""
    return RedirectResponse(url="/employee/", status_code=status.HTTP_302_FOUND)


@router.get("/shifts-map", response_class=HTMLResponse, name="employee_shifts_map")
async def employee_shifts_map(request: Request):
    """Карта доступных смен для сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/shifts_map.html", {
        "request": request,
        "current_user": current_user,
        "title": "Карта смен",
        "message": "Карта смен в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/calendar", response_class=HTMLResponse, name="employee_calendar")
async def employee_calendar(request: Request):
    """Календарь смен сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/calendar.html", {
        "request": request,
        "current_user": current_user,
        "title": "Мой календарь",
        "message": "Календарь сотрудника в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/history", response_class=HTMLResponse, name="employee_history")
async def employee_history(request: Request):
    """История работы сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/history.html", {
        "request": request,
        "current_user": current_user,
        "title": "История работы",
        "message": "История работы в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/earnings", response_class=HTMLResponse, name="employee_earnings")
async def employee_earnings(request: Request):
    """Заработок сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/earnings.html", {
        "request": request,
        "current_user": current_user,
        "title": "Мой заработок",
        "message": "Статистика заработка в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/applications", response_class=HTMLResponse, name="employee_applications")
async def employee_applications(request: Request):
    """Заявки сотрудника на смены"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/applications.html", {
        "request": request,
        "current_user": current_user,
        "title": "Мои заявки",
        "message": "Управление заявками в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/profile", response_class=HTMLResponse, name="employee_profile")
async def employee_profile(request: Request):
    """Профиль сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/profile.html", {
        "request": request,
        "current_user": current_user,
        "title": "Профиль сотрудника",
        "message": "Профиль в разработке",
        "available_interfaces": available_interfaces
    })


@router.get("/settings", response_class=HTMLResponse, name="employee_settings")
async def employee_settings(request: Request):
    """Настройки сотрудника"""
    current_user = await get_current_user(request)
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    user_role = current_user.get("role", "employee")
    if user_role != "employee":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("employee/settings.html", {
        "request": request,
        "current_user": current_user,
        "title": "Настройки сотрудника",
        "message": "Настройки в разработке",
        "available_interfaces": available_interfaces
    })
