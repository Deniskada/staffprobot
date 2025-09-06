"""
Роуты управления объектами для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger
from typing import Optional

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
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Список объектов владельца"""
    try:
        # Получение объектов владельца из временного хранилища
        objects_data = [
            obj for obj in objects_storage.values() 
            if obj["owner_id"] == current_user["id"]
        ]
        
        return templates.TemplateResponse("objects/list.html", {
            "request": request,
            "title": "Управление объектами",
            "objects": objects_data,
            "current_user": current_user
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
    name: str = Form(...),
    address: str = Form(...),
    hourly_rate: int = Form(...),
    opening_time: str = Form(...),
    closing_time: str = Form(...),
    max_distance: int = Form(500),
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Создание нового объекта"""
    try:
        logger.info(f"Creating object '{name}' for user {current_user['id']}")
        
        # Валидация данных
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        if max_distance <= 0:
            raise HTTPException(status_code=400, detail="Максимальное расстояние должно быть больше 0")
        
        # Получение данных формы
        form_data = await request.form()
        
        # Обработка чекбокса (он не отправляется, если не отмечен)
        available_for_applicants = "available_for_applicants" in form_data
        
        # Генерация нового ID
        new_id = max(objects_storage.keys()) + 1 if objects_storage else 1
        
        # Создание объекта в временном хранилище
        objects_storage[new_id] = {
            "id": new_id,
            "name": name,
            "address": address,
            "hourly_rate": hourly_rate,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "max_distance": max_distance,
            "is_active": True,
            "available_for_applicants": available_for_applicants,
            "created_at": "2024-01-15",  # TODO: Использовать реальную дату
            "owner_id": current_user["id"]
        }
        
        logger.info(f"Object {new_id} created successfully: {objects_storage[new_id]}")
        
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
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Детальная информация об объекте"""
    try:
        # Получение данных объекта из временного хранилища с проверкой владельца
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id].copy()
        
        # Проверка владельца
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому объекту")
        
        # Получаем тайм-слоты из хранилища тайм-слотов
        from apps.web.routes.timeslots import timeslots_storage
        object_data["timeslots"] = [
            slot for slot in timeslots_storage.values() 
            if slot["object_id"] == object_id
        ]
        
        return templates.TemplateResponse("objects/detail.html", {
            "request": request,
            "title": f"Объект: {object_data['name']}",
            "object": object_data,
            "current_user": current_user
        })
        
    except Exception as e:
        logger.error(f"Error loading object detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки информации об объекте")


@router.get("/{object_id}/edit", response_class=HTMLResponse)
async def edit_object_form(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Форма редактирования объекта"""
    try:
        # Получение данных объекта для редактирования с проверкой владельца
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id].copy()
        
        # Проверка владельца
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому объекту")
        
        return templates.TemplateResponse("objects/edit.html", {
            "request": request,
            "title": f"Редактирование: {object_data['name']}",
            "object": object_data,
            "current_user": current_user
        })
        
    except Exception as e:
        logger.error(f"Error loading edit form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/{object_id}/edit")
async def update_object(
    request: Request,
    object_id: int,
    name: str = Form(...),
    address: str = Form(...),
    hourly_rate: int = Form(...),
    opening_time: str = Form(...),
    closing_time: str = Form(...),
    max_distance: int = Form(500),
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Обновление объекта"""
    try:
        # Проверка существования объекта
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Проверка владельца
        if objects_storage[object_id]["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому объекту")
        
        logger.info(f"Updating object {object_id} for user {current_user['id']}")
        
        # Валидация данных
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        if max_distance <= 0:
            raise HTTPException(status_code=400, detail="Максимальное расстояние должно быть больше 0")
        
        # Получение данных формы
        form_data = await request.form()
        
        # Обработка чекбоксов (они не отправляются, если не отмечены)
        available_for_applicants = "available_for_applicants" in form_data
        is_active = "is_active" in form_data
        
        # Обновление объекта в временном хранилище
        objects_storage[object_id].update({
            "name": name,
            "address": address,
            "hourly_rate": hourly_rate,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "max_distance": max_distance,
            "available_for_applicants": available_for_applicants,
            "is_active": is_active
        })
        
        logger.info(f"Object {object_id} updated successfully: {objects_storage[object_id]}")
        
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
