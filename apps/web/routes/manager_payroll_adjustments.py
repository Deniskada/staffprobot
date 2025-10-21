"""Роуты для управления корректировками начислений (управляющий)."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, Request, Query, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, or_
from sqlalchemy.orm import selectinload

from apps.web.dependencies import require_manager_payroll_permission
from core.database.session import get_db_session
from apps.web.jinja import templates
from core.logging.logger import logger
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.user import User
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.contract import Contract
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.manager_permission_service import ManagerPermissionService

router = APIRouter(prefix="/payroll-adjustments", tags=["manager-payroll-adjustments"])


@router.get("", response_class=HTMLResponse)
async def manager_payroll_adjustments_list(
    request: Request,
    adjustment_type: Optional[str] = Query(None, description="Тип корректировки"),
    employee_id: Optional[str] = Query(None, description="ID сотрудника"),
    object_id: Optional[str] = Query(None, description="ID объекта"),
    is_applied: Optional[str] = Query(None, description="Статус применения: all/applied/unapplied"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(50, ge=1, le=200, description="Записей на странице"),
    current_user = Depends(require_manager_payroll_permission),
    session: AsyncSession = Depends(get_db_session)
):
    """Список корректировок начислений с фильтрами (только по доступным объектам)."""
    try:
        user_id = current_user.id
        
        # Получаем доступные объекты управляющего
        permission_service = ManagerPermissionService(session)
        accessible_objects = await permission_service.get_user_accessible_objects(user_id)
        accessible_object_ids = [obj.id for obj in accessible_objects]
        
        if not accessible_object_ids:
            return templates.TemplateResponse(
                "manager/payroll_adjustments/list.html",
                {
                    "request": request,
                    "current_user": current_user,
                    "adjustments": [],
                    "employees": [],
                    "objects": [],
                    "adjustment_types": [],
                    "total_count": 0,
                    "page": page,
                    "per_page": per_page,
                    "total_pages": 0,
                    "error": "У вас нет доступных объектов"
                }
            )
        
        # Конвертация строковых ID в int, игнорируя пустые строки
        employee_id_int = None
        if employee_id and employee_id.strip():
            try:
                employee_id_int = int(employee_id)
            except ValueError:
                pass
        
        object_id_int = None
        if object_id and object_id.strip():
            try:
                object_id_int = int(object_id)
            except ValueError:
                pass
        
        # Парсинг дат
        if date_from:
            try:
                start_date = date.fromisoformat(date_from)
            except ValueError:
                start_date = date.today() - timedelta(days=60)
        else:
            start_date = date.today() - timedelta(days=60)
        
        if date_to:
            try:
                end_date = date.fromisoformat(date_to)
            except ValueError:
                end_date = date.today()
        else:
            end_date = date.today()
        
        # Базовый запрос с фильтром по доступным объектам
        # Показываем корректировки либо с доступными объектами, либо без объекта (NULL)
        query = select(PayrollAdjustment).where(
            func.date(PayrollAdjustment.created_at) >= start_date,
            func.date(PayrollAdjustment.created_at) <= end_date,
            or_(
                PayrollAdjustment.object_id.in_(accessible_object_ids),
                PayrollAdjustment.object_id.is_(None)  # Разрешаем корректировки без объекта
            )
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
        
        if employee_id_int:
            query = query.where(PayrollAdjustment.employee_id == employee_id_int)
        
        if object_id_int:
            query = query.where(PayrollAdjustment.object_id == object_id_int)
        
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
        
        # Получить список сотрудников управляющего для выпадающего списка
        # Получаем всех сотрудников, работающих на доступных объектах
        employees_query = select(User).join(
            Contract, Contract.employee_id == User.id
        ).where(
            Contract.is_active == True,
            Contract.status == 'active'
        )
        
        # Добавляем фильтр по allowed_objects
        from sqlalchemy import text, cast
        from sqlalchemy.dialects.postgresql import JSONB
        
        # Проверяем пересечение allowed_objects с accessible_object_ids
        employee_conditions = []
        for obj_id in accessible_object_ids:
            employee_conditions.append(
                cast(Contract.allowed_objects, JSONB).op('@>')(cast([obj_id], JSONB))
            )
        
        if employee_conditions:
            query_condition = or_(*employee_conditions)
            employees_query = employees_query.where(query_condition)
        
        employees_query = employees_query.distinct().order_by(User.last_name, User.first_name)
        employees_result = await session.execute(employees_query)
        employees = employees_result.scalars().all()
        
        # Получить список доступных объектов для фильтра
        objects = accessible_objects
        
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
        
        # Получаем контекст управляющего
        from apps.web.routes.manager import get_manager_context
        manager_context = await get_manager_context(user_id, session)
        
        return templates.TemplateResponse(
            "manager/payroll_adjustments/list.html",
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
                "total_pages": total_pages,
                **manager_context
            }
        )
        
    except Exception as e:
        logger.error(f"Error loading manager payroll adjustments: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки начислений: {str(e)}")


@router.post("/create", response_class=JSONResponse)
async def manager_create_manual_adjustment(
    employee_id: int = Form(...),
    adjustment_type: str = Form(...),  # manual_bonus или manual_deduction
    amount: Decimal = Form(...),
    description: str = Form(...),
    adjustment_date: Optional[str] = Form(None),
    object_id: Optional[int] = Form(None),
    shift_id: Optional[int] = Form(None),
    current_user = Depends(require_manager_payroll_permission),
    session: AsyncSession = Depends(get_db_session)
):
    """Создать ручную корректировку (требует can_manage_payroll)."""
    try:
        if adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Неверный тип корректировки"}
            )
        
        # Парсим дату
        adjustment_date_obj = None
        if adjustment_date:
            try:
                from datetime import date
                adjustment_date_obj = date.fromisoformat(adjustment_date)
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Неверный формат даты"}
                )
        
        user_id = current_user.id
        
        # Проверяем доступ к объекту (если указан)
        if object_id:
            permission_service = ManagerPermissionService(session)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому объекту"}
                )
        
        adjustment_service = PayrollAdjustmentService(session)
        
        adjustment = await adjustment_service.create_manual_adjustment(
            employee_id=employee_id,
            amount=amount,
            adjustment_type=adjustment_type,
            description=description,
            created_by=user_id,
            object_id=object_id,
            shift_id=shift_id,
            adjustment_date=adjustment_date_obj
        )
        
        await session.commit()
        
        logger.info(
            f"Manual adjustment created by manager",
            adjustment_id=adjustment.id,
            employee_id=employee_id,
            type=adjustment_type,
            amount=float(amount),
            manager_id=user_id
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
async def manager_edit_adjustment(
    adjustment_id: int,
    amount: Optional[Decimal] = Form(None),
    description: Optional[str] = Form(None),
    current_user = Depends(require_manager_payroll_permission),
    session: AsyncSession = Depends(get_db_session)
):
    """Редактировать корректировку (требует can_manage_payroll)."""
    try:
        adjustment_service = PayrollAdjustmentService(session)
        user_id = current_user.id
        
        # Получить корректировку
        from sqlalchemy import select
        from domain.entities.payroll_adjustment import PayrollAdjustment
        query = select(PayrollAdjustment).where(PayrollAdjustment.id == adjustment_id)
        result = await session.execute(query)
        adjustment = result.scalar_one_or_none()
        
        if not adjustment:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Корректировка не найдена"}
            )
        
        # Проверить, что это ручная корректировка и она не применена
        if adjustment.adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Можно редактировать только ручные корректировки"}
            )
        
        if adjustment.is_applied:
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Нельзя редактировать примененные корректировки"}
            )
        
        # Проверить доступ к объекту (если указан)
        if adjustment.object_id:
            permission_service = ManagerPermissionService(session)
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_object_ids = [obj.id for obj in accessible_objects]
            
            if adjustment.object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этой корректировке"}
                )
        
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
            updated_by=user_id
        )
        
        await session.commit()
        
        logger.info(
            f"Adjustment updated by manager",
            adjustment_id=adjustment_id,
            updated_by=user_id,
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

