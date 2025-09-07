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
from apps.web.dependencies import get_current_user_dependency, require_role
from core.logging.logger import logger

router = APIRouter(prefix="/employees", tags=["employees"])
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def employees_list(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Список сотрудников владельца."""
    contract_service = ContractService()
    employees = await contract_service.get_contract_employees(current_user.id)
    
    return templates.TemplateResponse(
        "employees/list.html",
        {
            "request": request,
            "employees": employees,
            "current_user": current_user
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_employee_form(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Форма создания договора с сотрудником."""
    contract_service = ContractService()
    
    # Получаем доступные объекты
    objects = await contract_service.get_available_objects_for_contract(current_user.id)
    
    # Получаем шаблоны договоров
    templates_list = await contract_service.get_contract_templates()
    
    return templates.TemplateResponse(
        "employees/create.html",
        {
            "request": request,
            "objects": objects,
            "templates": templates_list,
            "current_user": current_user
        }
    )


@router.post("/create")
async def create_employee_contract(
    request: Request,
    employee_telegram_id: int = Form(...),
    title: str = Form(...),
    content: str = Form(...),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[]),
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Создание договора с сотрудником."""
    try:
        contract_service = ContractService()
        
        # Парсим даты
        start_date_obj = datetime.fromisoformat(start_date)
        end_date_obj = None
        if end_date:
            end_date_obj = datetime.fromisoformat(end_date)
        
        # Создаем договор
        contract = await contract_service.create_contract(
            owner_id=current_user.id,
            employee_telegram_id=employee_telegram_id,
            title=title,
            content=content,
            hourly_rate=hourly_rate,
            start_date=start_date_obj,
            end_date=end_date_obj,
            template_id=template_id,
            allowed_objects=allowed_objects
        )
        
        logger.info(f"Created contract {contract.id} for employee {employee_telegram_id}")
        return RedirectResponse(url="/employees", status_code=303)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating contract: {e}")
        raise HTTPException(status_code=500, detail="Ошибка создания договора")


@router.get("/{employee_id}", response_class=HTMLResponse)
async def employee_detail(
    employee_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Детальная информация о сотруднике."""
    contract_service = ContractService()
    
    # Получаем договоры сотрудника
    async with get_async_session() as session:
        # Находим сотрудника
        employee_query = select(User).where(User.id == employee_id)
        employee_result = await session.execute(employee_query)
        employee = employee_result.scalar_one_or_none()
        
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")
        
        # Получаем договоры
        contracts = await contract_service.get_employee_contracts(employee_id)
        
        # Фильтруем только договоры текущего владельца
        owner_contracts = [c for c in contracts if c.owner_id == current_user.id]
    
    return templates.TemplateResponse(
        "employees/detail.html",
        {
            "request": request,
            "employee": employee,
            "contracts": owner_contracts,
            "current_user": current_user
        }
    )


@router.get("/contract/{contract_id}", response_class=HTMLResponse)
async def contract_detail(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Детальная информация о договоре."""
    contract_service = ContractService()
    contract = await contract_service.get_contract(contract_id)
    
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    
    if contract.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому договору")
    
    return templates.TemplateResponse(
        "employees/contract_detail.html",
        {
            "request": request,
            "contract": contract,
            "current_user": current_user
        }
    )


@router.post("/contract/{contract_id}/terminate")
async def terminate_contract(
    contract_id: int,
    reason: str = Form(...),
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Расторжение договора."""
    contract_service = ContractService()
    
    # Проверяем, что договор принадлежит владельцу
    contract = await contract_service.get_contract(contract_id)
    if not contract or contract.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому договору")
    
    success = await contract_service.terminate_contract(contract_id, reason)
    
    if not success:
        raise HTTPException(status_code=400, detail="Ошибка расторжения договора")
    
    logger.info(f"Terminated contract {contract_id} by user {current_user.id}")
    return RedirectResponse(url="/employees", status_code=303)


@router.get("/contract/{contract_id}/edit", response_class=HTMLResponse)
async def edit_contract_form(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Форма редактирования договора."""
    contract_service = ContractService()
    contract = await contract_service.get_contract(contract_id)
    
    if not contract or contract.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет доступа к этому договору")
    
    # Получаем доступные объекты
    objects = await contract_service.get_available_objects_for_contract(current_user.id)
    
    return templates.TemplateResponse(
        "employees/edit_contract.html",
        {
            "request": request,
            "contract": contract,
            "objects": objects,
            "current_user": current_user
        }
    )


@router.post("/contract/{contract_id}/edit")
async def update_contract(
    contract_id: int,
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    hourly_rate: Optional[int] = Form(None),
    end_date: Optional[str] = Form(None),
    allowed_objects: List[int] = Form(default=[]),
    current_user: User = Depends(get_current_user_dependency()),
    _: None = Depends(require_role(["owner", "superadmin"]))
):
    """Обновление договора."""
    try:
        contract_service = ContractService()
        
        # Парсим дату окончания
        end_date_obj = None
        if end_date:
            end_date_obj = datetime.fromisoformat(end_date)
        
        # Обновляем договор
        contract = await contract_service.update_contract(
            contract_id=contract_id,
            title=title,
            content=content,
            hourly_rate=hourly_rate,
            end_date=end_date_obj,
            allowed_objects=allowed_objects
        )
        
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")
        
        logger.info(f"Updated contract {contract_id}")
        return RedirectResponse(url=f"/employees/contract/{contract_id}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating contract: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления договора")