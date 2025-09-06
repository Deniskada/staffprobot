"""
Роуты календарного планирования для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def calendar_view(request: Request):
    """Календарное планирование"""
    return templates.TemplateResponse("calendar/index.html", {
        "request": request,
        "title": "Календарное планирование"
    })


@router.get("/api/events")
async def get_events():
    """API для получения событий календаря"""
    # TODO: Получение реальных событий из базы
    events = [
        {
            "id": 1,
            "title": "Смена: Магазин №1",
            "start": "2025-01-15T09:00:00",
            "end": "2025-01-15T17:00:00",
            "color": "#28a745"
        },
        {
            "id": 2,
            "title": "Смена: Офис №2",
            "start": "2025-01-16T08:00:00",
            "end": "2025-01-16T16:00:00",
            "color": "#007bff"
        }
    ]
    return events
