"""Роуты для интерфейса управляющего."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from core.database.session import get_async_session
from shared.services.role_service import RoleService
from shared.services.manager_permission_service import ManagerPermissionService
from shared.services.role_based_login_service import RoleBasedLoginService
from apps.web.middleware.role_middleware import require_manager_or_owner
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.shift import Shift
from core.logging.logger import logger

router = APIRouter(prefix="/manager", tags=["manager"])
templates = Jinja2Templates(directory="apps/web/templates")


async def get_user_id_from_current_user(current_user, session: AsyncSession) -> Optional[int]:
    """Получает внутренний ID пользователя из current_user."""
    if isinstance(current_user, dict):
        from sqlalchemy import select
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        return current_user.id


@router.get("/", response_class=HTMLResponse)
async def manager_index(request: Request):
    """Главная страница управляющего - перенаправляет на дашборд."""
    return RedirectResponse(url="/manager/dashboard", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
async def manager_dashboard(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Дашборд управляющего."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сервисы
            role_service = RoleService(db)
            permission_service = ManagerPermissionService(db)
            login_service = RoleBasedLoginService(db)
            
            # Получаем доступные объекты
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            # Получаем права на каждый объект
            object_permissions = {}
            for obj in accessible_objects:
                # Находим договор управляющего для этого объекта
                manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
                for contract in manager_contracts:
                    permission = await permission_service.get_permission(contract.id, obj.id)
                    if permission:
                        object_permissions[obj.id] = permission.get_permissions_dict()
                        break
            
            # Получаем статистику
            accessible_objects_count = len(accessible_objects)
            
            # Получаем смены по доступным объектам
            object_ids = [obj.id for obj in accessible_objects]
            active_shifts = []
            scheduled_shifts = []
            
            if object_ids:
                from sqlalchemy import select, and_
                from datetime import datetime
                
                # Активные смены
                active_shifts_query = select(Shift).where(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.status == "active"
                    )
                ).options(
                    selectinload(Shift.user),
                    selectinload(Shift.object)
                )
                result = await db.execute(active_shifts_query)
                active_shifts = result.scalars().all()
                
                # Запланированные смены
                scheduled_shifts_query = select(Shift).where(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.status == "scheduled"
                    )
                ).options(
                    selectinload(Shift.user),
                    selectinload(Shift.object)
                )
                result = await db.execute(scheduled_shifts_query)
                scheduled_shifts = result.scalars().all()
            
            # Получаем последние смены
            recent_shifts = active_shifts + scheduled_shifts
            recent_shifts = sorted(recent_shifts, key=lambda x: x.start_time, reverse=True)[:10]
            
            # Названия прав
            permission_names = {
                "can_view": "Просмотр",
                "can_edit": "Редактирование",
                "can_delete": "Удаление",
                "can_manage_employees": "Управление сотрудниками",
                "can_view_finances": "Просмотр финансов",
                "can_edit_rates": "Редактирование ставок",
                "can_edit_schedule": "Редактирование расписания"
            }
            
            # Получаем данные для переключения интерфейсов
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/dashboard.html", {
                "request": request,
                "current_user": current_user,
                "accessible_objects": accessible_objects,
                "accessible_objects_count": accessible_objects_count,
                "active_shifts_count": len(active_shifts),
                "scheduled_shifts_count": len(scheduled_shifts),
                "employees_count": len(set(shift.user_id for shift in recent_shifts)),
                "recent_shifts": recent_shifts,
                "object_permissions": object_permissions,
                "permission_names": permission_names,
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error in manager dashboard: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки дашборда")


@router.get("/objects", response_class=HTMLResponse)
async def manager_objects(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Список объектов управляющего."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            permission_service = ManagerPermissionService(db)
            
            # Получаем доступные объекты
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            # Получаем права на каждый объект
            object_permissions = {}
            for obj in accessible_objects:
                manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
                for contract in manager_contracts:
                    permission = await permission_service.get_permission(contract.id, obj.id)
                    if permission:
                        object_permissions[obj.id] = permission.get_permissions_dict()
                        break
            
            # Названия прав
            permission_names = {
                "can_view": "Просмотр",
                "can_edit": "Редактирование",
                "can_delete": "Удаление",
                "can_manage_employees": "Управление сотрудниками",
                "can_view_finances": "Просмотр финансов",
                "can_edit_rates": "Редактирование ставок",
                "can_edit_schedule": "Редактирование расписания"
            }
            
            return templates.TemplateResponse("manager/objects.html", {
                "request": request,
                "current_user": current_user,
                "accessible_objects": accessible_objects,
                "object_permissions": object_permissions,
                "permission_names": permission_names
            })
        
    except Exception as e:
        logger.error(f"Error in manager objects: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки объектов")


@router.get("/objects/{object_id}", response_class=HTMLResponse)
async def manager_object_detail(
    object_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Детальная информация об объекте."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            permission_service = ManagerPermissionService(db)
            
            # Проверяем доступ к объекту
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            if not any(obj.id == object_id for obj in accessible_objects):
                raise HTTPException(status_code=403, detail="Нет доступа к объекту")
            
            # Получаем объект
            from sqlalchemy import select
            object_query = select(Object).where(Object.id == object_id)
            result = await db.execute(object_query)
            obj = result.scalar_one_or_none()
            
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден")
            
            # Получаем права на объект
            manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
            object_permission = None
            for contract in manager_contracts:
                permission = await permission_service.get_permission(contract.id, object_id)
                if permission:
                    object_permission = permission
                    break
            
            return templates.TemplateResponse("manager/objects/detail.html", {
                "request": request,
                "current_user": current_user,
                "object": obj,
                "object_permission": object_permission
            })
        
    except Exception as e:
        logger.error(f"Error in manager object detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки объекта")


@router.get("/objects/{object_id}/edit", response_class=HTMLResponse)
async def manager_object_edit(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Форма редактирования объекта управляющим."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сервисы
            permission_service = ManagerPermissionService(db)
            
            # Проверяем доступ к объекту
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            obj = next((o for o in accessible_objects if o.id == object_id), None)
            
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")
            
            # Получаем права на объект
            manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
            object_permission = None
            for contract in manager_contracts:
                permission = await permission_service.get_permission(contract.id, object_id)
                if permission:
                    object_permission = permission
                    break
            
            # Проверяем права на редактирование
            if not object_permission or not object_permission.can_edit:
                raise HTTPException(status_code=403, detail="Нет прав на редактирование объекта")
            
            # Преобразуем в формат для шаблона
            object_data = {
                "id": obj.id,
                "name": obj.name,
                "address": obj.address or "",
                "coordinates": obj.coordinates or "",
                "hourly_rate": obj.hourly_rate,
                "opening_time": obj.opening_time.strftime("%H:%M") if obj.opening_time else "",
                "closing_time": obj.closing_time.strftime("%H:%M") if obj.closing_time else "",
                "max_distance": obj.max_distance_meters or 500,
                "available_for_applicants": obj.available_for_applicants,
                "is_active": obj.is_active,
                "work_days_mask": obj.work_days_mask,
                "schedule_repeat_weeks": obj.schedule_repeat_weeks
            }
            
            return templates.TemplateResponse("manager/objects/edit.html", {
                "request": request,
                "title": f"Редактирование: {object_data['name']}",
                "object": object_data,
                "current_user": current_user,
                "object_permission": object_permission
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager object edit: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/objects/{object_id}/edit")
async def manager_object_edit_post(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Обновление объекта управляющим."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сервисы
            permission_service = ManagerPermissionService(db)
            
            # Проверяем доступ к объекту
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            obj = next((o for o in accessible_objects if o.id == object_id), None)
            
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")
            
            # Получаем права на объект
            manager_contracts = await permission_service.get_manager_contracts_for_user(user_id)
            object_permission = None
            for contract in manager_contracts:
                permission = await permission_service.get_permission(contract.id, object_id)
                if permission:
                    object_permission = permission
                    break
            
            # Проверяем права на редактирование
            if not object_permission or not object_permission.can_edit:
                raise HTTPException(status_code=403, detail="Нет прав на редактирование объекта")
            
            # Получение данных формы
            form_data = await request.form()
            
            name = form_data.get("name", "").strip()
            address = form_data.get("address", "").strip()
            hourly_rate_str = form_data.get("hourly_rate", "0").strip()
            opening_time = form_data.get("opening_time", "").strip()
            closing_time = form_data.get("closing_time", "").strip()
            max_distance_str = form_data.get("max_distance", "500").strip()
            latitude_str = form_data.get("latitude", "").strip()
            longitude_str = form_data.get("longitude", "").strip()
            available_for_applicants = form_data.get("available_for_applicants") == "true"
            is_active = form_data.get("is_active") == "true"
            
            # Получение дней недели
            work_days = form_data.getlist("work_days")
            work_days_mask = [False] * 7
            for day in work_days:
                try:
                    day_index = int(day)
                    if 0 <= day_index < 7:
                        work_days_mask[day_index] = True
                except ValueError:
                    pass
            
            schedule_repeat_weeks_str = form_data.get("schedule_repeat_weeks", "1").strip()
            
            logger.info(f"Updating object {object_id} for manager user {user_id}")
            
            # Валидация обязательных полей
            if not name:
                raise HTTPException(status_code=400, detail="Название объекта обязательно")
            if not address:
                raise HTTPException(status_code=400, detail="Адрес объекта обязателен")
            
            # Валидация и преобразование числовых полей
            try:
                # Поддержка запятой как десятичного разделителя ("500,00")
                normalized_rate = hourly_rate_str.replace(",", ".") if hourly_rate_str else "0"
                hourly_rate = int(float(normalized_rate)) if normalized_rate else 0
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ставки")
            
            try:
                max_distance = int(max_distance_str) if max_distance_str else 500
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат максимального расстояния")
            
            try:
                schedule_repeat_weeks = int(schedule_repeat_weeks_str) if schedule_repeat_weeks_str else 1
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат повторения")
            
            if hourly_rate <= 0:
                raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
            
            if max_distance <= 0:
                raise HTTPException(status_code=400, detail="Максимальное расстояние должно быть больше 0")
            
            if schedule_repeat_weeks <= 0:
                raise HTTPException(status_code=400, detail="Повторение должно быть больше 0")
            
            # Обработка координат
            coordinates = None
            if latitude_str and longitude_str:
                try:
                    lat = float(latitude_str)
                    lon = float(longitude_str)
                    coordinates = f"{lat},{lon}"
                except ValueError:
                    raise HTTPException(status_code=400, detail="Неверный формат координат")
            
            # Обработка времени
            from datetime import datetime, time
            opening_time_obj = None
            closing_time_obj = None
            
            if opening_time:
                try:
                    opening_time_obj = datetime.strptime(opening_time, "%H:%M").time()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Неверный формат времени открытия")
            
            if closing_time:
                try:
                    closing_time_obj = datetime.strptime(closing_time, "%H:%M").time()
                except ValueError:
                    raise HTTPException(status_code=400, detail="Неверный формат времени закрытия")
            
            # Обновление объекта
            from apps.web.services.object_service import ObjectService
            object_service = ObjectService(db)
            
            # Подготавливаем данные для обновления
            update_data = {
                "name": name,
                "address": address,
                "hourly_rate": hourly_rate,
                "opening_time": opening_time_obj,
                "closing_time": closing_time_obj,
                "max_distance_meters": max_distance,
                "coordinates": coordinates,
                "available_for_applicants": available_for_applicants,
                "is_active": is_active,
                "work_days_mask": work_days_mask,
                "schedule_repeat_weeks": schedule_repeat_weeks
            }
            
            # Обновляем объект
            updated_object = await object_service.update_object(object_id, update_data)
            
            if not updated_object:
                raise HTTPException(status_code=500, detail="Ошибка обновления объекта")
            
            logger.info(f"Object {object_id} updated successfully by manager {user_id}")
            
            # Перенаправляем на страницу объекта
            return RedirectResponse(url=f"/manager/objects/{object_id}", status_code=302)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating object {object_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления объекта")


@router.get("/employees", response_class=HTMLResponse)
async def manager_employees(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
):
    """Список сотрудников управляющего."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Здесь будет логика получения сотрудников
            # Пока возвращаем заглушку
            
            return templates.TemplateResponse("manager/employees.html", {
                "request": request,
                "current_user": current_user,
                "employees": []
            })
        
    except Exception as e:
        logger.error(f"Error in manager employees: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников")


@router.get("/calendar", response_class=HTMLResponse)
async def manager_calendar(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
):
    """Календарь управляющего."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Здесь будет логика календаря
            # Пока возвращаем заглушку
            
            return templates.TemplateResponse("manager/calendar.html", {
                "request": request,
                "current_user": current_user
            })
        
    except Exception as e:
        logger.error(f"Error in manager calendar: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки календаря")


@router.get("/reports", response_class=HTMLResponse)
async def manager_reports(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
):
    """Отчеты управляющего."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Здесь будет логика отчетов
            # Пока возвращаем заглушку
            
            return templates.TemplateResponse("manager/reports.html", {
                "request": request,
                "current_user": current_user
            })
        
    except Exception as e:
        logger.error(f"Error in manager reports: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки отчетов")
