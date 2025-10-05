"""Тестовый роут для проверки shared календаря."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, timedelta
import calendar as py_calendar

router = APIRouter()
from apps.web.jinja import templates

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

@router.get("/test/calendar", response_class=HTMLResponse)
async def test_calendar(request: Request):
    """Тестовая страница календаря без аутентификации."""
    try:
        # Текущая дата
        today = date.today()
        year = today.year
        month = today.month
        
        # Создаем тестовые данные календаря
        calendar_weeks = []
        first_day = date(year, month, 1)
        first_monday = first_day - timedelta(days=first_day.weekday())
        current_date = first_monday
        
        for week in range(6):
            week_data = []
            for day in range(7):
                week_data.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "day": current_date.day,
                    "is_other_month": current_date.month != month,
                    "is_today": current_date == today,
                    "shifts": [],
                    "timeslots": []
                })
                current_date += timedelta(days=1)
            calendar_weeks.append(week_data)
        
        return templates.TemplateResponse("test/calendar.html", {
            "request": request,
            "title": "Тест календаря",
            "calendar_title": f"{RU_MONTHS[month]} {year}",
            "current_date": f"{year}-{month:02d}-01",
            "view_type": "month",
            "show_today_button": True,
            "show_view_switcher": True,
            "show_filters": True,
            "show_refresh": True,
            "calendar_weeks": calendar_weeks,
            "employees": [],
            "objects": []
        })
        
    except Exception as e:
        return f"Ошибка: {str(e)}"
