"""
Веб-роуты для интерфейса модератора.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from apps.web.middleware.role_middleware import require_moderator_or_superadmin

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse)
async def moderator_dashboard_page(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin)
):
    """Главная страница модератора."""
    return templates.TemplateResponse("moderator/dashboard.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def moderator_dashboard_page_alt(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin)
):
    """Альтернативный роут для дашборда модератора."""
    return templates.TemplateResponse("moderator/dashboard.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/reviews", response_class=HTMLResponse)
async def moderator_reviews_page(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin)
):
    """Страница модерации отзывов."""
    return templates.TemplateResponse("moderator/reviews.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/appeals", response_class=HTMLResponse)
async def moderator_appeals_page(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin)
):
    """Страница рассмотрения обжалований."""
    # TODO: Создать шаблон для обжалований
    return templates.TemplateResponse("moderator/appeals.html", {
        "request": request,
        "current_user": current_user
    })


@router.get("/statistics", response_class=HTMLResponse)
async def moderator_statistics_page(
    request: Request,
    current_user: dict = Depends(require_moderator_or_superadmin)
):
    """Страница статистики модерации."""
    # TODO: Создать шаблон для статистики
    return templates.TemplateResponse("moderator/statistics.html", {
        "request": request,
        "current_user": current_user
    })
