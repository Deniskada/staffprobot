"""
Роуты для управления шаблонами планирования
"""
from fastapi import APIRouter, Request, Depends, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.template_service import TemplateService
from apps.web.services.object_service import ObjectService
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def templates_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список шаблонов планирования"""
    try:
        template_service = TemplateService(db)
        templates_data = await template_service.get_templates_by_owner(current_user["telegram_id"])
        
        # Получаем объекты для создания новых шаблонов
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
        return templates.TemplateResponse(
            "templates/index.html",
            {
                "request": request,
                "templates": templates_data,
                "objects": objects,
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading templates list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблонов")


@router.get("/create", response_class=HTMLResponse)
async def create_template_form(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма создания шаблона"""
    try:
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
        return templates.TemplateResponse(
            "templates/create.html",
            {
                "request": request,
                "objects": objects,
                "current_user": current_user
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading create template form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/create")
async def create_template(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового шаблона"""
    try:
        form_data = await request.form()
        
        # Парсим данные формы
        template_data = {
            "name": form_data.get("name", "").strip(),
            "description": form_data.get("description", "").strip(),
            "object_id": int(form_data.get("object_id", 0)),
            "start_time": form_data.get("start_time", "").strip(),
            "end_time": form_data.get("end_time", "").strip(),
            "hourly_rate": int(form_data.get("hourly_rate", 0)),
            "repeat_type": form_data.get("repeat_type", "none"),
            "repeat_days": form_data.get("repeat_days", "").strip(),
            "repeat_interval": int(form_data.get("repeat_interval", 1)),
            "is_public": form_data.get("is_public") == "on"
        }
        
        # Валидация
        if not template_data["name"]:
            raise HTTPException(status_code=400, detail="Название шаблона обязательно")
        
        if not template_data["object_id"]:
            raise HTTPException(status_code=400, detail="Выберите объект")
        
        if not template_data["start_time"] or not template_data["end_time"]:
            raise HTTPException(status_code=400, detail="Укажите время начала и окончания")
        
        if template_data["hourly_rate"] <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Создаем шаблон
        template_service = TemplateService(db)
        template = await template_service.create_template(template_data, current_user["telegram_id"])
        
        if not template:
            raise HTTPException(status_code=400, detail="Ошибка создания шаблона")
        
        # Перенаправляем на страницу со списком шаблонов
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/templates?created=true", status_code=303)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания шаблона: {str(e)}")


@router.get("/{template_id}", response_class=HTMLResponse)
async def template_detail(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали шаблона"""
    try:
        template_service = TemplateService(db)
        template = await template_service.get_template_by_id(template_id, current_user["telegram_id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        return templates.TemplateResponse(
            "templates/detail.html",
            {
                "request": request,
                "template": template,
                "current_user": current_user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблона")


@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_form(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма редактирования шаблона"""
    try:
        template_service = TemplateService(db)
        template = await template_service.get_template_by_id(template_id, current_user["telegram_id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
        return templates.TemplateResponse(
            "templates/edit.html",
            {
                "request": request,
                "template": template,
                "objects": objects,
                "current_user": current_user
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading edit template form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/{template_id}/edit")
async def update_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление шаблона"""
    try:
        form_data = await request.form()
        
        template_data = {
            "name": form_data.get("name", "").strip(),
            "description": form_data.get("description", "").strip(),
            "object_id": int(form_data.get("object_id", 0)),
            "start_time": form_data.get("start_time", "").strip(),
            "end_time": form_data.get("end_time", "").strip(),
            "hourly_rate": int(form_data.get("hourly_rate", 0)),
            "repeat_type": form_data.get("repeat_type", "none"),
            "repeat_days": form_data.get("repeat_days", "").strip(),
            "repeat_interval": int(form_data.get("repeat_interval", 1)),
            "is_public": form_data.get("is_public") == "on"
        }
        
        # Валидация
        if not template_data["name"]:
            raise HTTPException(status_code=400, detail="Название шаблона обязательно")
        
        template_service = TemplateService(db)
        template = await template_service.update_template(template_id, template_data, current_user["telegram_id"])
        
        if not template:
            raise HTTPException(status_code=400, detail="Ошибка обновления шаблона")
        
        return JSONResponse({
            "success": True,
            "message": "Шаблон успешно обновлен"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления шаблона: {str(e)}")


@router.post("/{template_id}/delete")
async def delete_template(
    template_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление шаблона"""
    try:
        template_service = TemplateService(db)
        success = await template_service.delete_template(template_id, current_user["telegram_id"])
        
        if not success:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        return JSONResponse({
            "success": True,
            "message": "Шаблон успешно удален"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления шаблона: {str(e)}")


@router.post("/{template_id}/apply")
async def apply_template(
    template_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Применение шаблона к периоду"""
    try:
        form_data = await request.form()
        
        start_date_str = form_data.get("start_date", "").strip()
        end_date_str = form_data.get("end_date", "").strip()
        
        if not start_date_str or not end_date_str:
            raise HTTPException(status_code=400, detail="Укажите даты начала и окончания")
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты")
        
        if start_date > end_date:
            raise HTTPException(status_code=400, detail="Дата начала не может быть позже даты окончания")
        
        template_service = TemplateService(db)
        result = await template_service.apply_template(
            template_id, start_date, end_date, current_user["telegram_id"]
        )
        
        return JSONResponse(result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying template {template_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка применения шаблона: {str(e)}")


@router.get("/api/templates")
async def get_templates_api(
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """API для получения списка шаблонов"""
    try:
        template_service = TemplateService(db)
        templates_data = await template_service.get_templates_by_owner(current_user["telegram_id"])
        
        templates_list = []
        for template in templates_data:
            templates_list.append({
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "object_name": template.object.name if template.object else "Неизвестный объект",
                "start_time": template.start_time,
                "end_time": template.end_time,
                "hourly_rate": float(template.hourly_rate),
                "repeat_type": template.repeat_type,
                "is_public": template.is_public,
                "created_at": template.created_at.isoformat() if template.created_at else None
            })
        
        return JSONResponse({"templates": templates_list})
        
    except Exception as e:
        logger.error(f"Error getting templates API: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки шаблонов")
