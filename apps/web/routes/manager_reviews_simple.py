"""
Простая версия страницы отзывов управляющего для отладки
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_manager_or_superadmin

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

@router.get("/manager/reviews-simple", response_class=HTMLResponse)
async def manager_reviews_simple(
    request: Request,
    current_user: dict = Depends(require_manager_or_superadmin)
):
    """Простая версия страницы отзывов управляющего"""
    return templates.TemplateResponse(
        "manager/reviews_simple.html",
        {
            "request": request,
            "current_user": current_user,
            "applications_count": 0,
            "new_applications_count": 0
        }
    )
