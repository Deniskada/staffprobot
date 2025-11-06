"""
Роуты для управления тайм-слотами менеджера
"""

from typing import List, Optional
from datetime import date, time, datetime, timedelta
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_async_session
from apps.web.services.object_service import ObjectService, TimeSlotService
from apps.web.services.template_service import TemplateService
from shared.services.manager_permission_service import ManagerPermissionService
from apps.web.middleware.role_middleware import require_manager_or_owner
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


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
    current_user: dict = Depends(require_manager_or_owner),
    object_id: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("slot_date"),
    sort_order: str = Query("desc")
):
    """Главная страница управления тайм-слотами для менеджера - табличное представление всех тайм-слотов"""
    try:
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        async with get_async_session() as session:
            from shared.services.manager_permission_service import ManagerPermissionService
            from apps.web.services.object_service import TimeSlotService
            from sqlalchemy import select
            from domain.entities.time_slot import TimeSlot
            
            permission_service = ManagerPermissionService(session)
            timeslot_service = TimeSlotService(session)
            
            # Получаем доступные объекты для менеджера
            user_id = await get_user_id_from_current_user(current_user, session)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")
            
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            
            if not accessible_objects:
                return templates.TemplateResponse(
                    "manager/timeslots/index.html",
                    {
                        "request": request,
                        "timeslots": [],
                        "objects": [],
                        "selected_object_id": None,
                        "selected_object": None,
                        "first_available_object_id": None,
                        "current_user": current_user,
                        "date_from": date_from,
                        "date_to": date_to,
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                )
            
            # Список объектов для фильтра
            objects_list = [{"id": obj.id, "name": obj.name} for obj in accessible_objects]
            first_available_object_id = accessible_objects[0].id if accessible_objects else None
            
            # Парсим object_id (может быть пустой строкой из формы)
            object_id_int = None
            if object_id and object_id.strip():
                try:
                    object_id_int = int(object_id)
                except (ValueError, TypeError):
                    object_id_int = None
            
            # Если указан object_id, фильтруем по нему
            selected_object = None
            selected_object_id = object_id_int
            if object_id_int:
                obj = next((o for o in accessible_objects if o.id == object_id_int), None)
                if obj:
                    selected_object = {
                        "id": obj.id,
                        "name": obj.name,
                        "address": obj.address or "",
                        "hourly_rate": float(obj.hourly_rate) if obj.hourly_rate else 0
                    }
            
            # Получаем тайм-слоты для всех доступных объектов (или одного, если указан фильтр)
            target_objects = [obj for obj in accessible_objects if not object_id_int or obj.id == object_id_int]
            
            all_timeslots = []
            for obj in target_objects:
                # Получаем тайм-слоты объекта
                query = select(TimeSlot).where(TimeSlot.object_id == obj.id)
                
                # Фильтрация по датам
                if date_from:
                    try:
                        from_date = date.fromisoformat(date_from)
                        query = query.where(TimeSlot.slot_date >= from_date)
                    except ValueError:
                        pass
                
                if date_to:
                    try:
                        to_date = date.fromisoformat(date_to)
                        query = query.where(TimeSlot.slot_date <= to_date)
                    except ValueError:
                        pass
                
                result = await session.execute(query)
                obj_timeslots = result.scalars().all()
                all_timeslots.extend(obj_timeslots)
            
            # Сортировка в памяти (как у owner)
            sort_by_norm = (sort_by or "slot_date").strip().lower()
            sort_order_norm = (sort_order or "desc").strip().lower()
            
            if sort_by_norm == "slot_date":
                all_timeslots.sort(key=lambda ts: (ts.slot_date, ts.start_time), reverse=(sort_order_norm == "desc"))
            elif sort_by_norm == "start_time":
                all_timeslots.sort(key=lambda ts: (ts.start_time, ts.slot_date), reverse=(sort_order_norm == "desc"))
            elif sort_by_norm == "hourly_rate":
                all_timeslots.sort(key=lambda ts: (ts.hourly_rate or 0, ts.slot_date), reverse=(sort_order_norm == "desc"))
            else:
                all_timeslots.sort(key=lambda ts: (ts.slot_date, ts.start_time), reverse=True)
            
            # Преобразуем в формат для шаблона
            timeslots_data = []
            for slot in all_timeslots:
                slot_obj = next((o for o in accessible_objects if o.id == slot.object_id), None)
                timeslots_data.append({
                    "id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": slot_obj.name if slot_obj else "Неизвестный объект",
                    "slot_date": slot.slot_date.strftime("%Y-%m-%d"),
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else (float(slot_obj.hourly_rate) if slot_obj and slot_obj.hourly_rate else 0),
                    "max_employees": slot.max_employees or 1,
                    "is_active": slot.is_active,
                    "created_at": slot.created_at.strftime("%Y-%m-%d") if slot.created_at else ""
                })
            
            return templates.TemplateResponse(
                "manager/timeslots/index.html",
                {
                    "request": request,
                    "title": "Тайм-слоты",
                    "timeslots": timeslots_data,
                    "objects": objects_list,
                    "selected_object_id": selected_object_id,
                    "selected_object": selected_object,
                    "first_available_object_id": first_available_object_id,
                    "current_user": current_user,
                    "date_from": date_from,
                    "date_to": date_to,
                    "sort_by": sort_by,
                    "sort_order": sort_order
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager_timeslots_index: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки тайм-слотов")


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
            
            return templates.TemplateResponse(
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
            planning_templates = await template_service.get_public_templates()
            
            return templates.TemplateResponse(
                "manager/timeslots/create.html",
                {
                    "request": request,
                    "object": obj,
                    "templates": planning_templates,
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
            
            # Обработка задач (shift_tasks) - одинаково для обоих режимов
            shift_tasks = []
            task_texts = form_data.getlist("task_text[]")
            task_amounts = form_data.getlist("task_amount[]")
            
            for idx, text in enumerate(task_texts):
                if text.strip():
                    is_mandatory = f"task_mandatory_{idx}" in form_data
                    requires_media = f"task_media_{idx}" in form_data
                    
                    task = {
                        "description": text.strip(),
                        "amount": float(task_amounts[idx]) if idx < len(task_amounts) and task_amounts[idx] else 0.0,
                        "is_mandatory": is_mandatory,
                        "requires_media": requires_media
                    }
                    shift_tasks.append(task)
            
            if creation_mode == "single":
                # Создание одного тайм-слота
                timeslot_data = {
                    "slot_date": datetime.strptime(form_data.get("slot_date"), "%Y-%m-%d").date(),
                    "start_time": form_data.get("start_time"),
                    "end_time": form_data.get("end_time"),
                    "hourly_rate": float(form_data.get("hourly_rate", obj.hourly_rate)),
                    "max_employees": int(form_data.get("max_employees", 1)),
                    "notes": form_data.get("notes", ""),
                    "penalize_late_start": "penalize_late_start" in form_data and form_data.get("penalize_late_start") not in ["false", ""],
                    "shift_tasks": shift_tasks if shift_tasks else None
                }
                
                timeslot = await timeslot_service.create_timeslot_for_manager(timeslot_data, object_id, telegram_id)
                if not timeslot:
                    raise HTTPException(status_code=400, detail="Ошибка создания тайм-слота")
                
                logger.info(f"Created single timeslot {timeslot.id} for object {object_id} by manager {telegram_id}")
                
            elif creation_mode == "template":
                # Создание множественных тайм-слотов
                start_date = datetime.strptime(form_data.get("start_date"), "%Y-%m-%d").date()
                end_date = datetime.strptime(form_data.get("end_date"), "%Y-%m-%d").date()
                start_time = form_data.get("start_time_multi")
                end_time = form_data.get("end_time_multi")
                weekdays = form_data.getlist("weekdays")  # Получаем список выбранных дней недели
                alternation_type = form_data.get("alternation_type", "daily")
                
                # Валидация
                if not weekdays:
                    raise HTTPException(status_code=400, detail="Выберите хотя бы один день недели")
                
                if not start_time or not end_time:
                    raise HTTPException(status_code=400, detail="Укажите время начала и окончания")
                
                # Получаем ставку (используем ставку объекта если не указана)
                hourly_rate = obj.hourly_rate
                if form_data.get("hourly_rate_multi"):
                    hourly_rate = float(form_data.get("hourly_rate_multi"))
                
                max_employees = int(form_data.get("max_employees_multi", 1))
                notes = form_data.get("notes_multi", "")
                
                # Создаем тайм-слоты для выбранных дней недели в указанном диапазоне дат
                created_count = 0
                current_date = start_date
                
                while current_date <= end_date:
                    # Проверяем, нужно ли создавать тайм-слот для этого дня
                    weekday = current_date.weekday()  # 0=понедельник, 6=воскресенье
                    weekday_str = str(weekday)
                    
                    # Преобразуем воскресенье (6) в 0 для соответствия с формой
                    if weekday == 6:
                        weekday_str = "0"
                    
                    if weekday_str in weekdays:
                        # Создаем тайм-слот для этого дня
                        timeslot_data = {
                            "slot_date": current_date,
                            "start_time": start_time,
                            "end_time": end_time,
                            "hourly_rate": hourly_rate,
                            "max_employees": max_employees,
                            "notes": notes,
                            "penalize_late_start": "penalize_late_start" in form_data and form_data.get("penalize_late_start") not in ["false", ""],
                            "shift_tasks": shift_tasks if shift_tasks else None
                        }
                        
                        timeslot = await timeslot_service.create_timeslot_for_manager(timeslot_data, object_id, telegram_id)
                        if timeslot:
                            created_count += 1
                    
                    # Переходим к следующему дню
                    current_date += timedelta(days=1)
                
                if created_count == 0:
                    raise HTTPException(status_code=400, detail="Не удалось создать ни одного тайм-слота")
                
                logger.info(f"Created {created_count} timeslots for object {object_id} by manager {telegram_id}")
            
            return RedirectResponse(
                url=f"/manager/timeslots?object_id={object_id}",
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
            
            return templates.TemplateResponse(
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
            
            # Обработка задач (shift_tasks)
            shift_tasks = []
            task_texts = form_data.getlist("task_text[]")
            task_amounts = form_data.getlist("task_amount[]")
            
            for idx, text in enumerate(task_texts):
                if text.strip():
                    # Проверяем чекбоксы для обязательности и медиа-отчета
                    is_mandatory = f"task_mandatory_{idx}" in form_data
                    requires_media = f"task_media_{idx}" in form_data
                    
                    task = {
                        "description": text.strip(),
                        "amount": float(task_amounts[idx]) if idx < len(task_amounts) and task_amounts[idx] else 0.0,
                        "is_mandatory": is_mandatory,
                        "requires_media": requires_media
                    }
                    shift_tasks.append(task)
            
            timeslot_data = {
                "slot_date": datetime.strptime(form_data.get("slot_date"), "%Y-%m-%d").date(),
                "start_time": form_data.get("start_time"),
                "end_time": form_data.get("end_time"),
                "hourly_rate": float(form_data.get("hourly_rate")),
                "max_employees": int(form_data.get("max_employees", 1)),
                "notes": form_data.get("notes", ""),
                "penalize_late_start": "penalize_late_start" in form_data and form_data.get("penalize_late_start") not in ["false", ""],
                "shift_tasks": shift_tasks if shift_tasks else None
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


@router.post("/manager/timeslots/{timeslot_id}/delete")
async def manager_timeslots_delete(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Удаление тайм-слота для менеджера"""
    try:
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        
        async with get_async_session() as session:
            timeslot_service = TimeSlotService(session)
            
            # Получаем тайм-слот для получения object_id
            timeslot = await timeslot_service.get_timeslot_by_id_for_manager(timeslot_id, telegram_id)
            if not timeslot:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден или доступ запрещен")
            
            object_id = timeslot.object_id
            
            # Удаляем тайм-слот
            success = await timeslot_service.delete_timeslot_for_manager(timeslot_id, telegram_id)
            if not success:
                raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
            
            logger.info(f"Deleted timeslot {timeslot_id} by manager {telegram_id}")
            
            return RedirectResponse(
                url=f"/manager/timeslots?object_id={object_id}",
                status_code=303
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager_timeslots_delete: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления тайм-слота")


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
            object_id = form_data.get("object_id")
            
            for timeslot_id_str in timeslot_ids:
                try:
                    timeslot_id = int(timeslot_id_str)
                    success = await timeslot_service.delete_timeslot_for_manager(timeslot_id, telegram_id)
                    if success:
                        deleted_count += 1
                        if not object_id:
                            object_id = str((await timeslot_service.get_timeslot_by_id_for_manager(timeslot_id, telegram_id)).object_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid timeslot_id: {timeslot_id_str}")
                    continue
            
            logger.info(f"Bulk deleted {deleted_count} timeslots by manager {telegram_id}")
            redirect_url = f"/manager/timeslots?object_id={object_id}" if object_id else "/manager/timeslots"
            
            return RedirectResponse(
                url=redirect_url,
                status_code=303
            )
            
    except Exception as e:
        logger.error(f"Error in manager_timeslots_bulk_delete: {e}")
        raise HTTPException(status_code=500, detail="Ошибка удаления тайм-слотов")


@router.post("/manager/timeslots/bulk-edit")
async def manager_timeslots_bulk_edit(
    request: Request,
    current_user: dict = Depends(require_manager_or_owner)
):
    """Массовое редактирование тайм-слотов для менеджера"""
    try:
        telegram_id = current_user.get("id") if isinstance(current_user, dict) else current_user.telegram_id
        form_data = await request.form()

        object_id = form_data.get("object_id")
        timeslot_ids_str = form_data.get("timeslot_ids", "")
        date_from = form_data.get("date_from", "").strip()
        date_to = form_data.get("date_to", "").strip()

        start_time = form_data.get("start_time", "").strip()
        end_time = form_data.get("end_time", "").strip()
        hourly_rate_str = form_data.get("hourly_rate", "").strip()
        max_employees_str = form_data.get("max_employees", "").strip()
        set_active = "is_active" in form_data
        set_inactive = "is_inactive" in form_data

        date_from_obj = None
        date_to_obj = None

        if date_from and date_to:
            from datetime import date
            try:
                date_from_obj = date.fromisoformat(date_from)
                date_to_obj = date.fromisoformat(date_to)
                if date_from_obj > date_to_obj:
                    raise HTTPException(status_code=400, detail="Дата начала не может быть больше даты окончания")
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты")
        elif date_from or date_to:
            raise HTTPException(status_code=400, detail="Укажите обе даты периода или оставьте пустыми")

        update_params = {}

        from datetime import time
        if start_time:
            try:
                time.fromisoformat(start_time)
                update_params["start_time"] = start_time
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат времени начала")

        if end_time:
            try:
                time.fromisoformat(end_time)
                update_params["end_time"] = end_time
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат времени окончания")

        if start_time and end_time:
            if time.fromisoformat(start_time) >= time.fromisoformat(end_time):
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")

        if hourly_rate_str:
            try:
                hourly_rate = float(hourly_rate_str)
                if hourly_rate <= 0:
                    raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
                update_params["hourly_rate"] = hourly_rate
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ставки")

        if max_employees_str:
            try:
                max_employees = int(max_employees_str)
                if max_employees < 1:
                    raise HTTPException(status_code=400, detail="Лимит должен быть больше 0")
                update_params["max_employees"] = max_employees
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат лимита")

        if set_active and not set_inactive:
            update_params["is_active"] = True
        elif set_inactive and not set_active:
            update_params["is_active"] = False
        
        # Обработка новых полей: penalize_late_start / cancel_late_penalties
        if "penalize_late_start" in form_data:
            update_params["penalize_late_start"] = form_data.get("penalize_late_start") not in ["false", ""]
        # Отмена штрафов за опоздания имеет приоритет и принудительно отключает penalize_late_start
        if "cancel_late_penalties" in form_data:
            update_params["penalize_late_start"] = False
        
        # Обработка задач (shift_tasks) - новый формат с task_description_N
        shift_tasks = []
        task_index = 0
        while f"task_description_{task_index}" in form_data:
            task_desc = form_data.get(f"task_description_{task_index}", "").strip()
            if task_desc:
                task = {"description": task_desc}
                
                amount_str = form_data.get(f"task_amount_{task_index}", "").strip()
                if amount_str:
                    try:
                        task["amount"] = float(amount_str)
                    except ValueError:
                        pass
                
                task["is_mandatory"] = f"task_mandatory_{task_index}" in form_data
                task["requires_media"] = f"task_media_{task_index}" in form_data
                
                shift_tasks.append(task)
            task_index += 1
        
        if shift_tasks:
            update_params["shift_tasks"] = shift_tasks

        if not update_params:
            raise HTTPException(status_code=400, detail="Не указано ни одного параметра для изменения")

        if not object_id:
            raise HTTPException(status_code=400, detail="Не указан объект")

        async with get_async_session() as session:
            object_service = ObjectService(session)
            has_access = await object_service.get_object_by_id_for_manager(int(object_id), telegram_id)
            if not has_access:
                raise HTTPException(status_code=403, detail="Нет доступа к объекту")

            timeslot_service = TimeSlotService(session)

            if timeslot_ids_str:
                timeslot_ids = [int(ts_id.strip()) for ts_id in timeslot_ids_str.split(",") if ts_id.strip()]
                applicable_ids = []
                for ts_id in timeslot_ids:
                    slot = await timeslot_service.get_timeslot_by_id_for_manager(ts_id, telegram_id)
                    if not slot or slot.object_id != int(object_id):
                        continue
                    if date_from_obj and date_to_obj:
                        if not (date_from_obj <= slot.slot_date <= date_to_obj):
                            continue
                    applicable_ids.append((ts_id, slot.slot_date))
            else:
                raise HTTPException(status_code=400, detail="Не выбраны тайм-слоты для обновления")

            if not applicable_ids:
                raise HTTPException(status_code=400, detail="Нет подходящих тайм-слотов для обновления")

            updated_count = 0
            for ts_id, slot_date in applicable_ids:
                try:
                    slot = await timeslot_service.get_timeslot_by_id_for_manager(ts_id, telegram_id)
                    if not slot:
                        continue

                    slot_data = {
                        "slot_date": slot_date,
                        "start_time": update_params.get("start_time", slot.start_time.strftime("%H:%M")),
                        "end_time": update_params.get("end_time", slot.end_time.strftime("%H:%M")),
                        "hourly_rate": update_params.get("hourly_rate", slot.hourly_rate),
                        "max_employees": update_params.get("max_employees", slot.max_employees),
                        "is_active": update_params.get("is_active", slot.is_active),
                        "notes": slot.notes or "",
                        "penalize_late_start": update_params.get("penalize_late_start", slot.penalize_late_start if hasattr(slot, 'penalize_late_start') else True),
                        "ignore_object_tasks": update_params.get("ignore_object_tasks", slot.ignore_object_tasks if hasattr(slot, 'ignore_object_tasks') else False),
                        "shift_tasks": update_params.get("shift_tasks", slot.shift_tasks if hasattr(slot, 'shift_tasks') else None)
                    }
                    await timeslot_service.update_timeslot_for_manager(ts_id, slot_data, telegram_id)
                    updated_count += 1
                except Exception as ex:
                    logger.warning(f"Bulk update skipped for timeslot {ts_id}: {ex}")
                    continue

            logger.info(f"Bulk updated {updated_count} timeslots by manager {telegram_id}")

            return RedirectResponse(
                url=f"/manager/timeslots/object/{object_id}?success=bulk_updated&count={updated_count}",
                status_code=303
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manager_timeslots_bulk_edit: {e}")
        raise HTTPException(status_code=500, detail="Ошибка массового редактирования")
