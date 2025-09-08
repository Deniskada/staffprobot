"""
Роуты управления объектами для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.object_service import ObjectService, TimeSlotService
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

# Временное хранение объектов в памяти (для демонстрации)
# TODO: Заменить на работу с базой данных
objects_storage = {
    1: {
        "id": 1,
        "name": "Магазин №1",
        "address": "ул. Ленина, 10",
        "hourly_rate": 500,
        "opening_time": "09:00",
        "closing_time": "21:00",
        "max_distance": 500,
        "is_active": True,
        "available_for_applicants": True,
        "created_at": "2024-01-15",
        "owner_id": 1220971779
    },
    2: {
        "id": 2,
        "name": "Офис №2",
        "address": "пр. Мира, 25",
        "hourly_rate": 400,
        "opening_time": "08:00",
        "closing_time": "18:00",
        "max_distance": 300,
        "is_active": True,
        "available_for_applicants": False,
        "created_at": "2024-01-20",
        "owner_id": 1220971779
    }
}


@router.get("/", response_class=HTMLResponse)
async def objects_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    show_inactive: bool = Query(False),
    view_mode: str = Query("cards")
):
    """Список объектов владельца"""
    try:
        # Получение объектов владельца из базы данных
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"], include_inactive=show_inactive)
        
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
        
        return templates.TemplateResponse("objects/list.html", {
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


@router.get("/create", response_class=HTMLResponse)
async def create_object_form(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Форма создания объекта"""
    return templates.TemplateResponse("objects/create.html", {
        "request": request,
        "title": "Создание объекта",
        "current_user": current_user
    })


@router.post("/create")
async def create_object(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового объекта"""
    try:
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
            "coordinates": coordinates
        }
        
        new_object = await object_service.create_object(object_data, current_user["telegram_id"])
        
        logger.info(f"Object {new_object.id} created successfully")
        
        return RedirectResponse(url="/objects", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания объекта: {str(e)}")


@router.get("/{object_id}", response_class=HTMLResponse)
async def object_detail(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детальная информация об объекте"""
    try:
        # Получение данных объекта из базы данных с проверкой владельца
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем тайм-слоты
        timeslots = await timeslot_service.get_timeslots_by_object(object_id, current_user["telegram_id"])
        
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
        
        return templates.TemplateResponse("objects/detail.html", {
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


@router.get("/{object_id}/edit", response_class=HTMLResponse)
async def edit_object_form(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма редактирования объекта"""
    try:
        # Получение данных объекта из базы данных с проверкой владельца
        object_service = ObjectService(db)
        obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
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
        
        return templates.TemplateResponse("objects/edit.html", {
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


@router.post("/{object_id}/edit")
async def update_object(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление объекта"""
    try:
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
        
        # Обработка чекбоксов (они не отправляются, если не отмечены)
        available_for_applicants = "available_for_applicants" in form_data
        is_active = "is_active" in form_data
        
        # Обновление объекта в базе данных
        object_service = ObjectService(db)
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
        
        updated_object = await object_service.update_object(object_id, object_data, current_user["telegram_id"])
        if not updated_object:
            raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")
        
        logger.info(f"Object {object_id} updated successfully")
        
        return RedirectResponse(url=f"/objects/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления объекта: {str(e)}")


@router.post("/{object_id}/delete")
async def delete_object(
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Удаление объекта"""
    try:
        # TODO: Удаление объекта из базы данных с проверкой владельца
        logger.info(f"Deleting object {object_id} for user {current_user['id']}")
        
        # TODO: Здесь будет удаление из базы данных
        # await object_service.delete_object(object_id, current_user["id"])
        
        return RedirectResponse(url="/objects", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Error deleting object: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления объекта: {str(e)}")
