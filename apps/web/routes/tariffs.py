"""Роуты для управления тарифными планами."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.tariff_service import TariffService
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse, name="tariffs_list")
async def tariffs_list(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Список тарифных планов."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plans = await tariff_service.get_all_tariff_plans(active_only=False)
            statistics = await tariff_service.get_tariff_statistics()
        
        return templates.TemplateResponse("admin/tariffs.html", {
            "request": request,
            "current_user": current_user,
            "title": "Управление тарифными планами",
            "tariff_plans": tariff_plans,
            "statistics": statistics,
            "is_management": True
        })
        
    except Exception as e:
        logger.error(f"Error loading tariffs list: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки тарифов: {str(e)}")


@router.get("/create", response_class=HTMLResponse, name="create_tariff")
async def create_tariff_form(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Форма создания тарифного плана."""
    return templates.TemplateResponse("admin/tariff_form.html", {
        "request": request,
        "current_user": current_user,
        "title": "Создание тарифного плана",
        "tariff_plan": None,
        "is_create": True
    })


@router.post("/create", name="create_tariff_post")
async def create_tariff(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    currency: str = Form("RUB"),
    billing_period: str = Form("month"),
    max_objects: int = Form(...),
    max_employees: int = Form(...),
    max_managers: int = Form(0),
    features: str = Form("[]"),  # JSON строка
    is_active: bool = Form(True),
    is_popular: bool = Form(False),
    current_user: dict = Depends(require_superadmin)
):
    """Создание тарифного плана."""
    try:
        import json
        
        # Безопасный парсинг JSON для features
        try:
            features_list = json.loads(features) if features and features.strip() else []
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in features: {features}")
            features_list = []
        
        tariff_data = {
            "name": name,
            "description": description,
            "price": price,
            "currency": currency,
            "billing_period": billing_period,
            "max_objects": max_objects,
            "max_employees": max_employees,
            "max_managers": max_managers,
            "features": features_list,
            "is_active": is_active,
            "is_popular": is_popular
        }
        
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plan = await tariff_service.create_tariff_plan(tariff_data)
        
        logger.info(f"Created tariff plan: {tariff_plan.name}")
        return RedirectResponse(url="/admin/tariffs/", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"Error creating tariff plan: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания тарифа: {str(e)}")


@router.get("/{tariff_id}/edit", response_class=HTMLResponse, name="edit_tariff")
async def edit_tariff_form(
    request: Request,
    tariff_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """Форма редактирования тарифного плана."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plan = await tariff_service.get_tariff_plan_by_id(tariff_id)
        
        if not tariff_plan:
            raise HTTPException(status_code=404, detail="Тарифный план не найден")
        
        return templates.TemplateResponse("admin/tariff_form.html", {
            "request": request,
            "current_user": current_user,
            "title": f"Редактирование тарифа: {tariff_plan.name}",
            "tariff_plan": tariff_plan,
            "is_create": False
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading tariff for edit: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки тарифа: {str(e)}")


@router.post("/{tariff_id}/edit", name="edit_tariff_post")
async def edit_tariff(
    request: Request,
    tariff_id: int,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    price: float = Form(...),
    currency: str = Form("RUB"),
    billing_period: str = Form("month"),
    max_objects: int = Form(...),
    max_employees: int = Form(...),
    max_managers: int = Form(0),
    features: str = Form("[]"),  # JSON строка
    is_active: bool = Form(True),
    is_popular: bool = Form(False),
    current_user: dict = Depends(require_superadmin)
):
    """Редактирование тарифного плана."""
    try:
        import json
        
        # Безопасный парсинг JSON для features
        try:
            features_list = json.loads(features) if features and features.strip() else []
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in features: {features}")
            features_list = []
        
        tariff_data = {
            "name": name,
            "description": description,
            "price": price,
            "currency": currency,
            "billing_period": billing_period,
            "max_objects": max_objects,
            "max_employees": max_employees,
            "max_managers": max_managers,
            "features": features_list,
            "is_active": is_active,
            "is_popular": is_popular
        }
        
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plan = await tariff_service.update_tariff_plan(tariff_id, tariff_data)
        
        if not tariff_plan:
            raise HTTPException(status_code=404, detail="Тарифный план не найден")
        
        logger.info(f"Updated tariff plan: {tariff_plan.name}")
        return RedirectResponse(url="/admin/tariffs/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tariff plan: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления тарифа: {str(e)}")


@router.post("/{tariff_id}/delete", name="delete_tariff")
async def delete_tariff(
    request: Request,
    tariff_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """Удаление тарифного плана."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            success = await tariff_service.delete_tariff_plan(tariff_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Нельзя удалить тариф с активными подписками")
        
        logger.info(f"Deleted tariff plan: {tariff_id}")
        return RedirectResponse(url="/admin/tariffs/", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tariff plan: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка удаления тарифа: {str(e)}")


# API endpoints для AJAX запросов

@router.get("/api/list", response_class=JSONResponse, name="api_tariffs_list")
async def api_tariffs_list(
    current_user: dict = Depends(require_superadmin)
):
    """API: Список тарифных планов."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plans = await tariff_service.get_all_tariff_plans(active_only=False)
        
        return {
            "success": True,
            "data": [tariff.to_dict() for tariff in tariff_plans]
        }
        
    except Exception as e:
        logger.error(f"API Error loading tariffs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/statistics", response_class=JSONResponse, name="api_tariffs_statistics")
async def api_tariffs_statistics(
    current_user: dict = Depends(require_superadmin)
):
    """API: Статистика по тарифам."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            statistics = await tariff_service.get_tariff_statistics()
        
        return {
            "success": True,
            "data": statistics
        }
        
    except Exception as e:
        logger.error(f"API Error loading tariff statistics: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/{tariff_id}", response_class=JSONResponse, name="api_tariff_detail")
async def api_tariff_detail(
    tariff_id: int,
    current_user: dict = Depends(require_superadmin)
):
    """API: Детали тарифного плана."""
    try:
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            tariff_plan = await tariff_service.get_tariff_plan_by_id(tariff_id)
        
        if not tariff_plan:
            return {
                "success": False,
                "error": "Тарифный план не найден"
            }
        
        return {
            "success": True,
            "data": tariff_plan.to_dict()
        }
        
    except Exception as e:
        logger.error(f"API Error loading tariff detail: {e}")
        return {
            "success": False,
            "error": str(e)
        }
