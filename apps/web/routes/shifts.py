"""
Роуты управления сменами для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def shifts_list(request: Request):
    """Список смен"""
    return templates.TemplateResponse("shifts/list.html", {
        "request": request,
        "title": "Управление сменами"
    })


@router.get("/active", response_class=HTMLResponse)
async def active_shifts(request: Request):
    """Активные смены"""
    return templates.TemplateResponse("shifts/active.html", {
        "request": request,
        "title": "Активные смены"
    })


@router.get("/planned", response_class=HTMLResponse)
async def planned_shifts(request: Request):
    """Запланированные смены"""
    return templates.TemplateResponse("shifts/planned.html", {
        "request": request,
        "title": "Запланированные смены"
    })
