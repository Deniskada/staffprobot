"""Роуты для работы с отменой смен (владелец/управляющий)."""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Optional

from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from apps.web.middleware.role_middleware import require_manager_or_owner, get_user_id_from_current_user
from core.database.session import get_db_session
from apps.web.jinja import templates
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift_cancellation import ShiftCancellation
from domain.entities.user import User
from domain.entities.object import Object
from shared.services.shift_cancellation_service import ShiftCancellationService
from core.logging.logger import logger

router = APIRouter()


@router.post("/owner/shifts/schedule/{schedule_id}/cancel")
async def owner_cancel_shift(
    request: Request,
    schedule_id: int,
    reason: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Отмена запланированной смены владельцем."""
    try:
        # Получаем пользователя
        user_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return JSONResponse(
                {"success": False, "message": "Пользователь не найден"},
                status_code=404
            )
        
        # Проверяем, что смена существует и принадлежит владельцу
        shift_query = select(ShiftSchedule).where(ShiftSchedule.id == schedule_id)
        shift_result = await db.execute(shift_query)
        shift = shift_result.scalar_one_or_none()
        
        if not shift:
            return JSONResponse(
                {"success": False, "message": "Смена не найдена"},
                status_code=404
            )
        
        # Проверяем владение объектом
        object_query = select(Object).where(
            and_(
                Object.id == shift.object_id,
                Object.owner_id == user.id
            )
        )
        object_result = await db.execute(object_query)
        obj = object_result.scalar_one_or_none()
        
        if not obj:
            return JSONResponse(
                {"success": False, "message": "Доступ запрещен"},
                status_code=403
            )
        
        # Используем сервис для отмены
        cancellation_service = ShiftCancellationService(db)
        result = await cancellation_service.cancel_shift(
            shift_schedule_id=schedule_id,
            cancelled_by_user_id=user.id,
            cancelled_by_type='owner',
            cancellation_reason=reason,
            reason_notes=notes
        )
        
        if result['success']:
            # TODO: Отправить уведомление сотруднику
            return JSONResponse({
                "success": True,
                "message": "Смена успешно отменена"
            })
        else:
            return JSONResponse(
                {"success": False, "message": result['message']},
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"Error cancelling shift {schedule_id}: {e}")
        return JSONResponse(
            {"success": False, "message": "Ошибка отмены смены"},
            status_code=500
        )


@router.post("/manager/shifts/schedule/{schedule_id}/cancel")
async def manager_cancel_shift(
    request: Request,
    schedule_id: int,
    reason: str = Form(...),
    notes: Optional[str] = Form(None),
    current_user: dict = Depends(require_manager_or_owner),
    db: AsyncSession = Depends(get_db_session)
):
    """Отмена запланированной смены управляющим."""
    try:
        # Получаем внутренний ID пользователя согласно правилам user_id vs telegram_id
        internal_user_id = await get_user_id_from_current_user(current_user, db)
        if not internal_user_id:
            return JSONResponse(
                {"success": False, "message": "Пользователь не найден"},
                status_code=404
            )
        
        # Проверяем, что смена существует
        shift_query = select(ShiftSchedule).where(ShiftSchedule.id == schedule_id)
        shift_result = await db.execute(shift_query)
        shift = shift_result.scalar_one_or_none()
        
        if not shift:
            return JSONResponse(
                {"success": False, "message": "Смена не найдена"},
                status_code=404
            )
        
        # Нормализуем роли пользователя
        raw_roles = current_user.get("roles", []) or []
        roles = [getattr(r, "value", r) for r in raw_roles]
        is_superadmin = "superadmin" in roles
        is_owner = "owner" in roles
        is_manager = "manager" in roles

        # Проверяем доступ управляющего к объекту (для роли manager)
        if is_manager and not is_owner and not is_superadmin:
            from shared.services.manager_permission_service import ManagerPermissionService
            permission_service = ManagerPermissionService(db)
            # Получаем доступные объекты для пользователя-управляющего и проверяем доступ
            accessible_objects = await permission_service.get_user_accessible_objects(internal_user_id)
            has_access = any(obj.id == shift.object_id for obj in accessible_objects)
        elif is_owner and not is_superadmin:
            # Для owner проверяем владение
            object_query = select(Object).where(
                and_(
                    Object.id == shift.object_id,
                    Object.owner_id == internal_user_id
                )
            )
            object_result = await db.execute(object_query)
            has_access = object_result.scalar_one_or_none() is not None
        else:
            # superadmin — доступ разрешен
            has_access = True
        
        if not has_access:
            return JSONResponse(
                {"success": False, "message": "Доступ запрещен"},
                status_code=403
            )
        
        # Используем сервис для отмены
        cancellation_service = ShiftCancellationService(db)
        result = await cancellation_service.cancel_shift(
            shift_schedule_id=schedule_id,
            cancelled_by_user_id=internal_user_id,
            cancelled_by_type='manager',
            cancellation_reason=reason,
            reason_notes=notes
        )
        
        if result['success']:
            # TODO: Отправить уведомление сотруднику
            return JSONResponse({
                "success": True,
                "message": "Смена успешно отменена"
            })
        else:
            return JSONResponse(
                {"success": False, "message": result['message']},
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"Error cancelling shift {schedule_id}: {e}")
        return JSONResponse(
            {"success": False, "message": "Ошибка отмены смены"},
            status_code=500
        )


@router.get("/owner/cancellations", response_class=HTMLResponse)
async def owner_cancellations_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница модерации отмен смен (только с уважительными причинами)."""
    try:
        # Получаем пользователя
        user_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Получаем все отмены сотрудниками (требующие модерации)
        from sqlalchemy.orm import selectinload
        
        cancellations_query = (
            select(ShiftCancellation)
            .options(
                selectinload(ShiftCancellation.shift_schedule),
                selectinload(ShiftCancellation.employee),
                selectinload(ShiftCancellation.object),
                selectinload(ShiftCancellation.verified_by)
            )
            .join(ShiftSchedule, ShiftCancellation.shift_schedule_id == ShiftSchedule.id)
            .join(Object, ShiftCancellation.object_id == Object.id)
            .where(
                and_(
                    Object.owner_id == user.id,
                    ShiftCancellation.cancelled_by_type == 'employee'  # Только отмены сотрудниками
                )
            )
            .order_by(ShiftCancellation.created_at.desc())
        )
        
        cancellations_result = await db.execute(cancellations_query)
        cancellations = cancellations_result.scalars().all()
        
        return templates.TemplateResponse("owner/cancellations/list.html", {
            "request": request,
            "current_user": current_user,
            "cancellations": cancellations
        })
    
    except Exception as e:
        logger.error(f"Error loading cancellations list: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки списка отмен")


@router.post("/owner/cancellations/{cancellation_id}/verify")
async def owner_verify_cancellation(
    request: Request,
    cancellation_id: int,
    is_approved: bool = Form(...),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Верификация документа для уважительной причины отмены."""
    try:
        # Получаем пользователя
        user_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return JSONResponse(
                {"success": False, "message": "Пользователь не найден"},
                status_code=404
            )
        
        # Проверяем владение объектом отмены (с eager loading)
        from sqlalchemy.orm import selectinload
        cancellation_query = (
            select(ShiftCancellation)
            .options(
                selectinload(ShiftCancellation.shift_schedule),
                selectinload(ShiftCancellation.employee),
                selectinload(ShiftCancellation.object),
                selectinload(ShiftCancellation.payroll_adjustment)
            )
            .join(Object, ShiftCancellation.object_id == Object.id)
            .where(
                and_(
                    ShiftCancellation.id == cancellation_id,
                    Object.owner_id == user.id
                )
            )
        )
        cancellation_result = await db.execute(cancellation_query)
        cancellation = cancellation_result.scalar_one_or_none()
        
        if not cancellation:
            return JSONResponse(
                {"success": False, "message": "Отмена не найдена или доступ запрещен"},
                status_code=404
            )
        
        # Используем сервис для верификации
        cancellation_service = ShiftCancellationService(db)
        result = await cancellation_service.verify_cancellation_document(
            cancellation_id=cancellation_id,
            verified_by_user_id=user.id,
            is_approved=is_approved
        )
        
        if result['success']:
            # TODO: Отправить уведомление сотруднику о результате верификации
            return JSONResponse({
                "success": True,
                "message": f"Справка {'подтверждена' if is_approved else 'отклонена'}"
            })
        else:
            return JSONResponse(
                {"success": False, "message": result['message']},
                status_code=400
            )
    
    except Exception as e:
        logger.error(f"Error verifying cancellation {cancellation_id}: {e}")
        return JSONResponse(
            {"success": False, "message": "Ошибка верификации"},
            status_code=500
        )


@router.get("/owner/analytics/cancellations", response_class=HTMLResponse)
async def owner_cancellations_analytics(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    object_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница аналитики отмен смен."""
    from apps.analytics.analytics_service import AnalyticsService
    from apps.web.services.object_service import ObjectService
    from datetime import date, timedelta
    
    try:
        # Получаем пользователя
        user_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Обработка дат
        if date_from:
            start_date = date.fromisoformat(date_from)
        else:
            start_date = date.today() - timedelta(days=30)
        
        if date_to:
            end_date = date.fromisoformat(date_to)
        else:
            end_date = date.today()
        
        # Получаем объекты владельца для фильтра
        object_service = ObjectService(db)
        objects = await object_service.get_objects_by_owner(user.telegram_id)
        
        # Получаем статистику
        analytics_service = AnalyticsService()
        stats = analytics_service.get_cancellation_statistics(
            owner_id=user.id,
            start_date=start_date,
            end_date=end_date,
            object_id=object_id,
            employee_id=employee_id
        )
        
        # Получаем детальный список отмен для таблицы
        from sqlalchemy.orm import selectinload
        
        cancellations_query = (
            select(ShiftCancellation)
            .options(
                selectinload(ShiftCancellation.employee),
                selectinload(ShiftCancellation.object),
                selectinload(ShiftCancellation.shift_schedule),
                selectinload(ShiftCancellation.cancelled_by)
            )
            .join(Object, ShiftCancellation.object_id == Object.id)
            .where(Object.owner_id == user.id)
        )
        
        # Применяем фильтры
        if object_id:
            cancellations_query = cancellations_query.where(ShiftCancellation.object_id == object_id)
        if employee_id:
            cancellations_query = cancellations_query.where(ShiftCancellation.employee_id == employee_id)
        
        cancellations_query = cancellations_query.order_by(ShiftCancellation.created_at.desc())
        
        cancellations_result = await db.execute(cancellations_query)
        cancellations = cancellations_result.scalars().all()
        
        return templates.TemplateResponse("owner/analytics/cancellations.html", {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "cancellations": cancellations,
            "objects": objects,
            "filters": {
                'date_from': start_date.isoformat(),
                'date_to': end_date.isoformat(),
                'object_id': object_id,
                'employee_id': employee_id
            }
        })
    
    except Exception as e:
        logger.error(f"Error loading cancellations analytics: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки аналитики")

