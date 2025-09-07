from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import datetime
from apps.web.services.template_service import TemplateService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger
from core.database.session import get_async_session

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/", response_class=HTMLResponse)
async def templates_list(request: Request, template_type: str = "planning"):
    """Список шаблонов с выбором типа."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if template_type == "planning":
        # Шаблоны планирования
        async with get_async_session() as session:
            template_service = TemplateService(session)
            templates_list = await template_service.get_templates_by_owner(current_user["id"])
        
        return templates.TemplateResponse(
            "templates/list.html",
            {
                "request": request,
                "templates": templates_list,
                "template_type": "planning",
                "title": "Шаблоны планирования",
                "current_user": current_user
            }
        )
    elif template_type == "contract":
        # Шаблоны договоров
        from apps.web.services.contract_service import ContractService
        contract_service = ContractService()
        templates_list = await contract_service.get_contract_templates()
        
        return templates.TemplateResponse(
            "templates/list.html",
            {
                "request": request,
                "templates": templates_list,
                "template_type": "contract",
                "title": "Шаблоны договоров",
                "current_user": current_user
            }
        )
    else:
        # По умолчанию показываем шаблоны планирования
        return RedirectResponse(url="/templates?template_type=planning", status_code=302)


@router.get("/create", response_class=HTMLResponse)
async def create_template_form(request: Request, template_type: str = "planning"):
    """Форма создания шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    return templates.TemplateResponse(
        "templates/create.html",
        {
            "request": request,
            "template_type": template_type,
            "title": f"Создание шаблона {'планирования' if template_type == 'planning' else 'договора'}",
            "current_user": current_user
        }
    )


@router.post("/create")
async def create_template(
    request: Request,
    template_type: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    hourly_rate: int = Form(0),
    repeat_type: str = Form("none"),
    repeat_days: str = Form(""),
    is_public: bool = Form(False),
    content: str = Form(""),
    version: str = Form("1.0")
):
    """Создание шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        if template_type == "planning":
            # Создание шаблона планирования
            async with get_async_session() as session:
                template_service = TemplateService(session)
                
                template_data = {
                    "name": name,
                    "description": description,
                    "start_time": start_time,
                    "end_time": end_time,
                    "hourly_rate": hourly_rate,
                    "repeat_type": repeat_type,
                    "repeat_days": repeat_days,
                    "is_public": is_public
                }
                
                template = await template_service.create_template(template_data, current_user["id"])
                
                if template:
                    return RedirectResponse(url="/templates?template_type=planning", status_code=303)
                else:
                    raise HTTPException(status_code=400, detail="Ошибка создания шаблона планирования")
                    
        elif template_type == "contract":
            # Создание шаблона договора
            from apps.web.services.contract_service import ContractService
            contract_service = ContractService()
            
            template_data = {
                "name": name,
                "description": description,
                "content": content,
                "version": version,
                "created_by": current_user["id"]
            }
            
            template = await contract_service.create_contract_template(template_data)
            
            if template:
                return RedirectResponse(url="/templates?template_type=contract", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка создания шаблона договора")
        else:
            raise HTTPException(status_code=400, detail="Неверный тип шаблона")
                
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания шаблона: {str(e)}")


@router.get("/{template_id}", response_class=HTMLResponse)
async def template_detail(request: Request, template_id: int, template_type: str = "planning"):
    """Детали шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if template_type == "planning":
        async with get_async_session() as session:
            template_service = TemplateService(session)
            template = await template_service.get_template_by_id(template_id, current_user["id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон планирования не найден")
    elif template_type == "contract":
        from apps.web.services.contract_service import ContractService
        contract_service = ContractService()
        template = await contract_service.get_contract_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон договора не найден")
    else:
        raise HTTPException(status_code=400, detail="Неверный тип шаблона")
    
    return templates.TemplateResponse(
        "templates/detail.html",
        {
            "request": request,
            "template": template,
            "template_type": template_type,
            "title": f"Детали шаблона {'планирования' if template_type == 'planning' else 'договора'}",
            "current_user": current_user
        }
    )


@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_template_form(request: Request, template_id: int, template_type: str = "planning"):
    """Форма редактирования шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    if template_type == "planning":
        async with get_async_session() as session:
            template_service = TemplateService(session)
            template = await template_service.get_template_by_id(template_id, current_user["id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон планирования не найден")
    elif template_type == "contract":
        from apps.web.services.contract_service import ContractService
        contract_service = ContractService()
        template = await contract_service.get_contract_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон договора не найден")
    else:
        raise HTTPException(status_code=400, detail="Неверный тип шаблона")
    
    return templates.TemplateResponse(
        "templates/edit.html",
        {
            "request": request,
            "template": template,
            "template_type": template_type,
            "title": f"Редактирование шаблона {'планирования' if template_type == 'planning' else 'договора'}",
            "current_user": current_user
        }
    )


@router.post("/{template_id}/edit")
async def update_template(
    request: Request,
    template_id: int,
    template_type: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    start_time: str = Form(""),
    end_time: str = Form(""),
    hourly_rate: int = Form(0),
    repeat_type: str = Form("none"),
    repeat_days: str = Form(""),
    is_public: bool = Form(False),
    content: str = Form(""),
    version: str = Form("1.0")
):
    """Обновление шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        if template_type == "planning":
            # Обновление шаблона планирования
            async with get_async_session() as session:
                template_service = TemplateService(session)
                
                template_data = {
                    "name": name,
                    "description": description,
                    "start_time": start_time,
                    "end_time": end_time,
                    "hourly_rate": hourly_rate,
                    "repeat_type": repeat_type,
                    "repeat_days": repeat_days,
                    "is_public": is_public
                }
                
                success = await template_service.update_template(template_id, template_data, current_user["id"])
                
                if success:
                    return RedirectResponse(url=f"/templates/{template_id}?template_type=planning", status_code=303)
                else:
                    raise HTTPException(status_code=400, detail="Ошибка обновления шаблона планирования")
                    
        elif template_type == "contract":
            # Обновление шаблона договора
            from apps.web.services.contract_service import ContractService
            contract_service = ContractService()
            
            template_data = {
                "name": name,
                "description": description,
                "content": content,
                "version": version
            }
            
            success = await contract_service.update_contract_template(template_id, template_data)
            
            if success:
                return RedirectResponse(url=f"/templates/{template_id}?template_type=contract", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка обновления шаблона договора")
        else:
            raise HTTPException(status_code=400, detail="Неверный тип шаблона")
                
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления шаблона: {str(e)}")


@router.post("/{template_id}/delete")
async def delete_template(request: Request, template_id: int, template_type: str = "planning"):
    """Удаление шаблона."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        if template_type == "planning":
            # Удаление шаблона планирования
            async with get_async_session() as session:
                template_service = TemplateService(session)
                success = await template_service.delete_template(template_id, current_user["id"])
            
            if success:
                return RedirectResponse(url="/templates?template_type=planning", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка удаления шаблона планирования")
                
        elif template_type == "contract":
            # Удаление шаблона договора
            from apps.web.services.contract_service import ContractService
            contract_service = ContractService()
            success = await contract_service.delete_contract_template(template_id)
            
            if success:
                return RedirectResponse(url="/templates?template_type=contract", status_code=303)
            else:
                raise HTTPException(status_code=400, detail="Ошибка удаления шаблона договора")
        else:
            raise HTTPException(status_code=400, detail="Неверный тип шаблона")
            
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка удаления шаблона: {str(e)}")