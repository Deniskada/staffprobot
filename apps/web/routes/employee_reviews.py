"""
Веб-роуты для интерфейса отзывов сотрудника.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from apps.web.middleware.role_middleware import require_employee_or_applicant
from typing import Optional

router = APIRouter()
from apps.web.jinja import templates


@router.get("/reviews", response_class=HTMLResponse)
async def employee_reviews_page(
    request: Request,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    current_user: dict = Depends(require_employee_or_applicant)
):
    """Страница отзывов сотрудника."""
    return templates.TemplateResponse("employee/reviews.html", {
        "request": request,
        "current_user": current_user,
        "available_interfaces": [
            {"title": "Сотрудник", "url": "/employee/", "icon": "bi-person-badge"},
            {"title": "Управляющий", "url": "/manager/", "icon": "bi-person-gear"}
        ],
        "applications_count": 0,
        "new_applications_count": 0,
        "filter_target_type": target_type,
        "filter_target_id": target_id
    })