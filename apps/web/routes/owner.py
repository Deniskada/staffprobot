"""
Роуты для владельцев объектов
URL-префикс: /owner/*
"""

from fastapi import APIRouter, Request, HTTPException, status, Form, Query
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


@router.get("/", response_class=HTMLResponse, name="owner_dashboard")
async def owner_dashboard(request: Request):
    """Дашборд владельца"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            user_id = await get_user_id_from_current_user(current_user, session)
            
            # Получаем статистику владельца
            objects_count = await session.execute(
                select(func.count(Object.id)).where(Object.owner_id == user_id)
            )
            total_objects = objects_count.scalar()
            
            shifts_count = await session.execute(
                select(func.count(Shift.id)).where(
                    Shift.object_id.in_(
                        select(Object.id).where(Object.owner_id == user_id)
                    )
                )
            )
            total_shifts = shifts_count.scalar()
            
            # Активные смены
            active_shifts_count = await session.execute(
                select(func.count(Shift.id)).where(
                    and_(
                        Shift.status == 'active',
                        Shift.object_id.in_(
                            select(Object.id).where(Object.owner_id == user_id)
                        )
                    )
                )
            )
            active_shifts = active_shifts_count.scalar()
            
            # Последние объекты
            recent_objects_result = await session.execute(
                select(Object).where(Object.owner_id == user_id)
                .order_by(desc(Object.created_at)).limit(5)
            )
            recent_objects = recent_objects_result.scalars().all()
        
        stats = {
            'total_objects': total_objects,
            'total_shifts': total_shifts,
            'active_shifts': active_shifts,
        }

        return templates.TemplateResponse("owner/dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Дашборд владельца",
            "stats": stats,
            "recent_objects": recent_objects,
        })
    except Exception as e:
        logger.error(f"Error loading owner dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/dashboard", response_class=HTMLResponse)
async def owner_dashboard_redirect(request: Request):
    """Редирект с /owner/dashboard на /owner/"""
    return RedirectResponse(url="/owner/", status_code=status.HTTP_302_FOUND)


@router.get("/objects", response_class=HTMLResponse, name="owner_objects")
async def owner_objects(
    request: Request,
    show_inactive: bool = Query(False),
    view_mode: str = Query("cards")
):
    """Список объектов владельца"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService
        
        async with get_async_session() as session:
            # Получение объектов владельца из базы данных
            object_service = ObjectService(session)
            objects = await object_service.get_objects_by_owner(current_user["id"], include_inactive=show_inactive)
            
            # Преобразуем в формат для шаблона
            objects_data = []
            for obj in objects:
                objects_data.append({
                    "id": obj.id,
                    "name": obj.name,
                    "address": obj.address or "",
                    "hourly_rate": float(obj.hourly_rate),
                    "opening_time": obj.opening_time.strftime("%H:%M"),
                    "closing_time": obj.closing_time.strftime("%H:%M"),
                    "max_distance": obj.max_distance_meters,
                    "is_active": obj.is_active,
                    "available_for_applicants": obj.available_for_applicants,
                    "created_at": obj.created_at.strftime("%Y-%m-%d"),
                    "owner_id": obj.owner_id
                })
            
            return templates.TemplateResponse("owner/objects/list.html", {
                "request": request,
                "title": "Управление объектами",
                "objects": objects_data,
                "current_user": current_user,
                "show_inactive": show_inactive,
                "view_mode": view_mode
            })
            
    except Exception as e:
        logger.error(f"Error loading objects list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки списка объектов")


@router.get("/objects/create", response_class=HTMLResponse, name="owner_objects_create")
async def owner_objects_create(request: Request):
    """Форма создания объекта"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("owner/objects/create.html", {
        "request": request,
        "title": "Создание объекта",
        "current_user": current_user
    })


@router.post("/objects/create")
async def owner_objects_create_post(request: Request):
    """Создание нового объекта"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService
        
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
        
        logger.info(f"Creating object '{name}' for user {current_user['id']}")
        
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
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        if max_distance <= 0:
            raise HTTPException(status_code=400, detail="Максимальное расстояние должно быть больше 0")
        
        # Обработка координат
        coordinates = None
        if latitude_str and longitude_str:
            try:
                lat = float(latitude_str)
                lon = float(longitude_str)
                # Проверяем диапазон координат
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coordinates = f"{lat},{lon}"
                else:
                    raise HTTPException(status_code=400, detail="Координаты вне допустимого диапазона")
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат координат")
        
        # Обработка чекбокса (он не отправляется, если не отмечен)
        available_for_applicants = "available_for_applicants" in form_data
        
        # Создание объекта в базе данных
        async with get_async_session() as session:
            object_service = ObjectService(session)
            object_data = {
                "name": name,
                "address": address,
                "hourly_rate": hourly_rate,
                "opening_time": opening_time,
                "closing_time": closing_time,
                "max_distance": max_distance,
                "available_for_applicants": available_for_applicants,
                "is_active": True,
                "coordinates": coordinates
            }
            
            new_object = await object_service.create_object(object_data, current_user["id"])
            logger.info(f"Object {new_object.id} created successfully")
            
        return RedirectResponse(url="/owner/objects", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания объекта: {str(e)}")


@router.get("/objects/{object_id}", response_class=HTMLResponse, name="owner_objects_detail")
async def owner_objects_detail(request: Request, object_id: int):
    """Детальная информация об объекте"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService, TimeSlotService
        
        async with get_async_session() as session:
            # Получение данных объекта из базы данных с проверкой владельца
            object_service = ObjectService(session)
            timeslot_service = TimeSlotService(session)
            
            obj = await object_service.get_object_by_id(object_id, current_user["id"])
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден")
            
            # Получаем тайм-слоты
            timeslots = await timeslot_service.get_timeslots_by_object(object_id, current_user["id"])
            
            # Преобразуем в формат для шаблона
            object_data = {
                "id": obj.id,
                "name": obj.name,
                "address": obj.address or "",
                "hourly_rate": float(obj.hourly_rate),
                "opening_time": obj.opening_time.strftime("%H:%M"),
                "closing_time": obj.closing_time.strftime("%H:%M"),
                "max_distance": obj.max_distance_meters,
                "is_active": obj.is_active,
                "available_for_applicants": obj.available_for_applicants,
                "created_at": obj.created_at.strftime("%Y-%m-%d"),
                "owner_id": obj.owner_id,
                "timeslots": [
                    {
                        "id": slot.id,
                        "start_time": slot.start_time.strftime("%H:%M"),
                        "end_time": slot.end_time.strftime("%H:%M"),
                        "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate),
                        "is_active": slot.is_active
                    }
                    for slot in timeslots
                ]
            }
            
            return templates.TemplateResponse("owner/objects/detail.html", {
                "request": request,
                "title": f"Объект: {object_data['name']}",
                "object": object_data,
                "current_user": current_user
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading object detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки информации об объекте")


@router.get("/objects/{object_id}/edit", response_class=HTMLResponse, name="owner_objects_edit")
async def owner_objects_edit(request: Request, object_id: int):
    """Форма редактирования объекта"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService
        
        async with get_async_session() as session:
            # Получение данных объекта из базы данных с проверкой владельца
            object_service = ObjectService(session)
            obj = await object_service.get_object_by_id(object_id, current_user["id"])
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден")
            
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
                "is_active": obj.is_active
            }
            
            return templates.TemplateResponse("owner/objects/edit.html", {
                "request": request,
                "title": f"Редактирование: {object_data['name']}",
                "object": object_data,
                "current_user": current_user
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading edit form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/objects/{object_id}/edit")
async def owner_objects_edit_post(request: Request, object_id: int):
    """Обновление объекта"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService
        
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
        
        logger.info(f"Updating object {object_id} for user {current_user['id']}")
        
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
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        if max_distance <= 0:
            raise HTTPException(status_code=400, detail="Максимальное расстояние должно быть больше 0")
        
        # Обработка координат
        coordinates = None
        if latitude_str and longitude_str:
            try:
                lat = float(latitude_str)
                lon = float(longitude_str)
                # Проверяем диапазон координат
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    coordinates = f"{lat},{lon}"
                else:
                    raise HTTPException(status_code=400, detail="Координаты вне допустимого диапазона")
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат координат")
        
        # Обработка чекбоксов/скрытых значений
        def to_bool(value: Optional[str]) -> bool:
            if value is None:
                return False
            return value.lower() in ("true", "on", "1", "yes")

        available_for_applicants = to_bool(form_data.get("available_for_applicants"))
        is_active = to_bool(form_data.get("is_active"))
        
        # Обновление объекта в базе данных
        async with get_async_session() as session:
            object_service = ObjectService(session)
            object_data = {
                "name": name,
                "address": address,
                "hourly_rate": hourly_rate,
                "opening_time": opening_time,
                "closing_time": closing_time,
                "max_distance": max_distance,
                "available_for_applicants": available_for_applicants,
                "is_active": is_active,
                "coordinates": coordinates
            }
            
            updated_object = await object_service.update_object(object_id, object_data, current_user["id"])
            if not updated_object:
                raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")
            
            logger.info(f"Object {object_id} updated successfully")
            
        return RedirectResponse(url=f"/owner/objects/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления объекта: {str(e)}")


@router.post("/objects/{object_id}/delete")
async def owner_objects_delete(object_id: int, request: Request):
    """Удаление объекта"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.object_service import ObjectService
        
        logger.info(f"Deleting object {object_id} for user {current_user['id']}")

        async with get_async_session() as session:
            object_service = ObjectService(session)
            success = await object_service.delete_object(object_id, current_user["id"])
            if not success:
                raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")

        return RedirectResponse(url="/owner/objects", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Error deleting object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления объекта: {str(e)}")


@router.get("/calendar", response_class=HTMLResponse, name="owner_calendar")
async def owner_calendar(request: Request):
    """Календарь смен владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на существующую страницу календаря
    return RedirectResponse(url="/calendar", status_code=status.HTTP_302_FOUND)


@router.get("/employees", response_class=HTMLResponse, name="owner_employees")
async def owner_employees(
    request: Request,
    view_mode: str = Query("cards"),
    show_former: bool = Query(False)
):
    """Список сотрудников владельца"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.contract_service import ContractService
        
        # Получаем реальных сотрудников из базы данных
        contract_service = ContractService()
        # Используем telegram_id для поиска пользователя в БД
        user_id = current_user["id"]  # Это telegram_id из токена
        
        if show_former:
            employees = await contract_service.get_all_contract_employees_by_telegram_id(user_id)
        else:
            employees = await contract_service.get_contract_employees_by_telegram_id(user_id)
        
        return templates.TemplateResponse(
            "owner/employees/list.html",
            {
                "request": request,
                "employees": employees,
                "title": "Управление сотрудниками",
                "current_user": current_user,
                "view_mode": view_mode,
                "show_former": show_former
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading employees list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки списка сотрудников")


@router.get("/employees/create", response_class=HTMLResponse, name="owner_employees_create")
async def owner_employees_create(
    request: Request,
    employee_telegram_id: Optional[int] = Query(None)
):
    """Создание договора с сотрудником"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.contract_service import ContractService
        from domain.entities.contract_template import ContractTemplate
        from domain.entities.owner_profile import OwnerProfile
        
        async with get_async_session() as session:
            # Получаем внутренний ID пользователя
            user_id = await get_user_id_from_current_user(current_user, session)
            
            # Получаем объекты владельца
            objects_query = select(Object).where(Object.owner_id == user_id)
            objects_result = await session.execute(objects_query)
            objects = objects_result.scalars().all()
            
            # Получаем шаблоны договоров владельца
            templates_query = select(ContractTemplate).where(ContractTemplate.owner_id == user_id)
            templates_result = await session.execute(templates_query)
            templates = templates_result.scalars().all()
            
            # Получаем данные сотрудника, если указан telegram_id
            employee_data = None
            if employee_telegram_id:
                employee_query = select(User).where(User.telegram_id == employee_telegram_id)
                employee_result = await session.execute(employee_query)
                employee = employee_result.scalar_one_or_none()
                if employee:
                    employee_data = {
                        "id": employee.id,
                        "telegram_id": employee.telegram_id,
                        "username": employee.username,
                        "first_name": employee.first_name,
                        "last_name": employee.last_name,
                        "phone": employee.phone
                    }
            
            # Получаем профиль владельца
            owner_profile_query = select(OwnerProfile).where(OwnerProfile.owner_id == user_id)
            owner_profile_result = await session.execute(owner_profile_query)
            owner_profile = owner_profile_result.scalar_one_or_none()
            
            # Подготавливаем данные профиля владельца для шаблона
            owner_profile_data = {}
            if owner_profile and owner_profile.profile_data:
                for tag_ref in owner_profile.profile_data:
                    if hasattr(tag_ref, 'to_dict'):
                        tag_dict = tag_ref.to_dict()
                        owner_profile_data[tag_dict['tag']] = tag_dict['value']
                    else:
                        # Если это уже словарь
                        owner_profile_data[tag_ref['tag']] = tag_ref['value']
            
            return templates.TemplateResponse(
                "owner/employees/create.html",
                {
                    "request": request,
                    "title": "Создание договора с сотрудником",
                    "current_user": current_user,
                    "objects": objects,
                    "templates": templates,
                    "employee": employee_data,
                    "owner_profile": owner_profile_data
                }
            )
            
    except Exception as e:
        logger.error(f"Error loading employee creation form: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы: {str(e)}")


@router.post("/employees/create")
async def owner_employees_create_post(request: Request):
    """Создание договора с сотрудником"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.contract_service import ContractService
        from apps.web.services.pdf_service import PDFService
        
        # Получаем данные формы
        form_data = await request.form()
        
        # Создаем договор
        contract_service = ContractService()
        pdf_service = PDFService()
        
        # Получаем данные из формы
        employee_name = form_data.get("employee_name", "").strip()
        employee_telegram_id = form_data.get("employee_telegram_id", "").strip()
        object_id = form_data.get("object_id", "").strip()
        template_id = form_data.get("template_id", "").strip()
        hourly_rate = form_data.get("hourly_rate", "").strip()
        
        # Валидация
        if not employee_name:
            raise HTTPException(status_code=400, detail="Имя сотрудника обязательно")
        if not employee_telegram_id:
            raise HTTPException(status_code=400, detail="Telegram ID сотрудника обязателен")
        if not object_id:
            raise HTTPException(status_code=400, detail="Объект обязателен")
        if not template_id:
            raise HTTPException(status_code=400, detail="Шаблон договора обязателен")
        
        try:
            employee_telegram_id = int(employee_telegram_id)
            object_id = int(object_id)
            template_id = int(template_id)
            if hourly_rate:
                hourly_rate = float(hourly_rate.replace(",", "."))
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат числовых полей")
        
        # Создаем договор
        contract_data = {
            "employee_name": employee_name,
            "employee_telegram_id": employee_telegram_id,
            "object_id": object_id,
            "template_id": template_id,
            "hourly_rate": hourly_rate,
            "owner_telegram_id": current_user["id"]
        }
        
        # Добавляем дополнительные поля из формы
        for key, value in form_data.items():
            if key.startswith("field_"):
                contract_data[key] = value
        
        contract = await contract_service.create_contract(contract_data)
        
        return RedirectResponse(url="/owner/employees", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating employee contract: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания договора: {str(e)}")


@router.get("/employees/{employee_id}", response_class=HTMLResponse, name="owner_employees_detail")
async def owner_employees_detail(request: Request, employee_id: int):
    """Детальная информация о сотруднике"""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        employee = await contract_service.get_employee_by_id(employee_id, current_user["id"])
        
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")
        
        return templates.TemplateResponse(
            "owner/employees/detail.html",
            {
                "request": request,
                "title": f"Сотрудник: {employee.get('name', 'Неизвестно')}",
                "current_user": current_user,
                "employee": employee
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading employee detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки информации о сотруднике")


@router.get("/shifts", response_class=HTMLResponse, name="owner_shifts")
async def owner_shifts(request: Request):
    """Управление сменами владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на существующую страницу смен
    return RedirectResponse(url="/shifts", status_code=status.HTTP_302_FOUND)


@router.get("/templates", response_class=HTMLResponse, name="owner_templates")
async def owner_templates(request: Request):
    """Шаблоны договоров владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на существующую страницу шаблонов
    return RedirectResponse(url="/templates", status_code=status.HTTP_302_FOUND)


@router.get("/reports", response_class=HTMLResponse, name="owner_reports")
async def owner_reports(request: Request):
    """Отчеты владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на существующую страницу отчетов
    return RedirectResponse(url="/reports", status_code=status.HTTP_302_FOUND)


@router.get("/profile", response_class=HTMLResponse, name="owner_profile")
async def owner_profile(request: Request):
    """Профиль владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    # Перенаправляем на существующую страницу профиля
    return RedirectResponse(url="/profile", status_code=status.HTTP_302_FOUND)


@router.get("/settings", response_class=HTMLResponse, name="owner_settings")
async def owner_settings(request: Request):
    """Настройки владельца"""
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("owner/settings.html", {
        "request": request,
        "current_user": current_user,
        "title": "Настройки владельца",
        "message": "Настройки в разработке"
    })
