"""
Роуты для календарного планирования
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.services.object_service import ObjectService, TimeSlotService
from core.database.session import get_db_session
from core.logging.logger import logger
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import calendar

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def calendar_view(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(require_owner_or_superadmin),
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
        
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
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
            timeslots = await timeslot_service.get_timeslots_by_object(selected_object.id, current_user["telegram_id"])
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
                timeslots = await timeslot_service.get_timeslots_by_object(obj.id, current_user["telegram_id"])
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
            "month_name": calendar.month_name[month],
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
    current_user: dict = Depends(require_owner_or_superadmin),
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
        
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
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
            timeslots = await timeslot_service.get_timeslots_by_object(selected_object.id, current_user["telegram_id"])
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
                timeslots = await timeslot_service.get_timeslots_by_object(obj.id, current_user["telegram_id"])
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
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Анализ пробелов в планировании"""
    try:
        # Получаем объекты и тайм-слоты
        object_service = ObjectService(db)
        timeslot_service = TimeSlotService(db)
        
        objects = await object_service.get_objects_by_owner(current_user["telegram_id"])
        
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
            current_user["telegram_id"], 
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