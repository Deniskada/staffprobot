"""
Роуты для интерфейса сотрудника (соискателя)
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, date, timedelta, time
from typing import List, Dict, Any, Optional
import logging
from io import BytesIO

from apps.web.dependencies import get_current_user_dependency
from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_employee_or_applicant
from domain.entities import User, Object, Application, Interview, ShiftSchedule, Shift
from domain.entities.application import ApplicationStatus
from apps.web.utils.timezone_utils import WebTimezoneHelper
from shared.services.role_based_login_service import RoleBasedLoginService
from shared.services.calendar_filter_service import CalendarFilterService
from openpyxl import Workbook

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

# Инициализируем помощник для работы с временными зонами
web_timezone_helper = WebTimezoneHelper()


def parse_date_or_default(value: Optional[str], default: date) -> date:
    """Преобразует строку даты в объект date, возвращает default при ошибке."""
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


async def load_employee_earnings(
    db: AsyncSession,
    user_id: int,
    start_date: date,
    end_date: date
) -> tuple[List[Dict[str, Any]], float, float, List[Dict[str, Any]]]:
    """Загружает завершенные смены сотрудника и агрегирует данные."""

    query = (
        select(Shift, Object)
        .join(Object, Shift.object_id == Object.id)
        .where(
            Shift.user_id == user_id,
            Shift.status == "completed",
            func.date(Shift.start_time) >= start_date,
            func.date(Shift.start_time) <= end_date,
        )
        .order_by(Shift.start_time.asc())
    )

    result = await db.execute(query)
    rows = result.all()

    earnings: List[Dict[str, Any]] = []
    total_hours = 0.0
    total_amount = 0.0
    summary_by_object: Dict[int, Dict[str, Any]] = {}

    for shift, obj in rows:
        timezone_str = getattr(obj, "timezone", None) or "Europe/Moscow"
        date_label = web_timezone_helper.format_datetime_with_timezone(
            shift.start_time, timezone_str, "%d.%m.%Y"
        )
        start_label = web_timezone_helper.format_datetime_with_timezone(
            shift.start_time, timezone_str, "%H:%M"
        )
        end_label = (
            web_timezone_helper.format_datetime_with_timezone(
                shift.end_time, timezone_str, "%H:%M"
            )
            if shift.end_time
            else "—"
        )

        duration_hours = float(shift.total_hours or 0)
        if not duration_hours and shift.start_time and shift.end_time:
            seconds = max((shift.end_time - shift.start_time).total_seconds(), 0)
            duration_hours = round(seconds / 3600, 2)

        hourly_rate = float(shift.hourly_rate or obj.hourly_rate or 0)
        amount = float(shift.total_payment or (duration_hours * hourly_rate))

        total_hours += duration_hours
        total_amount += amount

        earnings.append(
            {
                "shift_id": shift.id,
                "object_name": obj.name,
                "date_label": date_label,
                "start_label": start_label,
                "end_label": end_label,
                "duration_hours": duration_hours,
                "hourly_rate": hourly_rate,
                "amount": amount,
            }
        )

        summary_entry = summary_by_object.setdefault(
            obj.id,
            {
                "object_name": obj.name,
                "hours": 0.0,
                "amount": 0.0,
                "shifts": 0,
            },
        )
        summary_entry["hours"] += duration_hours
        summary_entry["amount"] += amount
        summary_entry["shifts"] += 1

    summary_list = sorted(
        summary_by_object.values(), key=lambda item: item["amount"], reverse=True
    )

    return earnings, total_hours, total_amount, summary_list


async def get_user_id_from_current_user(current_user, session):
    """Получает внутренний ID пользователя из current_user"""
    if isinstance(current_user, dict):
        # current_user - это словарь из JWT payload
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        # current_user - это объект User
        return current_user.id

async def get_available_interfaces_for_user(current_user, db):
    """Получает доступные интерфейсы для пользователя"""
    user_id = await get_user_id_from_current_user(current_user, db)
    login_service = RoleBasedLoginService(db)
    return await login_service.get_available_interfaces(user_id)


@router.get("/earnings", response_class=HTMLResponse)
async def employee_earnings(
    request: Request,
    date_from: Optional[str] = Query(None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания периода (YYYY-MM-DD)"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница заработка сотрудника."""

    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    end_default = datetime.utcnow().date()
    start_default = end_default - timedelta(days=30)

    start_date = parse_date_or_default(date_from, start_default)
    end_date = parse_date_or_default(date_to, end_default)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    earnings, total_hours, total_amount, summary_by_object = await load_employee_earnings(
        db, user_id, start_date, end_date
    )

    available_interfaces = await get_available_interfaces_for_user(current_user, db)
    applications_count_result = await db.execute(
        select(func.count(Application.id)).where(Application.applicant_id == user_id)
    )
    applications_count = applications_count_result.scalar() or 0

    return templates.TemplateResponse(
        "employee/earnings.html",
        {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "start_date": start_date,
            "end_date": end_date,
            "earnings": earnings,
            "total_hours": total_hours,
            "total_amount": total_amount,
            "summary_by_object": summary_by_object,
        },
    )


@router.get("/earnings/export")
async def employee_earnings_export(
    date_from: Optional[str] = Query(None, description="Дата начала периода (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания периода (YYYY-MM-DD)"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Экспорт заработка в Excel."""

    if isinstance(current_user, RedirectResponse):
        return current_user

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    end_default = datetime.utcnow().date()
    start_default = end_default - timedelta(days=30)

    start_date = parse_date_or_default(date_from, start_default)
    end_date = parse_date_or_default(date_to, end_default)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    earnings, total_hours, total_amount, summary_by_object = await load_employee_earnings(
        db, user_id, start_date, end_date
    )

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Сводка"
    summary_sheet.append(["Период", f"{start_date.strftime('%d.%m.%Y')} — {end_date.strftime('%d.%m.%Y')}"])
    summary_sheet.append(["Всего смен", len(earnings)])
    summary_sheet.append(["Общее число часов", total_hours])
    summary_sheet.append(["Заработано, ₽", total_amount])
    summary_sheet.append([])
    summary_sheet.append(["Объект", "Смен", "Часы", "Сумма, ₽"])

    for item in summary_by_object:
        summary_sheet.append([
            item["object_name"],
            item["shifts"],
            round(item["hours"], 2),
            round(item["amount"], 2),
        ])

    detail_sheet = workbook.create_sheet("Детализация")
    detail_sheet.append([
        "Дата",
        "Объект",
        "Время начала",
        "Время окончания",
        "Часы",
        "Ставка, ₽",
        "Сумма, ₽",
    ])

    for row in earnings:
        detail_sheet.append([
            row["date_label"],
            row["object_name"],
            row["start_label"],
            row["end_label"],
            round(row["duration_hours"], 2),
            round(row["hourly_rate"], 2),
            round(row["amount"], 2),
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"earnings_{start_date.isoformat()}_{end_date.isoformat()}.xlsx"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    return StreamingResponse(buffer, media_type=headers["Content-Type"], headers=headers)

@router.get("/", response_class=HTMLResponse)
async def employee_index(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Главная страница сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0
        
        # Получаем статистику
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        interviews_count = await db.execute(
            select(func.count(Interview.id)).where(
                    and_(
                    Interview.applicant_id == user_id,
                    Interview.status.in_(['SCHEDULED', 'PENDING'])
                )
            )
        )
        interviews_count = interviews_count.scalar() or 0
        
        available_objects_count = await db.execute(
            select(func.count(Object.id)).where(Object.available_for_applicants == True)
        )
        available_objects_count = available_objects_count.scalar() or 0
        
        history_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        history_count = history_count.scalar() or 0
        
        # Получаем последние заявки
        recent_applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(
            Application.applicant_id == user_id
        ).order_by(Application.created_at.desc()).limit(5)
        
        recent_applications_result = await db.execute(recent_applications_query)
        recent_applications = []
        for row in recent_applications_result:
            recent_applications.append({
                'id': row.Application.id,
                'object_name': row.object_name,
                'status': row.Application.status,
                'created_at': row.Application.created_at
            })
        
        # Получаем ближайшие собеседования
        upcoming_interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(
            and_(
                Interview.applicant_id == user_id,
                Interview.scheduled_at >= datetime.now(),
                Interview.status.in_(['SCHEDULED', 'PENDING'])
            )
        ).order_by(Interview.scheduled_at.asc()).limit(5)
        
        upcoming_interviews_result = await db.execute(upcoming_interviews_query)
        upcoming_interviews = []
        for row in upcoming_interviews_result:
            upcoming_interviews.append({
                'id': row.Interview.id,
                'object_name': row.object_name,
                'scheduled_at': row.Interview.scheduled_at,
                'type': row.Interview.type
            })
        
        # Всего заработано
        from sqlalchemy import func as _func
        total_earned = (await db.execute(
            select(_func.coalesce(_func.sum(Shift.total_payment), 0)).where(
                Shift.user_id == user_id,
                Shift.status == 'completed'
            )
        )).scalar() or 0

        return templates.TemplateResponse("employee/index.html", {
            "request": request,
            "current_user": current_user,
            "current_date": datetime.now(),
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "available_objects_count": available_objects_count,
            "history_count": history_count,
            "total_earned": float(total_earned),
            "recent_applications": recent_applications,
            "upcoming_interviews": upcoming_interviews,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки дашборда: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки дашборда: {e}")

@router.get("/objects", response_class=HTMLResponse)
async def employee_objects(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница поиска работы"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Получаем доступные объекты
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = []
        
        for obj in objects_result.scalars():
            # Парсим координаты из формата "lat,lon"
            lat, lon = obj.coordinates.split(',') if obj.coordinates else (0, 0)
            
            objects.append({
                'id': obj.id,
                'name': obj.name,
                'address': obj.address or '',
                'latitude': float(lat),
                'longitude': float(lon),
                'opening_time': str(obj.opening_time),
                'closing_time': str(obj.closing_time),
                'hourly_rate': float(obj.hourly_rate),
                'work_conditions': obj.work_conditions or 'Стандартные условия работы',
                'shift_tasks': obj.shift_tasks or ['Выполнение основных обязанностей']
            })
        
        # Получаем ключ API Яндекс Карт
        import os
        yandex_maps_api_key = os.getenv("YANDEX_MAPS_API_KEY", "")
        
        return templates.TemplateResponse("employee/objects.html", {
        "request": request,
        "current_user": current_user,
        "yandex_maps_api_key": yandex_maps_api_key,
            "objects": objects,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки объектов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки объектов: {e}")

@router.get("/api/objects")
async def employee_api_objects(
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """API для получения объектов для карты"""
    try:
        logger.info(f"API objects called, current_user: {type(current_user)}")
        
        if isinstance(current_user, RedirectResponse):
            logger.info("Redirecting to login")
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            logger.error("User not found")
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        logger.info(f"User ID: {user_id}")
        
        # Получаем доступные объекты
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = []
        
        # Получаем рейтинги для всех объектов
        from shared.services.rating_service import RatingService
        rating_service = RatingService(db)
        
        for obj in objects_result.scalars():
            # Парсим координаты из формата "lat,lon"
            lat, lon = obj.coordinates.split(',') if obj.coordinates else (0, 0)
            
            # Получаем рейтинг объекта
            rating = await rating_service.get_rating('object', obj.id)
            if not rating:
                rating = await rating_service.get_or_create_rating('object', obj.id)
            
            # Форматируем звездный рейтинг
            star_info = rating_service.get_star_rating(float(rating.average_rating))
            
            objects.append({
                'id': obj.id,
                'name': obj.name,
                'address': obj.address or '',
                'latitude': float(lat),
                'longitude': float(lon),
                'opening_time': str(obj.opening_time),
                'closing_time': str(obj.closing_time),
                'hourly_rate': float(obj.hourly_rate),
                'work_conditions': obj.work_conditions or 'Стандартные условия работы',
                'shift_tasks': obj.shift_tasks or ['Выполнение основных обязанностей'],
                'rating': {
                    'average_rating': float(rating.average_rating),
                    'total_reviews': rating.total_reviews,
                    'stars': star_info
                }
            })
        
        logger.info(f"Found {len(objects)} objects")
        return {"objects": objects}
        
    except Exception as e:
        logger.error(f"Ошибка загрузки объектов API: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки объектов: {e}")

@router.get("/applications", response_class=HTMLResponse)
async def employee_applications(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница заявок сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Получаем заявки
        applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(Application.applicant_id == user_id).order_by(Application.created_at.desc())
        
        applications_result = await db.execute(applications_query)
        applications = []
        for row in applications_result:
            applications.append({
                'id': row.Application.id,
                'object_id': row.Application.object_id,
                'object_name': row.object_name,
                'status': row.Application.status.value.lower(),
                'message': row.Application.message,
                'preferred_schedule': row.Application.preferred_schedule,
                'created_at': row.Application.created_at,
                'interview_scheduled_at': row.Application.interview_scheduled_at,
                'interview_type': row.Application.interview_type,
                'interview_result': row.Application.interview_result
            })
        
        # Статистика заявок
        applications_stats = {
            'pending': len([a for a in applications if a['status'] == 'pending']),
            'approved': len([a for a in applications if a['status'] == 'approved']),
            'rejected': len([a for a in applications if a['status'] == 'rejected']),
            'interview': len([a for a in applications if a['status'] == 'interview'])
        }
        
        # Получаем объекты для фильтра
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = [{'id': obj.id, 'name': obj.name} for obj in objects_result.scalars()]
        
        return templates.TemplateResponse("employee/applications.html", {
            "request": request,
            "current_user": current_user,
            "applications": applications,
            "applications_stats": applications_stats,
            "objects": objects,
            "applications_count": applications_count,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки заявок: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки заявок: {e}")

@router.post("/api/applications")
async def employee_create_application(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        form_data = await request.form()
        object_id = form_data.get("object_id")
        message = form_data.get("message", "").strip()

        if not object_id:
            raise HTTPException(status_code=400, detail="Не указан объект")

        object_query = select(Object).where(and_(Object.id == int(object_id), Object.available_for_applicants == True))
        obj_result = await db.execute(object_query)
        obj = obj_result.scalar_one_or_none()
        if not obj:
            raise HTTPException(status_code=404, detail="Объект не найден или недоступен")

        existing_query = select(Application).where(and_(
            Application.applicant_id == user_id,
            Application.object_id == int(object_id),
            Application.status.in_([ApplicationStatus.PENDING, ApplicationStatus.APPROVED, ApplicationStatus.INTERVIEW])
        ))
        existing_result = await db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="У вас уже есть активная заявка на этот объект")

        application = Application(
            applicant_id=user_id,
            object_id=int(object_id),
            message=message,
            status=ApplicationStatus.PENDING
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)

        # Отправляем уведомления через асинхронную команду  
        try:
            logger.info(f"=== Начинаем отправку уведомлений ===")
            from core.database.session import get_sync_session
            from shared.services.notification_service import NotificationService
            from core.config.settings import settings
            from domain.entities.user import User
            
            # Получаем синхронную сессию для NotificationService
            session_factory = get_sync_session
            with session_factory() as session:
                logger.info(f"Sending notification to owner_id={obj.owner_id}, application_id={application.id}")
                
                telegram_token = settings.telegram_bot_token
                logger.info(f"Telegram token получен: {telegram_token[:10]}...")
                
                notification_service = NotificationService(
                    session=session,
                    telegram_token=telegram_token
                )
                
                # Получаем информацию о пользователе для имени в уведомлении
                user_query = select(User).where(User.id == user_id)
                user_result = session.execute(user_query)
                applicant_user = user_result.scalar_one_or_none()
                
                applicant_name = "Пользователь"
                if applicant_user:
                    if applicant_user.first_name or applicant_user.last_name:
                        parts = []
                        if applicant_user.first_name:
                            parts.append(applicant_user.first_name.strip())
                        if applicant_user.last_name:
                            parts.append(applicant_user.last_name.strip())
                        applicant_name = " ".join(parts) if parts else applicant_user.username
                    elif applicant_user.username:
                        applicant_name = applicant_user.username
                
                # Уведомляем владельца конкретного объекта
                owner_id = obj.owner_id
                logger.info(f"Creating notification for owner user_id={owner_id}, for application_id={application.id}")
                
                notification_payload = {
                    "application_id": application.id,
                    "applicant_name": applicant_name,
                    "object_name": obj.name,
                    "message": message
                }
                
                logger.info(f"Notification payload: {notification_payload}")
                
                # Создаем уведомления для владельца  
                try:
                    notifications = notification_service.create(
                        [owner_id],
                        "application_created",
                        notification_payload,
                        send_telegram=True
                    )
                    logger.info(f"Notification created: {len(notifications)} notifications")
                    session.commit()
                    logger.info(f"Notifications committed to database successfully")
                except Exception as service_error:
                    logger.error(f"Error in notification service create: {service_error}")
                    raise service_error
                    
        except Exception as notification_error:
            logger.error(f"Ошибка отправки уведомлений: {notification_error}")
            # Не прерываем выполнение основной операции

        return {"id": application.id, "status": application.status.value, "message": "Заявка успешно создана"}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Ошибка создания заявки: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка создания заявки: {exc}")

@router.get("/api/applications/{application_id}")
async def employee_application_details_api(
    application_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Необходима авторизация")

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    query = select(Application, Object.name.label("object_name")).join(Object).where(
        and_(Application.id == application_id, Application.applicant_id == user_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    application = row.Application
    return {
        "id": application.id,
        "object_id": application.object_id,
        "object_name": row.object_name,
        "status": application.status.value.lower(),
        "message": application.message,
        "preferred_schedule": application.preferred_schedule,
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "interview_scheduled_at": application.interview_scheduled_at.isoformat() if application.interview_scheduled_at else None,
        "interview_type": application.interview_type,
        "interview_result": application.interview_result
    }


@router.get("/api/applications/{application_id}/interview")
async def employee_application_interview_api(
    application_id: int,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    if isinstance(current_user, RedirectResponse):
        raise HTTPException(status_code=401, detail="Необходима авторизация")

    user_id = await get_user_id_from_current_user(current_user, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    query = select(Application, Object.name.label("object_name"), Object.address.label("object_address"))\
        .join(Object).where(and_(Application.id == application_id, Application.applicant_id == user_id))
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Заявка или собеседование не найдены")

    application = row.Application
    if application.status != ApplicationStatus.INTERVIEW:
        raise HTTPException(status_code=404, detail="Собеседование не назначено")

    return {
        "application_id": application.id,
        "object_name": row.object_name,
        "location": row.object_address,
        "scheduled_at": application.interview_scheduled_at.isoformat() if application.interview_scheduled_at else None,
        "type": application.interview_type,
        "notes": application.interview_result,
        "contact_person": None,
        "contact_phone": None
    }

@router.get("/calendar", response_class=HTMLResponse)
async def employee_calendar(
    request: Request,
    year: int = Query(None),
    month: int = Query(None),
    object_id: int = Query(None),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Календарь сотрудника (общий календарь объектов/смен)."""
    try:
        from datetime import date
        import json

        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        available_interfaces = await get_available_interfaces_for_user(current_user, db)

        # Текущая дата по умолчанию
        today = date.today()
        if year is None:
            year = today.year
        if month is None:
            month = today.month

        # Получаем объекты, доступные сотруднику по активным договорам
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        from domain.entities.contract import Contract
        from domain.entities.object import Object
        from domain.entities.time_slot import TimeSlot
        from domain.entities.shift_schedule import ShiftSchedule
        from domain.entities.shift import Shift

        # Активные договоры сотрудника
        contracts_query = select(Contract).where(
            and_(Contract.employee_id == user_id, Contract.is_active == True)
        )
        contracts = (await db.execute(contracts_query)).scalars().all()

        # Список доступных object_ids из allowed_objects договоров
        object_ids = []
        import json as _json
        for c in contracts:
            if c and c.allowed_objects:
                allowed = c.allowed_objects if isinstance(c.allowed_objects, list) else _json.loads(c.allowed_objects)
                for oid in allowed:
                    if oid not in object_ids:
                        object_ids.append(oid)

        # Опциональная фильтрация по выбранному объекту
        if object_id and object_id in object_ids:
            object_ids = [object_id]

        # Карта объектов
        objects_map = {}
        if object_ids:
            objs_q = select(Object).where(Object.id.in_(object_ids))
            objs = (await db.execute(objs_q)).scalars().all()
            objects_map = {o.id: o for o in objs}

        # Тайм-слоты с текущего месяца до конца года (как у владельца)
        timeslots_data = []
        if object_ids:
            start_date = date(year, month, 1)
            end_date = date(year, 12, 31)

            ts_q = select(TimeSlot).options(selectinload(TimeSlot.object)).where(
                and_(
                    TimeSlot.object_id.in_(object_ids),
                    TimeSlot.slot_date >= start_date,
                    TimeSlot.slot_date < end_date,
                    TimeSlot.is_active == True,
                )
            ).order_by(TimeSlot.slot_date, TimeSlot.start_time)

            timeslots = (await db.execute(ts_q)).scalars().all()
            for slot in timeslots:
                obj = objects_map.get(slot.object_id)
                if not obj:
                    continue
                timeslots_data.append({
                    "id": slot.id,
                    "object_id": slot.object_id,
                    "object_name": obj.name,
                    "date": slot.slot_date.isoformat(),
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "hourly_rate": float(slot.hourly_rate) if slot.hourly_rate else float(obj.hourly_rate) if obj.hourly_rate else 0,
                    "max_employees": slot.max_employees or 1,
                    "is_active": slot.is_active,
                    "notes": slot.notes or "",
                })

        # Смены за месяц (запланированные и фактические)
        shifts_data = []
        if object_ids:
            start_date = date(year, month, 1)
            end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

            # Запланированные
            sched_q = select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.object_id.in_(object_ids),
                    ShiftSchedule.planned_start >= start_date,
                    ShiftSchedule.planned_start < end_date,
                )
            ).order_by(ShiftSchedule.planned_start)
            scheduled = (await db.execute(sched_q)).scalars().all()

            # Фактические
            act_q = select(Shift).options(selectinload(Shift.user)).where(
                and_(
                    Shift.object_id.in_(object_ids),
                    Shift.start_time >= start_date,
                    Shift.start_time < end_date,
                )
            ).order_by(Shift.start_time)
            actual = (await db.execute(act_q)).scalars().all()

            # Преобразуем (запланированные)
            # Загрузим пользователей для отображения имени
            user_ids = list({s.user_id for s in scheduled if s.user_id})
            users_map = {}
            if user_ids:
                users_res = await db.execute(select(User).where(User.id.in_(user_ids)))
                users_map = {u.id: u for u in users_res.scalars().all()}

            for s in scheduled:
                obj = objects_map.get(s.object_id)
                if not obj:
                    continue
                emp = users_map.get(s.user_id)
                emp_name = (f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else None)
                shifts_data.append({
                    "id": f"schedule_{s.id}",
                    "object_id": s.object_id,
                    "object_name": obj.name,
                    "date": s.planned_start.date().isoformat(),
                    "start_time": web_timezone_helper.format_time_with_timezone(s.planned_start, obj.timezone if obj else 'Europe/Moscow'),
                    "end_time": web_timezone_helper.format_time_with_timezone(s.planned_end, obj.timezone if obj else 'Europe/Moscow'),
                    "status": s.status,
                    "time_slot_id": s.time_slot_id,
                    "employee_name": emp_name,
                    "notes": s.notes or "",
                })

            # Преобразуем (фактические)
            act_user_ids = list({sh.user_id for sh in actual if sh.user_id})
            act_users_map = {}
            if act_user_ids:
                act_users_res = await db.execute(select(User).where(User.id.in_(act_user_ids)))
                act_users_map = {u.id: u for u in act_users_res.scalars().all()}

            for sh in actual:
                obj = objects_map.get(sh.object_id)
                if not obj:
                    continue
                emp = act_users_map.get(sh.user_id)
                emp_name = (f"{emp.first_name or ''} {emp.last_name or ''}".strip() if emp else None)
                shifts_data.append({
                    "id": sh.id,
                    "object_id": sh.object_id,
                    "object_name": obj.name,
                    "date": sh.start_time.date().isoformat(),
                    "start_time": web_timezone_helper.format_time_with_timezone(sh.start_time, obj.timezone if obj else 'Europe/Moscow'),
                    "end_time": web_timezone_helper.format_time_with_timezone(sh.end_time, obj.timezone if obj else 'Europe/Moscow') if sh.end_time else None,
                    "status": sh.status,
                    "time_slot_id": sh.time_slot_id,
                    "employee_name": emp_name,
                    "notes": sh.notes or "",
                })

        # Сетка календаря
        calendar_weeks = _create_calendar_grid_employee(year, month, timeslots_data, shifts_data)

        # JSON для шаблона
        def _serialize(obj):
            if isinstance(obj, date):
                return obj.isoformat()
            from datetime import datetime as _dt
            if isinstance(obj, _dt):
                return obj.isoformat()
            raise TypeError(str(type(obj)))

        calendar_weeks_json = json.dumps(calendar_weeks, default=_serialize)

        # Счетчик заявок для бейджа в шапке
        applications_count_result = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count_result.scalar() or 0

        # Заголовок месяца
        RU_MONTHS = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        title = f"{RU_MONTHS[month]} {year}"

        return templates.TemplateResponse("employee/calendar.html", {
            "request": request,
            "title": title,
            "calendar_title": title,
            "year": year,
            "month": month,
            "current_date": today,
            "calendar_weeks": calendar_weeks,
            "calendar_weeks_json": calendar_weeks_json,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки календаря: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки календаря: {e}")


@router.get("/api/employees")
async def employee_api_employees(
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Возвращает только текущего сотрудника для панели сотрудников."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            return []

        name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username or f"ID {user.id}"
        return [{
            "id": int(user.id),
            "name": str(name),
            "role": "employee",
            "is_active": bool(user.is_active),
            "telegram_id": int(user.telegram_id) if user.telegram_id else None,
            # для dnd назначения самим сотрудником на слот
            "draggable": True,
        }]
    except Exception as e:
        logger.error(f"Ошибка загрузки сотрудника: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки сотрудников")


def _create_calendar_grid_employee(
    year: int,
    month: int,
    timeslots: List[Dict[str, Any]],
    shifts: List[Dict[str, Any]] | None = None,
) -> List[List[Dict[str, Any]]]:
    """Создает календарную сетку для сотрудника (показываем все активные тайм‑слоты и все смены, кроме отмененных)."""
    import calendar as _cal
    from datetime import date, timedelta

    if shifts is None:
        shifts = []

    first_day = date(year, month, 1)
    last_day = date(year, month, _cal.monthrange(year, month)[1])
    
    # Находим понедельник для начала календаря
    today = date.today()
    if today.year == year and today.month == month:
        # Если смотрим текущий месяц - начинаем за 2 недели до текущей
        current_monday = today - timedelta(days=today.weekday())
        first_monday = current_monday - timedelta(weeks=2)
    else:
        # Для других месяцев - начинаем с первого понедельника месяца
        first_monday = first_day - timedelta(days=first_day.weekday())

    calendar_grid: List[List[Dict[str, Any]]] = []
    current_date = first_monday

    for _ in range(6):
        week_data: List[Dict[str, Any]] = []
        for _d in range(7):
            current_date_str = current_date.isoformat()

            # Смены за день
            all_day_shifts = [s for s in shifts if s.get("date") == current_date_str]
            day_shifts = [s for s in all_day_shifts if s.get("status") != "cancelled"]

            # Тайм-слоты за день
            day_timeslots = []
            for slot in timeslots:
                if slot.get("date") == current_date_str and slot.get("is_active", True):
                    slot_with_status = slot.copy()
                    slot_with_status["status"] = "available"
                    day_timeslots.append(slot_with_status)

            week_data.append({
                "date": current_date,
                "day": current_date.day,
                "is_current_month": current_date.month == month,
                "is_other_month": current_date.month != month,
                "is_today": current_date == date.today(),
                "timeslots": day_timeslots,
                "timeslots_count": len(day_timeslots),
                "shifts": day_shifts,
                "shifts_count": len(day_shifts),
            })

            current_date += timedelta(days=1)

        calendar_grid.append(week_data)

    return calendar_grid


@router.get("/shifts", response_class=HTMLResponse)
async def employee_shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр: active, planned, completed, cancelled"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Табличный список смен сотрудника (по аналогии с владельцем)."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user

        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")

        # Фильтр периода
        from datetime import datetime as _dt, time as _time
        df = _dt.strptime(date_from, "%Y-%m-%d") if date_from else None
        dt = _dt.strptime(date_to, "%Y-%m-%d") if date_to else None

        # Фактические смены
        from sqlalchemy import select, desc, and_
        shifts_q = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.user)
        ).where(Shift.user_id == user_id)
        if df:
            shifts_q = shifts_q.where(Shift.start_time >= df)
        if dt:
            shifts_q = shifts_q.where(Shift.start_time <= dt)

        # Запланированные смены
        schedules_q = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user)
        ).where(ShiftSchedule.user_id == user_id)
        if df:
            schedules_q = schedules_q.where(ShiftSchedule.planned_start >= df)
        if dt:
            schedules_q = schedules_q.where(ShiftSchedule.planned_start <= dt)

        # Получение
        shifts = (await db.execute(shifts_q.order_by(desc(Shift.created_at)))).scalars().all()
        schedules = (await db.execute(schedules_q.order_by(desc(ShiftSchedule.created_at)))).scalars().all()

        # Форматирование
        all_shifts = []
        for s in shifts:
            all_shifts.append({
                'id': s.id,
                'type': 'shift',
                'object_name': s.object.name if s.object else '-',
                'user_name': f"{s.user.first_name} {s.user.last_name or ''}".strip() if s.user else '-',
                'start_time': web_timezone_helper.format_datetime_with_timezone(s.start_time, s.object.timezone if s.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if s.start_time else '-',
                'end_time': web_timezone_helper.format_datetime_with_timezone(s.end_time, s.object.timezone if s.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if s.end_time else '-',
                'status': s.status,
                'total_hours': float(s.total_hours) if s.total_hours else None,
                'total_payment': float(s.total_payment) if s.total_payment else None,
            })
        for sc in schedules:
            all_shifts.append({
                'id': sc.id,
                'type': 'schedule',
                'object_name': sc.object.name if sc.object else '-',
                'user_name': f"{sc.user.first_name} {sc.user.last_name or ''}".strip() if sc.user else '-',
                'start_time': web_timezone_helper.format_datetime_with_timezone(sc.planned_start, sc.object.timezone if sc.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if sc.planned_start else '-',
                'end_time': web_timezone_helper.format_datetime_with_timezone(sc.planned_end, sc.object.timezone if sc.object else 'Europe/Moscow', '%Y-%m-%d %H:%M') if sc.planned_end else '-',
                'status': sc.status,
                'total_hours': None,
                'total_payment': None,
            })

        # Фильтр статуса
        if status:
            if status == 'planned':
                all_shifts = [x for x in all_shifts if x['type'] == 'schedule']
            else:
                all_shifts = [x for x in all_shifts if x['status'] == status]

        # Сортировка и пагинация
        all_shifts.sort(key=lambda x: x['start_time'] or '', reverse=True)
        total = len(all_shifts)
        start_i = (page - 1) * per_page
        end_i = start_i + per_page
        page_shifts = all_shifts[start_i:end_i]

        # Интерфейсы
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Подсчет заявок для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0

        return templates.TemplateResponse("employee/shifts/list.html", {
            "request": request,
            "current_user": current_user,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "shifts": page_shifts,
            "stats": {
                "total": total,
                "active": len([s for s in all_shifts if s['status'] == 'active']),
                "planned": len([s for s in all_shifts if s['type'] == 'schedule']),
                "completed": len([s for s in all_shifts if s['status'] == 'completed'])
            },
            "filters": {"status": status, "date_from": date_from, "date_to": date_to},
            "pagination": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1)//per_page}
        })
    except Exception as e:
        logger.error(f"Error loading employee shifts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка загрузки смен сотрудника")

@router.get("/profile", response_class=HTMLResponse)
async def employee_profile(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница профиля сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем данные пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Статистика профиля
        logger.info(f"Getting applications count for user_id: {user_id}")
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        logger.info(f"Applications count: {applications_count}")
        
        interviews_count = await db.execute(
            select(func.count(Interview.id)).where(Interview.applicant_id == user_id)
        )
        interviews_count = interviews_count.scalar() or 0
        
        successful_count = await db.execute(
            select(func.count(Application.id)).where(
                and_(Application.applicant_id == user_id, Application.status == 'APPROVED')
            )
        )
        successful_count = successful_count.scalar() or 0
        
        in_progress_count = await db.execute(
            select(func.count(Application.id)).where(
                and_(Application.applicant_id == user_id, Application.status == 'PENDING')
            )
        )
        in_progress_count = in_progress_count.scalar() or 0
        
        logger.info(f"Creating profile_stats with applications_count: {applications_count}")
        profile_stats = {
            'applications': applications_count,
            'interviews': interviews_count,
            'successful': successful_count,
            'in_progress': in_progress_count
        }
        logger.info(f"Profile stats created: {profile_stats}")
        
        # Категории работы
        work_categories = [
            "Уборка и санитария",
            "Обслуживание клиентов", 
            "Безопасность",
            "Техническое обслуживание",
            "Административные задачи",
            "Продажи и маркетинг",
            "Складские операции",
            "Специализированные задачи"
        ]
        
        return templates.TemplateResponse("employee/profile.html", {
            "request": request,
            "current_user": user,
            "user": user,
            "profile_stats": profile_stats,
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "work_categories": work_categories,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки профиля: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки профиля: {e}")


@router.post("/profile")
async def employee_profile_update(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Обновление профиля сотрудника"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные из формы
        try:
            # Попробуем получить JSON данные
            json_data = await request.json()
            logger.info(f"Received JSON data: {json_data}")
            form_data = json_data
        except:
            # Если не JSON, то form data
            form_data = await request.form()
            logger.info(f"Received form data: {dict(form_data)}")
        
        # Получаем пользователя
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        # Обновляем поля с правильной кодировкой
        if 'first_name' in form_data:
            user.first_name = form_data['first_name']
            logger.info(f"Updated first_name: {user.first_name}")
        if 'last_name' in form_data:
            user.last_name = form_data['last_name']
            logger.info(f"Updated last_name: {user.last_name}")
        if 'phone' in form_data:
            user.phone = form_data['phone']
            logger.info(f"Updated phone: {user.phone}")
        if 'email' in form_data:
            user.email = form_data['email'] or None
            logger.info(f"Updated email: {user.email}")
        if 'birth_date' in form_data:
            birth_date_str = form_data['birth_date']
            if birth_date_str:
                try:
                    from datetime import datetime
                    user.birth_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                    logger.info(f"Updated birth_date: {user.birth_date}")
                except ValueError:
                    logger.error(f"Invalid birth_date format: {birth_date_str}")
            else:
                user.birth_date = None
        if 'work_experience' in form_data:
            user.work_experience = form_data['work_experience']
        if 'education' in form_data:
            user.education = form_data['education']
        if 'skills' in form_data:
            user.skills = form_data['skills']
        if 'about' in form_data:
            user.about = form_data['about']
        if 'preferred_schedule' in form_data:
            user.preferred_schedule = form_data['preferred_schedule']
        if 'min_salary' in form_data:
            min_salary_str = form_data['min_salary']
            if min_salary_str and min_salary_str.isdigit():
                user.min_salary = int(min_salary_str)
                logger.info(f"Updated min_salary: {user.min_salary}")
            else:
                user.min_salary = None
        if 'availability_notes' in form_data:
            user.availability_notes = form_data['availability_notes']
        if 'preferred_work_types' in form_data:
            # Для чекбоксов form_data может быть списком или строкой
            work_types = form_data.get('preferred_work_types')
            if isinstance(work_types, list):
                user.preferred_work_types = work_types
            elif isinstance(work_types, str):
                user.preferred_work_types = [work_types]
            else:
                user.preferred_work_types = []
            logger.info(f"Updated preferred_work_types: {user.preferred_work_types}")
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Profile updated for user {user_id}")
        
        result = {"success": True, "message": "Профиль успешно обновлен"}
        logger.info(f"Returning result: {result}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка обновления профиля")


@router.get("/history", response_class=HTMLResponse)
async def employee_history(
    request: Request,
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница истории активности: заявки, собеседования, смены."""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
            
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем статистику для навигации
        applications_count = await db.execute(
            select(func.count(Application.id)).where(Application.applicant_id == user_id)
        )
        applications_count = applications_count.scalar() or 0
        
        # Период
        from datetime import datetime as _dt
        df = _dt.strptime(date_from, "%Y-%m-%d").date() if date_from else None
        dt = _dt.strptime(date_to, "%Y-%m-%d").date() if date_to else None

        # Получаем историю событий
        history_events = []
        
        # Заявки
        applications_query = select(Application, Object.name.label('object_name')).join(
            Object, Application.object_id == Object.id
        ).where(Application.applicant_id == user_id).order_by(Application.created_at.desc())
        
        applications_result = await db.execute(applications_query)
        for row in applications_result:
            history_events.append({
                'id': row.Application.id,
                'type': 'application',
                'title': f'Подана заявка на работу',
                'description': f'Заявка на объект "{row.object_name}"',
                'object_name': row.object_name,
                'status': row.Application.status,
                'created_at': row.Application.created_at,
                'start': row.Application.created_at,
                'end': None
            })
        
        # Собеседования
        interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(Interview.applicant_id == user_id)
        if df:
            interviews_query = interviews_query.where(Interview.scheduled_at >= df)
        if dt:
            # включительно конец дня
            from datetime import datetime, time
            interviews_query = interviews_query.where(Interview.scheduled_at <= datetime.combine(dt, time.max))
        interviews_query = interviews_query.order_by(Interview.scheduled_at.desc())
        
        interviews_result = await db.execute(interviews_query)
        for row in interviews_result:
            history_events.append({
                'id': row.Interview.id,
                'type': 'interview',
                'title': f'Собеседование',
                'description': f'Собеседование на объекте "{row.object_name}"',
                'object_name': row.object_name,
                'status': row.Interview.status,
                'created_at': row.Interview.scheduled_at,
                'start': row.Interview.scheduled_at,
                'end': None
            })
        
        # Смены сотрудника: запланированные (расписание), фактические (смены)
        # Запланированные
        sched_q = select(ShiftSchedule, Object.name.label('object_name')).join(
            Object, ShiftSchedule.object_id == Object.id
        ).where(ShiftSchedule.user_id == user_id)
        if df:
            sched_q = sched_q.where(ShiftSchedule.planned_start >= df)
        if dt:
            from datetime import datetime, time
            sched_q = sched_q.where(ShiftSchedule.planned_start <= datetime.combine(dt, time.max))
        sched_q = sched_q.order_by(ShiftSchedule.planned_start.desc())

        sched_res = await db.execute(sched_q)
        for row in sched_res:
            history_events.append({
                'id': row.ShiftSchedule.id,
                'type': 'planned_shift',
                'title': 'Запланирована смена',
                'description': f"Объект \"{row.object_name}\"",
                'object_name': row.object_name,
                'status': row.ShiftSchedule.status,
                'created_at': row.ShiftSchedule.planned_start,
                'start': row.ShiftSchedule.planned_start,
                'end': row.ShiftSchedule.planned_end,
                'is_cancellable': row.ShiftSchedule.status == 'planned'
            })

        # Фактические (активные/завершенные/отмененные)
        shift_q = select(Shift, Object.name.label('object_name')).join(
            Object, Shift.object_id == Object.id
        ).where(Shift.user_id == user_id)
        if df:
            shift_q = shift_q.where(Shift.start_time >= df)
        if dt:
            from datetime import datetime, time
            shift_q = shift_q.where(Shift.start_time <= datetime.combine(dt, time.max))
        shift_q = shift_q.order_by(Shift.start_time.desc())

        shift_res = await db.execute(shift_q)
        # Подсчет заработка по завершенным сменам
        total_earned_period = 0.0
        for row in shift_res:
            earned = None
            if row.Shift.status == 'completed':
                if row.Shift.total_payment:
                    earned = float(row.Shift.total_payment)
                elif row.Shift.start_time and row.Shift.end_time and row.Shift.hourly_rate:
                    duration = (row.Shift.end_time - row.Shift.start_time).total_seconds() / 3600.0
                    earned = float(row.Shift.hourly_rate) * max(0.0, duration)
                if earned:
                    total_earned_period += earned

            history_events.append({
                'id': row.Shift.id,
                'type': 'shift',
                'title': 'Смена',
                'description': f"Объект \"{row.object_name}\"",
                'object_name': row.object_name,
                'status': row.Shift.status,
                'created_at': row.Shift.start_time,
                'start': row.Shift.start_time,
                'end': row.Shift.end_time,
                'earned': earned
            })

        # Сортируем по дате
        history_events.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Статистика
        stats = {
            'total_applications': len([e for e in history_events if e['type'] == 'application']),
            'total_interviews': len([e for e in history_events if e['type'] == 'interview']),
            'total_shifts': len([e for e in history_events if e['type'] in ('shift', 'planned_shift')]),
            'completed_shifts': len([e for e in history_events if e.get('status') == 'completed']),
            'planned_shifts': len([e for e in history_events if e['type'] == 'planned_shift' and e.get('status') == 'planned']),
            'cancelled_shifts': len([e for e in history_events if e.get('status') == 'cancelled']),
            'earned_period': round(total_earned_period, 2),
            'success_rate': 0
        }
        
        successful_applications = len([e for e in history_events if e['type'] == 'application' and e['status'] == 'APPROVED'])
        if stats['total_applications'] > 0:
            stats['success_rate'] = round((successful_applications / stats['total_applications']) * 100)
        
        return templates.TemplateResponse("employee/history.html", {
        "request": request,
        "current_user": current_user,
            "history_events": history_events,
            "stats": stats,
            "available_interfaces": available_interfaces,
            "applications_count": applications_count,
            "date_from": date_from,
            "date_to": date_to
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки истории: {e}")


@router.get("/api/calendar/data")
async def employee_calendar_api_data(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    object_ids: Optional[str] = Query(None, description="ID объектов через запятую"),
    current_user: dict = Depends(get_current_user_dependency()),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Новый универсальный API для получения данных календаря сотрудника.
    Использует CalendarFilterService для правильной фильтрации смен.
    """
    try:
        # Парсим даты
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты. Используйте YYYY-MM-DD")
        
        # Парсим фильтр объектов
        object_filter = None
        if object_ids:
            try:
                object_filter = [int(obj_id.strip()) for obj_id in object_ids.split(",") if obj_id.strip()]
            except ValueError:
                raise HTTPException(status_code=400, detail="Неверный формат ID объектов")
        
        # Получаем роль пользователя
        user_role = current_user.get("role", "employee")
        user_telegram_id = current_user.get("id")
        
        if not user_telegram_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем данные календаря через универсальный сервис
        calendar_service = CalendarFilterService(db)
        calendar_data = await calendar_service.get_calendar_data(
            user_telegram_id=user_telegram_id,
            user_role=user_role,
            date_range_start=start_date_obj,
            date_range_end=end_date_obj,
            object_filter=object_filter
        )
        
        # Преобразуем в формат, совместимый с существующим JavaScript
        timeslots_data = []
        for ts in calendar_data.timeslots:
            timeslots_data.append({
                "id": ts.id,
                "object_id": ts.object_id,
                "object_name": ts.object_name,
                "date": ts.date.isoformat(),
                "start_time": ts.start_time.strftime("%H:%M"),
                "end_time": ts.end_time.strftime("%H:%M"),
                "hourly_rate": ts.hourly_rate,
                "max_employees": ts.max_employees,
                "current_employees": ts.current_employees,
                "available_slots": ts.available_slots,
                "status": ts.status.value,
                "is_active": ts.is_active,
                "notes": ts.notes,
                "work_conditions": ts.work_conditions,
                "shift_tasks": ts.shift_tasks,
                "coordinates": ts.coordinates,
                "can_edit": ts.can_edit,
                "can_plan": ts.can_plan,
                "can_view": ts.can_view
            })
        
        shifts_data = []
        for s in calendar_data.shifts:
            shifts_data.append({
                "id": s.id,
                "user_id": s.user_id,
                "user_name": s.user_name,
                "object_id": s.object_id,
                "object_name": s.object_name,
                "time_slot_id": s.time_slot_id,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "planned_start": s.planned_start.isoformat() if s.planned_start else None,
                "planned_end": s.planned_end.isoformat() if s.planned_end else None,
                "shift_type": s.shift_type.value,
                "status": s.status.value,
                "hourly_rate": s.hourly_rate,
                "total_hours": s.total_hours,
                "total_payment": s.total_payment,
                "notes": s.notes,
                "is_planned": s.is_planned,
                "schedule_id": s.schedule_id,
                "actual_shift_id": s.actual_shift_id,
                "start_coordinates": s.start_coordinates,
                "end_coordinates": s.end_coordinates,
                "can_edit": s.can_edit,
                "can_cancel": s.can_cancel,
                "can_view": s.can_view
            })
        
        return {
            "timeslots": timeslots_data,
            "shifts": shifts_data,
            "metadata": {
                "date_range_start": calendar_data.date_range_start.isoformat(),
                "date_range_end": calendar_data.date_range_end.isoformat(),
                "user_role": calendar_data.user_role,
                "total_timeslots": calendar_data.total_timeslots,
                "total_shifts": calendar_data.total_shifts,
                "planned_shifts": calendar_data.planned_shifts,
                "active_shifts": calendar_data.active_shifts,
                "completed_shifts": calendar_data.completed_shifts,
                "accessible_objects": calendar_data.accessible_objects
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting employee calendar data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка получения данных календаря")


@router.post("/api/calendar/plan-shift")
async def employee_plan_shift(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """API: сотрудник планирует смену для себя на тайм-слот."""
    try:
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(status_code=401, detail="Необходима авторизация")
        
        data = await request.json()
        timeslot_id = data.get('timeslot_id')
        employee_id = data.get('employee_id')
        
        if not timeslot_id:
            raise HTTPException(status_code=400, detail="Не указан ID тайм-слота")
        
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Проверяем что сотрудник планирует смену только для себя
        if int(employee_id) != int(user_id):
            raise HTTPException(status_code=403, detail="Можно планировать смену только для себя")
        
        # Получаем тайм-слот
        from domain.entities.time_slot import TimeSlot
        from domain.entities.contract import Contract
        timeslot = (await db.execute(select(TimeSlot).options(selectinload(TimeSlot.object)).where(TimeSlot.id == timeslot_id))).scalar_one_or_none()
        
        if not timeslot:
            raise HTTPException(status_code=404, detail="Тайм-слот не найден")
        
        # Проверяем что у сотрудника есть активный договор с доступом к этому объекту
        contracts = (await db.execute(
            select(Contract).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.is_active == True,
                    Contract.status == 'active'
                )
            )
        )).scalars().all()
        
        has_access = False
        import json as _json
        for contract in contracts:
            if contract.allowed_objects:
                allowed = contract.allowed_objects if isinstance(contract.allowed_objects, list) else _json.loads(contract.allowed_objects)
                if timeslot.object_id in allowed:
                    has_access = True
                    break
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Нет доступа к объекту")
        
        # Проверяем что тайм-слот еще не занят
        existing_schedules = (await db.execute(
            select(ShiftSchedule).where(
                and_(
                    ShiftSchedule.time_slot_id == timeslot_id,
                    ShiftSchedule.status.in_(['planned', 'confirmed'])
                )
            )
        )).scalars().all()
        
        if len(existing_schedules) >= (timeslot.max_employees or 1):
            raise HTTPException(status_code=400, detail="Тайм-слот уже занят")
        
        # Создаем запланированную смену
        import pytz
        object_timezone = timeslot.object.timezone if timeslot.object and timeslot.object.timezone else 'Europe/Moscow'
        tz = pytz.timezone(object_timezone)
        
        slot_datetime_naive = datetime.combine(timeslot.slot_date, timeslot.start_time)
        end_datetime_naive = datetime.combine(timeslot.slot_date, timeslot.end_time)
        
        slot_datetime = tz.localize(slot_datetime_naive).astimezone(pytz.UTC).replace(tzinfo=None)
        end_datetime = tz.localize(end_datetime_naive).astimezone(pytz.UTC).replace(tzinfo=None)
        
        shift_schedule = ShiftSchedule(
            user_id=user_id,
            object_id=timeslot.object_id,
            time_slot_id=timeslot_id,
            planned_start=slot_datetime,
            planned_end=end_datetime,
            status='planned',
            hourly_rate=float(timeslot.hourly_rate) if timeslot.hourly_rate else float(timeslot.object.hourly_rate) if timeslot.object else 0,
            notes=''
        )
        
        db.add(shift_schedule)
        await db.commit()
        await db.refresh(shift_schedule)
        
        logger.info(f"Employee {user_id} successfully planned shift {shift_schedule.id} for timeslot {timeslot_id}")
        return {
            "success": True,
            "message": "Смена успешно запланирована",
            "shift_id": shift_schedule.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error planning shift for employee: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка планирования смены: {str(e)}")


@router.post("/api/shifts/cancel")
async def employee_cancel_planned_shift(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant)
):
    """Отмена запланированной смены сотрудником (смена в ShiftSchedule)."""
    try:
        data = await request.json()
        schedule_id = data.get('schedule_id')
        if not schedule_id:
            raise HTTPException(status_code=400, detail="Не указан ID запланированной смены")

        async with get_async_session() as db:
            user_id = await get_user_id_from_current_user(current_user, db)
            if not user_id:
                raise HTTPException(status_code=401, detail="Пользователь не найден")

            # Найдем запланированную смену и проверим владельца
            from sqlalchemy import select
            schedule = (await db.execute(select(ShiftSchedule).where(ShiftSchedule.id == schedule_id))).scalar_one_or_none()
            if not schedule:
                raise HTTPException(status_code=404, detail="Запланированная смена не найдена")
            if int(schedule.user_id) != int(user_id):
                raise HTTPException(status_code=403, detail="Нельзя отменить чужую смену")
            if schedule.status != 'planned':
                raise HTTPException(status_code=400, detail="Можно отменять только запланированные смены")

            schedule.status = 'cancelled'
            await db.commit()
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling planned shift: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка отмены смены")