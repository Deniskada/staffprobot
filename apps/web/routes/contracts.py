"""
Роуты управления договорами для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def contracts_list(request: Request):
    """Список договоров - перенаправляем на сотрудников"""
    return RedirectResponse(url="/employees", status_code=302)


@router.get("/create", response_class=HTMLResponse)
async def create_contract_form(request: Request):
    """Форма создания договора - перенаправляем на создание договора сотрудника"""
    return RedirectResponse(url="/employees/create", status_code=302)


@router.post("/create")
async def create_contract(request: Request):
    """Создание нового договора - перенаправляем на сотрудников"""
    return RedirectResponse(url="/employees", status_code=302)


@router.get("/{contract_id}", response_class=HTMLResponse)
async def contract_detail(request: Request, contract_id: int):
    """Детальная информация о договоре - перенаправляем на детали договора"""
    return RedirectResponse(url=f"/employees/contract/{contract_id}", status_code=302)
