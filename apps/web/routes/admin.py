"""Роуты для администрирования системы (только для суперадмина)."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
import os
import httpx
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
from core.cache.redis_cache import cache
import json

router = APIRouter()
from apps.web.jinja import templates


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
            # Получаем внутренний ID пользователя
            telegram_id = current_user.get("id")  # Это telegram_id
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            
            if user_obj:
                login_service = RoleBasedLoginService(session)
                available_interfaces = await login_service.get_available_interfaces(user_obj.id)
            else:
                available_interfaces = []
        
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
    
    # Получаем статистику Redis для Cache Hit Rate
    from core.cache.redis_cache import cache
    cache_hit_rate = 0
    try:
        if not cache.is_connected:
            await cache.connect()
        redis_stats = await cache.get_stats()
        cache_hit_rate = redis_stats.get("hit_rate", 0)
    except Exception as e:
        logger.warning(f"Could not get Redis stats: {e}")
    
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
        "cache_hit_rate": cache_hit_rate,
        "available_interfaces": available_interfaces
    })


@router.get("/system-settings", response_class=HTMLResponse, name="admin_system_settings")
async def admin_system_settings(request: Request):
    """Системные настройки"""
    try:
        # Проверяем авторизацию и роль суперадмина
        current_user = await get_current_user_from_request(request)
        user_role = current_user.get("role", "employee")
        if user_role != "superadmin":
            return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        
        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        
        async with get_async_session() as session:
            # Получаем внутренний ID пользователя
            telegram_id = current_user.get("id")  # Это telegram_id
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            
            if user_obj:
                login_service = RoleBasedLoginService(session)
                available_interfaces = await login_service.get_available_interfaces(user_obj.id)
            else:
                available_interfaces = []
        
        return templates.TemplateResponse("admin/system_settings.html", {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces
        })
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        raise e
    except Exception as e:
        logger.error(f"Error in admin_system_settings: {e}")
        return templates.TemplateResponse("admin/error.html", {
            "request": request,
            "error": "Произошла ошибка при загрузке страницы"
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


@router.get("/cache/stats", response_class=HTMLResponse, name="admin_cache_stats")
async def admin_cache_stats(request: Request):
    """Статистика Redis кэша"""
    # Проверяем авторизацию и роль суперадмина
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Получаем статистику Redis
    from core.cache.redis_cache import cache
    from core.cache.cache_service import CacheService
    
    try:
        # Подключаемся к Redis если не подключен
        if not cache.is_connected:
            await cache.connect()
        
        # Получаем статистику
        redis_stats = await cache.get_stats()
        
        # Получаем количество ключей по типам
        all_keys = await cache.keys("*")
        key_counts = {
            "contract_employees": len([k for k in all_keys if k.startswith("contract_employees:")]),
            "all_contract_employees": len([k for k in all_keys if k.startswith("all_contract_employees:")]),
            "owner_objects": len([k for k in all_keys if k.startswith("owner_objects:")]),
            "objects_by_owner": len([k for k in all_keys if k.startswith("objects_by_owner:")]),
            "user": len([k for k in all_keys if k.startswith("user:")]),
            "object": len([k for k in all_keys if k.startswith("object:")]),
            "shift": len([k for k in all_keys if k.startswith("shift:")]),
            "active_shifts": len([k for k in all_keys if k.startswith("active_shifts:")]),
            "user_objects": len([k for k in all_keys if k.startswith("user_objects:")]),
            "analytics": len([k for k in all_keys if k.startswith("analytics:")]),
            "other": len([k for k in all_keys if not any(
                k.startswith(prefix) for prefix in [
                    "contract_employees:", "all_contract_employees:", "owner_objects:",
                    "objects_by_owner:", "user:", "object:", "shift:", 
                    "active_shifts:", "user_objects:", "analytics:"
                ]
            )])
        }
        
        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        async with get_async_session() as session:
            user_id = current_user.get("id")
            login_service = RoleBasedLoginService(session)
            available_interfaces = await login_service.get_available_interfaces(user_id)
        
        return templates.TemplateResponse("admin/cache_stats.html", {
            "request": request,
            "current_user": current_user,
            "title": "Статистика Redis кэша",
            "redis_stats": redis_stats,
            "key_counts": key_counts,
            "total_keys": len(all_keys),
            "available_interfaces": available_interfaces
        })
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return templates.TemplateResponse("admin/cache_stats.html", {
            "request": request,
            "current_user": current_user,
            "title": "Статистика Redis кэша",
            "error": f"Ошибка подключения к Redis: {str(e)}",
            "available_interfaces": []
        })


@router.get("/devops", response_class=HTMLResponse, name="admin_devops")
async def devops_dashboard(request: Request):
    """DevOps панель для владельца/админа"""
    # Проверяем авторизацию и роль
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    
    # Доступ: owner или superadmin
    if user_role not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        from domain.entities.bug_log import BugLog
        from domain.entities.deployment import Deployment
        from apps.web.services.github_service import github_service
        
        async with get_async_session() as session:
            # За последние 30 дней
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Подсчет деплоев
            deployments_query = select(func.count(Deployment.id)).where(
                Deployment.started_at >= thirty_days_ago
            )
            deployments_result = await session.execute(deployments_query)
            deployments_count = deployments_result.scalar() or 0
            
            # Успешные деплои
            success_deploys_query = select(func.count(Deployment.id)).where(
                and_(
                    Deployment.started_at >= thirty_days_ago,
                    Deployment.status == 'success'
                )
            )
            success_deploys_result = await session.execute(success_deploys_query)
            success_deploys_count = success_deploys_result.scalar() or 0
            
            # Deployment Frequency (DORA)
            deploy_frequency = round(deployments_count / 30, 2)
            
            # Failure Rate
            failure_rate = 0
            if deployments_count > 0:
                failure_rate = round((deployments_count - success_deploys_count) / deployments_count * 100, 1)
            
            # Баги (все открытые и критичные)
            critical_bugs_query = select(func.count(BugLog.id)).where(
                and_(
                    BugLog.status == 'open',
                    BugLog.priority.in_(['critical', 'high'])
                )
            )
            critical_bugs_result = await session.execute(critical_bugs_query)
            critical_bugs_count = critical_bugs_result.scalar() or 0
            open_bugs_query = select(func.count(BugLog.id)).where(BugLog.status == 'open')
            open_bugs_result = await session.execute(open_bugs_query)
            open_bugs_count = open_bugs_result.scalar() or 0
            
            # GitHub Issues
            github_issues_count = 0
            critical_issues_count = 0
            if github_service.token:
                try:
                    issues = await github_service.get_issues(
                        labels=["bug"],
                        state="open"
                    )
                    github_issues_count = len(issues)
                    critical_issues = [i for i in issues if 'priority-critical' in i.get('labels', [])]
                    critical_issues_count = len(critical_issues)
                except Exception as e:
                    logger.error(f"Failed to get GitHub issues: {e}")
        
        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        
        async with get_async_session() as session:
            # Получаем внутренний ID пользователя
            telegram_id = current_user.get("id")
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await session.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            
            if user_obj:
                login_service = RoleBasedLoginService(session)
                available_interfaces = await login_service.get_available_interfaces(user_obj.id)
            else:
                available_interfaces = []
        
        # Последние события Brain из Redis
        brain_events = []
        try:
            if not cache.is_connected:
                await cache.connect()
            raw = await cache.lrange("devops:brain_events", 0, 9)
            brain_events = [json.loads(x) for x in raw]
        except Exception as e:
            logger.warning(f"Cannot load brain events: {e}")

        return templates.TemplateResponse("admin/devops.html", {
            "request": request,
            "current_user": current_user,
            "title": "DevOps панель",
            "deployments_count": deployments_count,
            "success_deploys_count": success_deploys_count,
            "deploy_frequency": deploy_frequency,
            "failure_rate": failure_rate,
            "critical_bugs_count": critical_bugs_count,
            "open_bugs_count": open_bugs_count,
            "github_issues_count": github_issues_count,
            "critical_issues_count": critical_issues_count,
            "github_configured": bool(github_service.token),
            "brain_events": brain_events,
            "available_interfaces": available_interfaces
        })
        
    except Exception as e:
        logger.error(f"Error loading DevOps dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки панели: {str(e)}")


@router.get("/devops/architecture", response_class=HTMLResponse, name="admin_devops_architecture")
async def devops_architecture(request: Request):
    """Раздел архитектуры: снапшоты/дифф из Project Brain"""
    # Авторизация
    current_user = await get_current_user_from_request(request)
    user_role = current_user.get("role", "employee")
    if user_role not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)

    # Определяем базовый URL Project Brain (в контейнере localhost указывает на сам контейнер, а не на хост)
    configured = os.getenv("BRAIN_URL", "").strip()
    candidates = [
        configured,
        "http://project-brain-api:8003",  # если в одной docker-сети с именем сервиса
        "http://host.docker.internal:8003",  # docker desktop / совместимые среды
        "http://127.0.0.1:8003",  # локально вне контейнера
        "http://localhost:8003",
        # Внешние dev/prod URL, если Brain вынесен отдельно
        "http://dev.staffprobot.ru:8083",
        "http://staffprobot.ru:8083",
    ]
    candidates = [c.rstrip("/") for c in candidates if c]
    brain_url = None
    snapshots: List[dict] = []
    diff: dict = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for base in candidates:
                try:
                    # быстрый health/ping
                    r = await client.get(f"{base}/health")
                    if r.status_code != 200:
                        continue
                    # пробуем получить данные
                    snaps_resp = await client.get(f"{base}/api/architecture/snapshots")
                    diff_resp = await client.get(f"{base}/api/architecture/diff")
                    if snaps_resp.status_code == 200:
                        snapshots = snaps_resp.json().get("items", [])
                    if diff_resp.status_code == 200:
                        diff = diff_resp.json()
                    brain_url = base
                    break
                except Exception:
                    continue
            if brain_url is None:
                raise RuntimeError("Project Brain недоступен по кандидатам URL")
    except Exception as e:
        logger.warning(f"DevOps architecture: cannot reach Project Brain: {e}")
        brain_url = (configured or "").rstrip("/") or None

    # Доступные интерфейсы
    from shared.services.role_based_login_service import RoleBasedLoginService
    async with get_async_session() as session:
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        if user_obj:
            login_service = RoleBasedLoginService(session)
            available_interfaces = await login_service.get_available_interfaces(user_obj.id)
        else:
            available_interfaces = []

    return templates.TemplateResponse("admin/devops_architecture.html", {
        "request": request,
        "current_user": current_user,
        "title": "Architecture (Project Brain)",
        "snapshots": snapshots,
        "diff": diff,
        "brain_arch_url": f"{brain_url}/architecture" if brain_url else None,
        "brain_alive": bool(brain_url),
        "brain_base_url": brain_url,
        "available_interfaces": available_interfaces,
    })


@router.post("/api/admin/devops/brain/update")
async def api_devops_brain_update(payload: dict = Body(...)):
    """Webhook от Project Brain о завершении операций обучения/анализа.
    Сохраняет событие в Redis список devops:brain_events (макс 100).
    """
    try:
        event = {
            "event": payload.get("event", "unknown"),
            "commit_sha": payload.get("commit_sha"),
            "stats": payload.get("stats") or payload.get("cur_stats"),
            "snapshot": payload.get("snapshot"),
            "timestamp": payload.get("updated_at") or datetime.utcnow().isoformat() + "Z",
        }
        if not cache.is_connected:
            await cache.connect()
        await cache.lpush("devops:brain_events", json.dumps(event, ensure_ascii=False))
        # ограничиваем до 100
        await cache.ltrim("devops:brain_events", 0, 99)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to save brain event: {e}")
        raise HTTPException(status_code=500, detail="Failed to save brain event")


@router.post("/devops/architecture/reindex")
async def trigger_brain_reindex(request: Request):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    brain_url = os.getenv("BRAIN_URL", "").strip() or "http://project-brain-api:8003"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{brain_url.rstrip('/')}/api/architecture/reindex")
    except Exception as e:
        logger.warning(f"Reindex trigger failed: {e}")
    return RedirectResponse(url="/admin/devops/architecture", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/devops/architecture/analyze")
async def trigger_brain_analyze(request: Request, commit_sha: Optional[str] = Form(None)):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    brain_url = os.getenv("BRAIN_URL", "").strip() or "http://project-brain-api:8003"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{brain_url.rstrip('/')}/api/architecture/analyze",
                json={"project": "staffprobot", "commit_sha": commit_sha or ""},
            )
    except Exception as e:
        logger.warning(f"Analyze trigger failed: {e}")
    return RedirectResponse(url="/admin/devops/architecture", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/devops/bugs", response_class=HTMLResponse, name="admin_devops_bugs")
async def admin_devops_bugs(request: Request, priority: Optional[str] = Query(None), status_f: Optional[str] = Query(None)):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    try:
        from domain.entities.bug_log import BugLog
        async with get_async_session() as session:
            q = select(BugLog)
            if priority:
                q = q.where(BugLog.priority == priority)
            if status_f:
                q = q.where(BugLog.status == status_f)
            q = q.order_by(desc(BugLog.created_at))
            res = await session.execute(q)
            bugs = res.scalars().all()
        return templates.TemplateResponse("admin/devops_bugs.html", {
            "request": request,
            "current_user": current_user,
            "title": "Баги (DevOps)",
            "bugs": bugs,
            "priority": priority,
            "status_f": status_f,
        })
    except Exception as e:
        logger.error(f"Error loading bugs list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки багов")


@router.post("/devops/bugs/{bug_id}/update")
async def admin_devops_bug_update(request: Request, bug_id: int, new_status: str = Form(...), new_priority: Optional[str] = Form(None)):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    from domain.entities.bug_log import BugLog
    try:
        async with get_async_session() as session:
            res = await session.execute(select(BugLog).where(BugLog.id == bug_id))
            bug = res.scalar_one_or_none()
            if not bug:
                raise HTTPException(status_code=404, detail="Bug not found")
            bug.status = new_status
            if new_priority:
                bug.priority = new_priority
            await session.commit()
        return RedirectResponse(url="/admin/devops/bugs", status_code=status.HTTP_303_SEE_OTHER)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bug: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления бага")


@router.post("/devops/architecture/sync-datasets")
async def trigger_brain_sync_datasets(request: Request):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    brain_url = os.getenv("BRAIN_URL", "").strip() or "http://project-brain-api:8003"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(f"{brain_url.rstrip('/')}/api/datasets/sync")
    except Exception as e:
        logger.warning(f"Sync datasets trigger failed: {e}")
    return RedirectResponse(url="/admin/devops/architecture", status_code=status.HTTP_303_SEE_OTHER)


# ===== Internal exports for Project Brain datasets (read-only) =====
@router.get("/api/admin/devops/export/faq", response_class=HTMLResponse)
async def export_faq(request: Request):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        async with get_async_session() as session:
            from domain.entities.faq_entry import FAQEntry
            res = await session.execute(select(FAQEntry))
            items = [
                {
                    "id": e.id,
                    "category": e.category,
                    "question": e.question,
                    "answer": e.answer,
                    "updated_at": getattr(e, "updated_at", None),
                }
                for e in res.scalars().all()
            ]
            return HTMLResponse(
                content=json.dumps({"items": items}, ensure_ascii=False),
                media_type="application/json",
            )
    except Exception as e:
        logger.error(f"export_faq failed: {e}")
        raise HTTPException(status_code=500, detail="export_faq failed")


@router.get("/api/admin/devops/export/bugs", response_class=HTMLResponse)
async def export_bugs(request: Request):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        async with get_async_session() as session:
            from domain.entities.bug_log import BugLog
            res = await session.execute(select(BugLog))
            items = [
                {
                    "id": b.id,
                    "title": b.title,
                    "what_doing": b.what_doing,
                    "expected": b.expected,
                    "actual": b.actual,
                    "priority": getattr(b, "priority", None),
                    "status": getattr(b, "status", None),
                    "updated_at": getattr(b, "updated_at", None),
                }
                for b in res.scalars().all()
            ]
            return HTMLResponse(
                content=json.dumps({"items": items}, ensure_ascii=False),
                media_type="application/json",
            )
    except Exception as e:
        logger.error(f"export_bugs failed: {e}")
        raise HTTPException(status_code=500, detail="export_bugs failed")


@router.get("/api/admin/devops/export/changelog", response_class=HTMLResponse)
async def export_changelog(request: Request):
    current_user = await get_current_user_from_request(request)
    if current_user.get("role") not in ["owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        async with get_async_session() as session:
            from domain.entities.changelog_entry import ChangelogEntry
            res = await session.execute(select(ChangelogEntry))
            items = [
                {
                    "id": c.id,
                    "component": c.component,
                    "change_type": c.change_type,
                    "description": c.description,
                    "priority": c.priority,
                    "impact_score": getattr(c, "impact_score", None),
                    "created_at": getattr(c, "date", None),
                }
                for c in res.scalars().all()
            ]
            return HTMLResponse(
                content=json.dumps({"items": items}, ensure_ascii=False),
                media_type="application/json",
            )
    except Exception as e:
        logger.error(f"export_changelog failed: {e}")
        raise HTTPException(status_code=500, detail="export_changelog failed")
