"""Роуты для управления сотрудниками."""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.user import User
from domain.entities.object import Object
from apps.web.services.contract_service import ContractService
from apps.web.services.pdf_service import PDFService
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def employees_list(
    request: Request,
    view_mode: str = Query("cards", description="Режим отображения: cards или list"),
    show_former: bool = Query(False, description="Показать бывших сотрудников")
):
    """Список сотрудников владельца."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем реальных сотрудников из базы данных
    contract_service = ContractService()
    # Используем telegram_id для поиска пользователя в БД
    user_id = current_user["id"]  # Это telegram_id из токена
    
    if show_former:
        employees = await contract_service.get_all_contract_employees_by_telegram_id(user_id)
    else:
        employees = await contract_service.get_contract_employees_by_telegram_id(user_id)
    
    return templates.TemplateResponse(
        "employees/list.html",
        {
            "request": request,
            "employees": employees,
            "title": "Управление сотрудниками",
            "current_user": current_user,
            "view_mode": view_mode,
            "show_former": show_former
        }
    )


@router.get("/create", response_class=HTMLResponse)
async def create_contract_form(
    request: Request,
    employee_telegram_id: int = Query(None, description="Telegram ID сотрудника для предзаполнения")
):
    """Форма создания договора с сотрудником."""
    # Проверяем авторизацию
    from apps.web.app import require_manager_or_owner
    current_user = await require_manager_or_owner(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем доступных сотрудников и объекты
    contract_service = ContractService()
    # Используем telegram_id для поиска пользователя в БД
    user_id = current_user["id"]  # Это telegram_id из токена
    
    # Получаем внутренний ID пользователя для проверки роли
    async with get_async_session() as session:
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        internal_user_id = user_obj.id if user_obj else None
        user_role = user_obj.role if user_obj else None
    
    # В зависимости от роли получаем объекты
    if user_role == "owner":
        available_employees = await contract_service.get_available_employees(user_id)
        objects = await contract_service.get_owner_objects(user_id)
    else:  # manager
        from apps.web.services.manager_permission_service import ManagerPermissionService
        permission_service = ManagerPermissionService(session)
        available_employees = await contract_service.get_available_employees(user_id)
        objects = await permission_service.get_user_accessible_objects(internal_user_id)
    
    # Получаем профиль владельца для тегов
    async with get_async_session() as session:
        
        # Получаем профиль владельца для тегов
        from apps.web.services.tag_service import TagService
        tag_service = TagService()
        owner_profile = await tag_service.get_owner_profile(session, internal_user_id)
    
    # Получаем шаблоны с учетом роли пользователя
    if user_role == "owner":
        templates_list = await contract_service.get_contract_templates_for_user(internal_user_id)
    else:  # manager
        # Для управляющего получаем только публичные шаблоны
        from sqlalchemy import select, and_
        from domain.entities.contract import ContractTemplate
        async with get_async_session() as session:
            templates_query = select(ContractTemplate).where(
                and_(ContractTemplate.is_active == True, ContractTemplate.is_public == True)
            )
            result = await session.execute(templates_query)
            templates_list = result.scalars().all()
    
    # Текущая дата для шаблона (формат YYYY-MM-DD)
    from datetime import date
    current_date = date.today().strftime("%Y-%m-%d")
    
    # Подготавливаем шаблоны в JSON формате для JavaScript
    templates_json = []
    for template in templates_list:
        templates_json.append({
            "id": template.id,
            "name": template.name,
            "content": template.content,
            "version": template.version,
            "fields_schema": template.fields_schema or []
        })
    
    # Получаем теги владельца для подстановки
    owner_tags = {}
    if owner_profile:
        owner_tags = owner_profile.get_tags_for_templates()
        # Добавляем системные теги
        from datetime import datetime
        owner_tags.update({
            'current_date': datetime.now().strftime('%d.%m.%Y'),
            'current_time': datetime.now().strftime('%H:%M'),
            'current_year': str(datetime.now().year)
        })
    
    return templates.TemplateResponse(
        "employees/create.html",
        {
            "request": request,
            "title": "Создание договора",
            "current_user": current_user,
            "available_employees": available_employees,
            "objects": objects,
            "templates": templates_list,
            "templates_json": templates_json,  # Добавляем JSON данные для JavaScript
            "current_date": current_date,
            "employee_telegram_id": employee_telegram_id,
            "owner_tags": owner_tags  # Теги владельца для JavaScript
        }
    )


@router.post("/create")
async def create_contract(
    request: Request,
    employee_telegram_id: int = Form(...),
    title: str = Form(...),
    content: str = Form(""),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[])
):
    """Создание договора с сотрудником."""
    # Проверяем авторизацию
    from apps.web.app import require_manager_or_owner
    current_user = await require_manager_or_owner(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Валидация
        if not hourly_rate:
            raise HTTPException(status_code=400, detail="Часовая ставка обязательна")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
        # Парсим даты
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Получаем данные формы для динамических полей
        form_data = await request.form()
        dynamic_values = {}
        
        # Извлекаем значения динамических полей
        for key, value in form_data.items():
            if key.startswith("field_"):
                field_key = key[6:]  # Убираем префикс "field_"
                dynamic_values[field_key] = value
        
        # Получаем владельца объектов для создания договора
        async with get_async_session() as session:
            user_query = select(User).where(User.telegram_id == current_user["id"])
            user_result = await session.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            user_role = user_obj.role if user_obj else None
            
            if user_role == "manager":
                # Для управляющего находим владельца объектов
                from apps.web.services.manager_permission_service import ManagerPermissionService
                permission_service = ManagerPermissionService(session)
                accessible_objects = await permission_service.get_user_accessible_objects(user_obj.id)
                
                if not accessible_objects:
                    raise HTTPException(status_code=403, detail="У вас нет доступа к объектам")
                
                # Получаем владельца первого объекта
                first_object = accessible_objects[0]
                owner_query = select(User).where(User.id == first_object.owner_id)
                owner_result = await session.execute(owner_query)
                owner_obj = owner_result.scalar_one_or_none()
                
                if not owner_obj:
                    raise HTTPException(status_code=404, detail="Владелец объектов не найден")
                
                owner_telegram_id = owner_obj.telegram_id
            else:
                owner_telegram_id = current_user["id"]
        
        # Создаем договор
        contract_data = {
            "employee_telegram_id": employee_telegram_id,
            "title": title,
            "content": content if content else None,
            "hourly_rate": hourly_rate,
            "start_date": start_date_obj,
            "end_date": end_date_obj,
            "template_id": template_id,
            "allowed_objects": allowed_objects,
            "values": dynamic_values if dynamic_values else None
        }
        
        contract = await contract_service.create_contract(owner_telegram_id, contract_data)
        
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
    # Используем telegram_id для поиска владельца в БД
    employee = await contract_service.get_employee_by_telegram_id(employee_id, current_user["id"])
    
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
    contract = await contract_service.get_contract_by_telegram_id(contract_id, current_user["id"])
    
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
    contract = await contract_service.get_contract_by_telegram_id(contract_id, current_user["id"])
    
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    
    # Получаем доступные объекты и шаблоны
    objects = await contract_service.get_owner_objects(current_user["id"])
    templates_list = await contract_service.get_contract_templates()
    
    return templates.TemplateResponse(
        "employees/edit_contract.html",
        {
            "request": request,
            "contract": contract,
            "objects": objects,
            "templates": templates_list,
            "title": "Редактирование договора",
            "current_user": current_user
        }
    )


@router.post("/contract/{contract_id}/edit")
async def update_contract(
    request: Request,
    contract_id: int,
    title: str = Form(...),
    content: str = Form(...),
    hourly_rate: Optional[int] = Form(None),
    start_date: str = Form(...),
    end_date: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    allowed_objects: List[int] = Form(default=[])
):
    """Обновление договора."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        
        # Валидация
        if not hourly_rate:
            raise HTTPException(status_code=400, detail="Часовая ставка обязательна")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
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
            "template_id": template_id,
            "allowed_objects": allowed_objects
        }
        
        success = await contract_service.update_contract_by_telegram_id(
            contract_id, current_user["id"], contract_data
        )
        
        if success:
            return RedirectResponse(url=f"/employees/contract/{contract_id}", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка обновления договора")
            
    except Exception as e:
        logger.error(f"Error updating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка обновления договора: {str(e)}")
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
        
        # Валидация
        if not hourly_rate:
            raise HTTPException(status_code=400, detail="Часовая ставка обязательна")
        
        if hourly_rate <= 0:
            raise HTTPException(status_code=400, detail="Ставка должна быть больше 0")
        
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


@router.post("/contract/{contract_id}/activate")
async def activate_contract(
    request: Request,
    contract_id: int
):
    """Активация договора."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    contract_service = ContractService()
    try:
        await contract_service.activate_contract_by_telegram_id(
            contract_id=contract_id,
            owner_telegram_id=current_user["id"]
        )
        return JSONResponse({"success": True, "message": "Договор успешно активирован"})
    except Exception as e:
        logger.error(f"Ошибка активации договора: {str(e)}")
        return JSONResponse({"success": False, "detail": f"Ошибка активации договора: {str(e)}"}, status_code=500)


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
        success = await contract_service.terminate_contract_by_telegram_id(contract_id, current_user["id"], reason)
        
        if success:
            return RedirectResponse(url="/employees", status_code=303)
        else:
            raise HTTPException(status_code=400, detail="Ошибка расторжения договора")
            
    except Exception as e:
        logger.error(f"Error terminating contract: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка расторжения договора: {str(e)}")


@router.get("/contract/{contract_id}/pdf")
async def download_contract_pdf(
    request: Request,
    contract_id: int
):
    """Скачать договор в формате PDF."""
    # Проверяем авторизацию
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    try:
        contract_service = ContractService()
        contract = await contract_service.get_contract_by_telegram_id(contract_id, current_user["id"])
        
        if not contract:
            raise HTTPException(status_code=404, detail="Договор не найден")
        
        # Генерируем PDF
        pdf_service = PDFService()
        pdf_data = await pdf_service.generate_contract_pdf(contract)
        
        # Формируем имя файла
        filename = f"contract_{contract.contract_number}_{contract.start_date.strftime('%Y%m%d')}.pdf"
        
        # Возвращаем PDF как файл для скачивания
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating contract PDF: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка генерации PDF: {str(e)}")