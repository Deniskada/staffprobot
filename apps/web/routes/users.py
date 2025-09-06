"""Роуты для управления пользователями."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, List
from core.auth.user_manager import user_manager
from apps.web.middleware.auth_middleware import auth_middleware
from domain.entities.user import UserRole
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


async def get_current_user_from_request(request: Request) -> dict:
    """Получение текущего пользователя из запроса"""
    user = await auth_middleware.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user


async def require_owner_or_superadmin(current_user: dict = Depends(get_current_user_from_request)):
    """Проверка роли владельца или суперадмина"""
    user_role = current_user.get("role", "employee")
    if user_role not in ["owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
    return current_user


@router.get("/", response_class=HTMLResponse)
async def users_list(request: Request, current_user: dict = Depends(require_owner_or_superadmin)):
    """Список пользователей"""
    try:
        # Получаем всех пользователей
        users = await user_manager.get_all_users()
        
        return templates.TemplateResponse("users/list.html", {
            "request": request,
            "title": "Управление пользователями",
            "users": users,
            "roles": [role for role in UserRole]
        })
    except Exception as e:
        logger.error(f"Error getting users list: {e}")
        return templates.TemplateResponse("users/list.html", {
            "request": request,
            "title": "Управление пользователями",
            "users": [],
            "roles": [role for role in UserRole],
            "error": f"Ошибка загрузки пользователей: {str(e)}"
        })


@router.post("/{user_id}/role")
async def update_user_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Обновление роли пользователя"""
    try:
        # Проверяем, что роль валидна
        try:
            user_role = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверная роль")
        
        # Обновляем роль пользователя
        success = await user_manager.update_user_role(user_id, role)
        
        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Перенаправляем обратно к списку пользователей
        return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления роли: {str(e)}")


@router.get("/{user_id}/edit", response_class=HTMLResponse)
async def edit_user(request: Request, user_id: int, current_user: dict = Depends(require_owner_or_superadmin)):
    """Страница редактирования пользователя"""
    try:
        user = await user_manager.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return templates.TemplateResponse("users/edit.html", {
            "request": request,
            "title": f"Редактирование пользователя {user.get('first_name', '')}",
            "user": user,
            "roles": [role for role in UserRole]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user for edit: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки пользователя: {str(e)}")


async def require_superadmin(current_user: dict = Depends(get_current_user_from_request)):
    """Проверка роли суперадмина"""
    user_role = current_user.get("role", "employee")
    if user_role != "superadmin":
        raise HTTPException(status_code=403, detail="Требуются права суперадмина")
    return current_user


@router.post("/{user_id}/delete")
async def delete_user(request: Request, user_id: int, current_user: dict = Depends(require_superadmin)):
    """Удаление пользователя (только для суперадминов)"""
    try:
        success = await user_manager.delete_user(user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления пользователя: {str(e)}")
