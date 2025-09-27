"""Роуты для администрирования системы (только для суперадмина)."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import auth_middleware
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.contract import Contract
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


async def get_current_user_from_request(request: Request) -> dict:
    """Получение текущего пользователя из запроса"""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user


@router.get("/", response_class=HTMLResponse, name="admin_dashboard")
async def admin_dashboard(request: Request):
    """Главная страница администратора"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            # Получаем статистику
            users_count = await session.execute(select(func.count(User.id)))
            total_users = users_count.scalar()
            
            owners_count = await session.execute(
                select(func.count(User.id)).where(User.role == UserRole.OWNER)
            )
            total_owners = owners_count.scalar()
            
            objects_count = await session.execute(select(func.count(Object.id)))
            total_objects = objects_count.scalar()
            
            shifts_count = await session.execute(select(func.count(Shift.id)))
            total_shifts = shifts_count.scalar()
            
            # Активные пользователи за последние 30 дней
            thirty_days_ago = datetime.now() - timedelta(days=30)
            active_users_count = await session.execute(
                select(func.count(User.id)).where(
                    and_(User.updated_at >= thirty_days_ago, User.is_active == True)
                )
            )
            active_users = active_users_count.scalar()
            
            # Последние зарегистрированные пользователи
            recent_users_result = await session.execute(
                select(User).order_by(desc(User.created_at)).limit(5)
            )
            recent_users = recent_users_result.scalars().all()
        
        stats = {
            'total_users': total_users,
            'total_owners': total_owners,
            'total_objects': total_objects,
            'total_shifts': total_shifts,
            'active_users': active_users,
            'recent_users': recent_users
        }
        
        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        async with get_async_session() as session:
            user_id = current_user.get("id")  # Это telegram_id
            login_service = RoleBasedLoginService(session)
            available_interfaces = await login_service.get_available_interfaces(user_id)
        
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "title": "Панель администратора",
            "available_interfaces": available_interfaces
        })
        
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки панели: {str(e)}")


@router.get("/users", response_class=HTMLResponse, name="admin_users")
async def admin_users_list(
    request: Request,
    role: Optional[str] = Query(None, description="Фильтр по роли"),
    search: Optional[str] = Query(None, description="Поиск по имени/username")
):
    """Управление пользователями"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        logger.info("Starting admin users list request")
        async with get_async_session() as session:
            logger.info("Database session created")
            query = select(User)
            
            # Фильтрация по роли
            if role and role != "all":
                try:
                    user_role_enum = UserRole(role)
                    query = query.where(User.role == user_role_enum)
                except ValueError:
                    pass
            
            # Поиск по имени
            if search:
                search_filter = f"%{search}%"
                query = query.where(
                    (User.first_name.ilike(search_filter)) |
                    (User.last_name.ilike(search_filter)) |
                    (User.username.ilike(search_filter))
                )
            
            query = query.order_by(desc(User.created_at))
            logger.info("Executing query")
            result = await session.execute(query)
            logger.info("Query executed, getting users")
            users = result.scalars().all()
            logger.info(f"Found {len(users)} users")
            
            # Получаем данные для переключения интерфейсов
            from shared.services.role_based_login_service import RoleBasedLoginService
            login_service = RoleBasedLoginService(session)
            user_id = current_user.get("id")  # Это telegram_id
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("admin/users.html", {
                "request": request,
                "current_user": current_user,
                "users": users,
                "roles": list(UserRole),
                "current_role_filter": role,
                "current_search": search,
                "title": "Управление пользователями",
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error loading admin users: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки пользователей: {str(e)}")


@router.post("/users/{user_id}/role", name="admin_update_user_role")
async def update_user_role(
    request: Request,
    user_id: int,
    new_role: str = Form(...)
):
    """Обновление роли пользователя"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        # Проверяем валидность роли
        try:
            role_enum = UserRole(new_role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверная роль: {new_role}")
        
        async with get_async_session() as session:
            # Находим пользователя
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            # Обновляем роль
            user.role = role_enum
            await session.commit()
        
        logger.info(f"Admin {current_user.get('id')} updated user {user_id} role to {new_role}")
        
        return RedirectResponse(
            url="/admin/users", 
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления роли: {str(e)}")


@router.post("/users/{user_id}/toggle-active", name="admin_toggle_user_active")
async def toggle_user_active(
    request: Request,
    user_id: int
):
    """Блокировка/разблокировка пользователя"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            user_result = await session.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=404, detail="Пользователь не найден")
            
            # Переключаем активность
            user.is_active = not user.is_active
            await session.commit()
        
        action = "заблокирован" if not user.is_active else "разблокирован"
        logger.info(f"Admin {current_user.get('id')} {action} user {user_id}")
        
        return RedirectResponse(
            url="/admin/users", 
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling user active status: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка изменения статуса: {str(e)}")


@router.get("/tariffs", response_class=HTMLResponse, name="admin_tariffs")
async def admin_tariffs(
    request: Request
):
    """Управление тарифными планами"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = current_user.get("id")  # Это telegram_id
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    # Перенаправляем на новый роут тарифов
    return RedirectResponse(url="/admin/tariffs/", status_code=status.HTTP_302_FOUND)


@router.get("/monitoring", response_class=HTMLResponse, name="admin_monitoring")
async def admin_monitoring(
    request: Request
):
    """Мониторинг системы"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = current_user.get("id")  # Это telegram_id
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("admin/monitoring.html", {
        "request": request,
        "current_user": current_user,
        "title": "Мониторинг системы",
        "prometheus_url": "http://localhost:9090",
        "grafana_url": "http://localhost:3000",
        "available_interfaces": available_interfaces
    })


@router.get("/reports", response_class=HTMLResponse, name="admin_reports")
async def admin_reports(request: Request):
    """Административные отчеты"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем данные для переключения интерфейсов
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        user_id = current_user.get("id")  # Это telegram_id
        login_service = RoleBasedLoginService(session)
        available_interfaces = await login_service.get_available_interfaces(user_id)
    
    return templates.TemplateResponse("admin/reports.html", {
        "request": request,
        "current_user": current_user,
        "title": "Административные отчеты",
        "message": "Функция в разработке",
        "available_interfaces": available_interfaces
    })
