"""Утилиты для работы с календарем."""

from typing import List, Dict, Any
from datetime import date, timedelta
from core.logging.logger import logger


def create_calendar_grid(year: int, month: int, timeslots: List[Dict[str, Any]], shifts: List[Dict[str, Any]] = None) -> List[List[Dict[str, Any]]]:
    """
    Создает календарную сетку с тайм-слотами и сменами.
    
    Возвращает сетку 6x7 (6 недель, 7 дней), где текущая неделя всегда будет 3-й строкой.
    Это гарантирует, что все дни месяца будут отображены.
    
    Args:
        year: Год
        month: Месяц (1-12)
        timeslots: Список тайм-слотов
        shifts: Список смен
    
    Returns:
        Список недель, где каждая неделя - список дней с данными
    """
    import calendar as py_calendar
    
    if shifts is None:
        shifts = []
    
    # Получаем первый день месяца и количество дней
    first_day = date(year, month, 1)
    last_day = date(year, month, py_calendar.monthrange(year, month)[1])
    
    # Находим понедельник для начала календаря
    today = date.today()
    if today.year == year and today.month == month:
        # Если смотрим текущий месяц - начинаем за 2 недели до текущей
        current_monday = today - timedelta(days=today.weekday())
        first_monday = current_monday - timedelta(weeks=2)
    else:
        # Для других месяцев - начинаем с первого понедельника месяца
        first_monday = first_day - timedelta(days=first_day.weekday())
    
    # Создаем сетку 6x7 (6 недель, 7 дней) - текущая неделя будет 3-й строкой
    calendar_grid = []
    current_date = first_monday
    
    for week in range(6):
        week_data = []
        for day in range(7):
            # Сначала собираем все смены за день
            all_day_shifts = [
                shift for shift in shifts 
                if shift.get("date") == current_date
            ]
            
            # Группируем активные и завершенные смены по объектам
            active_shifts_by_object = {}
            completed_shifts_by_object = {}
            
            for shift in all_day_shifts:
                object_id = shift.get("object_id")
                if object_id:
                    if shift.get("status") == "active":
                        active_shifts_by_object[object_id] = shift
                    elif shift.get("status") == "completed":
                        completed_shifts_by_object[object_id] = shift
            
            # Показываем все смены
            day_shifts = all_day_shifts
            
            # Фильтруем тайм-слоты
            day_timeslots = []
            for slot in timeslots:
                if slot.get("date") == current_date and slot.get("is_active", True):
                    # Проверяем, есть ли смены для этого тайм-слота
                    has_related_shift = False
                    for shift in day_shifts:
                        # Проверяем, что смена не отменена и относится к тому же объекту
                        if (shift.get("object_id") == slot.get("object_id") and 
                            shift.get("status") not in ['cancelled']):
                            has_related_shift = True
                            break
                    
                    # Показываем тайм-слот всегда
                    day_timeslots.append(slot)
            
            week_data.append({
                "date": current_date,
                "day": current_date.day,
                "is_current_month": current_date.month == month,
                "is_other_month": current_date.month != month,
                "is_today": current_date == date.today(),
                "timeslots": day_timeslots,
                "timeslots_count": len(day_timeslots),
                "shifts": day_shifts,
                "shifts_count": len(day_shifts)
            })
            current_date += timedelta(days=1)
        
        calendar_grid.append(week_data)
    
    return calendar_grid

