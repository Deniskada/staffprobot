"""Роуты для управления графиками выплат."""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.database.session import get_db_session
from apps.web.middleware.auth_middleware import get_current_user, require_owner_or_superadmin
from apps.web.jinja import templates
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


@router.get("/payment-schedules/{schedule_id}/data")
async def get_payment_schedule_data(
    schedule_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить данные графика выплат в JSON для редактирования."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Получить график
        query = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="График не найден")
        
        # Проверить доступ (для кастомных графиков)
        if schedule.is_custom and schedule.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        return JSONResponse(content={
            "id": schedule.id,
            "name": schedule.name,
            "frequency": schedule.frequency,
            "payment_day": schedule.payment_day,
            "payment_period": schedule.payment_period,
            "is_custom": schedule.is_custom
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment schedule data: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки данных графика: {str(e)}")


@router.get("/payment-schedules/{schedule_id}/view", response_class=HTMLResponse)
async def view_payment_schedule(
    request: Request,
    schedule_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Просмотр графика выплат."""
    try:
        owner_id = await get_user_id_from_current_user(current_user, db)
        if not owner_id:
            raise HTTPException(status_code=403, detail="Пользователь не найден")
        
        # Получить график
        query = select(PaymentSchedule).where(PaymentSchedule.id == schedule_id)
        result = await db.execute(query)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            raise HTTPException(status_code=404, detail="График не найден")
        
        # Проверить доступ (для кастомных графиков)
        if schedule.is_custom and schedule.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")
        
        # Сгенерировать таблицу графика на год
        schedule_table = generate_schedule_table(schedule)
        
        # Собрать параметры графика для отображения
        schedule_params = []
        if schedule.payment_period:
            period = schedule.payment_period
            if period.get('start_offset'):
                schedule_params.append(f"Смещение начала: {period.get('start_offset')} дней")
            if period.get('end_offset'):
                schedule_params.append(f"Смещение конца: {period.get('end_offset')} дней")
            if period.get('duration'):
                schedule_params.append(f"Длительность: {period.get('duration')} дней")
            if period.get('description'):
                schedule_params.append(period.get('description'))
        
        return templates.TemplateResponse(
            "owner/payment_schedules/view.html",
            {
                "request": request,
                "schedule": schedule,
                "schedule_table": schedule_table,
                "schedule_params": schedule_params
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing payment schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка просмотра графика: {str(e)}")


def generate_schedule_table(schedule: PaymentSchedule) -> list:
    """Генерирует таблицу графика выплат на год вперед."""
    today = datetime.now().date()
    table = []
    
    if schedule.frequency == 'daily':
        # Ежедневно на 365 дней
        period = schedule.payment_period or {}
        offset = period.get('offset', -1)
        
        for i in range(365):
            payment_date = today + timedelta(days=i)
            period_date = payment_date + timedelta(days=offset)
            
            table.append({
                'payment_date': payment_date.strftime('%d.%m.%Y'),
                'period_start': period_date.strftime('%d.%m.%Y'),
                'period_end': period_date.strftime('%d.%m.%Y'),
                'days': 1
            })
    
    elif schedule.frequency == 'weekly':
        # Еженедельно на 52 недели
        period = schedule.payment_period or {}
        start_offset = period.get('start_offset', -6)
        end_offset = period.get('end_offset', -1)
        
        # Найти первую дату выплаты (следующий день недели payment_day)
        current = today
        target_weekday = schedule.payment_day if schedule.payment_day < 7 else 0
        while current.weekday() != (target_weekday - 1 if target_weekday > 0 else 6):
            current += timedelta(days=1)
        
        for i in range(52):
            payment_date = current + timedelta(weeks=i)
            period_start = payment_date + timedelta(days=start_offset)
            period_end = payment_date + timedelta(days=end_offset)
            days = (period_end - period_start).days + 1
            
            table.append({
                'payment_date': payment_date.strftime('%d.%m.%Y'),
                'period_start': period_start.strftime('%d.%m.%Y'),
                'period_end': period_end.strftime('%d.%m.%Y'),
                'days': days
            })
    
    elif schedule.frequency == 'monthly':
        # Ежемесячно
        period = schedule.payment_period or {}
        payments_config = period.get('payments', [])
        
        if not payments_config:
            # Старый формат для системных графиков
            calc_rules = period.get('calc_rules', {})
            if calc_rules.get('period') == 'previous_month':
                # За весь предыдущий месяц
                for month in range(12):
                    payment_date = datetime(today.year, today.month, schedule.payment_day)
                    payment_date = payment_date + timedelta(days=30*month)
                    
                    # Период - весь предыдущий месяц
                    period_start = datetime(payment_date.year, payment_date.month - 1 if payment_date.month > 1 else 12, 1)
                    period_end = datetime(payment_date.year, payment_date.month, 1) - timedelta(days=1)
                    days = (period_end - period_start.date()).days + 1 if hasattr(period_start, 'date') else (period_end - period_start).days + 1
                    
                    table.append({
                        'payment_date': payment_date.strftime('%d.%m.%Y'),
                        'period_start': period_start.strftime('%d.%m.%Y'),
                        'period_end': period_end.strftime('%d.%m.%Y'),
                        'days': days
                    })
        else:
            # Новый формат (кастомные графики)
            for month in range(12):
                for payment in payments_config:
                    payment_date_str = payment.get('next_payment_date')
                    if not payment_date_str:
                        continue
                    
                    base_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                    payment_date = datetime(base_date.year, base_date.month + month, base_date.day).date()
                    
                    start_offset = payment.get('start_offset', 0)
                    end_offset = payment.get('end_offset', 0)
                    is_end_of_month = payment.get('is_end_of_month', False)
                    
                    period_start = payment_date + timedelta(days=start_offset)
                    
                    if is_end_of_month:
                        # Последний день месяца периода
                        next_month = datetime(period_start.year, period_start.month + 1, 1)
                        period_end = (next_month - timedelta(days=1)).date()
                    else:
                        period_end = payment_date + timedelta(days=end_offset)
                    
                    days = (period_end - period_start).days + 1
                    
                    table.append({
                        'payment_date': payment_date.strftime('%d.%m.%Y'),
                        'period_start': period_start.strftime('%d.%m.%Y'),
                        'period_end': period_end.strftime('%d.%m.%Y'),
                        'days': days
                    })
    
    return table


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

