"""
Роуты для управления тайм-слотами объектов
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.object_service import ObjectService, TimeSlotService
from apps.web.routes.owner import get_available_interfaces_for_user, get_user_id_from_current_user
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional
from datetime import time, date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def timeslots_all_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    object_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("slot_date"),
    sort_order: str = Query("desc")
):
    """Список всех тайм-слотов с фильтром по объектам"""
    try:
        logger.info(f"Loading all timeslots with filters: object_id={object_id}, date_from={date_from}, date_to={date_to}")
        
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        # Получаем все объекты владельца для фильтра
        all_objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
        # Если указан object_id, фильтруем по нему
        if object_id:
            obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
            if not obj:
                raise HTTPException(status_code=404, detail="Объект не найден")
            
            timeslots = await timeslot_service.get_timeslots_by_object(
                object_id, 
                current_user["telegram_id"],
                date_from=date_from,
                date_to=date_to,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            selected_object = {
                "id": obj.id,
                "name": obj.name,
                "address": obj.address or "",
                "hourly_rate": float(getattr(obj, "hourly_rate", 0) or 0)
            }
        else:
            # Показываем тайм-слоты всех объектов
            timeslots = []
            for obj in all_objects:
                obj_timeslots = await timeslot_service.get_timeslots_by_object(
                    obj.id, 
                    current_user["telegram_id"],
                    date_from=date_from,
                    date_to=date_to,
                    sort_by=sort_by,
                    sort_order=sort_order
                )
                timeslots.extend(obj_timeslots)
            
            selected_object = None
        
        # Преобразуем в формат для шаблона
        timeslots_data = []
        for slot in timeslots:
            # Получаем объект для каждого слота
            slot_obj = next((o for o in all_objects if o.id == slot.object_id), None)
            timeslots_data.append({
                "id": slot.id,
                "object_id": slot.object_id,
                "object_name": slot_obj.name if slot_obj else "Неизвестный объект",
                "slot_date": slot.slot_date.strftime("%Y-%m-%d"),
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else (float(slot_obj.hourly_rate) if slot_obj else 0),
                "max_employees": slot.max_employees,
                "is_active": slot.is_active,
                "created_at": slot.created_at.strftime("%Y-%m-%d")
            })
        
        # Список объектов для фильтра
        objects_list = [{"id": obj.id, "name": obj.name} for obj in all_objects]
        
        return templates.TemplateResponse("owner/timeslots/list_all.html", {
            "request": request,
            "title": "Тайм-слоты",
            "timeslots": timeslots_data,
            "objects": objects_list,
            "selected_object_id": object_id,
            "selected_object": selected_object,
            "current_user": current_user,
            "date_from": date_from,
            "date_to": date_to,
            "sort_by": sort_by,
            "sort_order": sort_order
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading timeslots: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки тайм-слотов")


@router.get("/object/{object_id}", response_class=HTMLResponse)
async def timeslots_list(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("slot_date"),
    sort_order: str = Query("desc")
):
    """Редирект на новый роут с фильтром по объекту"""
    # Формируем URL с query параметрами
    params = [f"object_id={object_id}"]
    if date_from:
        params.append(f"date_from={date_from}")
    if date_to:
        params.append(f"date_to={date_to}")
    params.append(f"sort_by={sort_by}")
    params.append(f"sort_order={sort_order}")
    
    redirect_url = f"/owner/timeslots?{'&'.join(params)}"
    return RedirectResponse(url=redirect_url, status_code=303)


@router.get("/object/{object_id}/old", response_class=HTMLResponse)
async def timeslots_list_old(
    request: Request,
    object_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    sort_by: str = Query("slot_date"),
    sort_order: str = Query("desc")
):
    """Старый список тайм-слотов объекта (deprecated, оставлен для совместимости)"""
    try:
        logger.info(f"Loading timeslots for object {object_id} with filters: date_from={date_from}, date_to={date_to}, sort_by={sort_by}, sort_order={sort_order}")
        
        # Получение информации об объекте и тайм-слотов из базы данных
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        # Получаем объект
        obj = await object_service.get_object_by_id(object_id, current_user["telegram_id"])
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем тайм-слоты с фильтрацией и сортировкой
        timeslots = await timeslot_service.get_timeslots_by_object(
            object_id, 
            current_user["telegram_id"],
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
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
            "address": obj.address or "",
            "hourly_rate": float(getattr(obj, "hourly_rate", 0) or 0),
            "opening_time": getattr(obj, "opening_time", None).strftime("%H:%M") if getattr(obj, "opening_time", None) else "",
            "closing_time": getattr(obj, "closing_time", None).strftime("%H:%M") if getattr(obj, "closing_time", None) else ""
        }
        
        return templates.TemplateResponse("owner/timeslots/list.html", {
            "request": request,
            "title": f"Тайм-слоты: {object_data['name']}",
            "timeslots": timeslots_data,
            "object_id": object_id,
            "object": object_data,
            "current_user": current_user,
            "date_from": date_from,
            "date_to": date_to,
            "sort_by": sort_by,
            "sort_order": sort_order
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
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        try:
            telegram_id = int(telegram_id)
        except Exception:
            pass
        obj = await object_service.get_object_by_id(object_id, telegram_id)
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем все объекты пользователя для мульти-выбора
        all_objects = await object_service.get_objects_by_owner(telegram_id, include_inactive=False)
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
        # Гарантируем наличие текущего объекта в списке выбора
        if not any(o.get("id") == object_id for o in objects_data):
            objects_data.append({
                "id": obj.id,
                "name": obj.name,
                "address": obj.address or "",
                "hourly_rate": float(getattr(obj, "hourly_rate", 0) or 0),
                "opening_time": getattr(obj, "opening_time", None).strftime("%H:%M") if getattr(obj, "opening_time", None) else "",
                "closing_time": getattr(obj, "closing_time", None).strftime("%H:%M") if getattr(obj, "closing_time", None) else ""
            })
        
        # Ранее здесь подгружались шаблоны планирования — удалено
        
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
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        try:
            telegram_id = int(telegram_id)
        except Exception:
            pass
        creation_mode = form_data.get("creation_mode", "single")
        # Интервалы времени (могут быть несколько)
        interval_starts = form_data.getlist("interval_start")
        interval_ends = form_data.getlist("interval_end")
        hourly_rate_str = form_data.get("hourly_rate", "0")
        max_employees_str = form_data.get("max_employees", "1")
        is_active = "is_active" in form_data
        slot_date_str = form_data.get("slot_date", "")
        series_start_date_str = form_data.get("series_start_date", "")
        series_end_date_str = form_data.get("series_end_date", "")
        weekdays_raw = form_data.getlist("weekdays")  # опционально
        
        # Получаем выбранные объекты
        selected_objects = list({x for x in form_data.getlist("selected_objects") if str(x).strip() != ""})
        logger.warning(f"TimeslotsCreate payload: mode={creation_mode}, slot_date={slot_date_str}, series=({series_start_date_str},{series_end_date_str}), weekdays={weekdays_raw}, starts={interval_starts}, ends={interval_ends}, objects={selected_objects}, rate='{hourly_rate_str}', max_emp='{max_employees_str}'")
        if not selected_objects:
            # Фолбек: если нет выбранных объектов, используем текущий объект
            selected_objects = [str(object_id)]
            logger.info(f"No objects selected, using current object {object_id}")
        
        # Валидация и преобразование данных
        try:
            # поддержка запятой и десятичной ставки
            hourly_rate = float(hourly_rate_str.replace(',', '.'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ставки")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        try:
            max_employees = int(max_employees_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат лимита сотрудников")
        if max_employees < 1:
            raise HTTPException(status_code=400, detail="Лимит сотрудников должен быть >= 1")
        
        # Валидация интервалов времени
        if not interval_starts or not interval_ends:
            raise HTTPException(status_code=400, detail="Нужно указать хотя бы один интервал времени")
        parsed_intervals = []
        def _normalize_time_str(t: str) -> str:
            t = (t or "").strip()
            if not t:
                return t
            parts = t.split(":")
            if len(parts) < 2:
                # невалидно
                return ""
            h, m = parts[0].strip(), parts[1].strip()
            # поддержка HH:MM:SS — игнорируем секунды
            if len(parts) >= 3 and parts[2].strip():
                sec = parts[2].strip()
                if not sec.isdigit():
                    return ""
            if not h.isdigit() or not m.isdigit():
                return ""
            h_i, m_i = int(h), int(m)
            if h_i < 0 or h_i > 23 or m_i < 0 or m_i > 59:
                return ""
            return f"{h_i:02d}:{m_i:02d}"
        logger.info(f"Intervals raw: starts={interval_starts}, ends={interval_ends}")
        for s, e in zip(interval_starts, interval_ends):
            # Пропускаем пустые строки (например, незаполненные поля)
            s_n = _normalize_time_str(s)
            e_n = _normalize_time_str(e)
            if not s_n or not e_n:
                continue
            try:
                s_time = time.fromisoformat(s_n)
                e_time = time.fromisoformat(e_n)
            except ValueError:
                logger.error(f"Invalid time format: s='{s}', e='{e}', normalized s='{s_n}', e='{e_n}'")
                raise HTTPException(status_code=400, detail="Неверный формат времени")
            if s_time >= e_time:
                raise HTTPException(status_code=400, detail="Время начала должно быть меньше времени окончания")
            parsed_intervals.append((s_n, e_n))
        if not parsed_intervals:
            raise HTTPException(status_code=400, detail="Нужно указать хотя бы один валидный интервал времени")
        
        # Обработка задач тайм-слота
        penalize_late_start = "penalize_late_start" in form_data
        ignore_object_tasks = "ignore_object_tasks" in form_data
        
        task_texts = form_data.getlist("task_texts[]")
        task_amounts = form_data.getlist("task_amounts[]")
        task_mandatory_indices = [int(i) for i in form_data.getlist("task_mandatory[]")]
        task_media_indices = [int(i) for i in form_data.getlist("task_requires_media[]")]
        
        shift_tasks = []
        for idx, text in enumerate(task_texts):
            if text.strip():
                amount = float(task_amounts[idx]) if idx < len(task_amounts) and task_amounts[idx] else 0
                task = {
                    "text": text.strip(),
                    "is_mandatory": idx in task_mandatory_indices,
                    "requires_media": idx in task_media_indices,
                    "bonus_amount": amount if amount >= 0 else 0,
                    "deduction_amount": abs(amount) if amount < 0 else 0
                }
                shift_tasks.append(task)
        
        created_count = 0
        timeslot_service = TimeSlotService(db)

        # Считаем предполагаемое количество для лимита
        def count_days(start_d: date, end_d: date, weekdays: list[int]) -> int:
            if start_d > end_d:
                return 0
            total = 0
            cur = start_d
            while cur <= end_d:
                if not weekdays or ((cur.weekday()) in weekdays):
                    total += 1
                cur += timedelta(days=1)
            return total

        if creation_mode == "series":
            # Диапазон дат
            try:
                start_d = date.fromisoformat(series_start_date_str)
                end_d = date.fromisoformat(series_end_date_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат дат серии")
            if start_d > end_d:
                raise HTTPException(status_code=400, detail="Дата начала серии должна быть меньше или равна дате окончания")

            try:
                weekdays = [int(x) for x in weekdays_raw if str(x).strip() != ""]
            except ValueError:
                weekdays = []

            total_estimated = len(selected_objects) * len(parsed_intervals) * count_days(start_d, end_d, weekdays)
            if total_estimated > 1000:
                raise HTTPException(status_code=400, detail="Лимит: не более 1000 тайм-слотов за один раз")

            # Итерируем даты и объекты
            cur = start_d
            while cur <= end_d:
                if not weekdays or (cur.weekday() in weekdays):
                    for obj_id in selected_objects:
                        for s, e in parsed_intervals:
                            try:
                                timeslot_data = {
                                    "slot_date": cur,
                                    "start_time": s,
                                    "end_time": e,
                                    "hourly_rate": hourly_rate,
                                    "max_employees": max_employees,
                                    "is_active": is_active,
                                    "penalize_late_start": penalize_late_start,
                                    "ignore_object_tasks": ignore_object_tasks,
                                    "shift_tasks": shift_tasks if shift_tasks else None
                                }
                                new_timeslot = await timeslot_service.create_timeslot(timeslot_data, int(obj_id), telegram_id)
                                if new_timeslot:
                                    created_count += 1
                            except Exception as e:
                                logger.error(f"Error creating timeslot for object {obj_id} on {cur}: {e}")
                                continue
                cur += timedelta(days=1)
        else:
            # Один день
            if not slot_date_str:
                raise HTTPException(status_code=400, detail="Не указана дата")
            try:
                slot_d = date.fromisoformat(slot_date_str)
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат даты")

            total_estimated = len(selected_objects) * len(parsed_intervals)
            if total_estimated > 1000:
                raise HTTPException(status_code=400, detail="Лимит: не более 1000 тайм-слотов за один раз")

            for obj_id in selected_objects:
                for s, e in parsed_intervals:
                    try:
                        timeslot_data = {
                            "slot_date": slot_d,
                            "start_time": s,
                            "end_time": e,
                            "hourly_rate": hourly_rate,
                            "max_employees": max_employees,
                            "is_active": is_active,
                            "penalize_late_start": penalize_late_start,
                            "ignore_object_tasks": ignore_object_tasks,
                            "shift_tasks": shift_tasks if shift_tasks else None
                        }
                        new_timeslot = await timeslot_service.create_timeslot(timeslot_data, int(obj_id), telegram_id)
                        if new_timeslot:
                            created_count += 1
                            logger.info(f"Timeslot {new_timeslot.id} created for object {obj_id}")
                    except Exception as e:
                        logger.error(f"Error creating timeslot for object {obj_id}: {e}")
                        continue
        
        if created_count == 0:
            raise HTTPException(status_code=400, detail="Не удалось создать ни одного тайм-слота")
        
        logger.info(f"Created {created_count} timeslots for {len(selected_objects)} objects")
        
        return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
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
        # Проверяем, что current_user - это словарь, а не RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        # Получение тайм-слота из базы данных
        timeslot_service = TimeSlotService(db)
        object_service = ObjectService(db)
        
        # Получаем тайм-слот с проверкой владельца
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
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
            "slot_date": timeslot.slot_date.strftime("%Y-%m-%d"),
            "start_time": timeslot.start_time.strftime("%H:%M"),
            "end_time": timeslot.end_time.strftime("%H:%M"),
            "hourly_rate": float(timeslot.hourly_rate) if timeslot.hourly_rate else float(obj.hourly_rate),
            "max_employees": timeslot.max_employees or 1,
            "is_active": timeslot.is_active
        }
        
        object_data = {
            "id": obj.id,
            "name": obj.name,
            "address": obj.address or "",
            "hourly_rate": float(obj.hourly_rate) if obj.hourly_rate else 0,
            "opening_time": obj.opening_time.strftime("%H:%M") if obj.opening_time else "00:00",
            "closing_time": obj.closing_time.strftime("%H:%M") if obj.closing_time else "23:59",
            "max_distance": obj.max_distance_meters or 0
        }
        
        # Получаем задачи тайм-слота
        from domain.entities.timeslot_task_template import TimeslotTaskTemplate
        tasks_query = select(TimeslotTaskTemplate).where(
            TimeslotTaskTemplate.timeslot_id == timeslot_id
        ).order_by(TimeslotTaskTemplate.display_order)
        tasks_result = await db.execute(tasks_query)
        timeslot_tasks = tasks_result.scalars().all()
        
        # Получаем данные для переключения интерфейсов
        user_id = await get_user_id_from_current_user(current_user, db)
        available_interfaces = await get_available_interfaces_for_user(user_id)
        
        return templates.TemplateResponse("owner/timeslots/edit.html", {
            "request": request,
            "title": f"Редактирование тайм-слота: {object_data['name']}",
            "timeslot": timeslot_data,
            "object_id": timeslot.object_id,
            "object": object_data,
            "timeslot_tasks": timeslot_tasks,
            "current_user": current_user,
            "available_interfaces": available_interfaces
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
            # Преобразуем через float, чтобы поддержать формат "500.0"
            hourly_rate = int(float(hourly_rate_str))
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
        
        # Обработка задач тайм-слота
        task_ids = form_data.getlist("task_ids[]")
        task_texts = form_data.getlist("task_texts[]")
        
        if task_texts:
            from domain.entities.timeslot_task_template import TimeslotTaskTemplate
            from domain.entities.user import User
            
            # Получить внутренний ID пользователя
            telegram_id = current_user.get("telegram_id") or current_user.get("id")
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await db.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            user_id = user_obj.id if user_obj else None
            
            # Удалить все существующие задачи тайм-слота
            delete_query = select(TimeslotTaskTemplate).where(
                TimeslotTaskTemplate.timeslot_id == timeslot_id
            )
            delete_result = await db.execute(delete_query)
            old_tasks = delete_result.scalars().all()
            for old_task in old_tasks:
                await db.delete(old_task)
            
            # Создать новые задачи
            for idx, task_text in enumerate(task_texts):
                if task_text.strip():  # Пропускаем пустые
                    new_task = TimeslotTaskTemplate(
                        timeslot_id=timeslot_id,
                        task_text=task_text.strip(),
                        display_order=idx,
                        created_by_id=user_id
                    )
                    db.add(new_task)
            
            await db.commit()
            
            logger.info(f"Timeslot {timeslot_id} tasks updated: {len([t for t in task_texts if t.strip()])} tasks")
        
        logger.info(f"Timeslot {timeslot_id} updated successfully")
        
        return RedirectResponse(url=f"/owner/timeslots/object/{updated_timeslot.object_id}", status_code=status.HTTP_302_FOUND)
        
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
        
        return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        
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
            return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
        ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
        if not ids:
            return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)

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
        return RedirectResponse(url=f"/owner/timeslots/object/{object_id}", status_code=status.HTTP_302_FOUND)
    except Exception as e:
        logger.error(f"Error bulk deleting timeslots: {e}")
        raise HTTPException(status_code=500, detail="Ошибка массового удаления тайм-слотов")