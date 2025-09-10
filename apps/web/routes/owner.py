"""
Роуты для владельцев объектов
URL-префикс: /owner/*
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from typing import List, Optional
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta, date, time
from typing import Optional, List, Dict, Any
import calendar

from core.database.session import get_async_session, get_db_session
from apps.web.middleware.auth_middleware import get_current_user
from apps.web.dependencies import get_current_user_dependency, require_role
from apps.web.services.object_service import ObjectService, TimeSlotService
from domain.entities.user import User, UserRole
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


def get_user_internal_id_from_current_user(current_user):
    """Получает внутренний ID пользователя из current_user (синхронно)"""
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        # Хардкод маппинг telegram_id -> internal_id из БД запроса
        telegram_to_internal = {
            1220971779: 1,  # owner
            1657453440: 2,  # owner  
            1170536174: 3,  # owner
            6562516971: 4,  # owner
            12345: 5,       # owner
            1821645654: 7,  # superadmin
        }
        internal_id = telegram_to_internal.get(telegram_id)
        if internal_id:
            logger.info(f"DEBUG: telegram_id {telegram_id} -> internal_id {internal_id}")
            return internal_id
        else:
            logger.error(f"Unknown telegram_id: {telegram_id}")
            return None
    else:
        return current_user.id


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
async def owner_objects_create_post(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового объекта"""
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
        
        logger.info(f"Creating object '{name}' for user {current_user['id']} (type: {type(current_user['id'])})")
        
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
        
        # Обработка графика работы
        work_days = form_data.getlist("work_days")
        work_days_mask = 0
        for day in work_days:
            work_days_mask += int(day)
        
        schedule_repeat_weeks_str = form_data.get("schedule_repeat_weeks", "1").strip()
        try:
            schedule_repeat_weeks = int(schedule_repeat_weeks_str) if schedule_repeat_weeks_str else 1
        except ValueError:
            schedule_repeat_weeks = 1
        
        # Создание объекта в базе данных
        object_service = ObjectService(db)
        object_data = {
            "name": name,
            "address": address,
            "hourly_rate": hourly_rate,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "max_distance": max_distance,
            "available_for_applicants": available_for_applicants,
            "is_active": True,
            "coordinates": coordinates,
            "work_days_mask": work_days_mask,
            "schedule_repeat_weeks": schedule_repeat_weeks
        }
        
        new_object = await object_service.create_object(object_data, int(current_user["id"]))
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
async def owner_objects_delete(
    object_id: int, 
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Полное удаление объекта из базы данных"""
    try:
        from apps.web.services.object_service import ObjectService
        
        logger.info(f"Hard deleting object {object_id} for user {current_user['id']}")

        object_service = ObjectService(db)
        success = await object_service.hard_delete_object(object_id, int(current_user["id"]))
        if not success:
            raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")

        return RedirectResponse(url="/owner/objects", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Error hard deleting object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления объекта: {str(e)}")


# ===============================
# КАЛЕНДАРЬ
# ===============================

@router.get("/calendar", response_class=HTMLResponse, name="owner_calendar")
async def owner_calendar(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None)
):
    """Календарный вид планирования"""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
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
        
        # Получаем объекты пользователя
        async with get_async_session() as session:
            object_service = ObjectService(session)
            timeslot_service = TimeSlotService(session)
            
            # ОРИГИНАЛ: используем telegram_id владельца (а не внутренний id)
            owner_telegram_id = current_user.get("telegram_id") or current_user.get("id")
            objects = await object_service.get_objects_by_owner(owner_telegram_id)
            
            # Если выбран конкретный объект, проверяем доступ
            selected_object = None
            if object_id:
                for obj in objects:
                    if obj.id == object_id:
                        selected_object = obj
                        break
                if not selected_object:
                    raise HTTPException(status_code=404, detail="Объект не найден")
            
            # Получаем тайм-слоты для выбранного объекта или всех объектов
            timeslots_data = []
            if selected_object:
                timeslots = await timeslot_service.get_timeslots_by_object(selected_object.id, owner_telegram_id)
                for slot in timeslots:
                    timeslots_data.append({
                        "id": slot.id,
                        "object_id": slot.object_id,
                        "object_name": selected_object.name,
                        "date": slot.slot_date,
                        "start_time": slot.start_time.strftime("%H:%M"),
                        "end_time": slot.end_time.strftime("%H:%M"),
                        "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(selected_object.hourly_rate),
                        "is_active": slot.is_active,
                        "notes": slot.notes or ""
                    })
            else:
                # Получаем тайм-слоты для всех объектов
                for obj in objects:
                    timeslots = await timeslot_service.get_timeslots_by_object(obj.id, owner_telegram_id)
                    for slot in timeslots:
                        timeslots_data.append({
                            "id": slot.id,
                            "object_id": slot.object_id,
                            "object_name": obj.name,
                            "date": slot.slot_date,
                            "start_time": slot.start_time.strftime("%H:%M"),
                            "end_time": slot.end_time.strftime("%H:%M"),
                            "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate),
                            "is_active": slot.is_active,
                            "notes": slot.notes or ""
                        })
            
            # Создаем календарную сетку
            logger.info(f"Creating calendar grid with {len(timeslots_data)} timeslots")
            calendar_data = _create_calendar_grid(year, month, timeslots_data)
            logger.info(f"Calendar grid created with {len(calendar_data)} weeks")
            
            # Подготавливаем данные для шаблона
            objects_list = [{"id": obj.id, "name": obj.name} for obj in objects]
            
            # Навигация по месяцам
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            
            return templates.TemplateResponse("owner/calendar/index.html", {
                "request": request,
                "title": "Календарное планирование",
                "current_user": current_user,
                "year": year,
                "month": month,
                "month_name": RU_MONTHS[month],
                "calendar_data": calendar_data,
                "objects": objects_list,
                "selected_object_id": object_id,
                "selected_object": selected_object,
                "timeslots": timeslots_data,
                "prev_month": prev_month,
                "prev_year": prev_year,
                "next_month": next_month,
                "next_year": next_year,
                "today": today
            })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading calendar: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки календаря")


@router.get("/calendar/api/timeslots-status")
async def owner_calendar_api_timeslots_status(
    year: int = Query(...),
    month: int = Query(...),
    object_id: Optional[int] = Query(None),
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение статуса тайм-слотов для календаря"""
    try:
        logger.info(f"Getting timeslots status for {year}-{month}, object_id: {object_id}")
        
        # Получаем реальные тайм-слоты из базы
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from domain.entities.time_slot import TimeSlot
        from domain.entities.object import Object
        from domain.entities.user import User
        
        # Получаем владельца из текущего пользователя (по telegram_id)
        if not current_user or not getattr(current_user, "telegram_id", None):
            return []
        owner_query = select(User).where(User.telegram_id == current_user.telegram_id)
        owner_result = await db.execute(owner_query)
        owner = owner_result.scalar_one_or_none()
        
        if not owner:
            return []
        
        # Получаем объекты владельца (используем ВНУТРЕННИЙ owner.id)
        objects_query = select(Object).where(Object.owner_id == owner.id)
        if object_id:
            objects_query = objects_query.where(Object.id == object_id)
        
        objects_result = await db.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        if not object_ids:
            return []
        
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
        
        logger.info(f"Found {len(timeslots)} real timeslots")
        
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
        
        logger.info(f"Found {len(scheduled_shifts)} scheduled shifts")
        
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
        
        logger.info(f"Found {len(actual_shifts)} actual shifts")
        
        # Создаем карту запланированных смен по time_slot_id
        scheduled_shifts_map = {}
        # Индекс для запланированных смен по объекту и дате (на случай отсутствия привязки к time_slot)
        scheduled_by_object_date = {}
        for shift in scheduled_shifts:
            if shift.time_slot_id:
                scheduled_shifts_map.setdefault(shift.time_slot_id, [])
                scheduled_shifts_map[shift.time_slot_id].append({
                    "id": shift.id,
                    "user_id": shift.user_id,
                    "status": shift.status,
                    "start_time": shift.planned_start.time().strftime("%H:%M"),
                    "end_time": shift.planned_end.time().strftime("%H:%M"),
                    "notes": shift.notes
                })
            # Индекс по объекту и дате
            key = (shift.object_id, shift.planned_start.date())
            scheduled_by_object_date.setdefault(key, []).append(shift)
        
        # Создаем карту отработанных смен по time_slot_id
        actual_shifts_map = {}
        # Дополнительно индексируем смены по объекту и дате для поиска пересечений со слотами без time_slot_id
        actual_by_object_date = {}
        for shift in actual_shifts:
            if shift.time_slot_id:
                actual_shifts_map.setdefault(shift.time_slot_id, [])
                actual_shifts_map[shift.time_slot_id].append({
                    "id": shift.id,
                    "user_id": shift.user_id,
                    "user_name": f"{shift.user.first_name} {shift.user.last_name or ''}".strip(),
                    "status": shift.status,
                    "start_time": shift.start_time.time().strftime("%H:%M"),
                    "end_time": shift.end_time.time().strftime("%H:%M") if shift.end_time else None,
                    "total_hours": float(shift.total_hours) if shift.total_hours else None,
                    "total_payment": float(shift.total_payment) if shift.total_payment else None,
                    "is_planned": shift.is_planned,
                    "notes": shift.notes
                })
            # Индекс по объекту и дате
            key = (shift.object_id, shift.start_time.date())
            actual_by_object_date.setdefault(key, []).append(shift)
        
        # Создаем данные для каждого тайм-слота
        test_data = []
        for slot in timeslots:
            # Определяем статус на основе запланированных и отработанных смен
            status = "empty"
            scheduled_shifts = []
            actual_shifts = []
            
            # Ищем запланированные смены для этого конкретного тайм-слота
            if slot.id in scheduled_shifts_map:
                scheduled_shifts = scheduled_shifts_map[slot.id]
            else:
                # Дополнительно ищем пересечения по объекту и дате для запланированных (если были без time_slot_id)
                key_sched = (slot.object_id, slot.slot_date)
                overlaps_sched = []
                for sh in scheduled_by_object_date.get(key_sched, []):
                    sh_start = sh.planned_start.time()
                    sh_end = sh.planned_end.time()
                    if (sh_start < slot.end_time) and (slot.start_time < sh_end):
                        overlaps_sched.append(sh)
                if overlaps_sched:
                    for sh in overlaps_sched:
                        scheduled_shifts.append({
                            "id": sh.id,
                            "user_id": sh.user_id,
                            "status": sh.status,
                            "start_time": sh.planned_start.time().strftime("%H:%M"),
                            "end_time": sh.planned_end.time().strftime("%H:%M"),
                            "notes": sh.notes
                        })
            
            # Ищем отработанные смены для этого конкретного тайм-слота
            if slot.id in actual_shifts_map:
                actual_shifts = actual_shifts_map[slot.id]
            else:
                # Дополнительно ищем пересечения по объекту и дате (для спонтанных/без привязки к слоту)
                key = (slot.object_id, slot.slot_date)
                overlaps = []
                for sh in actual_by_object_date.get(key, []):
                    # Пересечение по времени: (sh.start < slot.end) and (slot.start < sh.end)
                    sh_start = sh.start_time.time()
                    sh_end = sh.end_time.time() if sh.end_time else None
                    if sh_end is None:
                        # Активная смена без конца – считаем пересекающейся, если начата до конца слота
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
                            "start_time": sh.start_time.time().strftime("%H:%M"),
                            "end_time": sh.end_time.time().strftime("%H:%M") if sh.end_time else None,
                            "total_hours": float(sh.total_hours) if sh.total_hours else None,
                            "total_payment": float(sh.total_payment) if sh.total_payment else None,
                            "is_planned": sh.is_planned,
                            "notes": sh.notes
                        })
            
            # Определяем статус с приоритетом:
            # active > completed > confirmed(scheduled) > planned(scheduled) > cancelled (если нет планов) > empty
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
            
            # Подсчитываем занятость с учётом правил
            max_slots = slot.max_employees or 1
            # Плановые для счётчика: только planned/confirmed, ограничиваем лимитом
            scheduled_effective = [s for s in scheduled_shifts if s.get("status") in ("planned", "confirmed")]
            planned_count = min(len(scheduled_effective), max_slots)

            # Фактические для счётчика: исключаем отменённые
            actual_non_cancelled = [a for a in actual_shifts if a.get("status") != "cancelled"]
            actual_planned_nc = [a for a in actual_non_cancelled if a.get("is_planned")]
            actual_spont_nc = [a for a in actual_non_cancelled if not a.get("is_planned")]

            # Базовая нагрузка: плановые + фактические запланированные, не превышает лимит
            base_total = min(max_slots, planned_count + len(actual_planned_nc))
            # Спонтанные (не отменённые) могут превышать лимит
            total_shifts = base_total + len(actual_spont_nc)
            availability = f"{total_shifts}/{max_slots}"
            
            test_data.append({
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
        
        logger.info(f"Returning {len(test_data)} test timeslots")
        return test_data
        
    except Exception as e:
        logger.error(f"Error getting timeslots status: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки статуса тайм-слотов")


@router.get("/calendar/api/objects")
async def owner_calendar_api_objects(request: Request):
    """API: список объектов владельца (массив для drag&drop-панели)."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    try:
        async with get_async_session() as session:
            # Определяем владельца по telegram_id
            from sqlalchemy import select
            from domain.entities.user import User
            from domain.entities.object import Object

            if not current_user or not current_user.get("telegram_id"):
                return []

            owner_q = select(User).where(User.telegram_id == current_user["telegram_id"])
            owner = (await session.execute(owner_q)).scalar_one_or_none()
            if not owner:
                return []

            objects_q = select(Object).where(Object.owner_id == owner.id, Object.is_active == True).order_by(Object.created_at.desc())
            objects = (await session.execute(objects_q)).scalars().all()

            return [
                {
                    "id": obj.id,
                    "name": obj.name,
                    "hourly_rate": float(obj.hourly_rate),
                    "opening_time": obj.opening_time.strftime("%H:%M") if obj.opening_time else "09:00",
                    "closing_time": obj.closing_time.strftime("%H:%M") if obj.closing_time else "21:00",
                }
                for obj in objects
            ]

    except Exception as e:
        logger.error(f"Error getting objects: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки объектов")


@router.post("/calendar/api/quick-create-timeslot")
async def owner_calendar_quick_create_timeslot(
    request: Request,
    object_id: int = Form(...),
    slot_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    hourly_rate: int = Form(...),
):
    """API: быстрое создание тайм-слота из drag&drop-панели."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Доступ запрещен")

    try:
        # Валидация
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

        async with get_async_session() as session:
            from apps.web.services.object_service import ObjectService, TimeSlotService

            timeslot_service = TimeSlotService(session)
            object_service = ObjectService(session)

            # Создание слота
            timeslot_data = {
                "slot_date": slot_date_obj,
                "start_time": start_time,
                "end_time": end_time,
                "hourly_rate": hourly_rate,
                "is_active": True,
            }

            new_slot = await timeslot_service.create_timeslot(
                timeslot_data,
                object_id,
                current_user.get("telegram_id") or current_user.get("id"),
            )
            if not new_slot:
                raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")

            # Инфо об объекте для ответа
            obj = await object_service.get_object_by_id(
                object_id,
                current_user.get("telegram_id") or current_user.get("id"),
            )

            return {
                "success": True,
                "timeslot": {
                    "id": new_slot.id,
                    "object_id": new_slot.object_id,
                    "object_name": obj.name if obj else "Неизвестный объект",
                    "date": new_slot.slot_date.strftime("%Y-%m-%d"),
                    "start_time": new_slot.start_time.strftime("%H:%M"),
                    "end_time": new_slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(new_slot.hourly_rate) if new_slot.hourly_rate else 0,
                    "is_active": new_slot.is_active,
                },
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quick timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слота: {str(e)}")
@router.get("/calendar/api/timeslot/{timeslot_id}")
async def owner_calendar_api_timeslot_detail(
    request: Request,
    timeslot_id: int
):
    """Детали конкретного тайм-слота"""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    try:
        async with get_async_session() as session:
            from sqlalchemy import select, and_
            from sqlalchemy.orm import selectinload
            from domain.entities.time_slot import TimeSlot
            from domain.entities.object import Object
            from domain.entities.user import User

            # Владелец по текущему пользователю
            if not current_user or not current_user.get("telegram_id"):
                raise HTTPException(status_code=403, detail="Нет доступа")
            owner_q = select(User).where(User.telegram_id == current_user["telegram_id"])
            owner = (await session.execute(owner_q)).scalar_one_or_none()
            if not owner:
                raise HTTPException(status_code=404, detail="Пользователь не найден")

            # Слот + проверка принадлежности через объект
            slot_q = select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id)
            slot = (await session.execute(slot_q)).scalar_one_or_none()
            if not slot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден")
            obj_q = select(Object).where(Object.id == slot.object_id, Object.owner_id == owner.id)
            if (await session.execute(obj_q)).scalar_one_or_none() is None:
                raise HTTPException(status_code=403, detail="Нет доступа к тайм-слоту")

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
                "scheduled": [],
                "actual": [],
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeslot details: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")


def _create_calendar_grid(year: int, month: int, timeslots: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Создает календарную сетку с тайм-слотами"""
    import calendar as py_calendar
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
            day_timeslots = [
                slot for slot in timeslots 
                if slot["date"] == current_date and slot.get("is_active", True)
            ]
            if day_timeslots:
                logger.info(f"Found {len(day_timeslots)} timeslots for {current_date}")
            else:
                # Отладка: проверим, какие даты есть в тайм-слотах
                if current_date.month == month:  # Только для текущего месяца
                    slot_dates = [slot["date"] for slot in timeslots if slot.get("is_active", True)]
                    logger.info(f"No timeslots for {current_date}, available dates: {slot_dates[:5]}")  # Показываем первые 5
            
            week_data.append({
                "date": current_date,
                "is_current_month": current_date.month == month,
                "is_today": current_date == date.today(),
                "timeslots": day_timeslots,
                "timeslots_count": len(day_timeslots)
            })
            current_date += timedelta(days=1)
        
        calendar_grid.append(week_data)
    
    return calendar_grid


# Русские названия месяцев (И.п.)
RU_MONTHS = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]
# ШАБЛОНЫ ДОГОВОРОВ
# ===============================

@router.get("/templates/contracts", response_class=HTMLResponse, name="owner_contract_templates")
async def owner_contract_templates(request: Request):
    """Список шаблонов договоров."""
    # Проверяем авторизацию и роль владельца
    current_user = await get_current_user(request)
    user_role = current_user.get("role", "employee")
    if user_role != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        templates_list = await contract_service.get_contract_templates()
        
        return templates.TemplateResponse(
            "owner/templates/contracts/list.html",
            {
                "request": request,
                "templates": templates_list,
                "title": "Шаблоны договоров",
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading contract templates: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблонов договоров")


# ===============================
# ТАЙМ-СЛОТЫ
# ===============================

@router.get("/timeslots/object/{object_id}", response_class=HTMLResponse)
async def owner_timeslots_list(
    request: Request,
    object_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Список тайм-слотов объекта владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
        
        # Получение информации об объекте и тайм-слотов из базы данных
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        # Получаем объект
        obj = await object_service.get_object_by_id(object_id, telegram_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем тайм-слоты
        timeslots = await timeslot_service.get_timeslots_by_object(object_id, telegram_id)
        
        # Преобразуем в формат для шаблона
        timeslots_data = []
        for slot in timeslots:
            timeslots_data.append({
                "id": slot.id,
                "object_id": slot.object_id,
                "slot_date": slot.slot_date.strftime("%Y-%m-%d"),
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate),
                "is_active": slot.is_active,
                "created_at": slot.created_at.strftime("%Y-%m-%d")
            })
        
        # Информация об объекте
        object_data = {
            "id": obj.id,
            "name": obj.name,
            "address": obj.address or ""
        }
        
        return templates.TemplateResponse("owner/timeslots/list.html", {
            "request": request,
            "title": f"Тайм-слоты: {object_data['name']}",
            "timeslots": timeslots_data,
            "object_id": object_id,
            "object": object_data,
            "current_user": current_user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading timeslots: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки тайм-слотов")


@router.get("/timeslots/{timeslot_id}/edit", response_class=HTMLResponse)
async def owner_timeslot_edit_form(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма редактирования тайм-слота владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
        
        # Получение тайм-слота из базы данных
        timeslot_service = TimeSlotService(db)
        object_service = ObjectService(db)
        
        # Получаем тайм-слот с проверкой владельца
        timeslot = await timeslot_service.get_timeslot_by_id(timeslot_id, telegram_id)
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Получаем объект
        obj = await object_service.get_object_by_id(timeslot.object_id, telegram_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        timeslot_data = {
            "id": timeslot.id,
            "object_id": timeslot.object_id,
            "start_time": timeslot.start_time.strftime("%H:%M"),
            "end_time": timeslot.end_time.strftime("%H:%M"),
            "hourly_rate": float(timeslot.hourly_rate) if timeslot.hourly_rate else float(obj.hourly_rate),
            "is_active": timeslot.is_active
        }
        
        object_data = {
            "id": obj.id,
            "name": obj.name,
            "address": obj.address or ""
        }
        
        return templates.TemplateResponse("owner/timeslots/edit.html", {
            "request": request,
            "title": f"Редактирование тайм-слота: {object_data['name']}",
            "timeslot": timeslot_data,
            "object_id": timeslot.object_id,
            "object": object_data,
            "current_user": current_user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading edit form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/timeslots/{timeslot_id}/edit")
async def owner_timeslot_update(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление тайм-слота владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
            
        logger.info(f"Updating timeslot {timeslot_id}")
        
        # Получение данных формы
        form_data = await request.form()
        start_time = form_data.get("start_time", "")
        end_time = form_data.get("end_time", "")
        hourly_rate_str = form_data.get("hourly_rate", "0")
        is_active = "is_active" in form_data
        
        # Логирование для отладки
        logger.info(f"Form data: start_time={start_time}, end_time={end_time}, hourly_rate_str='{hourly_rate_str}', is_active={is_active}")
        
        # Валидация и преобразование данных
        try:
            # Очищаем строку от пробелов и проверяем на пустоту
            hourly_rate_str = hourly_rate_str.strip()
            if not hourly_rate_str:
                raise ValueError("Пустое значение ставки")
            hourly_rate = int(hourly_rate_str)
        except ValueError as e:
            logger.error(f"Error parsing hourly_rate '{hourly_rate_str}': {e}")
            raise HTTPException(status_code=400, detail=f"Неверный формат ставки: '{hourly_rate_str}'")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Валидация времени
        from datetime import time
        try:
            start = time.fromisoformat(start_time)
            end = time.fromisoformat(end_time)
            if start >= end:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат времени")
        
        # Обновление тайм-слота в базе данных
        timeslot_service = TimeSlotService(db)
        timeslot_data = {
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "is_active": is_active
        }
        
        updated_timeslot = await timeslot_service.update_timeslot(timeslot_id, timeslot_data, telegram_id)
        if not updated_timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
        
        logger.info(f"Timeslot {timeslot_id} updated successfully")
        
        return RedirectResponse(url=f"/owner/timeslots/object/{updated_timeslot.object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления тайм-слота: {str(e)}")


@router.post("/timeslots/{timeslot_id}/delete")
async def owner_timeslot_delete(
    timeslot_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление тайм-слота владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
            
        logger.info(f"Deleting timeslot {timeslot_id}")
        
        # Удаление тайм-слота из базы данных
        timeslot_service = TimeSlotService(db)
        
        # Получаем тайм-слот для получения object_id
        timeslot = await timeslot_service.get_timeslot_by_id(timeslot_id, telegram_id)
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        object_id = timeslot.object_id
        
        # Удаляем тайм-слот
        success = await timeslot_service.delete_timeslot(timeslot_id, telegram_id)
        if not success:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
        
        logger.info(f"Timeslot {timeslot_id} deleted successfully")
        
        return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тайм-слота: {str(e)}")


@router.get("/timeslots/object/{object_id}/create", response_class=HTMLResponse)
async def owner_timeslot_create_form(
    request: Request,
    object_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма создания тайм-слота владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
        
        # Получение информации об объекте из базы данных
        object_service = ObjectService(db)
        
        # Получаем объект
        obj = await object_service.get_object_by_id(object_id, telegram_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Информация об объекте
        object_data = {
            "id": obj.id,
            "name": obj.name,
            "address": obj.address or ""
        }
        
        return templates.TemplateResponse("owner/timeslots/create.html", {
            "request": request,
            "title": f"Создание тайм-слота: {object_data['name']}",
            "object_id": object_id,
            "object": object_data,
            "current_user": current_user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading create form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы создания")


@router.post("/timeslots/object/{object_id}/create")
async def owner_timeslot_create(
    request: Request,
    object_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание тайм-слота владельца."""
    try:
        # Получаем telegram_id из current_user
        if isinstance(current_user, dict):
            telegram_id = current_user.get("id")
        else:
            telegram_id = current_user.telegram_id
            
        logger.info(f"Creating timeslot for object {object_id}")
        
        # Получение данных формы
        form_data = await request.form()
        slot_date = form_data.get("slot_date", "")
        start_time = form_data.get("start_time", "")
        end_time = form_data.get("end_time", "")
        hourly_rate_str = form_data.get("hourly_rate", "0")
        is_active = "is_active" in form_data
        
        # Логирование для отладки
        logger.info(f"Form data: slot_date={slot_date}, start_time={start_time}, end_time={end_time}, hourly_rate_str='{hourly_rate_str}', is_active={is_active}")
        
        # Валидация и преобразование данных
        try:
            # Очищаем строку от пробелов и проверяем на пустоту
            hourly_rate_str = hourly_rate_str.strip()
            if not hourly_rate_str:
                raise ValueError("Пустое значение ставки")
            hourly_rate = int(hourly_rate_str)
        except ValueError as e:
            logger.error(f"Error parsing hourly_rate '{hourly_rate_str}': {e}")
            raise HTTPException(status_code=400, detail=f"Неверный формат ставки: '{hourly_rate_str}'")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Валидация времени
        from datetime import time, date
        try:
            start = time.fromisoformat(start_time)
            end = time.fromisoformat(end_time)
            if start >= end:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат времени")
        
        # Валидация даты
        try:
            slot_date_obj = date.fromisoformat(slot_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты")
        
        # Создание тайм-слота в базе данных
        timeslot_service = TimeSlotService(db)
        timeslot_data = {
            "object_id": object_id,
            "slot_date": slot_date,
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "is_active": is_active
        }
        
        created_timeslot = await timeslot_service.create_timeslot(timeslot_data, telegram_id)
        if not created_timeslot:
            raise HTTPException(status_code=400, detail="Ошибка создания тайм-слота")
        
        logger.info(f"Timeslot created successfully with ID: {created_timeslot.id}")
        
        return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слота: {str(e)}")


@router.get("/shifts", response_class=HTMLResponse, name="owner_shifts")
async def owner_shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр по статусу: active, planned, completed"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    object_id: Optional[str] = Query(None, description="ID объекта"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список смен владельца."""
    try:
        # Получаем telegram_id из current_user
        telegram_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # Получаем внутренний ID пользователя из БД
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        user_id = user_obj.id if user_obj else None
        
        # Базовый запрос для смен
        shifts_query = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.user)
        )
        
        # Базовый запрос для запланированных смен
        schedules_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user)
        )
        
        # Фильтрация по владельцу
        if user_role != "superadmin":
            # Получаем объекты владельца
            owner_objects = select(Object.id).where(Object.owner_id == user_id)
            shifts_query = shifts_query.where(Shift.object_id.in_(owner_objects))
            schedules_query = schedules_query.where(ShiftSchedule.object_id.in_(owner_objects))
        
        # Получение объектов для фильтра
        objects_query = select(Object)
        if user_role != "superadmin":
            objects_query = objects_query.where(Object.owner_id == user_id)
        objects_result = await db.execute(objects_query)
        objects = objects_result.scalars().all()
        
        # Применение фильтров
        if object_id:
            shifts_query = shifts_query.where(Shift.object_id == int(object_id))
            schedules_query = schedules_query.where(ShiftSchedule.object_id == int(object_id))
        
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
                'start_time': shift.start_time.strftime('%Y-%m-%d %H:%M') if shift.start_time else '-',
                'end_time': shift.end_time.strftime('%Y-%m-%d %H:%M') if shift.end_time else '-',
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
                'start_time': schedule.planned_start.strftime('%Y-%m-%d %H:%M') if schedule.planned_start else '-',
                'end_time': schedule.planned_end.strftime('%Y-%m-%d %H:%M') if schedule.planned_end else '-',
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
        
        return templates.TemplateResponse("owner/shifts/list.html", {
            "request": request,
            "shifts": paginated_shifts,
            "objects": objects,
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
        logger.error(f"Error loading shifts: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки смен")


@router.get("/shifts/{shift_id}", response_class=HTMLResponse)
async def owner_shift_detail(
    request: Request, 
    shift_id: int, 
    shift_type: Optional[str] = Query("shift"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали смены владельца"""
    try:
        # Получаем роль пользователя
        user_role = current_user.get("role")
        
        # Получаем внутренний ID пользователя
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        user_id = user_obj.id if user_obj else None
        
        if shift_type == "schedule":
            # Запланированная смена
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user)
            ).where(ShiftSchedule.id == shift_id)
        else:
            # Реальная смена
            query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(Shift.id == shift_id)
        
        result = await db.execute(query)
        shift = result.scalar_one_or_none()
        
        if not shift:
            return templates.TemplateResponse("owner/shifts/not_found.html", {
                "request": request,
                "current_user": current_user
            })
        
        # Проверка прав доступа
        if user_role != "superadmin":
            if shift.object.owner_id != user_id:
                return templates.TemplateResponse("owner/shifts/access_denied.html", {
                    "request": request,
                    "current_user": current_user
                })
        
        return templates.TemplateResponse("owner/shifts/detail.html", {
            "request": request,
            "current_user": current_user,
            "shift": shift,
            "shift_type": shift_type
        })
        
    except Exception as e:
        logger.error(f"Error loading shift detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей смены")


@router.post("/shifts/{shift_id}/cancel")
async def owner_cancel_shift(
    request: Request, 
    shift_id: int, 
    shift_type: Optional[str] = Query("shift"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Отмена смены владельца"""
    from fastapi.responses import JSONResponse
    from datetime import datetime
    
    try:
        # Получаем роль пользователя
        user_role = current_user.get("role")
        
        # Получаем внутренний ID пользователя
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        user_id = user_obj.id if user_obj else None
        
        if shift_type == "schedule":
            # Отмена запланированной смены
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object)
            ).where(ShiftSchedule.id == shift_id)
            result = await db.execute(query)
            shift = result.scalar_one_or_none()
            
            if shift and shift.status == "planned":
                # Проверка прав доступа
                if user_role != "superadmin":
                    if shift.object.owner_id != user_id:
                        return JSONResponse(
                            status_code=403,
                            content={"success": False, "message": "Доступ запрещен"}
                        )
                
                # Отменяем смену
                shift.status = "cancelled"
                shift.updated_at = datetime.utcnow()
                await db.commit()
                
                return JSONResponse(
                    status_code=200,
                    content={"success": True, "message": "Смена отменена"}
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Смена не найдена или уже отменена"}
                )
        else:
            # Отмена реальной смены
            query = select(Shift).options(
                selectinload(Shift.object)
            ).where(Shift.id == shift_id)
            result = await db.execute(query)
            shift = result.scalar_one_or_none()
            
            if shift and shift.status == "active":
                # Проверка прав доступа
                if user_role != "superadmin":
                    if shift.object.owner_id != user_id:
                        return JSONResponse(
                            status_code=403,
                            content={"success": False, "message": "Доступ запрещен"}
                        )
                
                # Отменяем смену
                shift.status = "cancelled"
                shift.updated_at = datetime.utcnow()
                await db.commit()
                
                return JSONResponse(
                    status_code=200,
                    content={"success": True, "message": "Смена отменена"}
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Смена не найдена или уже завершена"}
                )
                
    except Exception as e:
        logger.error(f"Error canceling shift: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Ошибка отмены смены"}
        )


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


# ===== ШАБЛОНЫ ПЛАНИРОВАНИЯ =====

@router.get("/templates/planning", response_class=HTMLResponse, name="owner_planning_templates_list")
async def owner_planning_templates_list(request: Request):
    """Список шаблонов планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            templates_list = await template_service.get_templates_by_owner(current_user["id"])
        
        return templates.TemplateResponse(
            "owner/templates/planning/list.html",
            {
                "request": request,
                "templates": templates_list,
                "template_type": "planning",
                "title": "Шаблоны планирования",
                "current_user": current_user
            }
        )
    except Exception as e:
        logger.error(f"Error loading planning templates: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблонов планирования")


@router.get("/templates/planning/create", response_class=HTMLResponse, name="owner_planning_template_create")
async def owner_planning_template_create(request: Request):
    """Форма создания шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        "owner/templates/planning/create.html",
        {
            "request": request,
            "template_type": "planning",
            "title": "Создание шаблона планирования",
            "current_user": current_user
        }
    )


@router.post("/templates/planning/create", name="owner_planning_template_create_post")
async def owner_planning_template_create_post(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    hourly_rate: int = Form(0),
    repeat_type: str = Form("none"),
    repeat_days: str = Form(""),
    is_public: bool = Form(False)
):
    """Создание шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            
            template_data = {
                "name": name,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "hourly_rate": hourly_rate,
                "repeat_type": repeat_type,
                "repeat_days": repeat_days,
                "is_public": is_public
            }
            
            template = await template_service.create_template(template_data, current_user["id"])
            
            if template:
                return RedirectResponse(url="/owner/templates/planning", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка создания шаблона планирования")
                
    except Exception as e:
        logger.error(f"Error creating planning template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания шаблона планирования: {str(e)}")


@router.get("/templates/planning/{template_id}", response_class=HTMLResponse, name="owner_planning_template_detail")
async def owner_planning_template_detail(request: Request, template_id: int):
    """Детали шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            template = await template_service.get_template_by_id(template_id, current_user["id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон планирования не найден")
        
        return templates.TemplateResponse(
            "owner/templates/planning/detail.html",
            {
                "request": request,
                "template": template,
                "template_type": "planning",
                "title": "Детали шаблона планирования",
                "current_user": current_user
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading planning template detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблона планирования")


@router.get("/templates/planning/{template_id}/edit", response_class=HTMLResponse, name="owner_planning_template_edit")
async def owner_planning_template_edit(request: Request, template_id: int):
    """Форма редактирования шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            template = await template_service.get_template_by_id(template_id, current_user["id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон планирования не найден")
        
        return templates.TemplateResponse(
            "owner/templates/planning/edit.html",
            {
                "request": request,
                "template": template,
                "template_type": "planning",
                "title": "Редактирование шаблона планирования",
                "current_user": current_user
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading planning template edit: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/templates/planning/{template_id}/edit", name="owner_planning_template_edit_post")
async def owner_planning_template_edit_post(
    request: Request,
    template_id: int,
    name: str = Form(...),
    description: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    hourly_rate: int = Form(0),
    repeat_type: str = Form("none"),
    repeat_days: str = Form(""),
    is_public: bool = Form(False)
):
    """Обновление шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            
            template_data = {
                "name": name,
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "hourly_rate": hourly_rate,
                "repeat_type": repeat_type,
                "repeat_days": repeat_days,
                "is_public": is_public
            }
            
            success = await template_service.update_template(template_id, template_data, current_user["id"])
            
            if success:
                return RedirectResponse(url=f"/owner/templates/planning/{template_id}", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка обновления шаблона планирования")
                
    except Exception as e:
        logger.error(f"Error updating planning template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления шаблона планирования: {str(e)}")


@router.post("/templates/planning/{template_id}/delete", name="owner_planning_template_delete")
async def owner_planning_template_delete(request: Request, template_id: int):
    """Удаление шаблона планирования."""
    current_user = await get_current_user(request)
    if current_user.get("role") != "owner":
        return RedirectResponse(url="/auth/login", status_code=status.HTTP_302_FOUND)
    
    try:
        async with get_async_session() as session:
            from apps.web.services.template_service import TemplateService
            template_service = TemplateService(session)
            success = await template_service.delete_template(template_id, current_user["id"])
        
        if success:
            return RedirectResponse(url="/owner/templates/planning", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка удаления шаблона планирования")
            
    except Exception as e:
        logger.error(f"Error deleting planning template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка удаления шаблона планирования: {str(e)}")


# ===============================
# СОТРУДНИКИ
# ===============================

@router.get("/employees", response_class=HTMLResponse)
async def owner_employees_list(
    request: Request,
    view_mode: str = Query("cards", description="Режим отображения: cards или list"),
    show_former: bool = Query(False, description="Показать бывших сотрудников"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список сотрудников владельца."""
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
            "employees/list.html",
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
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки списка сотрудников: {str(e)}")


@router.get("/employees/create", response_class=HTMLResponse)
async def owner_employees_create_form(
    request: Request,
    employee_telegram_id: int = Query(None, description="Telegram ID сотрудника для предзаполнения"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма создания договора с сотрудником."""
    try:
        from apps.web.services.contract_service import ContractService
        from apps.web.services.tag_service import TagService
        
        # Получаем доступных сотрудников и объекты
        contract_service = ContractService()
        # Используем telegram_id для поиска пользователя в БД
        user_id = current_user["id"]  # Это telegram_id из токена
        available_employees = await contract_service.get_available_employees(user_id)
        objects = await contract_service.get_owner_objects(user_id)
        
        # Получаем внутренний ID пользователя для шаблонов
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        internal_user_id = user_obj.id if user_obj else None
        
        # Получаем профиль владельца для тегов
        tag_service = TagService()
        owner_profile = await tag_service.get_owner_profile(db, internal_user_id)
        
        # Получаем шаблоны с учетом владельца и публичных
        templates_list = await contract_service.get_contract_templates_for_user(internal_user_id)
        
        # Текущая дата для шаблона (формат YYYY-MM-DD)
        from datetime import date
        current_date = date.today().strftime("%Y-%m-%d")
        
        # Подготавливаем шаблоны в JSON формате для JavaScript
        templates_json = []
        for template in templates_list:
            templates_json.append({
                "id": template.id,
                "name": template.name,
                "content": template.content,
                "version": template.version,
                "fields_schema": template.fields_schema or []
            })
        
        # Получаем теги владельца для подстановки
        owner_tags = {}
        if owner_profile:
            owner_tags = owner_profile.get_tags_for_templates()
            # Добавляем системные теги
            from datetime import datetime
            owner_tags.update({
                'current_date': datetime.now().strftime('%d.%m.%Y'),
                'current_time': datetime.now().strftime('%H:%M'),
                'current_year': str(datetime.now().year)
            })
        
        return templates.TemplateResponse(
            "employees/create.html",
            {
                "request": request,
                "title": "Создание договора",
                "current_user": current_user,
                "available_employees": available_employees,
                "objects": objects,
                "templates": templates_list,
                "templates_json": templates_json,
                "owner_tags": owner_tags,
                "current_date": current_date,
                "employee_telegram_id": employee_telegram_id
            }
        )
    except Exception as e:
        logger.error(f"Error loading create contract form: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы: {str(e)}")


@router.get("/employees/{employee_id}", response_class=HTMLResponse)
async def owner_employee_detail(
    employee_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детальная информация о сотруднике."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        user_id = current_user["id"]
        
        # Получаем информацию о сотруднике
        employee_info = await contract_service.get_employee_by_telegram_id(employee_id, user_id)
        
        if not employee_info:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")
        
        return templates.TemplateResponse(
            "employees/detail.html",
            {
                "request": request,
                "title": f"Сотрудник {employee_info.get('name', 'Неизвестно')}",
                "current_user": current_user,
                "employee": employee_info
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading employee detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки информации о сотруднике: {str(e)}")


@router.post("/employees/create")
async def owner_employees_create_contract(
    request: Request,
    employee_telegram_id: int = Form(...),
    title: str = Form(...),
    content: str = Form(""),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[]),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание договора с сотрудником."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        
        # Парсим даты
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Получаем данные формы для динамических полей
        form_data = await request.form()
        dynamic_values = {}
        
        # Извлекаем значения динамических полей
        for key, value in form_data.items():
            if key.startswith("field_"):
                field_key = key[6:]  # Убираем префикс "field_"
                dynamic_values[field_key] = value
        
        # Создаем договор
        contract_data = {
            "employee_telegram_id": employee_telegram_id,
            "title": title,
            "content": content if content else None,
            "hourly_rate": hourly_rate,
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "template_id": template_id,
            "allowed_objects": allowed_objects,
            "values": dynamic_values if dynamic_values else None
        }
        
        contract = await contract_service.create_contract(current_user["id"], contract_data)
        
        if contract:
            return RedirectResponse(url="/owner/employees", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка создания договора")
            
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания договора: {str(e)}")


@router.get("/employees/contract/{contract_id}", response_class=HTMLResponse)
async def owner_contract_detail(
    contract_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали договора."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        contract = await contract_service.get_contract_by_telegram_id(contract_id, current_user["id"])
        
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")
        
        return templates.TemplateResponse(
            "employees/contract.html",
            {
                "request": request,
                "contract": contract,
                "title": f"Договор {contract.get('title', 'Без названия')}",
                "current_user": current_user
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading contract detail: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки информации о договоре: {str(e)}")


@router.get("/employees/contract/{contract_id}/edit", response_class=HTMLResponse)
async def owner_contract_edit_form(
    contract_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма редактирования договора."""
    try:
        from apps.web.services.contract_service import ContractService
        from apps.web.services.tag_service import TagService
        
        contract_service = ContractService()
        contract = await contract_service.get_contract_by_telegram_id(contract_id, current_user["id"])
        
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")
        
        # Получаем доступные объекты
        objects = await contract_service.get_owner_objects(current_user["id"])
        
        # Получаем внутренний ID пользователя для шаблонов
        user_query = select(User).where(User.telegram_id == current_user["id"])
        user_result = await db.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        internal_user_id = user_obj.id if user_obj else None
        
        # Получаем шаблоны
        templates_list = await contract_service.get_contract_templates_for_user(internal_user_id)
        
        # Получаем профиль владельца для тегов
        tag_service = TagService()
        owner_profile = await tag_service.get_owner_profile(db, internal_user_id)
        
        # Подготавливаем шаблоны в JSON формате
        templates_json = []
        for template in templates_list:
            templates_json.append({
                "id": template.id,
                "name": template.name,
                "content": template.content,
                "version": template.version,
                "fields_schema": template.fields_schema or []
            })
        
        # Получаем теги владельца
        owner_tags = {}
        if owner_profile:
            owner_tags = owner_profile.get_tags_for_templates()
            from datetime import datetime
            owner_tags.update({
                'current_date': datetime.now().strftime('%d.%m.%Y'),
                'current_time': datetime.now().strftime('%H:%M'),
                'current_year': str(datetime.now().year)
            })
        
        return templates.TemplateResponse(
            "employees/contract_edit.html",
            {
                "request": request,
                "contract": contract,
                "objects": objects,
                "templates": templates_list,
                "templates_json": templates_json,
                "owner_tags": owner_tags,
                "title": f"Редактирование договора {contract.get('title', 'Без названия')}",
                "current_user": current_user
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading contract edit form: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки формы: {str(e)}")


@router.post("/employees/contract/{contract_id}/edit")
async def owner_contract_edit(
    contract_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(""),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[]),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Редактирование договора."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        
        # Парсим даты
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Получаем данные формы для динамических полей
        form_data = await request.form()
        dynamic_values = {}
        
        # Извлекаем значения динамических полей
        for key, value in form_data.items():
            if key.startswith("field_"):
                field_key = key[6:]  # Убираем префикс "field_"
                dynamic_values[field_key] = value
        
        # Обновляем договор
        contract_data = {
            "title": title,
            "content": content if content else None,
            "hourly_rate": hourly_rate,
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "template_id": template_id,
            "allowed_objects": allowed_objects,
            "values": dynamic_values if dynamic_values else None
        }
        
        success = await contract_service.update_contract(contract_id, current_user["id"], contract_data)
        
        if success:
            return RedirectResponse(url=f"/owner/employees/contract/{contract_id}", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка обновления договора")
            
    except Exception as e:
        logger.error(f"Error updating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления договора: {str(e)}")


@router.post("/employees/contract/{contract_id}/activate")
async def owner_contract_activate(
    contract_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Активация договора."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        success = await contract_service.activate_contract(contract_id, current_user["id"])
        
        if success:
            return RedirectResponse(url=f"/owner/employees/contract/{contract_id}", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка активации договора")
            
    except Exception as e:
        logger.error(f"Error activating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка активации договора: {str(e)}")


@router.post("/employees/contract/{contract_id}/terminate")
async def owner_contract_terminate(
    contract_id: int,
    request: Request,
    reason: str = Form(""),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Расторжение договора."""
    try:
        from apps.web.services.contract_service import ContractService
        
        contract_service = ContractService()
        success = await contract_service.terminate_contract(contract_id, current_user["id"], reason)
        
        if success:
            return RedirectResponse(url="/owner/employees", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка расторжения договора")
            
    except Exception as e:
        logger.error(f"Error terminating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка расторжения договора: {str(e)}")


@router.get("/employees/contract/{contract_id}/pdf")
async def owner_contract_pdf(
    contract_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Генерация PDF договора."""
    try:
        from apps.web.services.contract_service import ContractService
        from apps.web.services.pdf_service import PDFService
        
        contract_service = ContractService()
        contract = await contract_service.get_contract_by_id_and_owner_telegram_id(contract_id, current_user["id"])
        
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")
        
        pdf_service = PDFService()
        pdf_content = await pdf_service.generate_contract_pdf(contract)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=contract_{contract_id}.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating contract PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации PDF: {str(e)}")
