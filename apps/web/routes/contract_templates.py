"""
Роуты управления шаблонами договоров для веб-приложения
"""

from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import datetime
from apps.web.services.contract_service import ContractService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def contract_templates_list(request: Request):
    """Список шаблонов договоров."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    templates_list = await contract_service.get_contract_templates()
    
    return templates.TemplateResponse(
        "owner/templates/contracts/list.html",
        {
            "request": request,
            "templates": templates_list,
            "title": "Шаблоны договоров",
            "current_user": current_user
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_contract_template_form(request: Request):
    """Форма создания шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    return templates.TemplateResponse(
        "owner/templates/contracts/create.html",
        {
            "request": request,
            "title": "Создание шаблона договора",
            "current_user": current_user
        }
    )


@router.post("/create")
async def create_contract_template(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    content: str = Form(...),
    version: str = Form("1.0"),
    is_public: Optional[bool] = Form(False),
    fields_schema: Optional[str] = Form(None)
):
    """Создание шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Создаем шаблон
        template_data = {
            "name": name,
            "description": description,
            "content": content,
            "version": version,
            "created_by": current_user["id"],  # Это telegram_id
            "is_public": bool(is_public),
            "fields_schema": None
        }
        # Парсим JSON схемы полей, если передана
        if fields_schema:
            try:
                import json
                template_data["fields_schema"] = json.loads(fields_schema)
            except Exception:
                template_data["fields_schema"] = None
        
        template = await contract_service.create_contract_template(template_data)
        
        if template:
            return RedirectResponse(url="/owner/contract-templates", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка создания шаблона")
            
    except Exception as e:
        logger.error(f"Error creating contract template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка создания шаблона: {str(e)}")


@router.get("/{template_id}", response_class=HTMLResponse)
async def contract_template_detail(request: Request, template_id: int):
    """Детали шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    template = await contract_service.get_contract_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    
    return templates.TemplateResponse(
        "owner/templates/contracts/detail.html",
        {
            "request": request,
            "template": template,
            "title": "Детали шаблона",
            "current_user": current_user
        }
    )


@router.get("/{template_id}/edit", response_class=HTMLResponse)
async def edit_contract_template_form(request: Request, template_id: int):
    """Форма редактирования шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    template = await contract_service.get_contract_template(template_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    
    return templates.TemplateResponse(
        "owner/templates/contracts/edit.html",
        {
            "request": request,
            "template": template,
            "title": "Редактирование шаблона",
            "current_user": current_user
        }
    )


@router.get("/api/{template_id}")
async def get_contract_template_api(
    template_id: int,
    request: Request
):
    """API для получения шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        contract_service = ContractService()
        template = await contract_service.get_contract_template(template_id, current_user["id"])
        
        if not template:
            raise HTTPException(status_code=404, detail="Шаблон не найден")
        
        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "content": template.content,
            "version": template.version,
            "is_public": template.is_public,
            "fields_schema": template.fields_schema or []
        }
        
    except Exception as e:
        logger.error(f"Error getting template API: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка получения шаблона: {str(e)}")


@router.post("/{template_id}/edit")
async def update_contract_template(
    request: Request,
    template_id: int,
    name: str = Form(...),
    description: str = Form(""),
    content: str = Form(...),
    version: str = Form("1.0"),
    is_public: Optional[bool] = Form(False),
    fields_schema: Optional[str] = Form(None)
):
    """Обновление шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Обновляем шаблон
        template_data = {
            "name": name,
            "description": description,
            "content": content,
            "version": version,
            "is_public": bool(is_public),
            "fields_schema": None
        }
        if fields_schema:
            try:
                import json
                template_data["fields_schema"] = json.loads(fields_schema)
            except Exception:
                template_data["fields_schema"] = None
        
        success = await contract_service.update_contract_template(template_id, template_data)
        
        if success:
            return RedirectResponse(url=f"/owner/contract-templates/{template_id}", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка обновления шаблона")
            
    except Exception as e:
        logger.error(f"Error updating contract template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления шаблона: {str(e)}")


@router.post("/{template_id}/delete")
async def delete_contract_template(request: Request, template_id: int):
    """Удаление шаблона договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        success = await contract_service.delete_contract_template(template_id)
        
        if success:
            return RedirectResponse(url="/owner/contract-templates", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка удаления шаблона")
            
    except Exception as e:
        logger.error(f"Error deleting contract template: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка удаления шаблона: {str(e)}")
