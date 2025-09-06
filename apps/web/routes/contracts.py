"""
Роуты управления договорами для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def contracts_list(request: Request):
    """Список договоров"""
    return templates.TemplateResponse("contracts/list.html", {
        "request": request,
        "title": "Договоры"
    })


@router.get("/create", response_class=HTMLResponse)
async def create_contract_form(request: Request):
    """Форма создания договора"""
    return templates.TemplateResponse("contracts/create.html", {
        "request": request,
        "title": "Создание договора"
    })


@router.post("/create")
async def create_contract(request: Request):
    """Создание нового договора"""
    # TODO: Обработка создания договора
    return {"status": "success", "message": "Договор создан"}


@router.get("/{contract_id}", response_class=HTMLResponse)
async def contract_detail(request: Request, contract_id: int):
    """Детальная информация о договоре"""
    return templates.TemplateResponse("contracts/detail.html", {
        "request": request,
        "title": f"Договор #{contract_id}"
    })
