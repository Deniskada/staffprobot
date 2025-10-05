"""
Тестовая страница для проверки dropdown меню
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_manager_or_superadmin

router = APIRouter()
from apps.web.jinja import templates

@router.get("/manager/test-dropdown", response_class=HTMLResponse)
async def test_dropdown_page(
    request: Request,
    current_user: dict = Depends(require_manager_or_superadmin)
):
    """Тестовая страница для проверки dropdown меню"""
    return templates.TemplateResponse(
        "manager/test_dropdown.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": [
                {"title": "Управляющий", "url": "/manager/", "icon": "bi-person-gear"},
                {"title": "Администратор", "url": "/admin/", "icon": "bi-shield-fill-check"}
            ],
            "applications_count": 0,
            "new_applications_count": 0
        }
    )
