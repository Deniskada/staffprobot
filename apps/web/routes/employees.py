"""Роуты для управления сотрудниками (для владельцев объектов)."""
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.auth.user_manager import user_manager
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/employees")
async def employees_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Страница списка сотрудников владельца."""
    try:
        # Получаем всех пользователей с ролью employee
        all_users = await user_manager.get_all_users()
        employees = [
            user for user in all_users 
            if 'employee' in user.get('roles', [])
        ]
        
        return templates.TemplateResponse("employees/list.html", {
            "request": request,
            "title": "Сотрудники",
            "employees": employees,
            "current_user": current_user
        })
        
    except Exception as e:
        logger.error(f"Error loading employees list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки списка сотрудников")


@router.get("/employees/{employee_id}")
async def employee_detail(
    request: Request,
    employee_id: int,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Детальная информация о сотруднике."""
    try:
        employee = await user_manager.get_user_by_id(employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")
        
        if 'employee' not in employee.get('roles', []):
            raise HTTPException(status_code=404, detail="Пользователь не является сотрудником")
        
        return templates.TemplateResponse("employees/detail.html", {
            "request": request,
            "title": f"Сотрудник {employee.get('first_name', '')} {employee.get('last_name', '')}",
            "employee": employee,
            "current_user": current_user
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading employee detail: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки информации о сотруднике")


@router.get("/employees/add")
async def add_employee_form(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Форма добавления нового сотрудника."""
    return templates.TemplateResponse("employees/add.html", {
        "request": request,
        "title": "Добавить сотрудника",
        "current_user": current_user
    })


@router.post("/employees/add")
async def add_employee(
    request: Request,
    telegram_id: int,
    first_name: str,
    last_name: str = "",
    username: str = "",
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Добавление нового сотрудника."""
    try:
        # Проверяем, существует ли пользователь
        existing_user = await user_manager.get_user_by_telegram_id(telegram_id)
        
        if existing_user:
            # Пользователь существует, добавляем роль employee
            if 'employee' not in existing_user.get('roles', []):
                new_roles = existing_user.get('roles', []) + ['employee']
                await user_manager.update_user_roles(telegram_id, new_roles)
                logger.info(f"Added employee role to existing user {telegram_id}")
        else:
            # Создаем нового пользователя
            # TODO: Реализовать создание пользователя через user_manager
            logger.warning(f"User creation not implemented yet for telegram_id {telegram_id}")
            raise HTTPException(status_code=501, detail="Создание пользователей пока не реализовано")
        
        return RedirectResponse(url="/employees", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding employee: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка добавления сотрудника: {str(e)}")
