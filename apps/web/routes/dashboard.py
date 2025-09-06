"""
Роуты дашборда для веб-приложения
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Dict, Any

from apps.web.services.auth_service import AuthService

router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

auth_service = AuthService()


async def get_current_user(request: Request) -> Dict[str, Any]:
    """Получение текущего пользователя из токена"""
    # TODO: Реализация получения пользователя из JWT токена
    # Пока возвращаем тестовые данные
    return {
        "id": 1,
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Тест",
        "last_name": "Пользователь",
        "role": "owner"
    }


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Главная страница дашборда"""
    
    # TODO: Получение реальных данных из базы
    dashboard_data = {
        "user": current_user,
        "stats": {
            "total_objects": 5,
            "active_shifts": 2,
            "total_employees": 12,
            "monthly_revenue": 150000
        },
        "recent_activity": [
            {
                "type": "shift_opened",
                "message": "Иван Петров открыл смену на объекте 'Магазин №1'",
                "time": "2 часа назад"
            },
            {
                "type": "contract_signed",
                "message": "Подписан договор с Анной Сидоровой",
                "time": "5 часов назад"
            },
            {
                "type": "report_generated",
                "message": "Сформирован отчет за неделю",
                "time": "1 день назад"
            }
        ]
    }
    
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "title": "Дашборд",
        "data": dashboard_data
    })


@router.get("/owner", response_class=HTMLResponse)
async def owner_dashboard(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Дашборд владельца объектов"""
    
    if current_user["role"] not in ["owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
    
    # TODO: Получение реальных данных для владельца
    owner_data = {
        "user": current_user,
        "objects": [
            {
                "id": 1,
                "name": "Магазин №1",
                "address": "ул. Ленина, 10",
                "active_shifts": 2,
                "monthly_revenue": 75000
            },
            {
                "id": 2,
                "name": "Офис №2",
                "address": "пр. Мира, 25",
                "active_shifts": 0,
                "monthly_revenue": 45000
            }
        ],
        "employees": [
            {
                "id": 1,
                "name": "Иван Петров",
                "role": "employee",
                "active_shifts": 1,
                "monthly_hours": 120
            },
            {
                "id": 2,
                "name": "Анна Сидорова",
                "role": "employee",
                "active_shifts": 1,
                "monthly_hours": 95
            }
        ],
        "reports": {
            "total_revenue": 120000,
            "total_shifts": 45,
            "total_hours": 360,
            "average_hourly_rate": 333
        }
    }
    
    return templates.TemplateResponse("dashboard/owner.html", {
        "request": request,
        "title": "Дашборд владельца",
        "data": owner_data
    })


@router.get("/employee", response_class=HTMLResponse)
async def employee_dashboard(request: Request, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Дашборд сотрудника"""
    
    if current_user["role"] not in ["employee", "owner", "superadmin"]:
        raise HTTPException(status_code=403, detail="Недостаточно прав доступа")
    
    # TODO: Получение реальных данных для сотрудника
    employee_data = {
        "user": current_user,
        "available_objects": [
            {
                "id": 1,
                "name": "Магазин №1",
                "address": "ул. Ленина, 10",
                "hourly_rate": 500,
                "next_shift": "2025-01-15 09:00"
            }
        ],
        "my_shifts": [
            {
                "id": 1,
                "object_name": "Магазин №1",
                "start_time": "2025-01-15 09:00",
                "end_time": "2025-01-15 17:00",
                "status": "planned",
                "hourly_rate": 500
            }
        ],
        "stats": {
            "total_hours_this_month": 120,
            "total_earnings": 60000,
            "completed_shifts": 15,
            "upcoming_shifts": 3
        }
    }
    
    return templates.TemplateResponse("dashboard/employee.html", {
        "request": request,
        "title": "Мой дашборд",
        "data": employee_data
    })
