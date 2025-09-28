"""
Веб-роуты для интерфейса отзывов управляющего.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_manager_or_superadmin

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/reviews", response_class=HTMLResponse)
async def manager_reviews_page(
    request: Request,
    current_user: dict = Depends(require_manager_or_superadmin)
):
    """Страница отзывов управляющего."""
    return templates.TemplateResponse("manager/reviews.html", {
        "request": request,
        "current_user": current_user
    })
