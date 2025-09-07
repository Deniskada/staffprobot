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
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def employees_list(request: Request):
    """Список сотрудников владельца."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем реальных сотрудников из базы данных
    contract_service = ContractService()
    employees = await contract_service.get_contract_employees(current_user["id"])
    
    return templates.TemplateResponse(
        "employees/list.html",
        {
            "request": request,
            "employees": employees,
            "title": "Управление сотрудниками",
            "current_user": current_user
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_contract_form(request: Request):
    """Форма создания договора с сотрудником."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем доступных сотрудников и объекты
    contract_service = ContractService()
    # Используем telegram_id для поиска пользователя в БД
    user_id = current_user["id"]  # Это telegram_id из токена
    available_employees = await contract_service.get_available_employees(user_id)
    objects = await contract_service.get_owner_objects(user_id)
    templates_list = await contract_service.get_contract_templates()
    
    # Текущая дата для шаблона (формат YYYY-MM-DD)
    from datetime import date
    current_date = date.today().strftime("%Y-%m-%d")
    
    # Отладочная информация
    logger.info(f"Available employees: {len(available_employees)}")
    logger.info(f"Objects: {len(objects)}")
    logger.info(f"Templates: {len(templates_list)}")
    for obj in objects:
        logger.info(f"Object: {obj.id} - {obj.name}")
    
    return templates.TemplateResponse(
        "employees/create.html",
        {
            "request": request,
            "title": "Создание договора",
            "current_user": current_user,
            "available_employees": available_employees,
            "objects": objects,
            "templates": templates_list,
            "current_date": current_date
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
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Парсим даты
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Создаем договор
        contract_data = {
            "employee_id": employee_id,
            "title": title,
            "content": content,
            "hourly_rate": hourly_rate,
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "template_id": template_id,
            "allowed_objects": allowed_objects
        }
        
        contract = await contract_service.create_contract(current_user["id"], contract_data)
        
        if contract:
            return RedirectResponse(url="/employees", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка создания договора")
            
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания договора: {str(e)}")


@router.get("/{employee_id}", response_class=HTMLResponse)
async def employee_detail(request: Request, employee_id: int):
    """Детали сотрудника."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    employee = await contract_service.get_employee_by_id(employee_id, current_user["id"])
    
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    return templates.TemplateResponse(
        "employees/detail.html",
        {
            "request": request,
            "employee": employee,
            "title": "Детали сотрудника",
            "current_user": current_user
        }
    )


@router.get("/contract/{contract_id}", response_class=HTMLResponse)
async def contract_detail(request: Request, contract_id: int):
    """Детали договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    contract = await contract_service.get_contract_by_id(contract_id, current_user["id"])
    
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    
    return templates.TemplateResponse(
        "employees/contract_detail.html",
        {
            "request": request,
            "contract": contract,
            "title": "Детали договора",
            "current_user": current_user
        }
    )


@router.get("/contract/{contract_id}/edit", response_class=HTMLResponse)
async def edit_contract_form(request: Request, contract_id: int):
    """Форма редактирования договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    contract = await contract_service.get_contract_by_id(contract_id, current_user["id"])
    objects = await contract_service.get_owner_objects(current_user["id"])
    
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    
    return templates.TemplateResponse(
        "employees/edit_contract.html",
        {
            "request": request,
            "contract": contract,
            "objects": objects,
            "title": "Редактирование договора",
            "current_user": current_user
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
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Парсим даты
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Обновляем договор
        contract_data = {
            "title": title,
            "content": content,
            "hourly_rate": hourly_rate,
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "allowed_objects": allowed_objects
        }
        
        success = await contract_service.update_contract(contract_id, current_user["id"], contract_data)
        
        if success:
            return RedirectResponse(url=f"/employees/contract/{contract_id}", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка обновления договора")
            
    except Exception as e:
        logger.error(f"Error updating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления договора: {str(e)}")


@router.post("/contract/{contract_id}/terminate")
async def terminate_contract(
    request: Request,
    contract_id: int,
    reason: str = Form(...)
):
    """Расторжение договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        success = await contract_service.terminate_contract(contract_id, current_user["id"], reason)
        
        if success:
            return RedirectResponse(url="/employees", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка расторжения договора")
            
    except Exception as e:
        logger.error(f"Error terminating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка расторжения договора: {str(e)}")