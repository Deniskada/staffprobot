"""
Веб-роуты для интерфейса отзывов владельца.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_owner_or_superadmin

router = APIRouter()
from apps.web.jinja import templates


@router.get("/reviews", response_class=HTMLResponse)
async def owner_reviews_page(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin)
):
    """Страница отзывов владельца."""
    return templates.TemplateResponse("owner/reviews.html", {
        "request": request,
        "current_user": current_user
    })
