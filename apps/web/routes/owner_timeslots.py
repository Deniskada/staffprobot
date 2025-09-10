"""
Роуты для управления тайм-слотами объектов
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.object_service import ObjectService, TimeSlotService
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional
from datetime import time, date
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/object/{object_id}", response_class=HTMLResponse)
async def timeslots_list(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Список тайм-слотов объекта"""
    try:
        # Получение информации об объекте и тайм-слотов из базы данных
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        # Получаем объект
        obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем тайм-слоты
        timeslots = await timeslot_service.get_timeslots_by_object(object_id, current_user["telegram_id"])
        
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


@router.get("/object/{object_id}/create", response_class=HTMLResponse)
async def create_timeslot_form(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма создания тайм-слота"""
    try:
        # Получение информации об объекте из базы данных
        object_service = ObjectService(db)
        obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем все объекты пользователя для мульти-выбора
        all_objects = await object_service.get_objects_by_owner(current_user["telegram_id"], include_inactive=False)
        objects_data = []
        for obj_item in all_objects:
            objects_data.append({
                "id": obj_item.id,
                "name": obj_item.name,
                "address": obj_item.address or "",
                "hourly_rate": float(obj_item.hourly_rate),
                "opening_time": obj_item.opening_time.strftime("%H:%M"),
                "closing_time": obj_item.closing_time.strftime("%H:%M")
            })
        
        # Получаем шаблоны планирования
        from apps.web.services.template_service import TemplateService
        template_service = TemplateService(db)
        planning_templates = await template_service.get_templates_by_owner(current_user["telegram_id"])
        templates_data = []
        for template in planning_templates:
            templates_data.append({
                "id": template.id,
                "name": template.name,
                "description": template.description or "",
                "start_time": template.start_time,
                "end_time": template.end_time,
                "hourly_rate": template.hourly_rate,
                "is_public": template.is_public
            })
        
        object_data = {
            "id": obj.id,
            "name": obj.name,
            "address": obj.address or ""
        }
        
        return templates.TemplateResponse("owner/timeslots/create.html", {
            "request": request,
            "title": f"Создание тайм-слотов",
            "object_id": object_id,
            "object": object_data,
            "all_objects": objects_data,
            "templates": templates_data,
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
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание новых тайм-слотов"""
    try:
        logger.info(f"Creating timeslots for object {object_id}")
        
        # Получение данных формы
        form_data = await request.form()
        start_time = form_data.get("start_time", "")
        end_time = form_data.get("end_time", "")
        hourly_rate_str = form_data.get("hourly_rate", "0")
        template_id_str = form_data.get("template_id", "")
        start_date_str = form_data.get("start_date", "")
        end_date_str = form_data.get("end_date", "")
        
        # Получаем выбранные объекты
        selected_objects = form_data.getlist("selected_objects")
        if not selected_objects:
            raise HTTPException(status_code=400, detail="Не выбрано ни одного объекта")
        
        # Валидация и преобразование данных
        try:
            hourly_rate = int(hourly_rate_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ставки")
        
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
        
        # Если выбран шаблон и задан диапазон дат — применяем шаблон
        created_count = 0
        if template_id_str and start_date_str and end_date_str:
            try:
                from apps.web.services.template_service import TemplateService
                template_service = TemplateService(db)
                start_date_parsed = date.fromisoformat(start_date_str)
                end_date_parsed = date.fromisoformat(end_date_str)
                apply_result = await template_service.apply_template_to_objects(
                    template_id=int(template_id_str),
                    start_date=start_date_parsed,
                    end_date=end_date_parsed,
                    object_ids=selected_objects,
                    owner_telegram_id=current_user["telegram_id"],
                    start_time_override=start_time or None,
                    end_time_override=end_time or None,
                    hourly_rate_override=hourly_rate,
                )
                if not apply_result.get("success"):
                    raise HTTPException(status_code=400, detail=apply_result.get("error", "Ошибка применения шаблона"))
                created_count = apply_result.get("created_slots_count", 0)
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат дат")
        else:
            # Иначе создаем одиночные слоты по введенным времени/ставке на сегодня
            timeslot_service = TimeSlotService(db)
            for obj_id in selected_objects:
                try:
                    timeslot_data = {
                        "slot_date": date.today(),
                        "start_time": start_time,
                        "end_time": end_time,
                        "hourly_rate": hourly_rate,
                        "is_active": True
                    }
                    new_timeslot = await timeslot_service.create_timeslot(timeslot_data, int(obj_id), current_user["telegram_id"])
                    if new_timeslot:
                        created_count += 1
                        logger.info(f"Timeslot {new_timeslot.id} created for object {obj_id}")
                except Exception as e:
                    logger.error(f"Error creating timeslot for object {obj_id}: {e}")
                    continue
        
        if created_count == 0:
            raise HTTPException(status_code=400, detail="Не удалось создать ни одного тайм-слота")
        
        logger.info(f"Created {created_count} timeslots for {len(selected_objects)} objects")
        
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating timeslots: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слотов: {str(e)}")


@router.get("/{timeslot_id}/edit", response_class=HTMLResponse)
async def edit_timeslot_form(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Форма редактирования тайм-слота"""
    try:
        # Получение тайм-слота из базы данных
        timeslot_service = TimeSlotService(db)
        object_service = ObjectService(db)
        
        # Получаем тайм-слот с проверкой владельца
        timeslot = await timeslot_service.get_timeslot_by_id(timeslot_id, current_user["telegram_id"])
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Получаем объект
        obj = await object_service.get_object_by_id(timeslot.object_id, current_user["telegram_id"])
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


@router.post("/{timeslot_id}/edit")
async def update_timeslot(
    request: Request,
    timeslot_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление тайм-слота"""
    try:
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
        
        updated_timeslot = await timeslot_service.update_timeslot(timeslot_id, timeslot_data, current_user["telegram_id"])
        if not updated_timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
        
        logger.info(f"Timeslot {timeslot_id} updated successfully")
        
        return RedirectResponse(url=f"/timeslots/object/{updated_timeslot.object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления тайм-слота: {str(e)}")


@router.post("/{timeslot_id}/delete")
async def delete_timeslot(
    timeslot_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление тайм-слота"""
    try:
        logger.info(f"Deleting timeslot {timeslot_id}")
        
        # Удаление тайм-слота из базы данных
        timeslot_service = TimeSlotService(db)
        
        # Получаем тайм-слот для получения object_id
        timeslot = await timeslot_service.get_timeslot_by_id(timeslot_id, current_user["telegram_id"])
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        object_id = timeslot.object_id
        
        # Удаляем тайм-слот
        success = await timeslot_service.delete_timeslot(timeslot_id, current_user["telegram_id"])
        if not success:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
        
        logger.info(f"Timeslot {timeslot_id} deleted successfully")
        
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тайм-слота: {str(e)}")


@router.post("/bulk-delete")
async def bulk_delete_timeslots(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Множественное удаление тайм-слотов"""
    try:
        form_data = await request.form()
        object_id = int(form_data.get("object_id", 0))
        ids_str = form_data.get("timeslot_ids", "")
        if not ids_str:
            return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
        if not ids:
            return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)

        timeslot_service = TimeSlotService(db)
        deleted = 0
        for ts_id in ids:
            try:
                ts = await timeslot_service.get_timeslot_by_id(ts_id, current_user["telegram_id"])
                if ts:
                    ok = await timeslot_service.delete_timeslot(ts_id, current_user["telegram_id"])
                    if ok:
                        deleted += 1
            except Exception as e:
                logger.error(f"Error bulk deleting {ts_id}: {e}")
                continue

        logger.info(f"Bulk deleted {deleted}/{len(ids)} timeslots for object {object_id}")
        return RedirectResponse(url=f"/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error bulk deleting timeslots: {e}")
        raise HTTPException(status_code=500, detail="Ошибка массового удаления тайм-слотов")