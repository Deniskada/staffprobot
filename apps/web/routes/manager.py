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
                from sqlalchemy import func, or_, text, cast, String, JSON, any_
                
                # Максимально простой подход - используем EXISTS с подзапросом
                employees_query = select(User).join(
                    Contract, User.id == Contract.employee_id
                ).where(
                    Contract.allowed_objects.op('?|')(object_ids),  # Проверяем пересечение массивов
                    Contract.is_active == True
                ).distinct()
                
                logger.info(f"Executing query: {employees_query}")
                result = await db.execute(employees_query)
                employees = result.scalars().all()
                logger.info(f"Found {len(employees)} employees")
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
            role = form_data.get("role", "employee")
            is_active = form_data.get("is_active") == "true"
            
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
            
            user = User(
                telegram_id=telegram_id,
                first_name=first_name,
                last_name=last_name,
                username=username,
                phone=phone,
                role=role,
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
            employee.is_active = form_data.get("is_active") == "true"
            
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
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/calendar.html", {
                "request": request,
                "current_user": current_user,
                "available_interfaces": available_interfaces
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
            
            # Получаем данные для переключения интерфейсов
            login_service = RoleBasedLoginService(db)
            available_interfaces = await login_service.get_available_interfaces(user_id)
            
            return templates.TemplateResponse("manager/reports.html", {
                "request": request,
                "current_user": current_user,
                "available_interfaces": available_interfaces
            })
        
    except Exception as e:
        logger.error(f"Error in manager reports: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки отчетов")
