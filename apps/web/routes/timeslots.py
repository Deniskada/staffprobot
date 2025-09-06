"""
Роуты для управления тайм-слотами объектов
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger
from typing import Optional
from datetime import time

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

# Временное хранилище тайм-слотов в памяти (для демонстрации)
# TODO: Заменить на работу с базой данных
timeslots_storage = {
    1: {
        "id": 1,
        "object_id": 1,
        "name": "Утренняя смена",
        "start_time": "09:00",
        "end_time": "12:00",
        "hourly_rate": 500,
        "is_active": True,
        "created_at": "2024-01-15"
    },
    2: {
        "id": 2,
        "object_id": 1,
        "name": "Дневная смена",
        "start_time": "12:00",
        "end_time": "15:00",
        "hourly_rate": 500,
        "is_active": True,
        "created_at": "2024-01-15"
    },
    3: {
        "id": 3,
        "object_id": 1,
        "name": "Вечерняя смена",
        "start_time": "15:00",
        "end_time": "18:00",
        "hourly_rate": 500,
        "is_active": True,
        "created_at": "2024-01-15"
    },
    4: {
        "id": 4,
        "object_id": 1,
        "name": "Ночная смена",
        "start_time": "18:00",
        "end_time": "21:00",
        "hourly_rate": 600,
        "is_active": True,
        "created_at": "2024-01-15"
    },
    5: {
        "id": 5,
        "object_id": 2,
        "name": "Рабочий день",
        "start_time": "08:00",
        "end_time": "18:00",
        "hourly_rate": 400,
        "is_active": True,
        "created_at": "2024-01-20"
    }
}


@router.get("/object/{object_id}", response_class=HTMLResponse)
async def timeslots_list(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Список тайм-слотов объекта"""
    try:
        # Получение тайм-слотов объекта
        timeslots_data = [
            slot for slot in timeslots_storage.values() 
            if slot["object_id"] == object_id
        ]
        
        # Получение информации об объекте (для заголовка)
        from apps.web.routes.objects import objects_storage
        object_data = objects_storage.get(object_id, {"name": f"Объект #{object_id}"})
        
        return templates.TemplateResponse("timeslots/list.html", {
            "request": request,
            "title": f"Тайм-слоты: {object_data['name']}",
            "timeslots": timeslots_data,
            "object_id": object_id,
            "object": object_data,
            "current_user": current_user
        })
        
    except Exception as e:
        logger.error(f"Error loading timeslots: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки тайм-слотов")


@router.get("/object/{object_id}/create", response_class=HTMLResponse)
async def create_timeslot_form(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Форма создания тайм-слота"""
    try:
        # Получение информации об объекте
        from apps.web.routes.objects import objects_storage
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id]
        
        # Проверка владельца
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому объекту")
        
        return templates.TemplateResponse("timeslots/create.html", {
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


@router.post("/object/{object_id}/create")
async def create_timeslot(
    request: Request,
    object_id: int,
    name: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    hourly_rate: int = Form(...),
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Создание нового тайм-слота"""
    try:
        # Проверка объекта
        from apps.web.routes.objects import objects_storage
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id]
        
        # Проверка владельца
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому объекту")
        
        logger.info(f"Creating timeslot '{name}' for object {object_id}")
        
        # Валидация данных
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Валидация времени
        try:
            start = time.fromisoformat(start_time)
            end = time.fromisoformat(end_time)
            if start >= end:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат времени")
        
        # Генерация нового ID
        new_id = max(timeslots_storage.keys()) + 1 if timeslots_storage else 1
        
        # Создание тайм-слота в временном хранилище
        timeslots_storage[new_id] = {
            "id": new_id,
            "object_id": object_id,
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "is_active": True,
            "created_at": "2024-01-15"  # TODO: Использовать реальную дату
        }
        
        logger.info(f"Timeslot {new_id} created successfully: {timeslots_storage[new_id]}")
        
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слота: {str(e)}")


@router.get("/{timeslot_id}/edit", response_class=HTMLResponse)
async def edit_timeslot_form(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Форма редактирования тайм-слота"""
    try:
        # Получение данных тайм-слота
        if timeslot_id not in timeslots_storage:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        timeslot_data = timeslots_storage[timeslot_id].copy()
        
        # Проверка владельца через объект
        from apps.web.routes.objects import objects_storage
        object_id = timeslot_data["object_id"]
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id]
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому тайм-слоту")
        
        return templates.TemplateResponse("timeslots/edit.html", {
            "request": request,
            "title": f"Редактирование: {timeslot_data['name']}",
            "timeslot": timeslot_data,
            "object": object_data,
            "current_user": current_user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading edit form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы редактирования")


@router.post("/{timeslot_id}/edit")
async def update_timeslot(
    request: Request,
    timeslot_id: int,
    name: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    hourly_rate: int = Form(...),
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Обновление тайм-слота"""
    try:
        # Проверка существования тайм-слота
        if timeslot_id not in timeslots_storage:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        timeslot_data = timeslots_storage[timeslot_id]
        
        # Проверка владельца через объект
        from apps.web.routes.objects import objects_storage
        object_id = timeslot_data["object_id"]
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id]
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому тайм-слоту")
        
        logger.info(f"Updating timeslot {timeslot_id} for user {current_user['id']}")
        
        # Валидация данных
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Валидация времени
        try:
            start = time.fromisoformat(start_time)
            end = time.fromisoformat(end_time)
            if start >= end:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат времени")
        
        # Получение данных формы
        form_data = await request.form()
        
        # Обработка чекбокса (он не отправляется, если не отмечен)
        is_active = "is_active" in form_data
        
        # Обновление тайм-слота в временном хранилище
        timeslots_storage[timeslot_id].update({
            "name": name,
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "is_active": is_active
        })
        
        logger.info(f"Timeslot {timeslot_id} updated successfully: {timeslots_storage[timeslot_id]}")
        
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления тайм-слота: {str(e)}")


@router.post("/{timeslot_id}/delete")
async def delete_timeslot(
    timeslot_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Удаление тайм-слота"""
    try:
        # Проверка существования тайм-слота
        if timeslot_id not in timeslots_storage:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        timeslot_data = timeslots_storage[timeslot_id]
        
        # Проверка владельца через объект
        from apps.web.routes.objects import objects_storage
        object_id = timeslot_data["object_id"]
        if object_id not in objects_storage:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        object_data = objects_storage[object_id]
        if object_data["owner_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Нет доступа к этому тайм-слоту")
        
        logger.info(f"Deleting timeslot {timeslot_id} for user {current_user['id']}")
        
        # Удаление тайм-слота из временного хранилища
        del timeslots_storage[timeslot_id]
        
        logger.info(f"Timeslot {timeslot_id} deleted successfully")
        
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тайм-слота: {str(e)}")
