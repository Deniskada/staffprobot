"""Роуты для управления графиками выплат."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import get_current_user, require_owner_or_superadmin
from domain.entities.payment_schedule import PaymentSchedule
from core.logging.logger import logger


router = APIRouter()


class CustomScheduleCreate(BaseModel):
    """Схема для создания кастомного графика выплат."""
    name: str
    frequency: str  # daily, weekly, biweekly, monthly
    payment_day: int
    payment_period: dict
    object_id: Optional[int] = None


async def get_user_id_from_current_user(current_user: dict, session: AsyncSession) -> Optional[int]:
    """Получает внутренний ID пользователя из current_user."""
    from domain.entities import User
    telegram_id = current_user.get("telegram_id") or current_user.get("id")
    user_query = select(User).where(User.telegram_id == telegram_id)
    user_result = await session.execute(user_query)
    user_obj = user_result.scalar_one_or_none()
    return user_obj.id if user_obj else None


@router.post("/payment-schedules/create-custom")
async def create_custom_payment_schedule(
    data: CustomScheduleCreate,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Создать кастомный график выплат для объекта."""
    try:
        # Получить внутренний ID владельца
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Проверить доступ к объекту (если указан)
        if data.object_id:
            from domain.entities.object import Object
            object_query = select(Object).where(
                Object.id == data.object_id,
                Object.owner_id == owner_id
            )
            object_result = await db.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            if not obj:
                raise HTTPException(status_code=403, detail="Объект не найден или нет доступа")
        
        # Создать кастомный график
        new_schedule = PaymentSchedule(
            name=data.name,
            frequency=data.frequency,
            payment_day=data.payment_day,
            payment_period=data.payment_period,
            owner_id=owner_id,
            object_id=data.object_id,
            is_custom=True,
            is_active=True
        )
        
        db.add(new_schedule)
        await db.commit()
        await db.refresh(new_schedule)
        
        logger.info(
            "Custom payment schedule created",
            schedule_id=new_schedule.id,
            owner_id=owner_id,
            object_id=data.object_id
        )
        
        return JSONResponse(content={
            "success": True,
            "id": new_schedule.id,
            "name": new_schedule.name
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating custom payment schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка создания графика: {str(e)}")


@router.get("/payment-schedules/available")
async def get_available_payment_schedules(
    object_id: Optional[int] = None,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить доступные графики выплат (системные + кастомные владельца)."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Системные графики (owner_id = NULL)
        query = select(PaymentSchedule).where(
            PaymentSchedule.is_active == True
        ).where(
            (PaymentSchedule.owner_id == None) | (PaymentSchedule.owner_id == owner_id)
        )
        
        # Если указан объект, добавить кастомные графики этого объекта
        if object_id:
            query = query.where(
                (PaymentSchedule.object_id == None) | (PaymentSchedule.object_id == object_id)
            )
        
        query = query.order_by(PaymentSchedule.is_custom.asc(), PaymentSchedule.id.asc())
        
        result = await db.execute(query)
        schedules = result.scalars().all()
        
        return JSONResponse(content=[
            {
                "id": s.id,
                "name": s.name + (" (кастомный)" if s.is_custom else ""),
                "frequency": s.frequency,
                "description": s.payment_period.get('description', '') if s.payment_period else '',
                "is_custom": s.is_custom
            }
            for s in schedules
        ])
        
    except Exception as e:
        logger.error(f"Error getting payment schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки графиков: {str(e)}")

