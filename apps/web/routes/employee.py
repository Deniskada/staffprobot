"""
Роуты для интерфейса сотрудника (соискателя)
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, date, timedelta
import logging

from apps.web.dependencies import get_current_user_dependency
from core.database.session import get_db_session
from apps.web.middleware.role_middleware import require_employee_or_applicant
from domain.entities import User, Object, Application, Interview, ShiftSchedule, Shift
from apps.web.utils.timezone_utils import WebTimezoneHelper
from shared.services.role_based_login_service import RoleBasedLoginService

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="apps/web/templates")

# Инициализируем помощник для работы с временными зонами
web_timezone_helper = WebTimezoneHelper()

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
        
        return templates.TemplateResponse("employee/index.html", {
            "request": request,
            "current_user": current_user,
            "current_date": datetime.now(),
            "applications_count": applications_count,
            "interviews_count": interviews_count,
            "available_objects_count": available_objects_count,
            "history_count": history_count,
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
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем доступные объекты
        objects_query = select(Object).where(Object.available_for_applicants == True)
        objects_result = await db.execute(objects_query)
        objects = []
        
        for obj in objects_result.scalars():
            objects.append({
                'id': obj.id,
                'name': obj.name,
                'address': obj.address,
                'latitude': obj.latitude,
                'longitude': obj.longitude,
                'opening_time': obj.opening_time.strftime('%H:%M'),
                'closing_time': obj.closing_time.strftime('%H:%M'),
                'hourly_rate': obj.hourly_rate,
                'work_conditions': obj.work_conditions,
                'shift_tasks': obj.shift_tasks or []
            })
        
        return templates.TemplateResponse("employee/objects.html", {
            "request": request,
            "current_user": current_user,
            "objects": objects,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки объектов: {e}")
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
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
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
                'status': row.Application.status,
                'message': row.Application.message,
                'preferred_schedule': row.Application.preferred_schedule,
                'created_at': row.Application.created_at,
                'interview_scheduled_at': row.Application.interview_scheduled_at,
                'interview_type': row.Application.interview_type,
                'interview_result': row.Application.interview_result
            })
        
        # Статистика заявок
        applications_stats = {
            'pending': len([a for a in applications if a['status'] == 'PENDING']),
            'approved': len([a for a in applications if a['status'] == 'APPROVED']),
            'rejected': len([a for a in applications if a['status'] == 'REJECTED']),
            'interview': len([a for a in applications if a['status'] == 'INTERVIEW'])
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
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки заявок: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки заявок: {e}")

@router.get("/calendar", response_class=HTMLResponse)
async def employee_calendar(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница календаря собеседований"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
        # Получаем собеседования
        interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(Interview.applicant_id == user_id).order_by(Interview.scheduled_at.desc())
        
        interviews_result = await db.execute(interviews_query)
        interviews = []
        for row in interviews_result:
            interviews.append({
                'id': row.Interview.id,
                'object_id': row.Interview.object_id,
                'object_name': row.object_name,
                'scheduled_at': row.Interview.scheduled_at,
                'type': row.Interview.type,
                'location': row.Interview.location,
                'contact_person': row.Interview.contact_person,
                'contact_phone': row.Interview.contact_phone,
                'notes': row.Interview.notes,
                'status': row.Interview.status,
                'result': row.Interview.result
            })
        
        # Статистика собеседований
        today = datetime.now().date()
        interviews_stats = {
            'scheduled': len([i for i in interviews if i['status'] == 'SCHEDULED']),
            'completed': len([i for i in interviews if i['status'] == 'COMPLETED']),
            'today': len([i for i in interviews if i['scheduled_at'].date() == today]),
            'cancelled': len([i for i in interviews if i['status'] == 'CANCELLED'])
        }
        
        # Ближайшие собеседования
        upcoming_interviews = [i for i in interviews if i['scheduled_at'] >= datetime.now()][:5]
        
        return templates.TemplateResponse("employee/calendar.html", {
            "request": request,
            "current_user": current_user,
            "interviews_stats": interviews_stats,
            "upcoming_interviews": upcoming_interviews,
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки календаря: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки календаря: {e}")

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
        if 'work_experience' in form_data:
            user.work_experience = form_data['work_experience']
        if 'skills' in form_data:
            user.skills = form_data['skills']
        if 'preferred_schedule' in form_data:
            user.preferred_schedule = form_data['preferred_schedule']
        if 'availability_notes' in form_data:
            user.availability_notes = form_data['availability_notes']
        
        # Сохраняем изменения
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Profile updated for user {user_id}")
        
        return {"success": True, "message": "Профиль успешно обновлен"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Ошибка обновления профиля")


@router.get("/history", response_class=HTMLResponse)
async def employee_history(
    request: Request,
    current_user: dict = Depends(require_employee_or_applicant),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница истории активности"""
    try:
        # Проверяем, что current_user не является RedirectResponse
        if isinstance(current_user, RedirectResponse):
            return current_user
            
        
        user_id = await get_user_id_from_current_user(current_user, db)
        available_interfaces = await get_available_interfaces_for_user(current_user, db)
        
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
                'created_at': row.Application.created_at
            })
        
        # Собеседования
        interviews_query = select(Interview, Object.name.label('object_name')).join(
            Object, Interview.object_id == Object.id
        ).where(Interview.applicant_id == user_id).order_by(Interview.scheduled_at.desc())
        
        interviews_result = await db.execute(interviews_query)
        for row in interviews_result:
            history_events.append({
                'id': row.Interview.id,
                'type': 'interview',
                'title': f'Собеседование',
                'description': f'Собеседование на объекте "{row.object_name}"',
                'object_name': row.object_name,
                'status': row.Interview.status,
                'created_at': row.Interview.scheduled_at
            })
        
        # Сортируем по дате
        history_events.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Статистика
        stats = {
            'total_applications': len([e for e in history_events if e['type'] == 'application']),
            'total_interviews': len([e for e in history_events if e['type'] == 'interview']),
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
            "available_interfaces": available_interfaces
        })
    except Exception as e:
        logger.error(f"Ошибка загрузки истории: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки истории: {e}")