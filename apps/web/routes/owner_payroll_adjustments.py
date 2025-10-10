"""Роуты для управления корректировками начислений (владелец)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload

from apps.web.dependencies import require_owner_or_superadmin, get_db_session
from apps.web.jinja import templates
from core.logging.logger import logger
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.shift import Shift
from shared.services.payroll_adjustment_service import PayrollAdjustmentService

router = APIRouter(prefix="/payroll-adjustments", tags=["owner-payroll-adjustments"])


@router.get("", response_class=HTMLResponse)
async def payroll_adjustments_list(
    request: Request,
    adjustment_type: Optional[str] = Query(None, description="Тип корректировки"),
    employee_id: Optional[int] = Query(None, description="ID сотрудника"),
    object_id: Optional[int] = Query(None, description="ID объекта"),
    is_applied: Optional[str] = Query(None, description="Статус применения: all/applied/unapplied"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(50, ge=1, le=200, description="Записей на странице"),
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Список корректировок начислений с фильтрами."""
    try:
        # Парсинг дат
        if date_from:
            try:
                start_date = date.fromisoformat(date_from)
            except ValueError:
                start_date = date.today().replace(day=1)
        else:
            start_date = date.today().replace(day=1)
        
        if date_to:
            try:
                end_date = date.fromisoformat(date_to)
            except ValueError:
                end_date = date.today()
        else:
            end_date = date.today()
        
        # Базовый запрос
        query = select(PayrollAdjustment).where(
            func.date(PayrollAdjustment.created_at) >= start_date,
            func.date(PayrollAdjustment.created_at) <= end_date
        ).options(
            selectinload(PayrollAdjustment.employee),
            selectinload(PayrollAdjustment.object),
            selectinload(PayrollAdjustment.shift),
            selectinload(PayrollAdjustment.creator),
            selectinload(PayrollAdjustment.updater)
        )
        
        # Фильтры
        if adjustment_type:
            query = query.where(PayrollAdjustment.adjustment_type == adjustment_type)
        
        if employee_id:
            query = query.where(PayrollAdjustment.employee_id == employee_id)
        
        if object_id:
            query = query.where(PayrollAdjustment.object_id == object_id)
        
        if is_applied == "applied":
            query = query.where(PayrollAdjustment.is_applied == True)
        elif is_applied == "unapplied":
            query = query.where(PayrollAdjustment.is_applied == False)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar()
        
        # Пагинация
        query = query.order_by(desc(PayrollAdjustment.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await session.execute(query)
        adjustments = result.scalars().all()
        
        # Получить список сотрудников для фильтра
        employees_query = select(User).where(User.id.in_(
            select(PayrollAdjustment.employee_id).distinct()
        )).order_by(User.last_name, User.first_name)
        employees_result = await session.execute(employees_query)
        employees = employees_result.scalars().all()
        
        # Получить список объектов для фильтра
        objects_query = select(Object).where(Object.id.in_(
            select(PayrollAdjustment.object_id).where(PayrollAdjustment.object_id.isnot(None)).distinct()
        )).order_by(Object.name)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        
        # Типы корректировок
        adjustment_types = [
            ('shift_base', 'Базовая оплата за смену'),
            ('late_start', 'Штраф за опоздание'),
            ('task_bonus', 'Премия за задачу'),
            ('task_penalty', 'Штраф за задачу'),
            ('manual_bonus', 'Ручная премия'),
            ('manual_deduction', 'Ручной штраф')
        ]
        
        # Расчет пагинации
        total_pages = (total_count + per_page - 1) // per_page
        
        return templates.TemplateResponse(
            "owner/payroll_adjustments/list.html",
            {
                "request": request,
                "current_user": current_user,
                "adjustments": adjustments,
                "employees": employees,
                "objects": objects,
                "adjustment_types": adjustment_types,
                # Фильтры
                "filter_adjustment_type": adjustment_type,
                "filter_employee_id": employee_id,
                "filter_object_id": object_id,
                "filter_is_applied": is_applied,
                "filter_date_from": date_from or start_date.isoformat(),
                "filter_date_to": date_to or end_date.isoformat(),
                # Пагинация
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading payroll adjustments list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки списка корректировок")


@router.post("/create", response_class=JSONResponse)
async def create_manual_adjustment(
    employee_id: int = Form(...),
    adjustment_type: str = Form(...),  # manual_bonus или manual_deduction
    amount: Decimal = Form(...),
    description: str = Form(...),
    object_id: Optional[int] = Form(None),
    shift_id: Optional[int] = Form(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать ручную корректировку."""
    try:
        if adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Неверный тип корректировки"}
            )
        
        adjustment_service = PayrollAdjustmentService(session)
        
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=employee_id,
            amount=amount,
            adjustment_type=adjustment_type,
            description=description,
            created_by=current_user["id"],
            object_id=object_id,
            shift_id=shift_id
        )
        
        await session.commit()
        
        logger.info(
            f"Manual adjustment created by owner",
            adjustment_id=adjustment.id,
            employee_id=employee_id,
            type=adjustment_type,
            amount=float(amount),
            owner_id=current_user["id"]
        )
        
        return JSONResponse(content={
            "success": True,
            "adjustment_id": adjustment.id,
            "message": "Корректировка успешно создана"
        })
        
    except Exception as e:
        logger.error(f"Error creating manual adjustment: {e}")
        await session.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/{adjustment_id}/edit", response_class=JSONResponse)
async def edit_adjustment(
    adjustment_id: int,
    amount: Optional[Decimal] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Редактировать корректировку."""
    try:
        adjustment_service = PayrollAdjustmentService(session)
        
        # Подготовка обновлений
        updates = {}
        if amount is not None:
            updates['amount'] = amount
        if description is not None:
            updates['description'] = description
        
        if not updates:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Нет данных для обновления"}
            )
        
        adjustment = await adjustment_service.update_adjustment(
            adjustment_id=adjustment_id,
            updates=updates,
            updated_by=current_user["id"]
        )
        
        await session.commit()
        
        logger.info(
            f"Adjustment updated by owner",
            adjustment_id=adjustment_id,
            updated_by=current_user["id"],
            fields=list(updates.keys())
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Корректировка успешно обновлена"
        })
        
    except ValueError as e:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error updating adjustment: {e}")
        await session.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/{adjustment_id}/history", response_class=JSONResponse)
async def get_adjustment_history(
    adjustment_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    session: AsyncSession = Depends(get_db_session)
):
    """Получить историю изменений корректировки."""
    try:
        adjustment_service = PayrollAdjustmentService(session)
        
        adjustment = await adjustment_service.get_adjustment_by_id(adjustment_id)
        
        if not adjustment:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Корректировка не найдена"}
            )
        
        edit_history = adjustment.edit_history or []
        
        # Обогащаем историю информацией о пользователях
        user_ids = set()
        for entry in edit_history:
            if entry.get('user_id'):
                user_ids.add(entry['user_id'])
        
        if user_ids:
            users_query = select(User).where(User.id.in_(user_ids))
            users_result = await session.execute(users_query)
            users = {user.id: user for user in users_result.scalars().all()}
            
            for entry in edit_history:
                user_id = entry.get('user_id')
                if user_id and user_id in users:
                    user = users[user_id]
                    entry['user_name'] = f"{user.last_name} {user.first_name}"
        
        return JSONResponse(content={
            "success": True,
            "history": edit_history,
            "adjustment": {
                "id": adjustment.id,
                "type": adjustment.adjustment_type,
                "amount": float(adjustment.amount),
                "description": adjustment.description,
                "created_at": adjustment.created_at.isoformat(),
                "updated_at": adjustment.updated_at.isoformat() if adjustment.updated_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting adjustment history: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

