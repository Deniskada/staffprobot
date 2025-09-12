"""
Роуты для календарного планирования
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from apps.web.dependencies import get_current_user_dependency, require_role
from apps.web.services.object_service import ObjectService, TimeSlotService
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta, time
from sqlalchemy.ext.asyncio import AsyncSession
import calendar

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

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Календарный вид планирования"""
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
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        objects = await object_service.get_objects_by_owner(current_user.telegram_id)
        
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
            timeslots = await timeslot_service.get_timeslots_by_object(selected_object.id, current_user.telegram_id)
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
                timeslots = await timeslot_service.get_timeslots_by_object(obj.id, current_user.telegram_id)
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
        calendar_data = _create_calendar_grid(year, month, timeslots_data)
        
        # Подготавливаем данные для шаблона
        objects_list = [{"id": obj.id, "name": obj.name} for obj in objects]
        
        # Навигация по месяцам
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        
        return templates.TemplateResponse("calendar/index.html", {
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


def _create_calendar_grid(year: int, month: int, timeslots: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Создает календарную сетку с тайм-слотами"""
    # Получаем первый день месяца и количество дней
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])
    
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
                if slot["date"] == current_date and slot["is_active"]
            ]
            
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


@router.get("/week", response_class=HTMLResponse)
async def week_view(
    request: Request,
    year: int = Query(None),
    week: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Недельный вид календаря"""
    try:
        # Определяем текущую неделю или переданные параметры
        today = date.today()
        if year is None:
            year = today.year
        if week is None:
            # Получаем номер недели для текущей даты
            week = today.isocalendar()[1]
        
        # Получаем первый день недели (понедельник)
        first_day_of_year = date(year, 1, 1)
        first_monday = first_day_of_year - timedelta(days=first_day_of_year.weekday())
        week_start = first_monday + timedelta(weeks=week-1)
        
        # Создаем список дней недели
        week_days = []
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            week_days.append(current_date)
        
        # Получаем объекты и тайм-слоты (аналогично месячному виду)
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        objects = await object_service.get_objects_by_owner(current_user.telegram_id)
        
        selected_object = None
        if object_id:
            for obj in objects:
                if obj.id == object_id:
                    selected_object = obj
                    break
            if not selected_object:
                raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Получаем тайм-слоты для недели
        timeslots_data = []
        if selected_object:
            timeslots = await timeslot_service.get_timeslots_by_object(selected_object.id, current_user.telegram_id)
            for slot in timeslots:
                if week_start <= slot.slot_date <= week_days[-1]:
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
            for obj in objects:
                timeslots = await timeslot_service.get_timeslots_by_object(obj.id, current_user.telegram_id)
                for slot in timeslots:
                    if week_start <= slot.slot_date <= week_days[-1]:
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
        
        # Группируем тайм-слоты по дням
        week_data = []
        for day_date in week_days:
            day_timeslots = [
                slot for slot in timeslots_data 
                if slot["date"] == day_date and slot["is_active"]
            ]
            week_data.append({
                "date": day_date,
                "is_today": day_date == today,
                "timeslots": day_timeslots,
                "timeslots_count": len(day_timeslots)
            })
        
        # Навигация по неделям
        prev_week = week - 1 if week > 1 else 52
        prev_year = year if week > 1 else year - 1
        next_week = week + 1 if week < 52 else 1
        next_year = year if week < 52 else year + 1
        
        objects_list = [{"id": obj.id, "name": obj.name} for obj in objects]
        
        return templates.TemplateResponse("calendar/week.html", {
            "request": request,
            "title": "Недельное планирование",
            "current_user": current_user,
            "year": year,
            "week": week,
            "week_data": week_data,
            "week_start": week_start,
            "week_end": week_days[-1],
            "objects": objects_list,
            "selected_object_id": object_id,
            "selected_object": selected_object,
            "prev_week": prev_week,
            "prev_year": prev_year,
            "next_week": next_week,
            "next_year": next_year,
            "today": today
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading week view: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки недельного вида")


@router.get("/analysis", response_class=HTMLResponse)
async def gap_analysis(
    request: Request,
    object_id: int = Query(None),
    days: int = Query(30),
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Анализ пробелов в планировании"""
    try:
        # Получаем объекты и тайм-слоты
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        objects = await object_service.get_objects_by_owner(current_user.telegram_id)
        
        selected_object = None
        if object_id:
            for obj in objects:
                if obj.id == object_id:
                    selected_object = obj
                    break
            if not selected_object:
                raise HTTPException(status_code=404, detail="Объект не найден")
        
        # Анализируем пробелы
        analysis_data = await _analyze_gaps(
            timeslot_service, 
            objects if not selected_object else [selected_object], 
            current_user.telegram_id, 
            days
        )
        
        objects_list = [{"id": obj.id, "name": obj.name} for obj in objects]
        
        return templates.TemplateResponse("calendar/analysis.html", {
            "request": request,
            "title": "Анализ пробелов в планировании",
            "current_user": current_user,
            "objects": objects_list,
            "selected_object_id": object_id,
            "selected_object": selected_object,
            "analysis_data": analysis_data,
            "days": days
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading gap analysis: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки анализа пробелов")


async def _analyze_gaps(
    timeslot_service: TimeSlotService, 
    objects: List, 
    telegram_id: int, 
    days: int
) -> Dict[str, Any]:
    """Анализирует пробелы в планировании"""
    today = date.today()
    end_date = today + timedelta(days=days)
    
    total_gaps = 0
    object_gaps = {}
    
    for obj in objects:
        timeslots = await timeslot_service.get_timeslots_by_object(obj.id, telegram_id)
        
        # Группируем тайм-слоты по дням
        daily_slots = {}
        for slot in timeslots:
            if today <= slot.slot_date <= end_date and slot.is_active:
                if slot.slot_date not in daily_slots:
                    daily_slots[slot.slot_date] = []
                daily_slots[slot.slot_date].append(slot)
        
        # Анализируем пробелы для каждого дня
        gaps = []
        current_date = today
        while current_date <= end_date:
            if current_date not in daily_slots:
                gaps.append({
                    "date": current_date,
                    "type": "no_slots",
                    "message": "Нет тайм-слотов на этот день"
                })
                total_gaps += 1
            else:
                # Проверяем покрытие рабочего времени
                slots = daily_slots[current_date]
                slots.sort(key=lambda x: x.start_time)
                
                # Здесь можно добавить логику анализа покрытия рабочего времени
                # Например, проверка на пробелы между тайм-слотами
                
            current_date += timedelta(days=1)
        
        object_gaps[obj.id] = {
            "object_name": obj.name,
            "gaps": gaps,
            "gaps_count": len(gaps)
        }
    
    return {
        "total_gaps": total_gaps,
        "object_gaps": object_gaps,
        "period": f"{today.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    }


@router.post("/api/quick-create-timeslot")
async def quick_create_timeslot(
    request: Request,
    object_id: int = Form(...),
    slot_date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    hourly_rate: int = Form(...),
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Быстрое создание тайм-слота через drag & drop"""
    try:
        # Валидация данных
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
        
        # Создание тайм-слота
        timeslot_service = TimeSlotService(db)
        timeslot_data = {
            "slot_date": slot_date_obj,
            "start_time": start_time,
            "end_time": end_time,
            "hourly_rate": hourly_rate,
            "is_active": True
        }
        
        new_timeslot = await timeslot_service.create_timeslot(timeslot_data, object_id, current_user.telegram_id)
        if not new_timeslot:
            raise HTTPException(status_code=404, detail="Объект не найден или нет доступа")
        
        # Получаем информацию об объекте для ответа
        object_service = ObjectService(db)
        obj = await object_service.get_object_by_id(object_id, current_user.telegram_id)
        
        return JSONResponse({
            "success": True,
            "timeslot": {
                "id": new_timeslot.id,
                "object_id": new_timeslot.object_id,
                "object_name": obj.name if obj else "Неизвестный объект",
                "date": new_timeslot.slot_date.strftime("%Y-%m-%d"),
                "start_time": new_timeslot.start_time.strftime("%H:%M"),
                "end_time": new_timeslot.end_time.strftime("%H:%M"),
                "hourly_rate": float(new_timeslot.hourly_rate) if new_timeslot.hourly_rate else 0,
                "is_active": new_timeslot.is_active
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating quick timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тайм-слота: {str(e)}")


@router.delete("/api/timeslot/{timeslot_id}")
async def delete_timeslot_api(
    timeslot_id: int,
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление тайм-слота через API"""
    try:
        timeslot_service = TimeSlotService(db)
        success = await timeslot_service.delete_timeslot(timeslot_id, current_user.telegram_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден или нет доступа")
        
        return JSONResponse({"success": True})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting timeslot: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тайм-слота: {str(e)}")


@router.get("/api/objects")
async def get_objects_api(
    current_user: dict = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Получение списка объектов для drag & drop"""
    try:
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(current_user.telegram_id)
        
        objects_data = []
        for obj in objects:
            objects_data.append({
                "id": obj.id,
                "name": obj.name,
                "hourly_rate": float(obj.hourly_rate),
                "opening_time": obj.opening_time.strftime("%H:%M") if obj.opening_time else "09:00",
                "closing_time": obj.closing_time.strftime("%H:%M") if obj.closing_time else "21:00"
            })
        
        return objects_data
        
    except Exception as e:
        logger.error(f"Error getting objects: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки объектов")


@router.get("/api/timeslots-status")
async def get_timeslots_status(
    year: int = Query(...),
    month: int = Query(...),
    object_id: Optional[int] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user_dependency()),
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
        
        # Получаем объекты владельца
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


@router.get("/api/timeslot/{timeslot_id}")
async def get_timeslot_details(
    timeslot_id: int,
    current_user: Optional[dict] = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"])),
    db: AsyncSession = Depends(get_db_session)
):
    """Детали конкретного тайм-слота: слот, запланированные и фактические смены."""
    try:
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from domain.entities.time_slot import TimeSlot
        from domain.entities.object import Object
        from domain.entities.user import User
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift import Shift

        # Владелец по текущему пользователю
        if not current_user or not getattr(current_user, "telegram_id", None):
            raise HTTPException(status_code=403, detail="Нет доступа")
        owner_q = select(User).where(User.telegram_id == current_user.telegram_id)
        owner = (await db.execute(owner_q)).scalar_one_or_none()
        if not owner:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Слот + проверка принадлежности через объект
        slot_q = select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id)
        slot = (await db.execute(slot_q)).scalar_one_or_none()
        if not slot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        obj_q = select(Object).where(Object.id == slot.object_id, Object.owner_id == owner.id)
        if (await db.execute(obj_q)).scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Нет доступа к тайм-слоту")

        # Запланированные смены по тайм-слоту
        sched_q = select(ShiftSchedule).options(selectinload(ShiftSchedule.user)).where(ShiftSchedule.time_slot_id == timeslot_id).order_by(ShiftSchedule.planned_start)
        sched = (await db.execute(sched_q)).scalars().all()
        scheduled = [
            {
                "id": s.id,
                "user_id": s.user_id,
                "user_name": f"{s.user.first_name} {s.user.last_name or ''}".strip() if s.user else None,
                "status": s.status,
                "start_time": s.planned_start.time().strftime("%H:%M"),
                "end_time": s.planned_end.time().strftime("%H:%M"),
                "notes": s.notes,
            }
            for s in sched
        ]

        # Фактические смены: сначала связанные с тайм-слотом напрямую
        act_q = select(Shift).options(selectinload(Shift.user)).where(Shift.time_slot_id == timeslot_id).order_by(Shift.start_time)
        acts_linked = (await db.execute(act_q)).scalars().all()

        # Плюс спонтанные/несвязанные: по объекту и дате слота, с пересечением времени
        day_start = datetime.combine(slot.slot_date, time.min)
        day_end = datetime.combine(slot.slot_date, time.max)
        act_day_q = select(Shift).options(selectinload(Shift.user)).where(
            and_(
                Shift.object_id == slot.object_id,
                Shift.start_time >= day_start,
                Shift.start_time <= day_end,
            )
        ).order_by(Shift.start_time)
        acts_day = (await db.execute(act_day_q)).scalars().all()

        # Отбираем пересекающиеся по времени и не дублируем
        def is_overlap(sh: Shift) -> bool:
            sh_start = sh.start_time.time()
            sh_end = sh.end_time.time() if sh.end_time else None
            if sh_end is None:
                return sh_start < slot.end_time
            return (sh_start < slot.end_time) and (slot.start_time < sh_end)

        linked_ids = {sh.id for sh in acts_linked}
        acts_overlap = [sh for sh in acts_day if (sh.id not in linked_ids) and is_overlap(sh)]

        acts_all = acts_linked + acts_overlap
        actual = [
            {
                "id": sh.id,
                "user_id": sh.user_id,
                "user_name": f"{sh.user.first_name} {sh.user.last_name or ''}".strip() if sh.user else None,
                "status": sh.status,
                "start_time": sh.start_time.time().strftime("%H:%M"),
                "end_time": sh.end_time.time().strftime("%H:%M") if sh.end_time else None,
                "total_hours": float(sh.total_hours) if sh.total_hours else None,
                "total_payment": float(sh.total_payment) if sh.total_payment else None,
                "is_planned": sh.is_planned,
                "notes": sh.notes,
            }
            for sh in acts_all
        ]

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
            "scheduled": scheduled,
            "actual": actual,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeslot details: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки деталей тайм-слота")