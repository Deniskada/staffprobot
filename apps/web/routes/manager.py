"""Роуты для интерфейса управляющего."""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, time, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from core.database.session import get_async_session, get_db_session
from shared.services.role_service import RoleService
from shared.services.manager_permission_service import ManagerPermissionService
from apps.web.utils.timezone_utils import web_timezone_helper
from shared.services.role_based_login_service import RoleBasedLoginService
from apps.web.middleware.role_middleware import require_manager_or_owner
from apps.web.dependencies import get_current_user_dependency
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
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
            login_service = RoleBasedLoginService(db)
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
            login_service = RoleBasedLoginService(db)
            
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
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/objects.html", {
                "request": request,
                "current_user": current_user,
                "accessible_objects": accessible_objects,
                "object_permissions": object_permissions,
                "permission_names": permission_names,
                "available_interfaces": available_interfaces
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
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/objects/detail.html", {
                "request": request,
                "current_user": current_user,
                "object": obj,
                "object_permission": object_permission,
                "available_interfaces": available_interfaces
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
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/objects/edit.html", {
                "request": request,
                "title": f"Редактирование: {object_data['name']}",
                "object": object_data,
                "current_user": current_user,
                "object_permission": object_permission,
                "available_interfaces": available_interfaces
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
            
            # Получение дней недели (битовая маска)
            work_days_mask_str = form_data.get("work_days_mask", "0").strip()
            try:
                work_days_mask = int(work_days_mask_str)
            except ValueError:
                work_days_mask = 0
            
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
            
            # Обновляем объект (используем метод для управляющих)
            updated_object = await object_service.update_object_by_manager(object_id, update_data)
            
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
        logger.info("Starting manager_employees function")
        
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            logger.info("Current user is RedirectResponse, redirecting")
            return current_user
        
        async with get_async_session() as db:
            logger.info("Got database session")
            
            user_id = await get_user_id_from_current_user(current_user, db)
            logger.info(f"User ID: {user_id}")
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сервисы
            logger.info("Creating services")
            permission_service = ManagerPermissionService(db)
            login_service = RoleBasedLoginService(db)
            
            # Получаем доступные объекты управляющего
            logger.info("Getting accessible objects")
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            logger.info(f"Accessible objects count: {len(accessible_objects)}")
            logger.info(f"Accessible objects: {[obj.id for obj in accessible_objects]}")
            
            object_ids = [obj.id for obj in accessible_objects]
            
            # Получаем сотрудников, работающих на доступных объектах
            employees = []
            if object_ids:
                logger.info(f"Getting employees for object IDs: {object_ids}")
                from sqlalchemy import select, distinct
                from domain.entities.contract import Contract
                from domain.entities.user import User
                
                # Получаем всех сотрудников, работающих на доступных объектах
                from sqlalchemy import func, or_, text, cast, String, JSON, any_, exists
                
                # Используем простой SQL с text() для проверки пересечения массивов
                employees_query = select(User).join(
                    Contract, User.id == Contract.employee_id
                ).where(
                    Contract.is_active == True,
                    text("EXISTS (SELECT 1 FROM json_array_elements(contracts.allowed_objects) AS elem WHERE elem::text::int = ANY(ARRAY[{}]))".format(','.join(map(str, object_ids))))
                ).distinct()
                
                logger.info(f"Executing query: {employees_query}")
                logger.info(f"Query parameters: object_ids={object_ids}")
                logger.info(f"SQL: {str(employees_query.compile(compile_kwargs={'literal_binds': True}))}")
                
                result = await db.execute(employees_query)
                employees = result.scalars().all()
                logger.info(f"Found {len(employees)} employees")
                
                # Логируем найденных сотрудников
                for emp in employees:
                    logger.info(f"Employee: {emp.id} - {emp.first_name} {emp.last_name}")
            else:
                logger.info("No accessible objects, returning empty employee list")
            
            # Получаем данные для переключения интерфейсов
            logger.info("Getting available interfaces")
            available_interfaces = await login_service.get_available_interfaces(user_id)
            logger.info(f"Available interfaces: {available_interfaces}")
            
            logger.info("Rendering template")
            return templates.TemplateResponse("manager/employees.html", {
                "request": request,
                "current_user": current_user,
                "employees": employees,
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error in manager employees: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников")


@router.get("/employees/add", response_class=HTMLResponse)
async def manager_employee_add_form(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Форма добавления нового сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем шаблоны договоров
            from sqlalchemy import select
            from domain.entities.contract import ContractTemplate
            
            templates_query = select(ContractTemplate).where(ContractTemplate.is_active == True)
            result = await db.execute(templates_query)
            contract_templates = result.scalars().all()
            
            # Получаем доступные объекты
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/employees/add.html", {
                "request": request,
                "current_user": current_user,
                "contract_templates": contract_templates,
                "accessible_objects": accessible_objects,
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error in manager employee add form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/employees/add")
async def manager_employee_add(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Создание нового сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            form_data = await request.form()
            
            # Получаем данные формы
            telegram_id = int(form_data.get("telegram_id"))
            first_name = form_data.get("first_name", "").strip()
            last_name = form_data.get("last_name", "").strip()
            username = form_data.get("username", "").strip()
            phone = form_data.get("phone", "").strip()
            email = form_data.get("email", "").strip()
            birth_date_str = form_data.get("birth_date", "").strip()
            role = form_data.get("role", "employee")
            is_active = form_data.get("is_active") == "true"
            
            # Дополнительные поля профиля (только для сотрудников)
            work_experience = form_data.get("work_experience", "").strip() if role == "employee" else None
            education = form_data.get("education", "").strip() if role == "employee" else None
            skills = form_data.get("skills", "").strip() if role == "employee" else None
            about = form_data.get("about", "").strip() if role == "employee" else None
            preferred_schedule = form_data.get("preferred_schedule", "").strip() if role == "employee" else None
            min_salary_str = form_data.get("min_salary", "").strip() if role == "employee" else None
            availability_notes = form_data.get("availability_notes", "").strip() if role == "employee" else None
            
            # Данные договора
            contract_template_id = form_data.get("contract_template")
            contract_objects = form_data.getlist("contract_objects")
            hourly_rate = int(form_data.get("hourly_rate", 500))
            start_date_str = form_data.get("start_date")
            end_date_str = form_data.get("end_date")
            
            # Валидация
            if not first_name:
                raise HTTPException(status_code=400, detail="Имя обязательно")
            
            # Создаем пользователя
            from domain.entities.user import User
            from shared.services.role_service import RoleService
            from apps.web.services.contract_service import ContractService
            from datetime import datetime, date
            
            # Обработка даты рождения
            birth_date = None
            if birth_date_str:
                try:
                    birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                except ValueError:
                    birth_date = None
            
            # Обработка минимальной зарплаты
            min_salary = None
            if min_salary_str and min_salary_str.isdigit():
                min_salary = int(min_salary_str)
            
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                phone=phone,
                email=email if email else None,
                birth_date=birth_date,
                work_experience=work_experience if work_experience else None,
                education=education if education else None,
                skills=skills if skills else None,
                about=about if about else None,
                preferred_schedule=preferred_schedule if preferred_schedule else None,
                min_salary=min_salary,
                availability_notes=availability_notes if availability_notes else None,
                role=role,
                roles=[role],
                is_active=is_active
            )
            
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            # Добавляем роль
            role_service = RoleService(db)
            from domain.entities.user import UserRole
            await role_service.add_role(user.id, UserRole(role))
            
            # Создаем договор (обязательно для сотрудников)
            if contract_objects:
                # Парсим даты
                start_date = None
                end_date = None
                if start_date_str:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                if end_date_str:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                
                # Создаем договор напрямую
                from domain.entities.contract import Contract
                
                contract = Contract(
                    employee_id=user.id,
                    owner_id=user_id,
                    template_id=int(contract_template_id),
                    hourly_rate=hourly_rate,
                    start_date=start_date,
                    end_date=end_date,
                    allowed_objects=[int(obj_id) for obj_id in contract_objects],
                    is_active=True,
                    status="active"
                )
                
                db.add(contract)
                await db.commit()
                await db.refresh(contract)
                
                # Создаем права управляющего на объекты если роль manager
                if role == "manager":
                    permission_service = ManagerPermissionService(db)
                    for obj_id in contract_objects:
                        await permission_service.create_permission(
                            contract_id=contract.id,
                            object_id=int(obj_id),
                            permissions={
                                "can_view": True,
                                "can_edit": True,
                                "can_delete": False,
                                "can_manage_employees": True,
                                "can_view_finances": True,
                                "can_edit_rates": True,
                                "can_edit_schedule": True
                            }
                        )
                
                logger.info(f"Created contract {contract.id} for employee {user.id}")
            
            logger.info(f"Created new employee {user.id} by manager {user_id}")
            
            return RedirectResponse(url=f"/manager/employees/{user.id}", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating employee: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания сотрудника")


@router.get("/employees/{employee_id}", response_class=HTMLResponse)
async def manager_employee_detail(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Детальная информация о сотруднике."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сотрудника
            from sqlalchemy import select
            from domain.entities.user import User
            from domain.entities.contract import Contract
            from domain.entities.shift import Shift
            from domain.entities.object import Object
            
            employee_query = select(User).where(User.id == employee_id)
            result = await db.execute(employee_query)
            employee = result.scalar_one_or_none()
            
            if not employee:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            # Получаем договор с сотрудником
            contract_query = select(Contract).where(
                Contract.employee_id == employee_id,
                Contract.is_active == True
            ).limit(1)
            result = await db.execute(contract_query)
            contract_obj = result.scalar_one_or_none()
            
            # Преобразуем договор в словарь для шаблона
            contract = None
            if contract_obj:
                contract = {
                    "id": contract_obj.id,
                    "contract_number": contract_obj.contract_number,
                    "title": contract_obj.title,
                    "hourly_rate": contract_obj.hourly_rate,
                    "start_date": contract_obj.start_date,
                    "end_date": contract_obj.end_date,
                    "status": contract_obj.status,
                    "is_manager": contract_obj.is_manager,
                    "manager_permissions": contract_obj.manager_permissions,
                    "is_active": contract_obj.is_active
                }
            
            # Получаем последние смены
            shifts_query = select(Shift).where(
                Shift.user_id == employee_id
            ).order_by(Shift.start_time.desc()).limit(10).options(
                selectinload(Shift.object)
            )
            result = await db.execute(shifts_query)
            recent_shifts = result.scalars().all()
            
            # Подсчитываем статистику
            total_shifts_query = select(Shift).where(Shift.user_id == employee_id)
            result = await db.execute(total_shifts_query)
            all_shifts = result.scalars().all()
            
            total_shifts = len(all_shifts)
            total_hours = sum(shift.duration_hours or 0 for shift in all_shifts)
            total_earnings = sum(shift.total_payment or 0 for shift in all_shifts)
            
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/employees/detail.html", {
                "request": request,
                "current_user": current_user,
                "employee": employee,
                "contract": contract,
                "recent_shifts": recent_shifts,
                "total_shifts": total_shifts,
                "total_hours": total_hours,
                "total_earnings": total_earnings,
                "available_interfaces": available_interfaces
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager employee detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудника")


@router.get("/employees/{employee_id}/edit", response_class=HTMLResponse)
async def manager_employee_edit_form(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Форма редактирования сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сотрудника
            from sqlalchemy import select
            from domain.entities.user import User
            from domain.entities.contract import Contract
            
            employee_query = select(User).where(User.id == employee_id)
            result = await db.execute(employee_query)
            employee = result.scalar_one_or_none()
            
            if not employee:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            # Получаем договор с сотрудником
            contract_query = select(Contract).where(
                Contract.employee_id == employee_id,
                Contract.is_active == True
            ).limit(1)
            result = await db.execute(contract_query)
            contract_obj = result.scalar_one_or_none()
            
            # Преобразуем договор в словарь для шаблона
            contract = None
            if contract_obj:
                contract = {
                    "id": contract_obj.id,
                    "contract_number": contract_obj.contract_number,
                    "title": contract_obj.title,
                    "hourly_rate": contract_obj.hourly_rate,
                    "start_date": contract_obj.start_date,
                    "end_date": contract_obj.end_date,
                    "status": contract_obj.status,
                    "is_manager": contract_obj.is_manager,
                    "manager_permissions": contract_obj.manager_permissions,
                    "is_active": contract_obj.is_active
                }
            
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/employees/edit.html", {
                "request": request,
                "current_user": current_user,
                "employee": employee,
                "contract": contract,
                "available_interfaces": available_interfaces
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager employee edit form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/employees/{employee_id}/edit")
async def manager_employee_edit(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Обновление сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            form_data = await request.form()
            
            # Получаем сотрудника
            from sqlalchemy import select
            from domain.entities.user import User
            
            employee_query = select(User).where(User.id == employee_id)
            result = await db.execute(employee_query)
            employee = result.scalar_one_or_none()
            
            if not employee:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            # Обновляем данные
            employee.first_name = form_data.get("first_name", "").strip()
            employee.last_name = form_data.get("last_name", "").strip()
            employee.username = form_data.get("username", "").strip()
            employee.phone = form_data.get("phone", "").strip()
            employee.email = form_data.get("email", "").strip() or None
            employee.is_active = form_data.get("is_active") == "true"
            
            # Обработка даты рождения
            birth_date_str = form_data.get("birth_date", "").strip()
            if birth_date_str:
                try:
                    employee.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                except ValueError:
                    pass
            else:
                employee.birth_date = None
            
            # Дополнительные поля профиля (только для сотрудников)
            if employee.role == "employee" or (hasattr(employee, 'roles') and employee.roles and "employee" in employee.roles):
                employee.work_experience = form_data.get("work_experience", "").strip() or None
                employee.education = form_data.get("education", "").strip() or None
                employee.skills = form_data.get("skills", "").strip() or None
                employee.about = form_data.get("about", "").strip() or None
                employee.preferred_schedule = form_data.get("preferred_schedule", "").strip() or None
                employee.availability_notes = form_data.get("availability_notes", "").strip() or None
                
                # Обработка минимальной зарплаты
                min_salary_str = form_data.get("min_salary", "").strip()
                if min_salary_str and min_salary_str.isdigit():
                    employee.min_salary = int(min_salary_str)
                else:
                    employee.min_salary = None
            
            await db.commit()
            await db.refresh(employee)
            
            logger.info(f"Updated employee {employee_id} by manager {user_id}")
            
            return RedirectResponse(url=f"/manager/employees/{employee_id}", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating employee: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления сотрудника")


@router.get("/employees/{employee_id}/shifts", response_class=HTMLResponse)
async def manager_employee_shifts(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Смены сотрудника."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сотрудника
            from sqlalchemy import select
            from domain.entities.user import User
            from domain.entities.shift import Shift
            from domain.entities.object import Object
            
            employee_query = select(User).where(User.id == employee_id)
            result = await db.execute(employee_query)
            employee = result.scalar_one_or_none()
            
            if not employee:
                raise HTTPException(status_code=404, detail="Сотрудник не найден")
            
            # Получаем смены
            shifts_query = select(Shift).where(
                Shift.user_id == employee_id
            ).order_by(Shift.start_time.desc()).options(
                selectinload(Shift.object)
            )
            result = await db.execute(shifts_query)
            shifts = result.scalars().all()
            
            # Получаем доступные объекты для фильтра
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            # Подсчитываем статистику
            total_hours = sum(shift.duration_hours or 0 for shift in shifts)
            total_earnings = sum(shift.total_payment or 0 for shift in shifts)
            
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/employees/shifts.html", {
                "request": request,
                "current_user": current_user,
                "employee": employee,
                "shifts": shifts,
                "objects": accessible_objects,
                "total_hours": total_hours,
                "total_earnings": total_earnings,
                "available_interfaces": available_interfaces
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager employee shifts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки смен")


@router.post("/employees/{employee_id}/terminate")
async def manager_employee_terminate(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Расторжение договора с сотрудником."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            form_data = await request.form()
            reason = form_data.get("reason", "").strip()
            
            if not reason:
                raise HTTPException(status_code=400, detail="Причина расторжения обязательна")
            
            # Получаем активный договор
            from sqlalchemy import select
            from domain.entities.contract import Contract
            from apps.web.services.contract_service import ContractService
            
            contract_query = select(Contract).where(
                Contract.employee_id == employee_id,
                Contract.is_active == True
            )
            result = await db.execute(contract_query)
            contract = result.scalar_one_or_none()
            
            if not contract:
                raise HTTPException(status_code=404, detail="Активный договор не найден")
            
            # Расторгаем договор
            contract.status = "terminated"
            contract.terminated_at = datetime.now()
            contract.termination_reason = reason
            
            await db.commit()
            await db.refresh(contract)
            
            logger.info(f"Terminated contract {contract.id} for employee {employee_id} by manager {user_id}")
            
            return RedirectResponse(url=f"/manager/employees/{employee_id}", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating employee contract: {e}")
        raise HTTPException(status_code=500, detail="Ошибка расторжения договора")


@router.get("/calendar", response_class=HTMLResponse)
async def manager_calendar(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(require_manager_or_owner),
):
    """Календарь управляющего."""
    try:
        logger.info("Starting manager_calendar function")
        
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            logger.info("Current user is RedirectResponse, redirecting")
            return current_user
        
        async with get_async_session() as db:
            logger.info("Got database session")
            
            user_id = await get_user_id_from_current_user(current_user, db)
            logger.info(f"User ID: {user_id}")
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем сервисы
            logger.info("Creating services")
            permission_service = ManagerPermissionService(db)
            login_service = RoleBasedLoginService(db)
            
            # Получаем доступные объекты управляющего
            logger.info("Getting accessible objects")
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            logger.info(f"Accessible objects count: {len(accessible_objects)}")
            
            # Определяем текущую дату или переданные параметры
            today = date.today()
            if year is None:
                year = today.year
            if month is None:
                month = today.month
            
            # Валидация даты
            if not (1 <= month <= 12):
                month = today.month
            if year < 2020 or year > 2030:
                year = today.year
            
            # Если выбран конкретный объект, проверяем доступ
            selected_object = None
            if object_id:
                for obj in accessible_objects:
                    if obj.id == object_id:
                        selected_object = obj
                        break
                if not selected_object:
                    raise HTTPException(status_code=404, detail="Объект не найден")
            
            # Получаем тайм-слоты для выбранного объекта или всех объектов
            from sqlalchemy import select, and_
            from sqlalchemy.orm import selectinload
            from domain.entities.time_slot import TimeSlot
            
            timeslots_data = []
            
            # Определяем объекты для запроса
            if selected_object:
                object_ids = [selected_object.id]
                objects_map = {selected_object.id: selected_object}
            else:
                object_ids = [obj.id for obj in accessible_objects]
                objects_map = {obj.id: obj for obj in accessible_objects}
            
            if object_ids:
                # Получаем тайм-слоты за месяц
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month + 1, 1)
                
                timeslots_query = select(TimeSlot).options(
                    selectinload(TimeSlot.object)
                ).where(
                    and_(
                        TimeSlot.object_id.in_(object_ids),
                        TimeSlot.slot_date >= start_date,
                        TimeSlot.slot_date < end_date,
                        TimeSlot.is_active == True
                    )
                ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
                
                timeslots_result = await db.execute(timeslots_query)
                timeslots = timeslots_result.scalars().all()
                
                logger.info(f"Found {len(timeslots)} timeslots for manager calendar")
                
                for slot in timeslots:
                    obj = objects_map.get(slot.object_id)
                    if obj:
                        timeslots_data.append({
                            "id": slot.id,
                            "object_id": slot.object_id,
                            "object_name": obj.name,
                            "date": slot.slot_date.isoformat(),
                            "start_time": slot.start_time.strftime("%H:%M"),
                            "end_time": slot.end_time.strftime("%H:%M"),
                            "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate),
                            "is_active": slot.is_active,
                            "notes": slot.notes or ""
                        })
            
            # Получаем данные о сменах за месяц
            shifts_data = []
            logger.info(f"Getting shifts for object_ids: {object_ids}, period: {start_date} to {end_date}")
            if object_ids:
                # Получаем запланированные смены
                from domain.entities.shift_schedule import ShiftSchedule
                scheduled_shifts_query = select(ShiftSchedule).where(
                    and_(
                        ShiftSchedule.object_id.in_(object_ids),
                        ShiftSchedule.planned_start >= start_date,
                        ShiftSchedule.planned_start < end_date
                    )
                ).order_by(ShiftSchedule.planned_start)
                
                scheduled_shifts_result = await db.execute(scheduled_shifts_query)
                scheduled_shifts = scheduled_shifts_result.scalars().all()
                logger.info(f"Found {len(scheduled_shifts)} scheduled shifts")
                
                # Получаем отработанные смены
                from domain.entities.shift import Shift
                actual_shifts_query = select(Shift).options(
                    selectinload(Shift.user)
                ).where(
                    and_(
                        Shift.object_id.in_(object_ids),
                        Shift.start_time >= start_date,
                        Shift.start_time < end_date
                    )
                ).order_by(Shift.start_time)
                
                actual_shifts_result = await db.execute(actual_shifts_query)
                actual_shifts = actual_shifts_result.scalars().all()
                
                # Получаем информацию о пользователях для запланированных смен
                user_ids = list(set(shift.user_id for shift in scheduled_shifts))
                users_query = select(User).where(User.id.in_(user_ids))
                users_result = await db.execute(users_query)
                users = {user.id: user for user in users_result.scalars().all()}
                
                # Преобразуем запланированные смены в формат для календаря
                for shift in scheduled_shifts:
                    obj = objects_map.get(shift.object_id)
                    if obj:
                        user = users.get(shift.user_id)
                        employee_name = f"{user.first_name} {user.last_name or ''}".strip() if user else f"ID {shift.user_id}"
                        
                        shift_data = {
                            "id": f"schedule_{shift.id}",
                            "object_id": shift.object_id,
                            "object_name": obj.name,
                            "date": shift.planned_start.date().isoformat(),
                            "start_time": web_timezone_helper.format_time_with_timezone(shift.planned_start, obj.timezone if obj else 'Europe/Moscow'),
                            "end_time": web_timezone_helper.format_time_with_timezone(shift.planned_end, obj.timezone if obj else 'Europe/Moscow'),
                            "status": shift.status,
                            "employee_name": employee_name,
                            "notes": shift.notes or ""
                        }
                        shifts_data.append(shift_data)
                        
                        # Логируем смену на 23 сентября
                        if shift.planned_start.date().isoformat() == "2025-09-23":
                            logger.info(f"Found shift on 23.09: {shift_data}")
                
                # Преобразуем отработанные смены в формат для календаря
                for shift in actual_shifts:
                    obj = objects_map.get(shift.object_id)
                    if obj:
                        shifts_data.append({
                            "id": shift.id,
                            "object_id": shift.object_id,
                            "object_name": obj.name,
                            "date": shift.start_time.date().isoformat(),
                            "start_time": web_timezone_helper.format_time_with_timezone(shift.start_time, obj.timezone if obj else 'Europe/Moscow'),
                            "end_time": web_timezone_helper.format_time_with_timezone(shift.end_time, obj.timezone if obj else 'Europe/Moscow') if shift.end_time else None,
                            "status": shift.status,
                            "employee_name": f"{shift.user.first_name} {shift.user.last_name or ''}".strip(),
                            "notes": shift.notes or ""
                        })
            
            # Создаем календарную сетку
            logger.info(f"Creating calendar grid with {len(timeslots_data)} timeslots and {len(shifts_data)} shifts")
            logger.info(f"Sample shifts_data: {shifts_data[:3] if shifts_data else 'No shifts'}")
            calendar_data = _create_calendar_grid_manager(year, month, timeslots_data, shifts_data)
            logger.info(f"Calendar grid created with {len(calendar_data)} weeks")
            logger.info(f"First week has {len(calendar_data[0]) if calendar_data else 0} days")
            
            # Проверяем структуру calendar_data
            if calendar_data and len(calendar_data) > 0:
                first_week = calendar_data[0]
                if first_week and len(first_week) > 0:
                    first_day = first_week[0]
                    logger.info(f"First day structure: {first_day.keys() if hasattr(first_day, 'keys') else type(first_day)}")
                    if hasattr(first_day, 'get'):
                        logger.info(f"First day timeslots_count: {first_day.get('timeslots_count', 'N/A')}")
                        logger.info(f"First day timeslots: {len(first_day.get('timeslots', []))}")
            
            # Подготавливаем данные для шаблона
            objects_list = [{"id": obj.id, "name": obj.name} for obj in accessible_objects]
            
            # Навигация по месяцам
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            
            # Русские названия месяцев
            RU_MONTHS = [
                "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
            ]
            
            # Получаем данные для переключения интерфейсов
            logger.info("Getting available interfaces")
            available_interfaces = await login_service.get_available_interfaces(user_id)
            logger.info(f"Available interfaces: {available_interfaces}")
            
            # Получаем список сотрудников для drag&drop панели
            employees_list = []
            # TODO: Реализовать загрузку сотрудников через ContractService
            # try:
            #     from apps.web.services.contract_service import ContractService
            #     contract_service = ContractService(session)
            #     # Получаем сотрудников для всех доступных объектов
            #     for obj in objects_list:
            #         employees = await contract_service.get_employees_by_object(obj["id"])
            #         for emp in employees:
            #             if not any(e["id"] == emp.id for e in employees_list):
            #                 employees_list.append({
            #                     "id": emp.id,
            #                     "name": emp.name,
            #                     "role": "employee"
            #                 })
            # except Exception as e:
            #     logger.warning(f"Could not load employees for manager calendar: {e}")
            #     employees_list = []
            
            # Подготавливаем данные для shared компонентов календаря
            calendar_title = f"{RU_MONTHS[month]} {year}"
            current_date = f"{year}-{month:02d}-01"
            
            # Используем calendar_data напрямую как calendar_weeks
            calendar_weeks = calendar_data
            
            logger.info("Rendering template")
            return templates.TemplateResponse("manager/calendar.html", {
                "request": request,
                "title": "Календарное планирование",
                "current_user": current_user,
                "year": year,
                "month": month,
                "month_name": RU_MONTHS[month],
                "calendar_title": calendar_title,
                "current_date": current_date,
                "view_type": "month",
                "show_today_button": True,
                "show_view_switcher": True,
                "show_filters": True,
                "show_refresh": True,
                "calendar_weeks": calendar_weeks,
                "accessible_objects": objects_list,
                "employees": employees_list,
                "selected_object_id": object_id,
                "selected_object": selected_object,
                "timeslots": timeslots_data,
                "prev_month": prev_month,
                "prev_year": prev_year,
                "next_month": next_month,
                "next_year": next_year,
                "today": today,
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error in manager calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки календаря")


@router.get("/calendar/api/timeslots-status")
async def get_timeslots_status_manager(
    year: int = Query(...),
    month: int = Query(...),
    object_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user_dependency())
):
    """Получение статуса тайм-слотов для календаря управляющего"""
    try:
        logger.info(f"Getting timeslots status for manager: {year}-{month}, object_id: {object_id}")
        
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        async with get_async_session() as db:
            # Получаем user_id
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            object_ids = [obj.id for obj in accessible_objects]
            
            if not object_ids:
                return []
            
            # Фильтруем по выбранному объекту, если указан
            if object_id:
                if object_id not in object_ids:
                    raise HTTPException(status_code=403, detail="Нет доступа к объекту")
                object_ids = [object_id]
            
            # Получаем тайм-слоты за месяц
            from sqlalchemy import select, and_
            from sqlalchemy.orm import selectinload
            from domain.entities.time_slot import TimeSlot
            from domain.entities.object import Object
            from domain.entities.user import User
            
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month + 1, 1)
            
            timeslots_query = select(TimeSlot).options(
                selectinload(TimeSlot.object)
            ).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= start_date,
                    TimeSlot.slot_date < end_date,
                    TimeSlot.is_active == True
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)
            
            timeslots_result = await db.execute(timeslots_query)
            timeslots = timeslots_result.scalars().all()
            
            logger.info(f"Found {len(timeslots)} timeslots for manager")
            
            # Получаем запланированные смены за месяц
            from domain.entities.shift_schedule import ShiftSchedule
            
            scheduled_shifts_query = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.object_id.in_(object_ids),
                    ShiftSchedule.planned_start >= start_date,
                    ShiftSchedule.planned_start < end_date
                )
            ).order_by(ShiftSchedule.planned_start)
            
            scheduled_shifts_result = await db.execute(scheduled_shifts_query)
            scheduled_shifts = scheduled_shifts_result.scalars().all()
            
            logger.info(f"Found {len(scheduled_shifts)} scheduled shifts for manager")
            
            # Получаем отработанные смены за месяц
            from domain.entities.shift import Shift
            
            actual_shifts_query = select(Shift).options(
                selectinload(Shift.user)
            ).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time < end_date
                )
            ).order_by(Shift.start_time)
            
            actual_shifts_result = await db.execute(actual_shifts_query)
            actual_shifts = actual_shifts_result.scalars().all()
            
            logger.info(f"Found {len(actual_shifts)} actual shifts for manager")
            
            # Получаем информацию о пользователях для запланированных смен
            user_ids = list(set(shift.user_id for shift in scheduled_shifts))
            users_query = select(User).where(User.id.in_(user_ids))
            users_result = await db.execute(users_query)
            users = {user.id: user for user in users_result.scalars().all()}
            
            # Создаем карту запланированных смен по time_slot_id
            scheduled_shifts_map = {}
            scheduled_by_object_date = {}
            for shift in scheduled_shifts:
                user = users.get(shift.user_id)
                user_name = f"{user.first_name} {user.last_name or ''}".strip() if user else f"ID {shift.user_id}"
                
                if shift.time_slot_id:
                    scheduled_shifts_map.setdefault(shift.time_slot_id, [])
                    obj = objects_map.get(shift.object_id)
                    scheduled_shifts_map[shift.time_slot_id].append({
                        "id": shift.id,
                        "user_id": shift.user_id,
                        "user_name": user_name,
                        "status": shift.status,
                        "start_time": web_timezone_helper.format_time_with_timezone(shift.planned_start, obj.timezone if obj else 'Europe/Moscow'),
                        "end_time": web_timezone_helper.format_time_with_timezone(shift.planned_end, obj.timezone if obj else 'Europe/Moscow'),
                        "notes": shift.notes
                    })
                key = (shift.object_id, shift.planned_start.date())
                scheduled_by_object_date.setdefault(key, []).append(shift)
            
            # Создаем карту отработанных смен по time_slot_id
            actual_shifts_map = {}
            actual_by_object_date = {}
            for shift in actual_shifts:
                if shift.time_slot_id:
                    actual_shifts_map.setdefault(shift.time_slot_id, [])
                    obj = objects_map.get(shift.object_id)
                    actual_shifts_map[shift.time_slot_id].append({
                        "id": shift.id,
                        "user_id": shift.user_id,
                        "user_name": f"{shift.user.first_name} {shift.user.last_name or ''}".strip(),
                        "status": shift.status,
                        "start_time": web_timezone_helper.format_time_with_timezone(shift.start_time, obj.timezone if obj else 'Europe/Moscow'),
                        "end_time": web_timezone_helper.format_time_with_timezone(shift.end_time, obj.timezone if obj else 'Europe/Moscow') if shift.end_time else None,
                        "total_hours": float(shift.total_hours) if shift.total_hours else None,
                        "total_payment": float(shift.total_payment) if shift.total_payment else None,
                        "is_planned": shift.is_planned,
                        "notes": shift.notes
                    })
                key = (shift.object_id, shift.start_time.date())
                actual_by_object_date.setdefault(key, []).append(shift)
            
            # Создаем данные для каждого тайм-слота
            result_data = []
            for slot in timeslots:
                # Определяем статус на основе запланированных и отработанных смен
                status = "empty"
                scheduled_shifts = []
                actual_shifts = []
                
                # Ищем запланированные смены для этого конкретного тайм-слота
                if slot.id in scheduled_shifts_map:
                    scheduled_shifts = scheduled_shifts_map[slot.id]
                else:
                    # Дополнительно ищем пересечения по объекту и дате
                    key_sched = (slot.object_id, slot.slot_date)
                    overlaps_sched = []
                    for sh in scheduled_by_object_date.get(key_sched, []):
                        sh_start = sh.planned_start.time()
                        sh_end = sh.planned_end.time()
                        if (sh_start < slot.end_time) and (slot.start_time < sh_end):
                            overlaps_sched.append(sh)
                    if overlaps_sched:
                        for sh in overlaps_sched:
                            user = users.get(sh.user_id)
                            user_name = f"{user.first_name} {user.last_name or ''}".strip() if user else f"ID {sh.user_id}"
                            scheduled_shifts.append({
                                "id": sh.id,
                                "user_id": sh.user_id,
                                "user_name": user_name,
                                "status": sh.status,
                                "start_time": web_timezone_helper.format_time_with_timezone(sh.planned_start, slot.object.timezone if slot.object else 'Europe/Moscow'),
                                "end_time": web_timezone_helper.format_time_with_timezone(sh.planned_end, slot.object.timezone if slot.object else 'Europe/Moscow'),
                                "notes": sh.notes
                            })
                
                # Ищем отработанные смены для этого конкретного тайм-слота
                if slot.id in actual_shifts_map:
                    actual_shifts = actual_shifts_map[slot.id]
                else:
                    # Дополнительно ищем пересечения по объекту и дате
                    key = (slot.object_id, slot.slot_date)
                    overlaps = []
                    for sh in actual_by_object_date.get(key, []):
                        sh_start = sh.start_time.time()
                        sh_end = sh.end_time.time() if sh.end_time else None
                        if sh_end is None:
                            if sh_start < slot.end_time:
                                overlaps.append(sh)
                        else:
                            if (sh_start < slot.end_time) and (slot.start_time < sh_end):
                                overlaps.append(sh)
                    if overlaps:
                        for sh in overlaps:
                            actual_shifts.append({
                                "id": sh.id,
                                "user_id": sh.user_id,
                                "user_name": f"{sh.user.first_name} {sh.user.last_name or ''}".strip(),
                                "status": sh.status,
                                "start_time": web_timezone_helper.format_time_with_timezone(sh.start_time, slot.object.timezone if slot.object else 'Europe/Moscow'),
                                "end_time": web_timezone_helper.format_time_with_timezone(sh.end_time, slot.object.timezone if slot.object else 'Europe/Moscow') if sh.end_time else None,
                                "total_hours": float(sh.total_hours) if sh.total_hours else None,
                                "total_payment": float(sh.total_payment) if sh.total_payment else None,
                                "is_planned": sh.is_planned,
                                "notes": sh.notes
                            })
                
                # Определяем статус с приоритетом
                has_actual_active = any(shift["status"] == "active" for shift in actual_shifts)
                has_actual_completed = any(shift["status"] == "completed" for shift in actual_shifts)
                has_actual_only_cancelled = bool(actual_shifts) and all(shift["status"] == "cancelled" for shift in actual_shifts)
                has_sched_confirmed = any(shift["status"] == "confirmed" for shift in scheduled_shifts)
                has_sched_planned = any(shift["status"] == "planned" for shift in scheduled_shifts)
                has_sched_cancelled = any(shift["status"] == "cancelled" for shift in scheduled_shifts)

                if has_actual_active:
                    status = "active"
                elif has_actual_completed:
                    status = "completed"
                elif has_sched_confirmed:
                    status = "confirmed"
                elif has_sched_planned:
                    status = "planned"
                elif has_actual_only_cancelled or has_sched_cancelled:
                    status = "cancelled"
                
                # Подсчитываем занятость
                max_slots = slot.max_employees or 1
                scheduled_effective = [s for s in scheduled_shifts if s.get("status") in ("planned", "confirmed")]
                planned_count = min(len(scheduled_effective), max_slots)

                actual_non_cancelled = [a for a in actual_shifts if a.get("status") != "cancelled"]
                actual_planned_nc = [a for a in actual_non_cancelled if a.get("is_planned")]
                actual_spont_nc = [a for a in actual_non_cancelled if not a.get("is_planned")]

                base_total = min(max_slots, planned_count + len(actual_planned_nc))
                total_shifts = base_total + len(actual_spont_nc)
                availability = f"{total_shifts}/{max_slots}"
                
                result_data.append({
                    "slot_id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": slot.object.name,
                    "date": slot.slot_date.isoformat(),
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else 0,
                    "status": status,
                    "scheduled_shifts": scheduled_shifts,
                    "actual_shifts": actual_shifts,
                    "availability": availability,
                    "occupied_slots": total_shifts,
                    "max_slots": max_slots
                })
            
            logger.info(f"Returning {len(result_data)} timeslots for manager")
            return result_data
        
    except Exception as e:
        logger.error(f"Error getting timeslots status for manager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки статуса тайм-слотов")


@router.get("/calendar/api/timeslot/{timeslot_id}")
async def get_timeslot_details_manager(
    timeslot_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Детали конкретного тайм-слота для управляющего"""
    try:
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from domain.entities.time_slot import TimeSlot
        from domain.entities.object import Object
        from domain.entities.user import User
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift import Shift

        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        async with get_async_session() as db:
            # Получаем user_id
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступных объектов")

            # Получаем слот и проверяем доступ
            slot_q = select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id)
            slot = (await db.execute(slot_q)).scalar_one_or_none()
            if not slot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден")
            
            if slot.object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к тайм-слоту")

            # Запланированные смены по тайм-слоту
            sched_q = select(ShiftSchedule).options(selectinload(ShiftSchedule.user)).where(ShiftSchedule.time_slot_id == timeslot_id).order_by(ShiftSchedule.planned_start)
            sched = (await db.execute(sched_q)).scalars().all()
            scheduled = [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "user_name": f"{s.user.first_name} {s.user.last_name or ''}".strip() if s.user else None,
                    "status": s.status,
                    "start_time": s.planned_start.time().strftime("%H:%M"),
                    "end_time": s.planned_end.time().strftime("%H:%M"),
                    "notes": s.notes,
                }
                for s in sched
            ]

            # Фактические смены
            act_q = select(Shift).options(selectinload(Shift.user)).where(Shift.time_slot_id == timeslot_id).order_by(Shift.start_time)
            acts_linked = (await db.execute(act_q)).scalars().all()

            # Плюс спонтанные/несвязанные: по объекту и дате слота, с пересечением времени
            from datetime import datetime, time
            day_start = datetime.combine(slot.slot_date, time.min)
            day_end = datetime.combine(slot.slot_date, time.max)
            act_day_q = select(Shift).options(selectinload(Shift.user)).where(
                and_(
                    Shift.object_id == slot.object_id,
                    Shift.start_time >= day_start,
                    Shift.start_time <= day_end,
                )
            ).order_by(Shift.start_time)
            acts_day = (await db.execute(act_day_q)).scalars().all()

            # Отбираем пересекающиеся по времени и не дублируем
            def is_overlap(sh: Shift) -> bool:
                sh_start = sh.start_time.time()
                sh_end = sh.end_time.time() if sh.end_time else None
                if sh_end is None:
                    return sh_start < slot.end_time
                return (sh_start < slot.end_time) and (slot.start_time < sh_end)

            linked_ids = {sh.id for sh in acts_linked}
            acts_overlap = [sh for sh in acts_day if (sh.id not in linked_ids) and is_overlap(sh)]

            acts_all = acts_linked + acts_overlap
            actual = [
                {
                    "id": sh.id,
                    "user_id": sh.user_id,
                    "user_name": f"{sh.user.first_name} {sh.user.last_name or ''}".strip() if sh.user else None,
                    "status": sh.status,
                    "start_time": sh.start_time.time().strftime("%H:%M"),
                    "end_time": sh.end_time.time().strftime("%H:%M") if sh.end_time else None,
                    "total_hours": float(sh.total_hours) if sh.total_hours else None,
                    "total_payment": float(sh.total_payment) if sh.total_payment else None,
                    "is_planned": sh.is_planned,
                    "notes": sh.notes,
                }
                for sh in acts_all
            ]

            return {
                "slot": {
                    "id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": slot.object.name if slot.object else None,
                    "date": slot.slot_date.strftime("%Y-%m-%d"),
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else None,
                    "max_employees": slot.max_employees or 1,
                    "is_active": slot.is_active,
                    "notes": slot.notes or "",
                },
                "scheduled": scheduled,
                "actual": actual,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeslot details for manager: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")


@router.get("/timeslots/{timeslot_id}", response_class=HTMLResponse)
async def manager_timeslot_detail(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_manager_or_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали тайм-слота управляющего"""
    try:
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        # Получаем внутренний ID пользователя
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=400, detail="Пользователь не найден")
        
        # Получаем доступные объекты управляющего
        permission_service = ManagerPermissionService(db)
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        accessible_object_ids = [obj.id for obj in accessible_objects]
        
        if not accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступных объектов")
        
        # Получаем тайм-слот
        timeslot_query = select(TimeSlot).options(
            selectinload(TimeSlot.object)
        ).where(TimeSlot.id == timeslot_id)
        
        timeslot_result = await db.execute(timeslot_query)
        timeslot = timeslot_result.scalar_one_or_none()
        
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Проверяем доступ к объекту
        if timeslot.object_id not in accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к тайм-слоту")
        
        # Получаем связанные смены и расписания
        # Запланированные смены
        scheduled_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.user)
        ).where(ShiftSchedule.time_slot_id == timeslot_id).order_by(ShiftSchedule.planned_start)
        
        scheduled_result = await db.execute(scheduled_query)
        scheduled_shifts = scheduled_result.scalars().all()
        
        # Фактические смены
        actual_query = select(Shift).options(
            selectinload(Shift.user)
        ).where(Shift.time_slot_id == timeslot_id).order_by(Shift.start_time)
        
        actual_result = await db.execute(actual_query)
        actual_shifts = actual_result.scalars().all()
        
        return templates.TemplateResponse(
            "manager/timeslot_detail.html",
            {
                "request": request,
                "title": f"Тайм-слот {timeslot.object.name if timeslot.object else 'Неизвестный объект'}",
                "timeslot": timeslot,
                "scheduled_shifts": scheduled_shifts,
                "actual_shifts": actual_shifts,
                "current_user": current_user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeslot detail for manager: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")


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
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                return templates.TemplateResponse("manager/reports/index.html", {
                    "request": request,
                    "current_user": current_user,
                    "available_interfaces": [],
                    "objects": [],
                    "employees": [],
                    "stats": {"total_shifts": 0, "total_hours": 0, "total_payment": 0, "active_objects": 0, "employees": 0}
                })
            
            # Получаем всех пользователей, которые работали на доступных объектах
            from sqlalchemy import select, and_
            from domain.entities.shift import Shift
            from domain.entities.user import User
            from datetime import datetime, timedelta
            
            employees_query = select(User.id, User.telegram_id, User.username, User.first_name, User.last_name, User.phone, User.role, User.is_active, User.created_at, User.updated_at).distinct().join(Shift, User.id == Shift.user_id).where(
                Shift.object_id.in_(accessible_object_ids)
            )
            employees_result = await db.execute(employees_query)
            employees = employees_result.all()
            
            # Если нет сотрудников из смен, показываем всех пользователей с ролью employee
            if not employees:
                all_employees_query = select(User.id, User.telegram_id, User.username, User.first_name, User.last_name, User.phone, User.role, User.is_active, User.created_at, User.updated_at).where(User.role == "employee")
                all_employees_result = await db.execute(all_employees_query)
                employees = all_employees_result.all()
            
            # Статистика за последний месяц
            month_ago = datetime.now() - timedelta(days=30)
            
            shifts_query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(
                and_(
                    Shift.object_id.in_(accessible_object_ids),
                    Shift.start_time >= month_ago
                )
            )
            shifts_result = await db.execute(shifts_query)
            recent_shifts = shifts_result.scalars().all()
            
            stats = {
                "total_shifts": len(recent_shifts),
                "total_hours": sum(s.total_hours or 0 for s in recent_shifts if s.total_hours),
                "total_payment": sum(s.total_payment or 0 for s in recent_shifts if s.total_payment),
                "active_objects": len(accessible_objects),
                "employees": len(employees)
            }
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/reports/index.html", {
                "request": request,
                "current_user": current_user,
                "objects": accessible_objects,
                "employees": employees,
                "available_interfaces": available_interfaces,
                "stats": stats
            })
        
    except Exception as e:
        logger.error(f"Error in manager reports: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки отчетов")


@router.post("/reports/generate")
async def manager_generate_report(
    request: Request,
    report_type: str = Form(...),
    date_from: str = Form(...),
    date_to: str = Form(...),
    object_id: Optional[int] = Form(None),
    employee_id: Optional[int] = Form(None),
    format: str = Form("excel"),
    current_user: dict = Depends(require_manager_or_owner),
):
    """Генерация отчета управляющего."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объектам")
            
            # Проверяем доступ к конкретному объекту, если указан
            if object_id and object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к указанному объекту")
            
            # Парсим даты
            from datetime import datetime
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
                end_date = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты")
            
            # Получаем смены за период
            from sqlalchemy import select, and_, desc
            from domain.entities.shift import Shift
            
            shifts_query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(
                and_(
                    Shift.object_id.in_(accessible_object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time <= end_date + timedelta(days=1)
                )
            )
            
            # Применение фильтров
            if object_id and object_id in accessible_object_ids:
                shifts_query = shifts_query.where(Shift.object_id == object_id)
            
            if employee_id:
                shifts_query = shifts_query.where(Shift.user_id == employee_id)
            
            # Выполнение запроса
            shifts_result = await db.execute(shifts_query.order_by(desc(Shift.start_time)))
            shifts = shifts_result.scalars().all()
            
            # Генерация отчета в зависимости от типа
            if report_type == "shifts":
                return await _generate_shifts_report_manager(shifts, format, start_date, end_date)
            elif report_type == "employees":
                return await _generate_employees_report_manager(shifts, format, start_date, end_date)
            elif report_type == "objects":
                return await _generate_objects_report_manager(shifts, format, start_date, end_date)
            else:
                return {"error": "Неизвестный тип отчета"}
        
    except Exception as e:
        logger.error(f"Error generating manager report: {e}")
        raise HTTPException(status_code=500, detail="Ошибка генерации отчета")


@router.get("/reports/stats/period")
async def manager_reports_stats_period(
    request: Request,
    date_from: str = Query(...),
    date_to: str = Query(...),
    object_id: Optional[int] = Query(None),
    current_user: dict = Depends(require_manager_or_owner),
):
    """Статистика за период для управляющего."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                return {"stats": {"total_shifts": 0, "total_hours": 0, "total_payment": 0}}
            
            # Проверяем доступ к конкретному объекту, если указан
            if object_id and object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к указанному объекту")
            
            # Парсим даты
            from datetime import datetime
            try:
                start_date = datetime.strptime(date_from, "%Y-%m-%d")
                end_date = datetime.strptime(date_to, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты")
            
            # Получаем смены за период
            from sqlalchemy import select, and_
            from domain.entities.shift import Shift
            
            shifts_query = select(Shift).where(
                and_(
                    Shift.object_id.in_(accessible_object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time <= end_date
                )
            )
            
            if object_id:
                shifts_query = shifts_query.where(Shift.object_id == object_id)
            
            shifts_result = await db.execute(shifts_query)
            shifts = shifts_result.scalars().all()
            
            stats = {
                "total_shifts": len(shifts),
                "total_hours": sum(s.total_hours or 0 for s in shifts if s.total_hours),
                "total_payment": sum(s.total_payment or 0 for s in shifts if s.total_payment)
            }
            
            return {"stats": stats}
        
    except Exception as e:
        logger.error(f"Error getting manager stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


async def _generate_shifts_report_manager(shifts: List[Shift], format: str, start_date: datetime, end_date: datetime):
    """Генерация отчета по сменам для управляющего"""
    data = []
    
    for shift in shifts:
        data.append({
            "ID": shift.id,
            "Сотрудник": f"{shift.user.first_name} {shift.user.last_name or ''}".strip(),
            "Объект": shift.object.name,
            "Дата начала": web_timezone_helper.format_datetime_with_timezone(shift.start_time, shift.object.timezone if shift.object else 'Europe/Moscow'),
            "Дата окончания": web_timezone_helper.format_datetime_with_timezone(shift.end_time, shift.object.timezone if shift.object else 'Europe/Moscow') if shift.end_time else "Не завершена",
            "Статус": shift.status,
            "Часов": shift.total_hours or 0,
            "Ставка": shift.hourly_rate or 0,
            "Сумма": shift.total_payment or 0,
            "Заметки": shift.notes or ""
        })
    
    if format == "excel":
        return await _create_excel_file_manager(data, f"manager_shifts_report_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}")
    else:
        return {"data": data, "total": len(data)}


async def _generate_employees_report_manager(shifts: List[Shift], format: str, start_date: datetime, end_date: datetime):
    """Генерация отчета по сотрудникам для управляющего"""
    # Группировка по сотрудникам
    employees_data = {}
    
    for shift in shifts:
        employee_id = shift.user_id
        if employee_id not in employees_data:
            employees_data[employee_id] = {
                "employee": shift.user,
                "shifts": [],
                "total_hours": 0,
                "total_payment": 0
            }
        
        employees_data[employee_id]["shifts"].append(shift)
        employees_data[employee_id]["total_hours"] += shift.total_hours or 0
        employees_data[employee_id]["total_payment"] += shift.total_payment or 0
    
    data = []
    for emp_data in employees_data.values():
        data.append({
            "Сотрудник": f"{emp_data['employee'].first_name} {emp_data['employee'].last_name or ''}".strip(),
            "Количество смен": len(emp_data["shifts"]),
            "Общее время": emp_data["total_hours"],
            "Общая сумма": emp_data["total_payment"],
            "Средняя ставка": emp_data["total_payment"] / emp_data["total_hours"] if emp_data["total_hours"] > 0 else 0
        })
    
    if format == "excel":
        return await _create_excel_file_manager(data, f"manager_employees_report_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}")
    else:
        return {"data": data, "total": len(data)}


async def _generate_objects_report_manager(shifts: List[Shift], format: str, start_date: datetime, end_date: datetime):
    """Генерация отчета по объектам для управляющего"""
    # Группировка по объектам
    objects_data = {}
    
    for shift in shifts:
        object_id = shift.object_id
        if object_id not in objects_data:
            objects_data[object_id] = {
                "object": shift.object,
                "shifts": [],
                "total_hours": 0,
                "total_payment": 0,
                "employees": set()
            }
        
        objects_data[object_id]["shifts"].append(shift)
        objects_data[object_id]["total_hours"] += shift.total_hours or 0
        objects_data[object_id]["total_payment"] += shift.total_payment or 0
        objects_data[object_id]["employees"].add(shift.user_id)
    
    data = []
    for obj_data in objects_data.values():
        data.append({
            "Объект": obj_data["object"].name,
            "Адрес": obj_data["object"].address or "",
            "Количество смен": len(obj_data["shifts"]),
            "Количество сотрудников": len(obj_data["employees"]),
            "Общее время": obj_data["total_hours"],
            "Общая сумма": obj_data["total_payment"],
            "Средняя ставка": obj_data["total_payment"] / obj_data["total_hours"] if obj_data["total_hours"] > 0 else 0
        })
    
    if format == "excel":
        return await _create_excel_file_manager(data, f"manager_objects_report_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}")
    else:
        return {"data": data, "total": len(data)}


async def _create_excel_file_manager(data: List[dict], filename: str):
    """Создание Excel файла для управляющего"""
    if not data:
        return {"error": "Нет данных для отчета"}
    
    try:
        import pandas as pd
        from openpyxl import Workbook
        from openpyxl.utils.dataframe import dataframe_to_rows
        from openpyxl.styles import Font, PatternFill, Alignment
        from fastapi.responses import StreamingResponse
        import io
        
        # Создание DataFrame
        df = pd.DataFrame(data)
        
        # Создание Excel файла
        wb = Workbook()
        ws = wb.active
        ws.title = "Отчет управляющего"
        
        # Добавление данных
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        # Стилизация
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Автоширина колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        # Сохранение в байты
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        # Возврат файла
        return StreamingResponse(
            io.BytesIO(excel_buffer.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
        
    except Exception as e:
        logger.error(f"Error creating Excel file for manager: {e}")
        return {"error": f"Ошибка создания Excel файла: {str(e)}"}


def _create_calendar_grid_manager(
    year: int,
    month: int,
    timeslots: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]] | None = None,
) -> List[List[Dict[str, Any]]]:
    """Создает календарную сетку с тайм-слотами и сменами для управляющего"""
    import calendar as py_calendar
    from datetime import date, timedelta
    if shifts is None:
        shifts = []
    
    # Получаем первый день месяца и количество дней
    first_day = date(year, month, 1)
    last_day = date(year, month, py_calendar.monthrange(year, month)[1])
    
    # Находим первый понедельник для отображения
    first_monday = first_day - timedelta(days=first_day.weekday())
    
    # Создаем сетку 6x7 (6 недель, 7 дней)
    calendar_grid = []
    current_date = first_monday
    
    for week in range(6):
        week_data = []
        for day in range(7):
            # Преобразуем current_date в строку для сравнения
            current_date_str = current_date.isoformat()
            
            # Смены за день
            all_day_shifts = [s for s in shifts if s.get("date") == current_date_str]
            
            # Логируем для отладки 23 сентября
            if current_date_str == "2025-09-23":
                logger.info(f"DEBUG 23.09: Found {len(all_day_shifts)} shifts for this day")
                logger.info(f"DEBUG 23.09: current_date_str={current_date_str}")
                logger.info(f"DEBUG 23.09: Total shifts in data: {len(shifts)}")
                for i, s in enumerate(shifts):
                    if s.get("date") == "2025-09-23":
                        logger.info(f"DEBUG 23.09: Shift {i}: {s}")
                for s in all_day_shifts:
                    logger.info(f"DEBUG 23.09 shift: {s}")
            active_by_object: Dict[int, Dict[str, Any]] = {}
            completed_by_object: Dict[int, Dict[str, Any]] = {}
            for s in all_day_shifts:
                oid = s.get("object_id")
                if not oid:
                    continue
                if s.get("status") == "active":
                    active_by_object[oid] = s
                elif s.get("status") == "completed":
                    completed_by_object[oid] = s

            # Скрываем planned, если есть active/completed по тому же объекту
            # Исключаем отмененные смены
            day_shifts = []
            for s in all_day_shifts:
                oid = s.get("object_id")
                # Исключаем отмененные смены
                if s.get("status") == "cancelled":
                    continue
                # Скрываем planned, если есть active/completed по тому же объекту
                if s.get("status") == "planned" and oid and (oid in active_by_object or oid in completed_by_object):
                    continue
                day_shifts.append(s)
            
            # Логируем для отладки 23 сентября
            if current_date_str == "2025-09-23":
                logger.info(f"DEBUG 23.09: all_day_shifts={len(all_day_shifts)}, day_shifts={len(day_shifts)}")
                for s in day_shifts:
                    logger.info(f"DEBUG 23.09 shift: {s}")

            # Тайм-слоты за день: показывать только если нет связанных смен (не cancelled)
            day_timeslots = []
            for slot in timeslots:
                if slot.get("date") == current_date_str and slot.get("is_active", True):
                    has_related = False
                    for s in day_shifts:
                        if s.get("object_id") == slot.get("object_id") and s.get("status") != "cancelled":
                            has_related = True
                            break
                    if not has_related:
                        # Добавляем поле status для тайм-слота
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


@router.get("/api/employees")
async def get_employees_for_manager(
    current_user: dict = Depends(require_manager_or_owner)
):
    """Получение списка сотрудников для управляющего"""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            object_ids = [obj.id for obj in accessible_objects]
            
            if not object_ids:
                return []
            
            # Получаем сотрудников, работающих на доступных объектах
            from sqlalchemy import select, distinct, text
            from domain.entities.contract import Contract
            from domain.entities.user import User
            
            employees_query = select(User).join(
                Contract, User.id == Contract.employee_id
            ).where(
                Contract.is_active == True,
                text("EXISTS (SELECT 1 FROM json_array_elements(contracts.allowed_objects) AS elem WHERE elem::text::int = ANY(ARRAY[{}]))".format(','.join(map(str, object_ids))))
            ).distinct()
            
            result = await db.execute(employees_query)
            employees = result.scalars().all()
            
            employees_data = []
            for emp in employees:
                employees_data.append({
                    "id": emp.id,
                    "telegram_id": emp.telegram_id,
                    "first_name": emp.first_name,
                    "last_name": emp.last_name,
                    "username": emp.username,
                    "phone": emp.phone,
                    "is_active": emp.is_active,
                    "name": f"{emp.first_name} {emp.last_name or ''}".strip() or emp.username or f"ID {emp.id}"
                })
            
            return employees_data
            
    except Exception as e:
        logger.error(f"Error getting employees for manager: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников")


@router.get("/")
async def manager_root_redirect():
    """Редирект с /manager на календарь управляющего."""
    return RedirectResponse(url="/manager/calendar")


@router.get("/calendar/api/objects")
async def get_objects_for_manager_calendar(
    current_user: dict = Depends(require_manager_or_owner)
):
    """Получение списка объектов для календаря управляющего"""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            objects_data = []
            for obj in accessible_objects:
                # Формируем время работы
                working_hours = "Не указано"
                if obj.opening_time and obj.closing_time:
                    working_hours = f"{obj.opening_time.strftime('%H:%M')} - {obj.closing_time.strftime('%H:%M')}"
                elif obj.opening_time:
                    working_hours = f"с {obj.opening_time.strftime('%H:%M')}"
                elif obj.closing_time:
                    working_hours = f"до {obj.closing_time.strftime('%H:%M')}"
                
                objects_data.append({
                    "id": obj.id,
                    "name": obj.name,
                    "address": obj.address,
                    "hourly_rate": float(obj.hourly_rate) if obj.hourly_rate else 0,
                    "is_active": obj.is_active,
                    "opening_time": obj.opening_time.strftime('%H:%M') if obj.opening_time else None,
                    "closing_time": obj.closing_time.strftime('%H:%M') if obj.closing_time else None,
                    "working_hours": working_hours
                })
            
            return objects_data
            
    except Exception as e:
        logger.error(f"Error getting objects for manager calendar: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки объектов")


@router.get("/api/employees/for-object/{object_id}")
async def get_employees_for_object_manager(
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Получение сотрудников для конкретного объекта управляющим"""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Проверяем доступ к объекту
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объекту")
            
            # Получаем сотрудников для объекта (копируем логику из календаря владельца)
            from sqlalchemy import select
            from domain.entities.contract import Contract
            from domain.entities.user import User
            import json
            
            # Получаем всех сотрудников с активными договорами
            employees_query = select(User).join(Contract, User.id == Contract.employee_id).where(
                Contract.is_active == True
            )
            employees_result = await db.execute(employees_query)
            employees = employees_result.scalars().all()
            
            employees_with_access = []
            added_employee_ids = set()  # Для отслеживания уже добавленных сотрудников
            
            for emp in employees:
                # Пропускаем, если сотрудник уже добавлен
                if emp.id in added_employee_ids:
                    continue
                
                # Проверяем, что пользователь имеет роль employee
                if "employee" not in (emp.roles if isinstance(emp.roles, list) else [emp.role]):
                    continue
                    
                # Получаем договоры сотрудника
                contract_query = select(Contract).where(
                    Contract.employee_id == emp.id,
                    Contract.is_active == True
                )
                contract_result = await db.execute(contract_query)
                contracts = contract_result.scalars().all()
                
                # Проверяем все договоры сотрудника
                for contract in contracts:
                    if contract and contract.allowed_objects:
                        allowed_objects = contract.allowed_objects if isinstance(contract.allowed_objects, list) else json.loads(contract.allowed_objects)
                        if object_id in allowed_objects:
                            employee_data = {
                                "id": int(emp.id),
                                "name": str(f"{emp.first_name or ''} {emp.last_name or ''}".strip() or emp.username or f"ID {emp.id}"),
                                "username": str(emp.username or ""),
                                "role": str(emp.role),
                                "is_active": bool(emp.is_active),
                                "telegram_id": int(emp.telegram_id) if emp.telegram_id else None
                            }
                            employees_with_access.append(employee_data)
                            added_employee_ids.add(emp.id)  # Помечаем сотрудника как добавленного
                            break  # Если нашли доступ, выходим из цикла по договорам
            
            employees_data = employees_with_access
            
            return employees_data
            
    except Exception as e:
        logger.error(f"Error getting employees for object {object_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников для объекта")


@router.post("/api/calendar/plan-shift")
async def plan_shift_manager(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Планирование смены управляющим"""
    logger.info("=== STARTING plan_shift_manager ===")
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        data = await request.json()
        logger.info(f"Planning shift with data: {data}")
        
        timeslot_id = data.get('timeslot_id')
        employee_id = data.get('employee_id')
        
        if not timeslot_id or not employee_id:
            raise HTTPException(status_code=400, detail="Не указан тайм-слот или сотрудник")
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем тайм-слот и проверяем доступ к объекту
            from sqlalchemy import select
            from domain.entities.time_slot import TimeSlot
            
            timeslot_query = select(TimeSlot).where(TimeSlot.id == timeslot_id)
            timeslot = (await db.execute(timeslot_query)).scalar_one_or_none()
            if not timeslot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден")
            
            object_id = timeslot.object_id
            
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объекту")
            
            # Создаем запланированную смену
            from domain.entities.shift_schedule import ShiftSchedule
            from datetime import datetime, time, date
            
            # Создаем datetime объекты для planned_start и planned_end из тайм-слота
            slot_datetime = datetime.combine(timeslot.slot_date, timeslot.start_time)
            end_datetime = datetime.combine(timeslot.slot_date, timeslot.end_time)
            
            shift_schedule = ShiftSchedule(
                user_id=int(employee_id),
                object_id=int(object_id),
                time_slot_id=int(timeslot_id),
                planned_start=slot_datetime,
                planned_end=end_datetime,
                status='planned',
                hourly_rate=float(data.get('hourly_rate', 500)),
                notes=data.get('notes', '')
            )
            
            db.add(shift_schedule)
            await db.commit()
            await db.refresh(shift_schedule)
            
            logger.info(f"Successfully planned shift {shift_schedule.id}")
            return {
                "success": True,
                "message": "Смена успешно запланирована",
                "shift_id": shift_schedule.id
            }
            
    except Exception as e:
        logger.error(f"Error planning shift: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка планирования смены: {str(e)}")


@router.get("/shifts", response_class=HTMLResponse, name="manager_shifts")
async def manager_shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр по статусу: active, planned, completed"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    object_id: Optional[str] = Query(None, description="ID объекта"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    current_user: dict = Depends(require_manager_or_owner),
):
    """Список смен управляющего."""
    try:
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            # Получаем внутренний ID пользователя
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                return templates.TemplateResponse("manager/shifts/list.html", {
                    "request": request,
                    "current_user": current_user,
                    "available_interfaces": [],
                    "shifts": [],
                    "objects": [],
                    "stats": {"total": 0, "active": 0, "planned": 0, "completed": 0},
                    "filters": {"status": status, "date_from": date_from, "date_to": date_to, "object_id": object_id},
                    "pagination": {"page": 1, "per_page": 20, "total": 0, "pages": 0}
                })
            
            # Базовый запрос для смен
            from sqlalchemy import select, desc
            shifts_query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(Shift.object_id.in_(accessible_object_ids))
            
            # Базовый запрос для запланированных смен
            schedules_query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user)
            ).where(ShiftSchedule.object_id.in_(accessible_object_ids))
            
            # Применение фильтров
            if object_id:
                if int(object_id) in accessible_object_ids:
                    shifts_query = shifts_query.where(Shift.object_id == int(object_id))
                    schedules_query = schedules_query.where(ShiftSchedule.object_id == int(object_id))
                else:
                    # Нет доступа к объекту
                    return templates.TemplateResponse("manager/shifts/list.html", {
                        "request": request,
                        "current_user": current_user,
                        "available_interfaces": [],
                        "shifts": [],
                        "objects": accessible_objects,
                        "stats": {"total": 0, "active": 0, "planned": 0, "completed": 0},
                        "filters": {"status": status, "date_from": date_from, "date_to": date_to, "object_id": object_id},
                        "pagination": {"page": 1, "per_page": 20, "total": 0, "pages": 0}
                    })
            
            # Получение данных
            shifts_result = await db.execute(shifts_query.order_by(desc(Shift.created_at)))
            shifts = shifts_result.scalars().all()
            
            schedules_result = await db.execute(schedules_query.order_by(desc(ShiftSchedule.created_at)))
            schedules = schedules_result.scalars().all()
            
            # Объединение и форматирование данных
            all_shifts = []
            
            # Добавляем обычные смены
            for shift in shifts:
                all_shifts.append({
                    'id': shift.id,
                    'type': 'shift',
                    'object_name': shift.object.name if shift.object else 'Неизвестный объект',
                    'user_name': f"{shift.user.first_name} {shift.user.last_name or ''}".strip() if shift.user else 'Неизвестный пользователь',
                    'start_time': web_timezone_helper.format_datetime_with_timezone(shift.start_time, shift.object.timezone if shift.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if shift.start_time else '-',
                    'end_time': web_timezone_helper.format_datetime_with_timezone(shift.end_time, shift.object.timezone if shift.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if shift.end_time else '-',
                    'status': shift.status,
                    'created_at': shift.created_at
                })
            
            # Добавляем запланированные смены
            for schedule in schedules:
                all_shifts.append({
                    'id': schedule.id,
                    'type': 'schedule',
                    'object_name': schedule.object.name if schedule.object else 'Неизвестный объект',
                    'user_name': f"{schedule.user.first_name} {schedule.user.last_name or ''}".strip() if schedule.user else 'Неизвестный пользователь',
                    'start_time': web_timezone_helper.format_datetime_with_timezone(schedule.planned_start, schedule.object.timezone if schedule.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if schedule.planned_start else '-',
                    'end_time': web_timezone_helper.format_datetime_with_timezone(schedule.planned_end, schedule.object.timezone if schedule.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if schedule.planned_end else '-',
                    'status': schedule.status,
                    'created_at': schedule.created_at
                })
            
            # Сортировка по дате создания
            all_shifts.sort(key=lambda x: x['created_at'], reverse=True)
            
            # Пагинация
            total_shifts = len(all_shifts)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_shifts = all_shifts[start_idx:end_idx]
            
            # Статистика
            stats = {
                'total': total_shifts,
                'active': len([s for s in all_shifts if s['status'] == 'active']),
                'planned': len([s for s in all_shifts if s['type'] == 'schedule']),
                'completed': len([s for s in all_shifts if s['status'] == 'completed'])
            }
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/shifts/list.html", {
                "request": request,
                "current_user": current_user,
                "available_interfaces": available_interfaces,
                "shifts": paginated_shifts,
                "objects": accessible_objects,
                "stats": stats,
                "filters": {
                    "status": status,
                    "date_from": date_from,
                    "date_to": date_to,
                    "object_id": object_id
                },
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total_shifts,
                    "pages": (total_shifts + per_page - 1) // per_page
                }
            })
            
    except Exception as e:
        logger.error(f"Error loading manager shifts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки смен")


@router.get("/shifts/{shift_id}", response_class=HTMLResponse)
async def manager_shift_detail(
    request: Request, 
    shift_id: int, 
    shift_type: Optional[str] = Query("shift"),
    current_user: dict = Depends(require_manager_or_owner),
):
    """Детали смены управляющего"""
    try:
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        async with get_async_session() as db:
            # Получаем внутренний ID пользователя
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            # Получаем доступные объекты управляющего
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if not accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объектам")
            
            shift_data = None
            
            # Импортируем select для запросов
            from sqlalchemy import select
            
            if shift_type == "schedule":
                # Запланированная смена
                query = select(ShiftSchedule).options(
                    selectinload(ShiftSchedule.object),
                    selectinload(ShiftSchedule.user)
                ).where(ShiftSchedule.id == shift_id)
                
                result = await db.execute(query)
                schedule = result.scalar_one_or_none()
                
                if not schedule:
                    raise HTTPException(status_code=404, detail="Запланированная смена не найдена")
                
                # Проверяем доступ к объекту
                if schedule.object_id not in accessible_object_ids:
                    raise HTTPException(status_code=403, detail="Нет доступа к объекту")
                
                shift_data = {
                    'id': schedule.id,
                    'type': 'schedule',
                    'object_name': schedule.object.name if schedule.object else 'Неизвестный объект',
                    'user_name': f"{schedule.user.first_name} {schedule.user.last_name or ''}".strip() if schedule.user else 'Неизвестный пользователь',
                    'start_time': web_timezone_helper.format_datetime_with_timezone(schedule.planned_start, schedule.object.timezone if schedule.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if schedule.planned_start else '-',
                    'end_time': web_timezone_helper.format_datetime_with_timezone(schedule.planned_end, schedule.object.timezone if schedule.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if schedule.planned_end else '-',
                    'status': schedule.status,
                    'hourly_rate': schedule.hourly_rate,
                    'notes': schedule.notes,
                    'created_at': schedule.created_at
                }
            else:
                # Обычная смена
                query = select(Shift).options(
                    selectinload(Shift.object),
                    selectinload(Shift.user)
                ).where(Shift.id == shift_id)
                
                result = await db.execute(query)
                shift = result.scalar_one_or_none()
                
                if not shift:
                    raise HTTPException(status_code=404, detail="Смена не найдена")
                
                # Проверяем доступ к объекту
                if shift.object_id not in accessible_object_ids:
                    raise HTTPException(status_code=403, detail="Нет доступа к объекту")
                
                shift_data = {
                    'id': shift.id,
                    'type': 'shift',
                    'object_name': shift.object.name if shift.object else 'Неизвестный объект',
                    'user_name': f"{shift.user.first_name} {shift.user.last_name or ''}".strip() if shift.user else 'Неизвестный пользователь',
                    'start_time': web_timezone_helper.format_datetime_with_timezone(shift.start_time, shift.object.timezone if shift.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if shift.start_time else '-',
                    'end_time': web_timezone_helper.format_datetime_with_timezone(shift.end_time, shift.object.timezone if shift.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if shift.end_time else '-',
                    'status': shift.status,
                    'total_hours': shift.total_hours,
                    'total_payment': shift.total_payment,
                    'notes': shift.notes,
                    'created_at': shift.created_at
                }
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/shifts/detail.html", {
                "request": request,
                "current_user": current_user,
                "available_interfaces": available_interfaces,
                "shift": shift_data
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading manager shift detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей смены")


@router.post("/calendar/api/quick-create-timeslot")
async def quick_create_timeslot_manager(
    request: Request,
    object_id: int = Form(...),
    slot_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    hourly_rate: int = Form(...),
    current_user: dict = Depends(require_manager_or_owner)
):
    """Быстрое создание тайм-слота управляющим"""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        logger.info(f"Quick create timeslot: object_id={object_id}, date={slot_date}, start={start_time}, end={end_time}, rate={hourly_rate}")
        
        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            logger.info(f"User ID: {user_id}")
            
            # Проверяем доступ к объекту
            logger.info(f"Object ID: {object_id}")
            
            permission_service = ManagerPermissionService(db)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            logger.info(f"Accessible object IDs: {accessible_object_ids}")
            
            if object_id not in accessible_object_ids:
                raise HTTPException(status_code=403, detail="Нет доступа к объекту")
            
            # Валидация данных
            try:
                slot_date_obj = datetime.strptime(slot_date, "%Y-%m-%d").date()
                start_time_obj = time.fromisoformat(start_time)
                end_time_obj = time.fromisoformat(end_time)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Неверный формат данных: {str(e)}")
            
            if start_time_obj >= end_time_obj:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
            if hourly_rate <= 0:
                raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
            
            # Создаем тайм-слот
            from domain.entities.time_slot import TimeSlot
            
            logger.info(f"Creating timeslot: object_id={object_id}, date={slot_date_obj}, start={start_time_obj}, end={end_time_obj}, rate={hourly_rate}")
            
            timeslot = TimeSlot(
                object_id=object_id,
                slot_date=slot_date_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
                hourly_rate=float(hourly_rate),
                max_employees=1,
                is_additional=False,
                is_active=True,
                notes=""
            )
            
            db.add(timeslot)
            await db.commit()
            await db.refresh(timeslot)
            
            logger.info(f"Timeslot created successfully with ID: {timeslot.id}")
            
            # Возвращаем результат до закрытия сессии
            result = {
                "success": True,
                "message": "Тайм-слот успешно создан",
                "timeslot_id": timeslot.id
            }
            
            logger.info(f"Returning success result: {result}")
            return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeslot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слота: {str(e)}")


@router.get("/profile", response_class=HTMLResponse)
async def manager_profile(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница профиля управляющего"""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Получаем доступные объекты для статистики
        permission_service = ManagerPermissionService(db)
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        
        # Получаем данные для переключения интерфейсов
        login_service = RoleBasedLoginService(db)
        available_interfaces = await login_service.get_available_interfaces(user_id)
        
        # Статистика профиля
        profile_stats = {
            'accessible_objects_count': len(accessible_objects),
            'total_contracts': 0,  # TODO: Добавить подсчет договоров
            'active_shifts_count': 0,  # TODO: Добавить подсчет активных смен
            'total_employees_count': 0  # TODO: Добавить подсчет сотрудников
        }
        
        return templates.TemplateResponse("manager/profile.html", {
            "request": request,
            "current_user": current_user,
            "user": user,
            "profile_stats": profile_stats,
            "accessible_objects": accessible_objects,
            "available_interfaces": available_interfaces
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager profile: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки профиля")


@router.get("/settings", response_class=HTMLResponse)
async def manager_settings(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница настроек управляющего"""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Получаем данные для переключения интерфейсов
        login_service = RoleBasedLoginService(db)
        available_interfaces = await login_service.get_available_interfaces(user_id)
        
        # Настройки по умолчанию
        settings = {
            'notifications': {
                'email_notifications': True,
                'shift_reminders': True,
                'object_updates': True,
                'employee_changes': False
            },
            'display': {
                'theme': 'light',
                'language': 'ru',
                'timezone': 'Europe/Moscow'
            },
            'calendar': {
                'default_view': 'month',
                'show_weekends': True,
                'working_hours_start': '09:00',
                'working_hours_end': '21:00'
            }
        }
        
        return templates.TemplateResponse("manager/settings.html", {
            "request": request,
            "current_user": current_user,
            "user": user,
            "settings": settings,
            "available_interfaces": available_interfaces
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager settings: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки настроек")
