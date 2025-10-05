"""Роуты для административных отчетов."""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timezone, timedelta

from core.database.session import get_async_session
from apps.web.middleware.auth_middleware import require_superadmin
from apps.web.services.reports_service import ReportsService
from core.logging.logger import logger

router = APIRouter()
from apps.web.jinja import templates


@router.get("/", response_class=HTMLResponse, name="admin_reports_dashboard")
async def admin_reports_dashboard(
    request: Request,
    current_user: dict = Depends(require_superadmin)
):
    """Дашборд административных отчетов."""
    try:
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            
            # Получаем краткую статистику для дашборда
            # За последние 30 дней
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            
            # Пользователи
            users_report = await reports_service.get_users_report(start_date, end_date)
            
            # Финансовый отчет
            financial_report = await reports_service.get_financial_report(start_date, end_date)
            
            # Системная аналитика
            system_report = await reports_service.get_system_analytics_report(start_date, end_date)
        
        return templates.TemplateResponse("admin/reports_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "title": "Административные отчеты",
            "users_summary": users_report.get("summary", {}),
            "financial_summary": financial_report.get("revenue", {}),
            "system_summary": {
                "users": system_report.get("users", {}),
                "objects": system_report.get("objects", {}),
                "subscriptions": system_report.get("subscriptions", {})
            }
        })
        
    except Exception as e:
        logger.error(f"Error loading reports dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {str(e)}")


@router.get("/users", response_class=HTMLResponse, name="users_report")
async def users_report(
    request: Request,
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    role: Optional[str] = Query(None, description="Фильтр по роли"),
    current_user: dict = Depends(require_superadmin)
):
    """Отчет по пользователям."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_users_report(start_dt, end_dt, role)
        
        return templates.TemplateResponse("admin/users_report.html", {
            "request": request,
            "current_user": current_user,
            "title": "Отчет по пользователям",
            "report_data": report_data,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "role": role
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating users report: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")


@router.get("/owners", response_class=HTMLResponse, name="owners_report")
async def owners_report(
    request: Request,
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(require_superadmin)
):
    """Отчет по владельцам."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_owners_report(start_dt, end_dt)
        
        return templates.TemplateResponse("admin/owners_report.html", {
            "request": request,
            "current_user": current_user,
            "title": "Отчет по владельцам",
            "report_data": report_data,
            "filters": {
                "start_date": start_date,
                "end_date": end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating owners report: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")


@router.get("/financial", response_class=HTMLResponse, name="financial_report")
async def financial_report(
    request: Request,
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(require_superadmin)
):
    """Финансовый отчет."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_financial_report(start_dt, end_dt)
        
        return templates.TemplateResponse("admin/financial_report.html", {
            "request": request,
            "current_user": current_user,
            "title": "Финансовый отчет",
            "report_data": report_data,
            "filters": {
                "start_date": start_date,
                "end_date": end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating financial report: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")


@router.get("/analytics", response_class=HTMLResponse, name="system_analytics")
async def system_analytics(
    request: Request,
    start_date: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    current_user: dict = Depends(require_superadmin)
):
    """Системная аналитика."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_system_analytics_report(start_dt, end_dt)
        
        return templates.TemplateResponse("admin/system_analytics.html", {
            "request": request,
            "current_user": current_user,
            "title": "Системная аналитика",
            "report_data": report_data,
            "filters": {
                "start_date": start_date,
                "end_date": end_date
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating system analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации аналитики: {str(e)}")


# API endpoints для AJAX запросов

@router.get("/api/users", response_class=JSONResponse, name="api_users_report")
async def api_users_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin)
):
    """API: Отчет по пользователям."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_users_report(start_dt, end_dt, role)
        
        return {
            "success": True,
            "data": report_data
        }
        
    except Exception as e:
        logger.error(f"API Error generating users report: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/api/financial", response_class=JSONResponse, name="api_financial_report")
async def api_financial_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin)
):
    """API: Финансовый отчет."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_financial_report(start_dt, end_dt)
        
        return {
            "success": True,
            "data": report_data
        }
        
    except Exception as e:
        logger.error(f"API Error generating financial report: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Экспорт отчетов

@router.get("/export/users.csv", name="export_users_csv")
async def export_users_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin)
):
    """Экспорт отчета по пользователям в CSV."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_users_report(start_dt, end_dt, role)
            csv_content = await reports_service.export_report_to_csv(report_data, "users")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=users_report.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting users CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


@router.get("/export/owners.csv", name="export_owners_csv")
async def export_owners_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin)
):
    """Экспорт отчета по владельцам в CSV."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_owners_report(start_dt, end_dt)
            csv_content = await reports_service.export_report_to_csv(report_data, "owners")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=owners_report.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting owners CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")


@router.get("/export/financial.csv", name="export_financial_csv")
async def export_financial_csv(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(require_superadmin)
):
    """Экспорт финансового отчета в CSV."""
    try:
        # Парсинг дат
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        async with get_async_session() as session:
            reports_service = ReportsService(session)
            report_data = await reports_service.get_financial_report(start_dt, end_dt)
            csv_content = await reports_service.export_report_to_csv(report_data, "financial")
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=financial_report.csv"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting financial CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка экспорта: {str(e)}")
