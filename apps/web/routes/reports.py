"""
Роуты отчетности для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def reports_list(request: Request):
    """Список отчетов"""
    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "title": "Отчеты"
    })


@router.get("/generate", response_class=HTMLResponse)
async def generate_report_form(request: Request):
    """Форма генерации отчета"""
    return templates.TemplateResponse("reports/generate.html", {
        "request": request,
        "title": "Генерация отчета"
    })


@router.post("/generate")
async def generate_report(request: Request):
    """Генерация отчета"""
    # TODO: Обработка генерации отчета
    return {"status": "success", "message": "Отчет сгенерирован"}
