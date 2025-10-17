from fastapi import APIRouter, Request, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.auth.user_manager import UserManager
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from domain.entities.user import User
from apps.web.utils.timezone_utils import web_timezone_helper

router = APIRouter()
from apps.web.jinja import templates
user_manager = UserManager()


async def get_user_id_from_current_user(current_user, session):
    """Получает внутренний ID пользователя из current_user"""
    if isinstance(current_user, dict):
        telegram_id = current_user.get("id")
        user_query = select(User).where(User.telegram_id == telegram_id)
        user_result = await session.execute(user_query)
        user_obj = user_result.scalar_one_or_none()
        return user_obj.id if user_obj else None
    else:
        return current_user.id


@router.get("/", response_class=HTMLResponse)
async def shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр по статусу: active, planned, completed"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    object_id: Optional[str] = Query(None, description="ID объекта"),
    sort: Optional[str] = Query(None, description="Поле сортировки: user_name, object_name, start_time, status, created_at"),
    order: Optional[str] = Query("asc", description="Порядок сортировки: asc, desc"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Количество на странице")
):
    """Список смен с фильтрацией"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем ID пользователя из словаря
    # current_user содержит telegram_id в поле "id", нужно получить внутренний ID из БД
    if isinstance(current_user, dict):
        telegram_id = current_user.get("id")
        user_role = current_user.get("role")
        # Получаем внутренний ID пользователя из БД
        async with get_async_session() as temp_session:
            user_query = select(User).where(User.telegram_id == telegram_id)
            user_result = await temp_session.execute(user_query)
            user_obj = user_result.scalar_one_or_none()
            user_id = user_obj.id if user_obj else None
    else:
        user_id = current_user.id
        user_role = current_user.role
    
    async with get_async_session() as session:
        # Базовый запрос для смен
        shifts_query = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.user)
        )
        
        # Базовый запрос для запланированных смен
        schedules_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object),
            selectinload(ShiftSchedule.user)
        )
        
        # Фильтрация по владельцу
        if user_role != "superadmin":
            # Получаем объекты владельца
            owner_objects = select(Object.id).where(Object.owner_id == user_id)
            shifts_query = shifts_query.where(Shift.object_id.in_(owner_objects))
            schedules_query = schedules_query.where(ShiftSchedule.object_id.in_(owner_objects))
        
        # Применение фильтров
        if status:
            if status == "active":
                shifts_query = shifts_query.where(Shift.status == "active")
            elif status == "planned":
                # Для запланированных смен используем ShiftSchedule
                pass
            elif status == "completed":
                shifts_query = shifts_query.where(Shift.status == "completed")
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            shifts_query = shifts_query.where(Shift.start_time >= date_from_obj)
            schedules_query = schedules_query.where(ShiftSchedule.planned_start >= date_from_obj)
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            shifts_query = shifts_query.where(Shift.start_time <= date_to_obj)
            schedules_query = schedules_query.where(ShiftSchedule.planned_start <= date_to_obj)
        
        if object_id and object_id.strip():
            try:
                object_id_int = int(object_id)
                shifts_query = shifts_query.where(Shift.object_id == object_id_int)
                schedules_query = schedules_query.where(ShiftSchedule.object_id == object_id_int)
            except ValueError:
                # Если object_id не является числом, игнорируем фильтр
                pass
        
        # Получение данных
        shifts_result = await session.execute(shifts_query.order_by(desc(Shift.start_time)))
        shifts = shifts_result.scalars().all()
        
        schedules_result = await session.execute(schedules_query.order_by(desc(ShiftSchedule.planned_start)))
        schedules = schedules_result.scalars().all()
        
        # Объединение и сортировка
        all_shifts = []
        
        # Добавляем реальные смены (отработанные) без динамического перерасчета
        for shift in shifts:
            all_shifts.append({
                'id': shift.id,
                'type': 'shift',
                'user': shift.user,
                'object': shift.object,
                'start_time': shift.start_time,
                'end_time': shift.end_time,
                'status': shift.status,
                'total_hours': getattr(shift, 'total_hours', None),
                'hourly_rate': shift.hourly_rate,
                'total_payment': getattr(shift, 'total_payment', None),
                'notes': shift.notes,
                'created_at': shift.created_at,
                'is_planned': shift.is_planned,
                'schedule_id': shift.schedule_id
            })
        
        # Добавляем запланированные смены (если не отфильтрованы)
        if not status or status == "planned":
            for schedule in schedules:
                # Плановые часы/оплата для planned/confirmed
                planned_hours = None
                planned_payment = None
                try:
                    if str(schedule.status) in ['planned', 'confirmed']:
                        # Вычисляем длительность из planned_end - planned_start
                        if schedule.planned_end and schedule.planned_start:
                            duration = schedule.planned_end - schedule.planned_start
                            planned_hours = round(duration.total_seconds() / 3600, 2)
                        
                        # Вычисляем оплату как planned_hours * hourly_rate
                        if planned_hours is not None and schedule.hourly_rate is not None:
                            planned_payment = round(planned_hours * float(schedule.hourly_rate), 2)
                        
                except Exception:
                    planned_hours = None
                    planned_payment = None
                
                all_shifts.append({
                    'id': schedule.id,
                    'type': 'schedule',
                    'user': schedule.user,
                    'object': schedule.object,
                    'start_time': schedule.planned_start,
                    'end_time': schedule.planned_end,
                    'status': schedule.status,
                    'total_hours': planned_hours,
                    'hourly_rate': schedule.hourly_rate,
                    'total_payment': planned_payment,
                    'notes': schedule.notes,
                    'created_at': schedule.created_at,
                    'is_planned': True,
                    'schedule_id': schedule.id
                })
        
        # Сортировка
        if sort:
            reverse = (order == "desc")
            def sort_key(item):
                if sort == "user_name":
                    u = item.get('user')
                    return (f"{u.first_name} {u.last_name or ''}".lower() if u else "")
                if sort == "object_name":
                    o = item.get('object')
                    return (o.name.lower() if o and o.name else "")
                if sort == "start_time":
                    return item.get('start_time') or datetime.min
                if sort == "status":
                    return item.get('status') or ""
                if sort == "created_at":
                    return item.get('created_at') or datetime.min
                return item.get('created_at') or datetime.min
            all_shifts.sort(key=sort_key, reverse=reverse)
        else:
            # По умолчанию сортировка по времени начала (новые сверху)
            all_shifts.sort(key=lambda x: x['start_time'] or datetime.min, reverse=True)
        
        # Пагинация
        total = len(all_shifts)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_shifts = all_shifts[start:end]
        
        # Получение объектов для фильтра
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await session.execute(objects_query)
        objects = objects_result.scalars().all()
        
        # Преобразование данных для шаблона
        formatted_shifts = []
        for shift in paginated_shifts:
            # Форматирование времени с учетом часового пояса объекта
            tz_name = shift['object'].timezone if shift['object'] else 'Europe/Moscow'
            start_time_str = web_timezone_helper.format_datetime_with_timezone(shift['start_time'], tz_name, '%d.%m.%Y %H:%M') if shift['start_time'] else '-'
            end_time_str = web_timezone_helper.format_datetime_with_timezone(shift['end_time'], tz_name, '%d.%m.%Y %H:%M') if shift['end_time'] else None
            
            formatted_shifts.append({
                'id': shift['id'],
                'type': shift['type'],
                'user_id': shift['user'].id if shift['user'] else None,
                'user_name': f"{shift['user'].first_name} {shift['user'].last_name or ''}".strip() if shift['user'] else 'Неизвестно',
                'object_id': shift['object'].id if shift['object'] else None,
                'object_name': shift['object'].name if shift['object'] else 'Неизвестно',
                'start_time': start_time_str,
                'end_time': end_time_str,
                'status': shift['status'],
                'total_hours': shift['total_hours'],
                'hourly_rate': shift['hourly_rate'],
                'total_payment': shift['total_payment'],
                'notes': shift['notes'],
                'created_at': shift['created_at'],
                'is_planned': shift['is_planned'],
                'schedule_id': shift['schedule_id']
            })
        
        # Статистика
        stats = {
            'total': total,
            'active': len([s for s in all_shifts if s['status'] == 'active']),
            'planned': len([s for s in all_shifts if s['type'] == 'schedule']),
            'completed': len([s for s in all_shifts if s['status'] == 'completed'])
        }
        
        return templates.TemplateResponse("owner/shifts/list.html", {
            "request": request,
            "current_user": current_user,
            "shifts": formatted_shifts,
            "objects": objects,
            "stats": stats,
            "filters": {
                "status": status,
                "date_from": date_from,
                "date_to": date_to,
                "object_id": object_id
            },
            "sort": {"field": sort, "order": order},
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }
        })


@router.get("/{shift_id}", response_class=HTMLResponse)
async def shift_detail(request: Request, shift_id: int, shift_type: Optional[str] = Query("shift")):
    """Детали смены"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем роль пользователя
    user_role = current_user.get("role") if isinstance(current_user, dict) else current_user.role
    
    async with get_async_session() as session:
        # Получаем внутренний ID пользователя
        user_id = await get_user_id_from_current_user(current_user, session)
        if shift_type == "schedule":
            # Запланированная смена
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.user)
            ).where(ShiftSchedule.id == shift_id)
        else:
            # Реальная смена
            query = select(Shift).options(
                selectinload(Shift.object),
                selectinload(Shift.user)
            ).where(Shift.id == shift_id)
        
        result = await session.execute(query)
        shift = result.scalar_one_or_none()
        
        if not shift:
            return templates.TemplateResponse("owner/shifts/not_found.html", {
                "request": request,
                "current_user": current_user
            })
        
        # Проверка прав доступа
        if user_role != "superadmin":
            if shift.object.owner_id != user_id:
                return templates.TemplateResponse("owner/shifts/access_denied.html", {
                    "request": request,
                    "current_user": current_user
                })
        
        # Загрузить задачи смены
        shift_tasks = []
        from shared.services.shift_task_journal import ShiftTaskJournal
        from domain.entities.timeslot_task_template import TimeslotTaskTemplate
        
        if shift_type == "shift":
            # Реальная смена: синхронизировать журнал и читать из него
            journal = ShiftTaskJournal(session)
            tasks_entities = await journal.get_by_shift(shift_id)
            
            # Если журнал пуст - синхронизировать из конфигурации
            if not tasks_entities:
                tasks_entities = await journal.sync_from_config(
                    shift_id=shift_id,
                    time_slot_id=shift.time_slot_id,
                    object_id=shift.object_id,
                    created_by_id=user_id
                )
            
            # Преобразовать в dict для шаблона
            shift_tasks = [{
                'id': t.id,
                'task_text': t.task_text,
                'source': t.source,
                'source_id': t.source_id,
                'is_mandatory': t.is_mandatory,
                'requires_media': t.requires_media,
                'deduction_amount': float(t.deduction_amount) if t.deduction_amount else 0,
                'is_completed': t.is_completed,
                'completed_at': t.completed_at,
                'media_refs': t.media_refs,
                'cost': float(t.cost) if t.cost else None
            } for t in tasks_entities]
            
        elif shift_type == "schedule":
            # Запланированная смена: превью из конфигурации (без статусов)
            # Задачи из объекта
            if shift.object and shift.object.shift_tasks:
                for task_data in shift.object.shift_tasks:
                    if isinstance(task_data, str):
                        shift_tasks.append({
                            'task_text': task_data,
                            'source': 'object',
                            'is_mandatory': True,
                            'requires_media': False,
                            'deduction_amount': 0
                        })
                    elif isinstance(task_data, dict):
                        shift_tasks.append({
                            'task_text': task_data.get('text', ''),
                            'source': 'object',
                            'is_mandatory': task_data.get('is_mandatory', True),
                            'requires_media': task_data.get('requires_media', False),
                            'deduction_amount': task_data.get('deduction_amount', 0)
                        })
            
            # Задачи из тайм-слота (если есть)
            if shift.time_slot_id:
                timeslot_query = select(TimeSlot).where(TimeSlot.id == shift.time_slot_id)
                timeslot_result = await session.execute(timeslot_query)
                timeslot = timeslot_result.scalar_one_or_none()
                
                ignore_object_tasks = timeslot.ignore_object_tasks if timeslot else False
                
                # Если ignore_object_tasks=True - очистить задачи объекта
                if ignore_object_tasks:
                    shift_tasks = [t for t in shift_tasks if t['source'] != 'object']
                
                # Добавить задачи тайм-слота
                timeslot_tasks_query = select(TimeslotTaskTemplate).where(
                    TimeslotTaskTemplate.timeslot_id == shift.time_slot_id
                ).order_by(TimeslotTaskTemplate.display_order)
                timeslot_tasks_result = await session.execute(timeslot_tasks_query)
                timeslot_tasks = timeslot_tasks_result.scalars().all()
                
                for template in timeslot_tasks:
                    shift_tasks.append({
                        'task_text': template.task_text,
                        'source': 'timeslot',
                        'is_mandatory': template.is_mandatory,
                        'requires_media': template.requires_media,
                        'deduction_amount': float(template.deduction_amount) if template.deduction_amount else 0
                    })
        
        return templates.TemplateResponse("owner/shifts/detail.html", {
            "request": request,
            "current_user": current_user,
            "shift": shift,
            "shift_type": shift_type,
            "object": shift.object,
            "shift_tasks": shift_tasks,
            "web_timezone_helper": web_timezone_helper
        })


@router.post("/{shift_id}/cancel")
async def cancel_shift(request: Request, shift_id: int, shift_type: Optional[str] = Query("shift")):
    """Отмена смены"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем роль пользователя
    user_role = current_user.get("role") if isinstance(current_user, dict) else current_user.role
    
    async with get_async_session() as session:
        # Получаем внутренний ID пользователя
        user_id = await get_user_id_from_current_user(current_user, session)
        if shift_type == "schedule":
            # Отмена запланированной смены
            query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object)
            ).where(ShiftSchedule.id == shift_id)
            result = await session.execute(query)
            shift = result.scalar_one_or_none()
            
            if shift and shift.status == "planned":
                # Проверка прав доступа
                if user_role != "superadmin":
                    if shift.object.owner_id != user_id:
                        return JSONResponse({"success": False, "error": "Нет прав доступа"})
                
                # Отмена смены
                shift.status = "cancelled"
                shift.updated_at = datetime.utcnow()
                await session.commit()
                
                return JSONResponse({"success": True, "message": "Запланированная смена отменена"})
            else:
                return JSONResponse({"success": False, "error": "Смена не найдена или уже отменена"})
        else:
            # Отмена активной смены
            query = select(Shift).options(
                selectinload(Shift.object)
            ).where(Shift.id == shift_id)
            result = await session.execute(query)
            shift = result.scalar_one_or_none()
            
            if shift and shift.status == "active":
                # Проверка прав доступа
                if user_role != "superadmin":
                    if shift.object.owner_id != user_id:
                        return JSONResponse({"success": False, "error": "Нет прав доступа"})
                
                # Закрытие смены
                shift.status = "completed"
                shift.end_time = datetime.utcnow()
                shift.updated_at = datetime.utcnow()
                await session.commit()
                
                return JSONResponse({"success": True, "message": "Смена завершена"})
            else:
                return JSONResponse({"success": False, "error": "Смена не найдена или уже завершена"})


@router.post("/{shift_id}/tasks/{task_id}/toggle")
async def toggle_task(request: Request, shift_id: int, task_id: int):
    """Переключить статус выполнения задачи."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        
        from shared.services.shift_task_journal import ShiftTaskJournal
        journal = ShiftTaskJournal(session)
        
        task = await journal.toggle_completed(task_id, user_id)
        
        if task:
            # Редирект обратно к карточке смены
            return RedirectResponse(
                url=f"/owner/shifts/{shift_id}?shift_type=shift",
                status_code=status.HTTP_302_FOUND
            )
        else:
            return RedirectResponse(
                url=f"/owner/shifts/{shift_id}?shift_type=shift",
                status_code=status.HTTP_302_FOUND
            )


@router.post("/{shift_id}/add-task")
async def add_manual_task(request: Request, shift_id: int):
    """Добавить ручную задачу к смене."""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    async with get_async_session() as session:
        user_id = await get_user_id_from_current_user(current_user, session)
        form_data = await request.form()
        task_text = form_data.get("task_text", "").strip()
        
        if not task_text:
            return RedirectResponse(
                url=f"/owner/shifts/{shift_id}?shift_type=shift",
                status_code=status.HTTP_302_FOUND
            )
        
        from shared.services.shift_task_journal import ShiftTaskJournal
        journal = ShiftTaskJournal(session)
        
        await journal.add_manual_task(
            shift_id=shift_id,
            task_text=task_text,
            created_by_id=user_id
        )
        
        return RedirectResponse(
            url=f"/owner/shifts/{shift_id}?shift_type=shift",
            status_code=status.HTTP_302_FOUND
        )


@router.get("/stats/summary")
async def shifts_stats(request: Request):
    """Статистика по сменам"""
    current_user = await require_owner_or_superadmin(request)
    if isinstance(current_user, RedirectResponse):
        return current_user
    
    # Получаем роль пользователя
    user_role = current_user.get("role") if isinstance(current_user, dict) else current_user.role
    
    async with get_async_session() as session:
        # Получаем внутренний ID пользователя
        user_id = await get_user_id_from_current_user(current_user, session)
        # Получаем объекты владельца
        owner_objects = select(Object.id).where(Object.owner_id == user_id)
        
        # Статистика по реальным сменам
        shifts_query = select(Shift).where(Shift.object_id.in_(owner_objects))
        shifts_result = await session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        # Статистика по запланированным сменам
        schedules_query = select(ShiftSchedule).where(ShiftSchedule.object_id.in_(owner_objects))
        schedules_result = await session.execute(schedules_query)
        schedules = schedules_result.scalars().all()
        
        # Расчет статистики
        stats = {
            "total_shifts": len(shifts),
            "active_shifts": len([s for s in shifts if s.status == "active"]),
            "completed_shifts": len([s for s in shifts if s.status == "completed"]),
            "planned_shifts": len([s for s in schedules if s.status == "planned"]),
            "total_hours": sum(s.total_hours or 0 for s in shifts if s.total_hours),
            "total_payment": sum(s.total_payment or 0 for s in shifts if s.total_payment),
            "avg_hours_per_shift": 0,
            "avg_payment_per_shift": 0
        }
        
        if stats["completed_shifts"] > 0:
            stats["avg_hours_per_shift"] = stats["total_hours"] / stats["completed_shifts"]
            stats["avg_payment_per_shift"] = stats["total_payment"] / stats["completed_shifts"]
        
        return stats