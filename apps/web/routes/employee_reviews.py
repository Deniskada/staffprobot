"""
Веб-роуты для интерфейса отзывов сотрудника.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_employee_or_applicant

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("/reviews", response_class=HTMLResponse)
async def employee_reviews_page(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant)
):
    """Страница отзывов сотрудника."""
    return templates.TemplateResponse("employee/reviews.html", {
        "request": request,
        "current_user": current_user
    })
