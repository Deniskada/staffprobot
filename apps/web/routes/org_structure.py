"""Роуты для управления организационной структурой."""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from decimal import Decimal

from apps.web.jinja import templates
from apps.web.middleware.auth_middleware import require_owner_or_superadmin, get_current_user
from apps.web.middleware.role_middleware import get_user_id_from_current_user
from core.database.session import get_db_session
from apps.web.services.org_structure_service import OrgStructureService
from apps.web.services.payment_system_service import PaymentSystemService
from core.logging.logger import logger

router = APIRouter()


@router.get("/org-structure", response_class=HTMLResponse)
async def owner_org_structure_list(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница управления организационной структурой."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        org_service = OrgStructureService(db)
        
        # Получить древовидную структуру
        org_tree = await org_service.get_org_tree(owner_id)
        
        # Получить количество подразделений
        units_count = await org_service.get_units_count(owner_id)
        
        # Получить системы оплаты и графики выплат для dropdown
        payment_system_service = PaymentSystemService(db)
        payment_systems = await payment_system_service.get_active_systems()
        
        from domain.entities.payment_schedule import PaymentSchedule
        from sqlalchemy import select
        
        schedules_query = select(PaymentSchedule).where(
            PaymentSchedule.is_active == True
        ).where(
            (PaymentSchedule.owner_id == None) |  # Системные
            (PaymentSchedule.owner_id == owner_id)  # Кастомные владельца
        ).order_by(PaymentSchedule.is_custom.asc(), PaymentSchedule.id.asc())
        schedules_result = await db.execute(schedules_query)
        payment_schedules = schedules_result.scalars().all()
        
        return templates.TemplateResponse(
            "owner/org_structure/list.html",
            {
                "request": request,
                "title": "Организационная структура",
                "org_tree": org_tree,
                "units_count": units_count,
                "payment_systems": payment_systems,
                "payment_schedules": payment_schedules
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading org structure: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки структуры: {str(e)}")


@router.post("/org-structure/create")
async def owner_org_structure_create(
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создание нового подразделения."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        form_data = await request.form()
        
        name = form_data.get("name", "").strip()
        description = form_data.get("description", "").strip()
        parent_id_str = form_data.get("parent_id", "").strip()
        payment_system_id_str = form_data.get("payment_system_id", "").strip()
        payment_schedule_id_str = form_data.get("payment_schedule_id", "").strip()
        
        inherit_late_settings = "inherit_late_settings" in form_data
        late_threshold_minutes_str = form_data.get("late_threshold_minutes", "").strip()
        late_penalty_per_minute_str = form_data.get("late_penalty_per_minute", "").strip()
        
        # Валидация
        if not name:
            raise HTTPException(status_code=400, detail="Название обязательно")
        
        # Парсинг ID
        parent_id = int(parent_id_str) if parent_id_str else None
        payment_system_id = int(payment_system_id_str) if payment_system_id_str else None
        payment_schedule_id = int(payment_schedule_id_str) if payment_schedule_id_str else None
        late_threshold_minutes = int(late_threshold_minutes_str) if late_threshold_minutes_str else None
        late_penalty_per_minute = float(late_penalty_per_minute_str.replace(",", ".")) if late_penalty_per_minute_str else None
        
        # Создать подразделение
        org_service = OrgStructureService(db)
        new_unit = await org_service.create_unit(
            owner_id=owner_id,
            name=name,
            parent_id=parent_id,
            description=description if description else None,
            payment_system_id=payment_system_id,
            payment_schedule_id=payment_schedule_id,
            inherit_late_settings=inherit_late_settings,
            late_threshold_minutes=late_threshold_minutes,
            late_penalty_per_minute=late_penalty_per_minute
        )
        
        logger.info("Org unit created via UI", unit_id=new_unit.id, owner_id=owner_id)
        
        return RedirectResponse(url="/owner/org-structure", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating org unit: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания подразделения: {str(e)}")


@router.post("/org-structure/{unit_id}/edit")
async def owner_org_structure_edit(
    unit_id: int,
    request: Request,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Редактирование подразделения."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        form_data = await request.form()
        
        name = form_data.get("name", "").strip()
        description = form_data.get("description", "").strip()
        payment_system_id_str = form_data.get("payment_system_id", "").strip()
        payment_schedule_id_str = form_data.get("payment_schedule_id", "").strip()
        
        inherit_late_settings = "inherit_late_settings" in form_data
        late_threshold_minutes_str = form_data.get("late_threshold_minutes", "").strip()
        late_penalty_per_minute_str = form_data.get("late_penalty_per_minute", "").strip()
        is_active_str = form_data.get("is_active", "").strip()
        
        # Валидация
        if not name:
            raise HTTPException(status_code=400, detail="Название обязательно")
        
        # Парсинг
        payment_system_id = int(payment_system_id_str) if payment_system_id_str else None
        payment_schedule_id = int(payment_schedule_id_str) if payment_schedule_id_str else None
        late_threshold_minutes = int(late_threshold_minutes_str) if late_threshold_minutes_str else None
        late_penalty_per_minute = float(late_penalty_per_minute_str.replace(",", ".")) if late_penalty_per_minute_str else None
        is_active = is_active_str.lower() in ("true", "on", "1", "yes") if is_active_str else True
        
        # Обновить подразделение
        org_service = OrgStructureService(db)
        updated_unit = await org_service.update_unit(
            unit_id=unit_id,
            owner_id=owner_id,
            data={
                "name": name,
                "description": description if description else None,
                "payment_system_id": payment_system_id,
                "payment_schedule_id": payment_schedule_id,
                "inherit_late_settings": inherit_late_settings,
                "late_threshold_minutes": late_threshold_minutes,
                "late_penalty_per_minute": late_penalty_per_minute,
                "is_active": is_active
            }
        )
        
        if not updated_unit:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")
        
        logger.info("Org unit updated via UI", unit_id=unit_id, owner_id=owner_id)
        
        return RedirectResponse(url="/owner/org-structure", status_code=status.HTTP_302_FOUND)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating org unit: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обновления подразделения: {str(e)}")


@router.post("/org-structure/{unit_id}/move")
async def owner_org_structure_move(
    unit_id: int,
    new_parent_id: Optional[int] = Form(None),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Перемещение подразделения."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        org_service = OrgStructureService(db)
        moved_unit = await org_service.move_unit(unit_id, new_parent_id, owner_id)
        
        if not moved_unit:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")
        
        logger.info("Org unit moved via UI", unit_id=unit_id, new_parent_id=new_parent_id)
        
        return JSONResponse(content={"success": True, "message": "Подразделение перемещено"})
        
    except HTTPException:
        raise
    except ValueError as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Error moving org unit: {e}")
        return JSONResponse(content={"success": False, "message": f"Ошибка: {str(e)}"}, status_code=500)


@router.post("/org-structure/{unit_id}/delete")
async def owner_org_structure_delete(
    unit_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Удаление подразделения (мягкое)."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        org_service = OrgStructureService(db)
        deleted = await org_service.delete_unit(unit_id, owner_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")
        
        logger.info("Org unit deleted via UI", unit_id=unit_id, owner_id=owner_id)
        
        return JSONResponse(content={"success": True, "message": "Подразделение удалено"})
        
    except HTTPException:
        raise
    except ValueError as e:
        return JSONResponse(content={"success": False, "message": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Error deleting org unit: {e}")
        return JSONResponse(content={"success": False, "message": f"Ошибка: {str(e)}"}, status_code=500)


@router.get("/org-structure/{unit_id}/data")
async def owner_org_structure_get_data(
    unit_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить данные подразделения для редактирования."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        org_service = OrgStructureService(db)
        unit = await org_service.get_unit_by_id(unit_id)
        
        if not unit or unit.owner_id != owner_id:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")
        
        return JSONResponse(content={
            "id": unit.id,
            "name": unit.name,
            "description": unit.description,
            "parent_id": unit.parent_id,
            "payment_system_id": unit.payment_system_id,
            "payment_schedule_id": unit.payment_schedule_id,
            "inherit_late_settings": unit.inherit_late_settings,
            "late_threshold_minutes": unit.late_threshold_minutes,
            "late_penalty_per_minute": float(unit.late_penalty_per_minute) if unit.late_penalty_per_minute else None,
            "level": unit.level,
            "is_active": unit.is_active
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting org unit data: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки данных: {str(e)}")

