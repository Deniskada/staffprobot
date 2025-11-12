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
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.contract import Contract
from shared.services.payroll_adjustment_service import PayrollAdjustmentService
from shared.services.manager_permission_service import ManagerPermissionService

router = APIRouter(tags=["manager-payroll-adjustments"])


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
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(session)

        if is_manager_only:
            accessible_objects = await permission_service.get_user_accessible_objects(user_id)
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(user_id)
        else:
            objects_query = select(Object).where(Object.owner_id == user_id, Object.is_active == True)
            objects_result = await session.execute(objects_query)
            accessible_objects = objects_result.scalars().all()
            accessible_employee_ids = None

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

        if object_id_int and object_id_int not in accessible_object_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к указанному объекту")
        
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
        
        if is_manager_only and employee_id_int and employee_id_int not in accessible_employee_ids:
            raise HTTPException(status_code=403, detail="Нет доступа к указанному сотруднику")

        # Базовый запрос с фильтром по доступным объектам
        # Показываем корректировки либо с доступными объектами, либо без объекта (NULL)
        # ИЛИ по корректировкам без object_id, но с shift_schedule_id, где объект смены доступен управляющему
        query = select(PayrollAdjustment).outerjoin(
            ShiftSchedule, PayrollAdjustment.shift_schedule_id == ShiftSchedule.id
        ).where(
            func.date(PayrollAdjustment.created_at) >= start_date,
            func.date(PayrollAdjustment.created_at) <= end_date,
            or_(
                PayrollAdjustment.object_id.in_(accessible_object_ids),  # Прямая привязка к объекту
                and_(
                    PayrollAdjustment.object_id.is_(None),  # object_id = NULL
                    PayrollAdjustment.shift_schedule_id.isnot(None),  # Но есть shift_schedule_id
                    ShiftSchedule.object_id.in_(accessible_object_ids)  # И объект смены доступен управляющему
                ),
                and_(
                    PayrollAdjustment.object_id.is_(None),  # object_id = NULL
                    PayrollAdjustment.shift_schedule_id.is_(None)  # И нет shift_schedule_id
                )
            )
        ).options(
            selectinload(PayrollAdjustment.employee),
            selectinload(PayrollAdjustment.object),
            selectinload(PayrollAdjustment.shift),
            selectinload(PayrollAdjustment.creator),
            selectinload(PayrollAdjustment.updater)
        )
        
        if is_manager_only and accessible_employee_ids:
            query = query.where(
                or_(
                    PayrollAdjustment.employee_id.is_(None),
                    PayrollAdjustment.employee_id.in_(accessible_employee_ids)
                )
            )
        elif is_manager_only:
            query = query.where(PayrollAdjustment.employee_id.is_(None))

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
        
        # Получить список сотрудников для выпадающего списка
        if is_manager_only and accessible_employee_ids:
            employees_query = (
                select(User)
                .where(User.id.in_(accessible_employee_ids))
                .order_by(User.last_name, User.first_name)
            )
            employees_result = await session.execute(employees_query)
            employees = employees_result.scalars().all()
        elif not is_manager_only:
            employees_query = (
                select(User)
                .join(Contract, Contract.employee_id == User.id)
                .where(Contract.owner_id == user_id, Contract.is_active == True)
                .distinct()
                .order_by(User.last_name, User.first_name)
            )
            employees_result = await session.execute(employees_query)
            employees = employees_result.scalars().all()
        else:
            employees = []
        
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
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(session)
        accessible_object_ids: List[int] = []
        accessible_employee_ids: List[int] = []

        if is_manager_only:
            accessible_object_ids = await permission_service.get_user_accessible_object_ids(user_id)
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(user_id)

            if object_id and object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому объекту"}
                )

            if employee_id not in accessible_employee_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому сотруднику"}
                )
        else:
            accessible_object_ids = []
        
        if shift_id:
            shift_query = select(Shift).where(Shift.id == shift_id)
            shift_result = await session.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            if not shift:
                return JSONResponse(
                    status_code=404,
                    content={"success": False, "error": "Смена не найдена"}
                )
            if is_manager_only and shift.object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этой смене"}
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
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(session)
        accessible_object_ids: List[int] = []
        accessible_employee_ids: List[int] = []

        if is_manager_only:
            accessible_object_ids = await permission_service.get_user_accessible_object_ids(user_id)
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(user_id)
        else:
            accessible_employee_ids = None
        user_roles = current_user.get_roles() if hasattr(current_user, 'get_roles') else current_user.roles
        is_manager_only = "manager" in user_roles and "owner" not in user_roles

        permission_service = ManagerPermissionService(session)
        accessible_object_ids: List[int] = []
        accessible_employee_ids: List[int] = []

        if is_manager_only:
            accessible_object_ids = await permission_service.get_user_accessible_object_ids(user_id)
            accessible_employee_ids = await permission_service.get_user_accessible_employee_ids(user_id)
        else:
            accessible_employee_ids = None

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
        
        # Проверить, что это ручная корректировка
        if adjustment.adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Можно редактировать только ручные корректировки"}
            )
        
        # Проверить доступ к объекту и сотруднику
        if is_manager_only:
            if adjustment.object_id and adjustment.object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этой корректировке"}
                )
            if adjustment.employee_id and adjustment.employee_id not in accessible_employee_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому сотруднику"}
                )
        
        # Подготовка обновлений
        updates = {}
        if amount is not None:
            # Для manual_deduction делаем сумму отрицательной
            if adjustment.adjustment_type == 'manual_deduction':
                updates['amount'] = -abs(amount)
            else:
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
        
        # Пересчитать суммы в начислении, если корректировка применена
        if adjustment.payroll_entry_id:
            from domain.entities.payroll_entry import PayrollEntry
            entry_query = select(PayrollEntry).where(PayrollEntry.id == adjustment.payroll_entry_id)
            entry_result = await session.execute(entry_query)
            entry = entry_result.scalar_one_or_none()
            
            if entry:
                if is_manager_only and entry.object_id and entry.object_id not in accessible_object_ids:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "error": "У вас нет доступа к начислению этой корректировки"}
                    )
                # Получить все корректировки этого начисления
                all_adjustments_query = select(PayrollAdjustment).where(
                    PayrollAdjustment.payroll_entry_id == adjustment.payroll_entry_id
                )
                all_adjustments_result = await session.execute(all_adjustments_query)
                all_adjustments = all_adjustments_result.scalars().all()
                
                # Пересчитать суммы
                gross = Decimal('0')
                bonuses = Decimal('0')
                deductions = Decimal('0')
                
                for adj in all_adjustments:
                    amount_dec = Decimal(str(adj.amount))
                    if adj.adjustment_type == 'shift_base':
                        gross += amount_dec
                    elif amount_dec > 0:
                        bonuses += amount_dec
                    else:
                        deductions += abs(amount_dec)
                
                entry.gross_amount = float(gross)
                entry.total_bonuses = float(bonuses)
                entry.total_deductions = float(deductions)
                entry.net_amount = float(gross + bonuses - deductions)
        
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


@router.post("/{adjustment_id}/delete", response_class=JSONResponse)
async def manager_delete_adjustment(
    adjustment_id: int,
    current_user = Depends(require_manager_payroll_permission),
    session: AsyncSession = Depends(get_db_session)
):
    """Удалить корректировку (требует can_manage_payroll)."""
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
        
        # Проверить, что это ручная корректировка
        if adjustment.adjustment_type not in ['manual_bonus', 'manual_deduction']:
            return JSONResponse(
                status_code=403,
                content={"success": False, "error": "Можно удалять только ручные корректировки"}
            )
        
        # Проверить доступ к объекту и сотруднику
        if is_manager_only:
            if adjustment.object_id and adjustment.object_id not in accessible_object_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этой корректировке"}
                )
            if adjustment.employee_id and adjustment.employee_id not in accessible_employee_ids:
                return JSONResponse(
                    status_code=403,
                    content={"success": False, "error": "У вас нет доступа к этому сотруднику"}
                )
        
        # Если корректировка применена к начислению, нужно пересчитать суммы
        payroll_entry_id = adjustment.payroll_entry_id
        
        # Удалить корректировку
        await session.delete(adjustment)
        
        # Пересчитать суммы в начислении, если было применено
        if payroll_entry_id:
            from domain.entities.payroll_entry import PayrollEntry
            entry_query = select(PayrollEntry).where(PayrollEntry.id == payroll_entry_id)
            entry_result = await session.execute(entry_query)
            entry = entry_result.scalar_one_or_none()
            
            if entry:
                if is_manager_only and entry.object_id and entry.object_id not in accessible_object_ids:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "error": "У вас нет доступа к начислению этой корректировки"}
                    )
                # Получить все оставшиеся корректировки
                remaining_adjustments_query = select(PayrollAdjustment).where(
                    PayrollAdjustment.payroll_entry_id == payroll_entry_id,
                    PayrollAdjustment.id != adjustment_id
                )
                remaining_result = await session.execute(remaining_adjustments_query)
                remaining_adjustments = remaining_result.scalars().all()
                
                # Пересчитать суммы
                gross = Decimal('0')
                bonuses = Decimal('0')
                deductions = Decimal('0')
                
                for adj in remaining_adjustments:
                    amount_dec = Decimal(str(adj.amount))
                    if adj.adjustment_type == 'shift_base':
                        gross += amount_dec
                    elif amount_dec > 0:
                        bonuses += amount_dec
                    else:
                        deductions += abs(amount_dec)
                
                entry.gross_amount = float(gross)
                entry.total_bonuses = float(bonuses)
                entry.total_deductions = float(deductions)
                entry.net_amount = float(gross + bonuses - deductions)
        
        await session.commit()
        
        logger.info(
            f"Adjustment deleted by manager",
            adjustment_id=adjustment_id,
            deleted_by=user_id,
            type=adjustment.adjustment_type,
            amount=float(adjustment.amount)
        )
        
        return JSONResponse(content={
            "success": True,
            "message": "Корректировка успешно удалена"
        })
        
    except Exception as e:
        logger.error(f"Error deleting adjustment: {e}")
        await session.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

