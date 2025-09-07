"""Роуты для управления сотрудниками."""

from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.user import User
from domain.entities.object import Object
from apps.web.services.contract_service import ContractService
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def employees_list(request: Request):
    """Список сотрудников владельца."""
    # Временная заглушка - показываем пустой список
    return templates.TemplateResponse(
        "employees/list.html",
        {
            "request": request,
            "employees": [],
            "title": "Управление сотрудниками"
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_contract_form(request: Request):
    """Форма создания договора с сотрудником."""
    return templates.TemplateResponse(
        "employees/create.html",
        {
            "request": request,
            "title": "Создание договора"
        }
    )


@router.post("/create")
async def create_contract(
    request: Request,
    employee_id: int = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[])
):
    """Создание договора с сотрудником."""
    # Временная заглушка - перенаправляем обратно
    return RedirectResponse(url="/employees", status_code=303)


@router.get("/{employee_id}", response_class=HTMLResponse)
async def employee_detail(request: Request, employee_id: int):
    """Детали сотрудника."""
    return templates.TemplateResponse(
        "employees/detail.html",
        {
            "request": request,
            "employee": None,
            "title": "Детали сотрудника"
        }
    )


@router.get("/contract/{contract_id}", response_class=HTMLResponse)
async def contract_detail(request: Request, contract_id: int):
    """Детали договора."""
    return templates.TemplateResponse(
        "employees/contract_detail.html",
        {
            "request": request,
            "contract": None,
            "title": "Детали договора"
        }
    )


@router.get("/contract/{contract_id}/edit", response_class=HTMLResponse)
async def edit_contract_form(request: Request, contract_id: int):
    """Форма редактирования договора."""
    return templates.TemplateResponse(
        "employees/edit_contract.html",
        {
            "request": request,
            "contract": None,
            "title": "Редактирование договора"
        }
    )


@router.post("/contract/{contract_id}/edit")
async def edit_contract(
    request: Request,
    contract_id: int,
    title: str = Form(...),
    content: str = Form(...),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    allowed_objects: List[int] = Form(default=[])
):
    """Редактирование договора."""
    return RedirectResponse(url=f"/employees/contract/{contract_id}", status_code=303)


@router.post("/contract/{contract_id}/terminate")
async def terminate_contract(
    request: Request,
    contract_id: int,
    reason: str = Form(...)
):
    """Расторжение договора."""
    return RedirectResponse(url="/employees", status_code=303)