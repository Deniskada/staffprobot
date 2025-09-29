"""
Веб-роуты для страницы обжалований пользователей.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_owner_or_superadmin
from core.logging.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/appeals", response_class=HTMLResponse)
async def appeals_page(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Страница обжалований пользователя.
    
    Args:
        request: HTTP запрос
        current_user: Текущий пользователь
        db: Сессия базы данных
        
    Returns:
        HTMLResponse: Страница обжалований
    """
    try:
        # Получаем роль пользователя для определения шаблона
        if isinstance(current_user, dict):
            user_role = current_user.get('role', 'employee')
        else:
            user_role = getattr(current_user, 'role', 'employee')
        
        # Определяем базовый шаблон в зависимости от роли
        if user_role == 'owner':
            base_template = "owner/base_owner.html"
        elif user_role == 'manager':
            base_template = "manager/base_manager.html"
        else:
            base_template = "employee/base_employee.html"
        
        return templates.TemplateResponse(
            "shared/appeals.html",
            {
                "request": request,
                "current_user": current_user,
                "user_role": user_role,
                "base_template": base_template,
                "applications_count": 0,  # Добавляем обязательную переменную
                "new_applications_count": 0  # Добавляем обязательную переменную
            }
        )
        
    except Exception as e:
        logger.error(f"Error rendering appeals page: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки страницы обжалований")
