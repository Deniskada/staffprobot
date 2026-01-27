from fastapi import APIRouter, Request, Query, status, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session, get_db_session
from core.auth.user_manager import UserManager
from apps.web.middleware.auth_middleware import require_owner_or_superadmin
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot
from domain.entities.object import Object
from domain.entities.user import User
from apps.web.utils.timezone_utils import web_timezone_helper
from apps.web.utils.shift_history_utils import build_shift_history_items
from shared.services.shift_history_service import ShiftHistoryService
from shared.services.cancellation_policy_service import CancellationPolicyService
from shared.services.shift_cancellation_service import ShiftCancellationService
from shared.services.shift_status_sync_service import ShiftStatusSyncService
from domain.entities.shift_cancellation import ShiftCancellation
from core.cache.redis_cache import cache
from core.logging.logger import logger

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


@router.get("/plan", response_class=HTMLResponse)
async def shifts_plan(
    request: Request,
    object_id: Optional[int] = Query(None, description="ID объекта для предзаполнения"),
    employee_id: Optional[int] = Query(None, description="ID сотрудника для предзаполнения"),
    return_to: Optional[str] = Query(None, description="URL для возврата после планирования"),
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Страница планирования смен."""
    try:
        if isinstance(current_user, RedirectResponse):
            return current_user
        
        # Получаем внутренний ID владельца
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        
        # Получаем объекты владельца
        from sqlalchemy import select
        from domain.entities.object import Object
        
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await db.execute(objects_query)
        objects = objects_result.scalars().all()
        
        objects_list = [{"id": obj.id, "name": obj.name} for obj in objects]
        
        # Если передан object_id, проверяем, что он принадлежит владельцу
        selected_object_id = None
        if object_id:
            for obj in objects:
                if obj.id == object_id:
                    selected_object_id = object_id
                    break

        preselected_employee_id = None
        if employee_id is not None:
            try:
                preselected_employee_id = int(employee_id)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid employee_id provided for owner shifts plan",
                    employee_id=employee_id
                )
                preselected_employee_id = None
        
        # Получаем данные для переключения интерфейсов
        from shared.services.role_based_login_service import RoleBasedLoginService
        login_service = RoleBasedLoginService(db)
        available_interfaces = await login_service.get_available_interfaces(user_id)
        
        return templates.TemplateResponse("owner/shifts/plan.html", {
            "request": request,
            "current_user": current_user,
            "objects": objects_list,
            "selected_object_id": selected_object_id,
            "preselected_employee_id": preselected_employee_id,
            "return_to": return_to or "/owner/shifts",
            "available_interfaces": available_interfaces
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading shifts plan page: {e}")
        raise HTTPException(status_code=500, detail="Ошибка загрузки страницы планирования")


@router.get("/api/schedule/{schedule_id}/object-id", response_class=JSONResponse)
async def get_schedule_object_id(
    schedule_id: int,
    current_user: dict = Depends(require_owner_or_superadmin),
    db: AsyncSession = Depends(get_db_session)
):
    """Получить object_id из запланированной смены."""
    try:
        if isinstance(current_user, RedirectResponse):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        
        # Получаем внутренний ID владельца
        user_id = await get_user_id_from_current_user(current_user, db)
        if not user_id:
            return JSONResponse({"error": "User not found"}, status_code=401)
        
        # Получаем запланированную смену
        schedule_query = select(ShiftSchedule).options(
            selectinload(ShiftSchedule.object)
        ).where(ShiftSchedule.id == schedule_id)
        
        result = await db.execute(schedule_query)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return JSONResponse({"error": "Schedule not found"}, status_code=404)
        
        # Проверяем, что объект принадлежит владельцу
        objects_query = select(Object).where(Object.owner_id == user_id)
        objects_result = await db.execute(objects_query)
        objects = objects_result.scalars().all()
        object_ids = [obj.id for obj in objects]
        
        if schedule.object_id not in object_ids:
            return JSONResponse({"error": "Access denied"}, status_code=403)
        
        return JSONResponse({
            "object_id": schedule.object_id,
            "employee_id": schedule.user_id
        })
        
    except Exception as e:
        logger.error(f"Error getting schedule object_id: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/", response_class=HTMLResponse)
async def shifts_list(
    request: Request,
    status: Optional[str] = Query(None, description="Фильтр по статусу: active, planned, completed"),
    date_from: Optional[str] = Query(None, description="Дата начала (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата окончания (YYYY-MM-DD)"),
    object_id: Optional[str] = Query(None, description="ID объекта"),
    q_user: Optional[str] = Query(None, description="Поиск по сотруднику (Фамилия Имя)"),
    q_object: Optional[str] = Query(None, description="Поиск по названию объекта"),
    sort: Optional[str] = Query(None, description="Поле сортировки: user_name, object_name, start_time, status, created_at"),
    order: Optional[str] = Query("asc", description="Порядок сортировки: asc, desc"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(25, ge=1, le=100, description="Количество на странице")
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
        
        # Применение фильтров по статусу
        if status:
            if status == "active":
                shifts_query = shifts_query.where(Shift.status == "active")
                # Для плановых смен активными считаются только confirmed
                schedules_query = schedules_query.where(ShiftSchedule.status == "confirmed")
            elif status == "planned":
                # Для запланированных смен показываем только ShiftSchedule со статусом planned
                shifts_query = shifts_query.where(False)  # Не показываем реальные смены
                schedules_query = schedules_query.where(ShiftSchedule.status == "planned")
            elif status == "completed":
                shifts_query = shifts_query.where(Shift.status == "completed")
                schedules_query = schedules_query.where(False)  # Не показываем плановые смены
            elif status == "cancelled":
                shifts_query = shifts_query.where(Shift.status == "cancelled")
                schedules_query = schedules_query.where(ShiftSchedule.status == "cancelled")
        
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
        
        # Добавляем запланированные смены
        # (теперь фильтрация по статусу уже применена в запросе)
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
        
        # Текстовые фильтры по сотруднику/объекту
        if q_user:
            qu = q_user.strip().lower()
            def user_name_val(item):
                u = item.get('user')
                last_first = f"{(u.last_name or '').strip()} {(u.first_name or '').strip()}".strip() if u else ''
                first_last = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip() if u else ''
                return last_first.lower(), first_last.lower()
            all_shifts = [it for it in all_shifts if qu in user_name_val(it)[0] or qu in user_name_val(it)[1]]
        if q_object:
            qo = q_object.strip().lower()
            all_shifts = [it for it in all_shifts if ((it.get('object').name.lower() if it.get('object') and it.get('object').name else '')) and qo in it.get('object').name.lower()]

        # Сортировка
        if sort:
            reverse = (order == "desc")
            def sort_key(item):
                if sort == "user_name":
                    u = item.get('user')
                    # Сортировка по Фамилии, затем Имени
                    last = (u.last_name or '').lower() if u else ''
                    first = (u.first_name or '').lower() if u else ''
                    return (last, first)
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
        
        # Пагинация - подсчет ПОСЛЕ всех фильтров
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
                'user_name': f"{(shift['user'].last_name or '').strip()} {(shift['user'].first_name or '').strip()}".strip() if shift['user'] else 'Неизвестно',
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
                "object_id": object_id,
                "q_user": q_user,
                "q_object": q_object
            },
            "sort": {"field": sort, "order": order},
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if total > 0 else 0
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
                selectinload(ShiftSchedule.user),
                selectinload(ShiftSchedule.actual_shifts)
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
        from domain.entities.timeslot_task_template import TimeslotTaskTemplate
        from domain.entities.task_entry import TaskEntryV2
        
        if shift_type == "shift":
            # Реальная смена: использовать TaskEntryV2 (новая система задач)
            entries_query = (
                select(TaskEntryV2)
                .where(TaskEntryV2.shift_id == shift_id)
                .options(selectinload(TaskEntryV2.template))
                .order_by(TaskEntryV2.id)
            )
            entries_res = await session.execute(entries_query)
            entries = entries_res.scalars().all()

            # Преобразовать в dict для шаблона
            for e in entries:
                tpl = e.template
                shift_tasks.append({
                    'id': e.id,
                    'task_text': (tpl.title if tpl else ''),
                    'source': 'task_v2',
                    'source_id': e.template_id,
                    'is_mandatory': bool(tpl.is_mandatory) if tpl else False,
                    'requires_media': bool(tpl.requires_media) if tpl else False,
                    'deduction_amount': float(tpl.default_bonus_amount) if (tpl and tpl.default_bonus_amount) else 0,
                    'is_completed': bool(e.is_completed),
                    'completed_at': e.completed_at,
                    'media_refs': e.completion_media or [],
                    'cost': None
                })
            
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
        
        timezone_name = getattr(shift.object, "timezone", None) or "Europe/Moscow"
        history_service = ShiftHistoryService(session)
        history_entries: List = []

        if shift_type == "schedule":
            history_entries.extend(
                await history_service.fetch_history(schedule_id=shift.id)
            )
            # Если есть связанные фактические смены, добавить их историю
            actual_shifts = getattr(shift, "actual_shifts", []) or []
            for actual in actual_shifts:
                history_entries.extend(
                    await history_service.fetch_history(shift_id=actual.id)
                )
        else:
            history_entries.extend(
                await history_service.fetch_history(shift_id=shift.id)
            )
            schedule_id = getattr(shift, "schedule_id", None)
            if schedule_id:
                history_entries.extend(
                    await history_service.fetch_history(schedule_id=schedule_id)
                )

        actor_ids = {entry.actor_id for entry in history_entries if entry.actor_id}
        actor_names: Dict[int, str] = {}
        if actor_ids:
            users_result = await session.execute(
                select(User.id, User.first_name, User.last_name).where(User.id.in_(actor_ids))
            )
            for row in users_result.all():
                full_name = " ".join(filter(None, [row.last_name, row.first_name])).strip()
                actor_names[row.id] = full_name or f"ID {row.id}"

        reason_titles: Dict[str, str] = {}
        owner_id = getattr(shift.object, "owner_id", None)
        if owner_id:
            reasons = await CancellationPolicyService.get_owner_reasons(
                session,
                owner_id,
                only_visible=False,
                only_active=True,
            )
            reason_titles = {reason.code: reason.title for reason in reasons}

        history_items = build_shift_history_items(
            history_entries,
            timezone=timezone_name,
            actor_names=actor_names,
            reason_titles=reason_titles,
        )
        
        # Загружаем отмену смены и её медиа (restruct1 Фаза 1.4)
        cancellation_with_media = None
        if shift_type == "schedule":
            cancellation_query = (
                select(ShiftCancellation)
                .where(ShiftCancellation.shift_schedule_id == shift.id)
                .options(selectinload(ShiftCancellation.media_files))
                .order_by(ShiftCancellation.created_at.desc())
                .limit(1)
            )
            cancellation_result = await session.execute(cancellation_query)
            cancellation = cancellation_result.scalar_one_or_none()
            
            if cancellation:
                # Генерируем URL для медиа
                from shared.services.media_storage import get_media_storage_client
                from core.config.settings import settings
                
                media_urls = []
                if cancellation.media_files:
                    storage_client = None
                    try:
                        storage_client = get_media_storage_client()
                    except Exception as e:
                        logger.warning(
                            "Failed to get storage client for cancellation media",
                            cancellation_id=cancellation.id,
                            error=str(e),
                        )
                    
                    for media_file in cancellation.media_files:
                        media_item = {
                            "file_type": media_file.file_type,
                            "mime_type": media_file.mime_type,
                            "file_size": media_file.file_size,
                        }
                        
                        # Определяем, является ли storage_key S3 ключом или Telegram file_id
                        is_s3_key = "/" in media_file.storage_key
                        has_telegram_file_id = media_file.telegram_file_id is not None
                        
                        # Если есть S3 ключ (и storage_client доступен) - генерируем S3 URL
                        if is_s3_key and storage_client:
                            try:
                                s3_url = await storage_client.get_url(media_file.storage_key, expires_in=3600)
                                media_item["s3_url"] = s3_url
                                logger.debug(
                                    "Generated S3 URL for cancellation media",
                                    cancellation_id=cancellation.id,
                                    media_id=media_file.id,
                                    storage_key=media_file.storage_key,
                                )
                            except Exception as e:
                                logger.warning(
                                    "Failed to get S3 URL for cancellation media",
                                    cancellation_id=cancellation.id,
                                    media_id=media_file.id,
                                    error=str(e),
                                )
                        
                        # Если есть telegram_file_id - добавляем информацию для отображения ссылки на Telegram
                        if has_telegram_file_id:
                            media_item["telegram_file_id"] = media_file.telegram_file_id
                        elif not is_s3_key:
                            # Если storage_key не S3 ключ, значит это Telegram file_id
                            media_item["telegram_file_id"] = media_file.storage_key
                        
                        media_urls.append(media_item)
                
                logger.debug(
                    "Cancellation with media prepared",
                    cancellation_id=cancellation.id,
                    media_count=len(cancellation.media_files),
                    media_urls_count=len(media_urls),
                )
                
                cancellation_with_media = {
                    "cancellation": cancellation,
                    "media_urls": media_urls,
                }

        return templates.TemplateResponse("owner/shifts/detail.html", {
            "request": request,
            "current_user": current_user,
            "shift": shift,
            "shift_type": shift_type,
            "object": shift.object,
            "shift_tasks": shift_tasks,
            "web_timezone_helper": web_timezone_helper,
            "history_items": history_items,
            "cancellation_with_media": cancellation_with_media,
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
        if not user_id:
            return JSONResponse({"success": False, "error": "Пользователь не найден"}, status_code=401)

        cancelled_by_type = "owner"
        actor_role = user_role if user_role != "superadmin" else "superadmin"
        if actor_role == "superadmin":
            cancelled_by_type = "owner"

        cancellation_service = ShiftCancellationService(session)
        sync_service = ShiftStatusSyncService(session)
        history_service = ShiftHistoryService(session)

        if shift_type == "schedule":
            schedule_query = select(ShiftSchedule).options(
                selectinload(ShiftSchedule.object),
                selectinload(ShiftSchedule.actual_shifts),
            ).where(ShiftSchedule.id == shift_id)
            schedule_result = await session.execute(schedule_query)
            schedule = schedule_result.scalar_one_or_none()

            if not schedule or schedule.status not in {"planned", "confirmed"}:
                return JSONResponse({"success": False, "error": "Смена не найдена или уже отменена"}, status_code=400)

            if user_role != "superadmin" and schedule.object.owner_id != user_id:
                return JSONResponse({"success": False, "error": "Нет прав доступа"}, status_code=403)

            cancel_result = await cancellation_service.cancel_shift(
                shift_schedule_id=schedule.id,
                cancelled_by_user_id=user_id,
                cancelled_by_type=cancelled_by_type,
                cancellation_reason="owner_decision",
                actor_role=actor_role,
                source="web",
                extra_payload={"origin": "owner_shifts_legacy"},
            )
            if not cancel_result.get("success"):
                return JSONResponse(
                    {"success": False, "error": cancel_result.get("message", "Не удалось отменить смену")},
                    status_code=400,
                )

            await cache.clear_pattern("calendar_shifts:*")
            await cache.clear_pattern("api_response:*")
            return JSONResponse({"success": True, "message": cancel_result.get("message", "Смена отменена")})

        # Работа с фактической сменой
        shift_query = select(Shift).options(
            selectinload(Shift.object)
        ).where(Shift.id == shift_id)
        shift_result = await session.execute(shift_query)
        shift = shift_result.scalar_one_or_none()

        if not shift or shift.status not in {"active", "planned"}:
            return JSONResponse({"success": False, "error": "Смена не найдена или уже завершена"}, status_code=400)

        if user_role != "superadmin" and shift.object.owner_id != user_id:
            return JSONResponse({"success": False, "error": "Нет прав доступа"}, status_code=403)

        if shift.schedule_id:
            cancel_result = await cancellation_service.cancel_shift(
                shift_schedule_id=shift.schedule_id,
                cancelled_by_user_id=user_id,
                cancelled_by_type=cancelled_by_type,
                cancellation_reason="owner_decision",
                actor_role=actor_role,
                source="web",
                extra_payload={"origin": "owner_shifts_legacy"},
            )
            if not cancel_result.get("success"):
                return JSONResponse(
                    {"success": False, "error": cancel_result.get("message", "Не удалось отменить смену")},
                    status_code=400,
                )
        else:
            previous_status = shift.status
            shift.status = "cancelled"
            if not shift.end_time:
                shift.end_time = datetime.utcnow()
            shift.updated_at = datetime.utcnow()

            await history_service.log_event(
                operation="shift_cancel",
                source="web",
                actor_id=user_id,
                actor_role=actor_role,
                shift_id=shift.id,
                schedule_id=None,
                old_status=previous_status,
                new_status="cancelled",
                payload={
                    "reason_code": "owner_decision",
                    "origin": "owner_shifts_legacy",
                },
            )
            # Нет связанного расписания — просто фиксируем факт через sync (ничего не изменит, но оставим для единообразия)
            await sync_service.cancel_linked_shifts(
                None,
                actor_id=user_id,
                actor_role=actor_role,
                source="web",
                payload={"origin": "owner_shifts_legacy"},
            )
            await session.commit()

        await cache.clear_pattern("calendar_shifts:*")
        await cache.clear_pattern("api_response:*")
        return JSONResponse({"success": True, "message": "Смена отменена"})


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