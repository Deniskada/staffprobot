"""
Роуты для управления тайм-слотами менеджера
"""

from typing import List, Optional
from datetime import date, time, datetime
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_async_session
from apps.web.services.object_service import ObjectService, TimeSlotService
from apps.web.services.template_service import TemplateService
from shared.services.manager_permission_service import ManagerPermissionService
from apps.web.middleware.role_middleware import require_manager_or_owner
from core.logging.logger import logger

router = APIRouter()


async def get_user_id_from_current_user(current_user, session: AsyncSession):
    """Получает внутренний ID пользователя из current_user"""
    if isinstance(current_user, dict):
        # current_user - это словарь из JWT payload
        telegram_id = current_user.get("id")
        from sqlalchemy import select
        from domain.entities.user import User
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        # current_user - это объект User
        return current_user.id


@router.get("/manager/timeslots", response_class=HTMLResponse)
async def manager_timeslots_index(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Главная страница управления тайм-слотами для менеджера"""
    try:
        
        async with get_async_session() as session:
            object_service = ObjectService(session)
            objects = await object_service.get_objects_by_manager(current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id)
            
            return request.app.state.templates.TemplateResponse(
                "manager/timeslots/index.html",
                {
                    "request": request,
                    "objects": objects,
                    "current_user": current_user
                }
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_index: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки объектов")


@router.get("/manager/timeslots/object/{object_id}", response_class=HTMLResponse)
async def manager_timeslots_list(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Список тайм-слотов объекта для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        async with get_async_session() as session:
            object_service = ObjectService(session)
            
            # Проверяем доступ к объекту
            obj = await object_service.get_object_by_id_for_manager(object_id, telegram_id)
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден или доступ запрещен")
            
            # Получаем тайм-слоты
            timeslots = await object_service.get_timeslots_by_object_for_manager(object_id, telegram_id)
            
            return request.app.state.templates.TemplateResponse(
                "manager/timeslots/list.html",
                {
                    "request": request,
                    "object": obj,
                    "timeslots": timeslots,
                    "current_user": current_user
                }
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки тайм-слотов")


@router.get("/manager/timeslots/object/{object_id}/create", response_class=HTMLResponse)
async def manager_timeslots_create_form(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Форма создания тайм-слота для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        async with get_async_session() as session:
            object_service = ObjectService(session)
            template_service = TemplateService(session)
            
            # Проверяем доступ к объекту
            obj = await object_service.get_object_by_id_for_manager(object_id, telegram_id)
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден или доступ запрещен")
            
            # Получаем публичные шаблоны
            templates = await template_service.get_public_templates()
            
            return request.app.state.templates.TemplateResponse(
                "manager/timeslots/create.html",
                {
                    "request": request,
                    "object": obj,
                    "templates": templates,
                    "current_user": current_user
                }
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_create_form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/manager/timeslots/object/{object_id}/create")
async def manager_timeslots_create(
    request: Request, 
    object_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Создание тайм-слота для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        # Получаем данные формы
        form_data = await request.form()
        creation_mode = form_data.get("creation_mode", "single")
        
        async with get_async_session() as session:
            object_service = ObjectService(session)
            timeslot_service = TimeSlotService(session)
            template_service = TemplateService(session)
            
            # Проверяем доступ к объекту
            obj = await object_service.get_object_by_id_for_manager(object_id, telegram_id)
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден или доступ запрещен")
            
            if creation_mode == "single":
                # Создание одного тайм-слота
                timeslot_data = {
                    "slot_date": datetime.strptime(form_data.get("slot_date"), "%Y-%m-%d").date(),
                    "start_time": form_data.get("start_time"),
                    "end_time": form_data.get("end_time"),
                    "hourly_rate": float(form_data.get("hourly_rate", obj.hourly_rate)),
                    "max_employees": int(form_data.get("max_employees", 1)),
                    "notes": form_data.get("notes", "")
                }
                
                timeslot = await timeslot_service.create_timeslot_for_manager(timeslot_data, object_id, telegram_id)
                if not timeslot:
                    raise HTTPException(status_code=400, detail="Ошибка создания тайм-слота")
                
                logger.info(f"Created single timeslot {timeslot.id} for object {object_id} by manager {telegram_id}")
                
            elif creation_mode == "template":
                # Создание по шаблону
                template_id = int(form_data.get("template_id"))
                start_date = datetime.strptime(form_data.get("start_date"), "%Y-%m-%d").date()
                end_date = datetime.strptime(form_data.get("end_date"), "%Y-%m-%d").date()
                
                hourly_rate_override = None
                if form_data.get("hourly_rate_override"):
                    hourly_rate_override = float(form_data.get("hourly_rate_override"))
                
                result = await template_service.apply_template_to_objects_for_manager(
                    template_id=template_id,
                    start_date=start_date,
                    end_date=end_date,
                    object_ids=[object_id],
                    telegram_id=telegram_id,
                    hourly_rate_override=hourly_rate_override
                )
                
                if not result.get("success"):
                    raise HTTPException(status_code=400, detail=result.get("error", "Ошибка применения шаблона"))
                
                logger.info(f"Applied template {template_id} to object {object_id} by manager {telegram_id}")
            
            return RedirectResponse(
                url=f"/manager/timeslots/object/{object_id}",
                status_code=303
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_create: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания тайм-слота")


@router.get("/manager/timeslots/{timeslot_id}/edit", response_class=HTMLResponse)
async def manager_timeslots_edit_form(
    request: Request, 
    timeslot_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Форма редактирования тайм-слота для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        async with get_async_session() as session:
            timeslot_service = TimeSlotService(session)
            
            # Получаем тайм-слот
            timeslot = await timeslot_service.get_timeslot_by_id_for_manager(timeslot_id, telegram_id)
            if not timeslot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден или доступ запрещен")
            
            return request.app.state.templates.TemplateResponse(
                "manager/timeslots/edit.html",
                {
                    "request": request,
                    "timeslot": timeslot,
                    "current_user": current_user
                }
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_edit_form: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки формы")


@router.post("/manager/timeslots/{timeslot_id}/edit")
async def manager_timeslots_edit(
    request: Request, 
    timeslot_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Редактирование тайм-слота для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        # Получаем данные формы
        form_data = await request.form()
        
        async with get_async_session() as session:
            timeslot_service = TimeSlotService(session)
            
            timeslot_data = {
                "slot_date": datetime.strptime(form_data.get("slot_date"), "%Y-%m-%d").date(),
                "start_time": form_data.get("start_time"),
                "end_time": form_data.get("end_time"),
                "hourly_rate": float(form_data.get("hourly_rate")),
                "max_employees": int(form_data.get("max_employees", 1)),
                "notes": form_data.get("notes", "")
            }
            
            timeslot = await timeslot_service.update_timeslot_for_manager(timeslot_id, timeslot_data, telegram_id)
            if not timeslot:
                raise HTTPException(status_code=400, detail="Ошибка обновления тайм-слота")
            
            logger.info(f"Updated timeslot {timeslot_id} by manager {telegram_id}")
            
            return RedirectResponse(
                url=f"/manager/timeslots/object/{timeslot.object_id}",
                status_code=303
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_edit: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления тайм-слота")


@router.post("/manager/timeslots/bulk-delete")
async def manager_timeslots_bulk_delete(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Массовое удаление тайм-слотов для менеджера"""
    try:
        
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        # Получаем данные формы
        form_data = await request.form()
        timeslot_ids = form_data.getlist("timeslot_ids")
        
        if not timeslot_ids:
            raise HTTPException(status_code=400, detail="Не выбраны тайм-слоты для удаления")
        
        async with get_async_session() as session:
            timeslot_service = TimeSlotService(session)
            deleted_count = 0
            
            for timeslot_id_str in timeslot_ids:
                try:
                    timeslot_id = int(timeslot_id_str)
                    success = await timeslot_service.delete_timeslot_for_manager(timeslot_id, telegram_id)
                    if success:
                        deleted_count += 1
                except (ValueError, TypeError):
                    logger.warning(f"Invalid timeslot_id: {timeslot_id_str}")
                    continue
            
            logger.info(f"Bulk deleted {deleted_count} timeslots by manager {telegram_id}")
            
            return RedirectResponse(
                url="/manager/timeslots",
                status_code=303
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_bulk_delete: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления тайм-слотов")
