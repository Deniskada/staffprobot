"""Универсальный API календаря для всех ролей."""

import logging
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import get_db_session
from apps.web.dependencies import get_current_user_dependency
from shared.services.calendar_filter_service import CalendarFilterService
from shared.models.calendar_data import CalendarFilter, ShiftType, ShiftStatus, TimeslotStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/calendar/data")
async def get_calendar_data(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    object_ids: Optional[str] = Query(None, description="ID объектов через запятую"),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить унифицированные данные календаря для пользователя.
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        object_ids: Фильтр по объектам (через запятую)
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Данные календаря с тайм-слотами и сменами
    """
    try:
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Парсим фильтр объектов
        object_filter = None
        if object_ids:
            try:
                object_filter = [int(obj_id.strip()) for obj_id in object_ids.split(",") if obj_id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ID объектов")
        
        # Получаем роль пользователя
        user_role = current_user.get("role", "applicant")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные календаря
        calendar_service = CalendarFilterService(db)
        calendar_data = await calendar_service.get_calendar_data(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj,
            object_filter=object_filter
        )
        
        # Преобразуем в JSON-сериализуемый формат
        return {
            "timeslots": [
                {
                    "id": ts.id,
                    "object_id": ts.object_id,
                    "object_name": ts.object_name,
                    "date": ts.date.isoformat(),
                    "start_time": ts.start_time.strftime("%H:%M"),
                    "end_time": ts.end_time.strftime("%H:%M"),
                    "hourly_rate": ts.hourly_rate,
                    "max_employees": ts.max_employees,
                    "current_employees": ts.current_employees,
                    "available_slots": ts.available_slots,
                    "status": ts.status.value,
                    "is_active": ts.is_active,
                    "notes": ts.notes,
                    "work_conditions": ts.work_conditions,
                    "shift_tasks": ts.shift_tasks,
                    "coordinates": ts.coordinates,
                    "can_edit": ts.can_edit,
                    "can_plan": ts.can_plan,
                    "can_view": ts.can_view
                }
                for ts in calendar_data.timeslots
            ],
            "shifts": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "user_name": s.user_name,
                    "object_id": s.object_id,
                    "object_name": s.object_name,
                    "time_slot_id": s.time_slot_id,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "planned_start": s.planned_start.isoformat() if s.planned_start else None,
                    "planned_end": s.planned_end.isoformat() if s.planned_end else None,
                    "shift_type": s.shift_type.value,
                    "status": s.status.value,
                    "hourly_rate": s.hourly_rate,
                    "total_hours": s.total_hours,
                    "total_payment": s.total_payment,
                    "notes": s.notes,
                    "is_planned": s.is_planned,
                    "schedule_id": s.schedule_id,
                    "actual_shift_id": s.actual_shift_id,
                    "start_coordinates": s.start_coordinates,
                    "end_coordinates": s.end_coordinates,
                    "can_edit": s.can_edit,
                    "can_cancel": s.can_cancel,
                    "can_view": s.can_view
                }
                for s in calendar_data.shifts
            ],
            "metadata": {
                "date_range_start": calendar_data.date_range_start.isoformat(),
                "date_range_end": calendar_data.date_range_end.isoformat(),
                "user_role": calendar_data.user_role,
                "total_timeslots": calendar_data.total_timeslots,
                "total_shifts": calendar_data.total_shifts,
                "planned_shifts": calendar_data.planned_shifts,
                "active_shifts": calendar_data.active_shifts,
                "completed_shifts": calendar_data.completed_shifts,
                "accessible_objects": calendar_data.accessible_objects
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения данных календаря")


@router.get("/api/calendar/timeslots")
async def get_timeslots(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    object_ids: Optional[str] = Query(None, description="ID объектов через запятую"),
    status: Optional[str] = Query(None, description="Статус тайм-слотов"),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить тайм-слоты для календаря.
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        object_ids: Фильтр по объектам (через запятую)
        status: Фильтр по статусу тайм-слотов
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список тайм-слотов
    """
    try:
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Парсим фильтр объектов
        object_filter = None
        if object_ids:
            try:
                object_filter = [int(obj_id.strip()) for obj_id in object_ids.split(",") if obj_id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ID объектов")
        
        # Получаем роль пользователя
        user_role = current_user.get("role", "applicant")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные календаря
        calendar_service = CalendarFilterService(db)
        calendar_data = await calendar_service.get_calendar_data(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj,
            object_filter=object_filter
        )
        
        # Фильтруем по статусу если указан
        timeslots = calendar_data.timeslots
        if status:
            try:
                status_enum = TimeslotStatus(status)
                timeslots = [ts for ts in timeslots if ts.status == status_enum]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Неверный статус тайм-слота: {status}")
        
        # Преобразуем в JSON-сериализуемый формат
        return {
            "timeslots": [
                {
                    "id": ts.id,
                    "object_id": ts.object_id,
                    "object_name": ts.object_name,
                    "date": ts.date.isoformat(),
                    "start_time": ts.start_time.strftime("%H:%M"),
                    "end_time": ts.end_time.strftime("%H:%M"),
                    "hourly_rate": ts.hourly_rate,
                    "max_employees": ts.max_employees,
                    "current_employees": ts.current_employees,
                    "available_slots": ts.available_slots,
                    "status": ts.status.value,
                    "is_active": ts.is_active,
                    "notes": ts.notes,
                    "work_conditions": ts.work_conditions,
                    "shift_tasks": ts.shift_tasks,
                    "coordinates": ts.coordinates,
                    "can_edit": ts.can_edit,
                    "can_plan": ts.can_plan,
                    "can_view": ts.can_view
                }
                for ts in timeslots
            ],
            "metadata": {
                "total_count": len(timeslots),
                "date_range_start": calendar_data.date_range_start.isoformat(),
                "date_range_end": calendar_data.date_range_end.isoformat(),
                "user_role": calendar_data.user_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting timeslots: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения тайм-слотов")


@router.get("/api/calendar/shifts")
async def get_shifts(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    object_ids: Optional[str] = Query(None, description="ID объектов через запятую"),
    shift_types: Optional[str] = Query(None, description="Типы смен через запятую"),
    shift_statuses: Optional[str] = Query(None, description="Статусы смен через запятую"),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить смены для календаря.
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        object_ids: Фильтр по объектам (через запятую)
        shift_types: Фильтр по типам смен
        shift_statuses: Фильтр по статусам смен
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список смен
    """
    try:
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Парсим фильтр объектов
        object_filter = None
        if object_ids:
            try:
                object_filter = [int(obj_id.strip()) for obj_id in object_ids.split(",") if obj_id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ID объектов")
        
        # Получаем роль пользователя
        user_role = current_user.get("role", "applicant")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные календаря
        calendar_service = CalendarFilterService(db)
        calendar_data = await calendar_service.get_calendar_data(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj,
            object_filter=object_filter
        )
        
        # Фильтруем по типам смен если указаны
        shifts = calendar_data.shifts
        if shift_types:
            try:
                type_enums = [ShiftType(t.strip()) for t in shift_types.split(",") if t.strip()]
                shifts = [s for s in shifts if s.shift_type in type_enums]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Неверный тип смены: {e}")
        
        # Фильтруем по статусам смен если указаны
        if shift_statuses:
            try:
                status_enums = [ShiftStatus(s.strip()) for s in shift_statuses.split(",") if s.strip()]
                shifts = [s for s in shifts if s.status in status_enums]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Неверный статус смены: {e}")
        
        # Преобразуем в JSON-сериализуемый формат
        return {
            "shifts": [
                {
                    "id": s.id,
                    "user_id": s.user_id,
                    "user_name": s.user_name,
                    "object_id": s.object_id,
                    "object_name": s.object_name,
                    "time_slot_id": s.time_slot_id,
                    "start_time": s.start_time.isoformat() if s.start_time else None,
                    "end_time": s.end_time.isoformat() if s.end_time else None,
                    "planned_start": s.planned_start.isoformat() if s.planned_start else None,
                    "planned_end": s.planned_end.isoformat() if s.planned_end else None,
                    "shift_type": s.shift_type.value,
                    "status": s.status.value,
                    "hourly_rate": s.hourly_rate,
                    "total_hours": s.total_hours,
                    "total_payment": s.total_payment,
                    "notes": s.notes,
                    "is_planned": s.is_planned,
                    "schedule_id": s.schedule_id,
                    "actual_shift_id": s.actual_shift_id,
                    "start_coordinates": s.start_coordinates,
                    "end_coordinates": s.end_coordinates,
                    "can_edit": s.can_edit,
                    "can_cancel": s.can_cancel,
                    "can_view": s.can_view
                }
                for s in shifts
            ],
            "metadata": {
                "total_count": len(shifts),
                "date_range_start": calendar_data.date_range_start.isoformat(),
                "date_range_end": calendar_data.date_range_end.isoformat(),
                "user_role": calendar_data.user_role,
                "planned_shifts": len([s for s in shifts if s.shift_type == ShiftType.PLANNED]),
                "active_shifts": len([s for s in shifts if s.shift_type == ShiftType.ACTIVE]),
                "completed_shifts": len([s for s in shifts if s.shift_type == ShiftType.COMPLETED]),
                "cancelled_shifts": len([s for s in shifts if s.shift_type == ShiftType.CANCELLED])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shifts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения смен")


@router.get("/api/calendar/stats")
async def get_calendar_stats(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить статистику календаря.
    
    Args:
        start_date: Начальная дата периода
        end_date: Конечная дата периода
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Статистика календаря
    """
    try:
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Получаем роль пользователя
        user_role = current_user.get("role", "applicant")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем статистику
        calendar_service = CalendarFilterService(db)
        stats = await calendar_service.get_calendar_stats(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj
        )
        
        return {
            "stats": stats,
            "metadata": {
                "date_range_start": start_date_obj.isoformat(),
                "date_range_end": end_date_obj.isoformat(),
                "user_role": user_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting calendar stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения статистики календаря")


@router.get("/api/calendar/objects")
async def get_accessible_objects(
    current_user: dict = Depends(get_current_user_dependency),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Получить список доступных объектов для пользователя.
    
    Args:
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        Список доступных объектов
    """
    try:
        # Получаем роль пользователя
        user_role = current_user.get("role", "applicant")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем доступные объекты
        calendar_service = CalendarFilterService(db)
        accessible_objects = await calendar_service.object_access_service.get_accessible_objects(
            user_telegram_id=user_telegram_id,
            user_role=user_role
        )
        
        return {
            "objects": accessible_objects,
            "metadata": {
                "total_count": len(accessible_objects),
                "user_role": user_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting accessible objects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения доступных объектов")
