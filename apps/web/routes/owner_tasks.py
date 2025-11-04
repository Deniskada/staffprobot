"""Роуты владельца для управления задачами (Tasks v2) - использует shared TaskService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from core.config.settings import settings
from domain.entities.user import User
from shared.services.task_service import TaskService
from fastapi import HTTPException


router = APIRouter()


@router.get("/owner/tasks")
async def owner_tasks_index(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Главная страница задач."""
    if not settings.enable_tasks_v2:
        raise HTTPException(
            status_code=404,
            detail="Tasks v2 отключен. Включите enable_tasks_v2 в настройках."
        )
    
    return templates.TemplateResponse(
        "owner/tasks/index.html",
        {"request": request}
    )


@router.get("/owner/tasks/templates")
async def owner_tasks_templates(
    request: Request,
    show_inactive: int = 0,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Библиотека шаблонов задач."""
    task_service = TaskService(session)
    
    # active_only зависит от переключателя show_inactive
    active_only = None if show_inactive else False  # False = показывать все для owner
    
    templates_list = await task_service.get_templates_for_role(
        user_id=current_user.id,
        role="owner",
        active_only=active_only
    )
    return templates.TemplateResponse(
        "owner/tasks/templates.html",
        {
            "request": request, 
            "templates_list": templates_list,
            "show_inactive": show_inactive
        }
    )


@router.post("/owner/tasks/templates/create")
async def owner_tasks_templates_create(
    request: Request,
    code: str = Form(None),
    title: str = Form(...),
    description: str = Form(None),
    is_mandatory: int = Form(0),
    requires_media: int = Form(0),
    requires_geolocation: int = Form(0),
    default_amount: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Создать шаблон задачи."""
    from decimal import Decimal
    import re
    from core.logging.logger import logger
    
    task_service = TaskService(session)
    
    # Автогенерация кода если не указан
    if not code or not code.strip():
        # Генерируем код из названия
        code_base = re.sub(r'[^\w\s-]', '', title.lower())
        code_base = re.sub(r'[-\s]+', '_', code_base)
        code = code_base[:50]
        
        # Проверяем уникальность
        counter = 1
        original_code = code
        while True:
            from domain.entities.task_template import TaskTemplateV2
            check_query = select(TaskTemplateV2).where(
                TaskTemplateV2.owner_id == current_user.id,
                TaskTemplateV2.code == code
            )
            existing = await session.execute(check_query)
            if not existing.scalar_one_or_none():
                break
            code = f"{original_code}_{counter}"
            counter += 1
        
        logger.info(f"Auto-generated code: {code} for template: {title}")
    
    amount = Decimal(default_amount) if default_amount else None
    
    await task_service.create_template(
        owner_id=current_user.id,
        code=code,
        title=title,
        description=description,
        is_mandatory=bool(is_mandatory),
        requires_media=bool(requires_media),
        requires_geolocation=bool(requires_geolocation),
        default_amount=amount,
        object_id=None
    )
    
    return RedirectResponse(url="/owner/tasks/templates", status_code=303)


@router.post("/owner/tasks/templates/{template_id}/edit")
async def owner_tasks_templates_edit(
    request: Request,
    template_id: int,
    code: str = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    is_mandatory: int = Form(0),
    requires_media: int = Form(0),
    requires_geolocation: int = Form(0),
    default_amount: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Редактировать шаблон задачи."""
    from decimal import Decimal
    from domain.entities.task_template import TaskTemplateV2
    from core.logging.logger import logger
    
    template = await session.get(TaskTemplateV2, template_id)
    if not template or template.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/templates", status_code=303)
    
    template.code = code
    template.title = title
    template.description = description
    template.is_mandatory = bool(is_mandatory)
    template.requires_media = bool(requires_media)
    template.requires_geolocation = bool(requires_geolocation)
    template.default_bonus_amount = Decimal(default_amount) if default_amount else None
    
    await session.commit()
    logger.info(f"Updated TaskTemplateV2: {template_id}")
    
    return RedirectResponse(url="/owner/tasks/templates", status_code=303)


@router.post("/owner/tasks/templates/{template_id}/toggle")
async def owner_tasks_templates_toggle(
    request: Request,
    template_id: int,
    update_plans: int = Form(0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Переключить активность шаблона."""
    from domain.entities.task_template import TaskTemplateV2
    from domain.entities.task_plan import TaskPlanV2
    from core.logging.logger import logger
    
    template = await session.get(TaskTemplateV2, template_id)
    if not template or template.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/templates", status_code=303)
    
    new_state = not template.is_active
    template.is_active = new_state
    
    if update_plans:
        plans_query = select(TaskPlanV2).where(TaskPlanV2.template_id == template_id)
        plans_result = await session.execute(plans_query)
        plans = plans_result.scalars().all()
        
        for plan in plans:
            plan.is_active = new_state
        
        logger.info(f"Updated {len(plans)} plans for template {template_id} to active={new_state}")
    
    await session.commit()
    logger.info(f"Toggled TaskTemplateV2 {template_id}: active={new_state}")
    
    return RedirectResponse(url="/owner/tasks/templates", status_code=303)


@router.post("/owner/tasks/templates/{template_id}/delete")
async def owner_tasks_templates_delete(
    request: Request,
    template_id: int,
    delete_entries: int = Form(0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Удалить шаблон задачи."""
    from domain.entities.task_template import TaskTemplateV2
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.task_entry import TaskEntryV2
    from core.logging.logger import logger
    
    # Проверяем владельца
    template = await session.get(TaskTemplateV2, template_id)
    if not template or template.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/templates", status_code=303)
    
    if delete_entries:
        # Удаляем все entries и планы
        entries_query = select(TaskEntryV2).where(TaskEntryV2.template_id == template_id)
        entries_result = await session.execute(entries_query)
        entries = entries_result.scalars().all()
        for entry in entries:
            await session.delete(entry)
        
        plans_query = select(TaskPlanV2).where(TaskPlanV2.template_id == template_id)
        plans_result = await session.execute(plans_query)
        plans = plans_result.scalars().all()
        for plan in plans:
            await session.delete(plan)
        
        logger.info(f"Deleted {len(entries)} entries and {len(plans)} plans for template {template_id}")
    else:
        # Отвязываем от шаблона (обнуляем template_id)
        entries_query = select(TaskEntryV2).where(TaskEntryV2.template_id == template_id)
        entries_result = await session.execute(entries_query)
        entries = entries_result.scalars().all()
        for entry in entries:
            entry.template_id = None
        
        plans_query = select(TaskPlanV2).where(TaskPlanV2.template_id == template_id)
        plans_result = await session.execute(plans_query)
        plans = plans_result.scalars().all()
        for plan in plans:
            await session.delete(plan)  # Планы удаляем всегда
        
        logger.info(f"Unlinked {len(entries)} entries and deleted {len(plans)} plans for template {template_id}")
    
    await session.delete(template)
    await session.commit()
    logger.info(f"Deleted TaskTemplateV2: {template_id}")
    
    return RedirectResponse(url="/owner/tasks/templates", status_code=303)


@router.get("/owner/tasks/plan")
async def owner_tasks_plan(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Планирование задач."""
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.object import Object
    from sqlalchemy.orm import selectinload
    
    # require_role уже вернул User или редирект
    owner_id = current_user.id
    
    # Получаем планы с eager loading template и object
    plans_query = select(TaskPlanV2).where(TaskPlanV2.owner_id == owner_id).options(
        selectinload(TaskPlanV2.template),
        selectinload(TaskPlanV2.object)
    ).order_by(TaskPlanV2.created_at.desc())
    plans_result = await session.execute(plans_query)
    plans = plans_result.scalars().all()
    
    # Для модала - только активные шаблоны
    task_service = TaskService(session)
    templates_list = await task_service.get_templates_for_role(
        user_id=owner_id, 
        role="owner",
        for_selection=True  # Только активные для формы
    )
    
    objects_query = select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    objects_result = await session.execute(objects_query)
    objects_list = objects_result.scalars().all()
    
    return templates.TemplateResponse(
        "owner/tasks/plan.html",
        {"request": request, "plans": plans, "templates_list": templates_list, "objects_list": objects_list}
    )


@router.get("/owner/tasks/plan/create")
async def owner_tasks_plan_create_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Полноэкранная форма создания плана задач (вместо модального окна)."""
    task_service = TaskService(session)
    owner_id = current_user.id

    templates_list = await task_service.get_templates_for_role(
        user_id=owner_id,
        role="owner",
        for_selection=True
    )

    from domain.entities.object import Object
    objects_query = select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    objects_result = await session.execute(objects_query)
    objects_list = objects_result.scalars().all()

    return templates.TemplateResponse(
        "owner/tasks/plan_create.html",
        {"request": request, "templates_list": templates_list, "objects_list": objects_list}
    )


@router.post("/owner/tasks/plan/create")
async def owner_tasks_plan_create(
    request: Request,
    creation_mode: str = Form("template"),
    template_id: str = Form(None),
    task_title: str = Form(None),
    task_description: str = Form(None),
    task_mandatory: int = Form(0),
    task_media: int = Form(0),
    task_geolocation: int = Form(0),
    task_amount: str = Form(None),
    task_code: str = Form(None),
    object_ids: list[str] = Form(None),
    planned_date: str = Form(None),
    planned_time_start: str = Form(None),
    recurrence_type: str = Form(None),
    weekday: list[str] = Form(None),
    day_interval: int | None = Form(None),
    recurrence_end_date: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Создать план задачи (с шаблоном или без)."""
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.task_template import TaskTemplateV2
    from decimal import Decimal
    from datetime import datetime, time, date
    import re
    from core.logging.logger import logger
    
    owner_id = current_user.id
    obj_ids = [int(oid) for oid in object_ids] if object_ids else None
    obj_id = obj_ids[0] if obj_ids and len(obj_ids) == 1 else None  # Для обратной совместимости
    p_date = datetime.fromisoformat(planned_date) if planned_date else None
    p_time = datetime.strptime(planned_time_start, "%H:%M").time() if planned_time_start else None
    end_date = date.fromisoformat(recurrence_end_date) if recurrence_end_date else None
    
    # Определяем template_id в зависимости от режима
    final_template_id = None
    if creation_mode == "template" and template_id:
        final_template_id = int(template_id)
    elif creation_mode == "custom":
        # Создаём новый шаблон на лету
        if not task_code:
            # Автогенерация кода
            code_base = re.sub(r'[^\w\s-]', '', (task_title or 'task').lower())
            code_base = re.sub(r'[-\s]+', '_', code_base)[:50]
            counter = 1
            task_code = code_base
            while True:
                check = await session.execute(
                    select(TaskTemplateV2).where(
                        TaskTemplateV2.owner_id == owner_id,
                        TaskTemplateV2.code == task_code
                    )
                )
                if not check.scalar_one_or_none():
                    break
                task_code = f"{code_base}_{counter}"
                counter += 1
        
        # Создаём шаблон
        new_template = TaskTemplateV2(
            owner_id=owner_id,
            code=task_code,
            title=task_title or "Без названия",
            description=task_description,
            is_mandatory=bool(task_mandatory),
            requires_media=bool(task_media),
            requires_geolocation=bool(task_geolocation),
            default_bonus_amount=Decimal(task_amount) if task_amount else None,
            is_active=True,
            object_id=None  # Шаблоны без привязки к объекту
        )
        session.add(new_template)
        await session.flush()
        final_template_id = new_template.id
        logger.info(f"Created on-the-fly template: {new_template.id} ({task_code})")
    
    # Формируем recurrence_config (безопасный парсинг интервала)
    recurrence_config = None
    if recurrence_type == "weekdays" and weekday:
        recurrence_config = {"weekdays": [int(d) for d in weekday]}
    elif recurrence_type == "day_interval":
        try:
            interval = int(day_interval) if day_interval is not None else 1
        except Exception:
            interval = 1
        interval = max(1, interval)
        recurrence_config = {"interval": interval}
    
    # Создаём план
    from datetime import datetime, timezone
    plan = TaskPlanV2(
        template_id=final_template_id,
        owner_id=owner_id,
        object_id=obj_id,  # Для обратной совместимости (один объект)
        object_ids=obj_ids,  # Новое поле (несколько объектов)
        planned_date=p_date,
        planned_time_start=p_time,
        recurrence_type=recurrence_type if recurrence_type else None,
        recurrence_config=recurrence_config,
        recurrence_end_date=end_date,
        is_active=True
    )
    # Устанавливаем created_at сразу, чтобы избежать lazy-load (MissingGreenlet) при расчете периодичности
    try:
        setattr(plan, "created_at", datetime.now(timezone.utc))
    except Exception:
        pass
    session.add(plan)
    await session.flush()  # Получаем plan.id
    logger.info(f"Created TaskPlanV2: {plan.id}, template={final_template_id}, object={obj_id}, recurrence={recurrence_type}")
    
    # Мгновенное создание TaskEntry для уже активных смен
    from core.celery.tasks.task_assignment import create_task_entries_for_active_shifts
    created_entries = await create_task_entries_for_active_shifts(session, plan)
    logger.info(f"Created {created_entries} TaskEntryV2 for active shifts of plan {plan.id}")
    
    # Экстренные уведомления сотрудникам о новых задачах (без изменения старых тасок)
    try:
        from domain.entities.task_entry import TaskEntryV2
        from domain.entities.shift import Shift
        from sqlalchemy import and_
        # Целевые объекты плана
        target_object_ids = plan.object_ids or ([plan.object_id] if plan.object_id else None)

        # Собираем сотрудников из только что созданных schedule-entries
        entries_result = await session.execute(
            select(TaskEntryV2.employee_id).where(TaskEntryV2.plan_id == plan.id)
        )
        employee_ids = {eid for (eid,) in entries_result.all() if eid}

        # Плюс сотрудники с АКТИВНЫМИ сменами на целевых объектах: создаём entry по shift.id
        created_for_active = 0
        if target_object_ids:
            active_shifts_q = select(Shift).where(
                and_(
                    Shift.status == "active",
                    Shift.object_id.in_(target_object_ids)
                )
            )
            active_shifts_res = await session.execute(active_shifts_q)
            active_shifts = active_shifts_res.scalars().all()
            from domain.entities.task_template import TaskTemplateV2
            template = await session.get(TaskTemplateV2, plan.template_id)
            for sh in active_shifts:
                employee_ids.add(sh.user_id)
                # Проверим, не существует ли уже entry для этой смены
                exists_q = select(TaskEntryV2.id).where(
                    and_(TaskEntryV2.plan_id == plan.id, TaskEntryV2.shift_id == sh.id)
                )
                exists_res = await session.execute(exists_q)
                if exists_res.scalar_one_or_none():
                    continue
                entry = TaskEntryV2(
                    template_id=plan.template_id,
                    plan_id=plan.id,
                    shift_id=sh.id,
                    shift_schedule_id=sh.schedule_id if sh.schedule_id else None,
                    employee_id=sh.user_id,
                    is_completed=False,
                    requires_media=template.requires_media if template else False
                )
                session.add(entry)
                created_for_active += 1
            logger.info("Ensured task entries for active shifts", plan_id=plan.id, active_shifts=len(active_shifts), created=created_for_active)

        if employee_ids:
            # 1) Старый механизм экстренных уведомлений (оставляем для совместимости)
            from core.celery.tasks.task_notifications import notify_tasks_updated
            notify_tasks_updated.apply_async(args=[list(employee_ids)], queue='notifications')
            logger.info("Enqueued notify_tasks_updated", plan_id=plan.id, employees=len(employee_ids), queue='notifications')

            # 2) Новый универсальный pipeline уведомлений: создаём записи и отправляем через Celery
            try:
                from shared.services.notification_service import NotificationService
                from domain.entities.notification import (
                    NotificationType,
                    NotificationChannel,
                    NotificationPriority,
                )
                from core.celery.tasks.notification_tasks import send_notification_now

                notif_service = NotificationService()
                created_ids: list[int] = []  # только для TELEGRAM, IN_APP не шлём через Celery
                for eid in employee_ids:
                    # In-App (колокольчик)
                    await notif_service.create_notification(
                        user_id=int(eid),
                        type=NotificationType.TASK_ASSIGNED,
                        channel=NotificationChannel.IN_APP,
                        title="Новая задача",
                        message=(
                            "📋 Новая задача назначена. "
                            "Откройте '📝 Мои задачи', чтобы посмотреть список."
                        ),
                        data={"plan_id": plan.id},
                        priority=NotificationPriority.NORMAL,
                        scheduled_at=None,
                    )
                    # Telegram
                    n = await notif_service.create_notification(
                        user_id=int(eid),
                        type=NotificationType.TASK_ASSIGNED,
                        channel=NotificationChannel.TELEGRAM,
                        title="Новая задача",
                        message=(
                            "📋 Новая задача назначена. "
                            "Откройте '📝 Мои задачи', чтобы посмотреть список."
                        ),
                        data={"plan_id": plan.id},
                        priority=NotificationPriority.NORMAL,
                        scheduled_at=None,
                    )
                    if n and getattr(n, "id", None):
                        created_ids.append(int(n.id))

                for nid in created_ids:
                    send_notification_now.apply_async(args=[nid], queue="notifications")
                if created_ids:
                    logger.info(
                        "Enqueued send_notification_now for created notifications",
                        plan_id=plan.id,
                        total=len(created_ids),
                    )
            except Exception as _e:
                from core.logging.logger import logger as _logger
                _logger.error("Failed to enqueue universal notifications", plan_id=plan.id, error=str(_e))
    except Exception as e:
        from core.logging.logger import logger as _logger
        _logger.error("Failed to enqueue notify_tasks_updated", plan_id=plan.id, error=str(e))

    await session.commit()
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.post("/owner/tasks/plan/{plan_id}/toggle")
async def owner_tasks_plan_toggle(
    request: Request,
    plan_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Toggle активности плана."""
    from domain.entities.task_plan import TaskPlanV2
    
    plan = await session.get(TaskPlanV2, plan_id)
    if plan and plan.owner_id == current_user.id:
        plan.is_active = not plan.is_active
        await session.commit()
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.get("/owner/tasks/plan/{plan_id}/edit")
async def owner_tasks_plan_edit_page(
    request: Request,
    plan_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Страница редактирования плана задач."""
    from domain.entities.task_plan import TaskPlanV2
    
    plan = await session.get(TaskPlanV2, plan_id)
    if not plan or plan.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/plan", status_code=303)
    
    task_service = TaskService(session)
    owner_id = current_user.id

    templates_list = await task_service.get_templates_for_role(
        user_id=owner_id,
        role="owner",
        for_selection=True
    )

    from domain.entities.object import Object
    objects_query = select(Object).where(Object.owner_id == owner_id, Object.is_active == True).order_by(Object.name)
    objects_result = await session.execute(objects_query)
    objects_list = objects_result.scalars().all()

    # Загружаем шаблон плана
    from domain.entities.task_template import TaskTemplateV2
    template = await session.get(TaskTemplateV2, plan.template_id) if plan.template_id else None
    
    # Форматируем данные для формы
    planned_date_str = plan.planned_date.strftime("%Y-%m-%d") if plan.planned_date else None
    planned_time_str = plan.planned_time_start.strftime("%H:%M") if plan.planned_time_start else None
    recurrence_end_date_str = plan.recurrence_end_date.strftime("%Y-%m-%d") if plan.recurrence_end_date else None
    
    return templates.TemplateResponse(
        "owner/tasks/plan_edit.html",
        {
            "request": request,
            "plan": plan,
            "template": template,
            "templates_list": templates_list,
            "objects_list": objects_list,
            "planned_date_str": planned_date_str,
            "planned_time_str": planned_time_str,
            "recurrence_end_date_str": recurrence_end_date_str
        }
    )


@router.post("/owner/tasks/plan/{plan_id}/edit")
async def owner_tasks_plan_edit(
    request: Request,
    plan_id: int,
    object_ids: list[str] = Form(None),
    planned_date: str = Form(None),
    planned_time_start: str = Form(None),
    recurrence_type: str = Form(None),
    weekday: list[str] = Form(None),
    day_interval: int = Form(None),
    recurrence_end_date: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Редактировать план задачи."""
    from domain.entities.task_plan import TaskPlanV2
    from datetime import datetime, date
    from core.logging.logger import logger
    
    plan = await session.get(TaskPlanV2, plan_id)
    if not plan or plan.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/plan", status_code=303)
    
    # Обновляем поля
    obj_ids = [int(oid) for oid in object_ids] if object_ids else None
    plan.object_ids = obj_ids
    plan.object_id = obj_ids[0] if obj_ids and len(obj_ids) == 1 else None  # Для обратной совместимости
    plan.planned_date = datetime.fromisoformat(planned_date) if planned_date else None
    plan.planned_time_start = datetime.strptime(planned_time_start, "%H:%M").time() if planned_time_start and planned_time_start.strip() else None
    plan.recurrence_end_date = date.fromisoformat(recurrence_end_date) if recurrence_end_date else None
    
    # Обновляем периодичность
    plan.recurrence_type = recurrence_type if recurrence_type else None
    if recurrence_type == "weekdays" and weekday:
        plan.recurrence_config = {"weekdays": [int(d) for d in weekday]}
    elif recurrence_type == "day_interval" and day_interval:
        plan.recurrence_config = {"interval": day_interval}
    else:
        plan.recurrence_config = None
    
    await session.flush()
    
    # Мгновенное создание TaskEntry для активных смен после редактирования
    from core.celery.tasks.task_assignment import create_task_entries_for_active_shifts
    created_entries = await create_task_entries_for_active_shifts(session, plan)
    logger.info(f"Updated plan {plan.id}, created {created_entries} TaskEntryV2 for active shifts")

    # Дополнительно: обеспечить привязку к активным сменам (shift_id) и уведомить сотрудников
    try:
        from domain.entities.task_entry import TaskEntryV2
        from domain.entities.shift import Shift
        from sqlalchemy import select, and_
        target_object_ids = plan.object_ids or ([plan.object_id] if plan.object_id else None)
        employee_ids = set()
        if target_object_ids:
            active_shifts_q = select(Shift).where(
                and_(Shift.status == "active", Shift.object_id.in_(target_object_ids))
            )
            active_shifts_res = await session.execute(active_shifts_q)
            active_shifts = active_shifts_res.scalars().all()
            from domain.entities.task_template import TaskTemplateV2
            template = await session.get(TaskTemplateV2, plan.template_id)
            for sh in active_shifts:
                employee_ids.add(sh.user_id)
                exists_q = select(TaskEntryV2.id).where(
                    and_(TaskEntryV2.plan_id == plan.id, TaskEntryV2.shift_id == sh.id)
                )
                exists_res = await session.execute(exists_q)
                if exists_res.scalar_one_or_none():
                    continue
                entry = TaskEntryV2(
                    template_id=plan.template_id,
                    plan_id=plan.id,
                    shift_id=sh.id,
                    shift_schedule_id=sh.schedule_id if sh.schedule_id else None,
                    employee_id=sh.user_id,
                    is_completed=False,
                    requires_media=template.requires_media if template else False
                )
                session.add(entry)
            if employee_ids:
                # 1) Совместимость: экстренное уведомление
                from core.celery.tasks.task_notifications import notify_tasks_updated
                notify_tasks_updated.apply_async(args=[list(employee_ids)], queue='notifications')
                logger.info("Enqueued notify_tasks_updated (edit)", plan_id=plan.id, employees=len(employee_ids), queue='notifications')

                # 2) Новый pipeline уведомлений
                try:
                    from shared.services.notification_service import NotificationService
                    from domain.entities.notification import (
                        NotificationType,
                        NotificationChannel,
                        NotificationPriority,
                    )
                    from core.celery.tasks.notification_tasks import send_notification_now

                    notif_service = NotificationService()
                    created_ids: list[int] = []
                    for eid in employee_ids:
                        # In-App (колокольчик)
                        await notif_service.create_notification(
                            user_id=int(eid),
                            type=NotificationType.TASK_ASSIGNED,
                            channel=NotificationChannel.IN_APP,
                            title="Новая задача",
                            message=(
                                "📋 Новая задача назначена. "
                                "Откройте ‘📝 Мои задачи’, чтобы посмотреть список."
                            ),
                            data={"plan_id": plan.id},
                            priority=NotificationPriority.NORMAL,
                            scheduled_at=None,
                        )
                        # Telegram
                        n = await notif_service.create_notification(
                            user_id=int(eid),
                            type=NotificationType.TASK_ASSIGNED,
                            channel=NotificationChannel.TELEGRAM,
                            title="Новая задача",
                            message=(
                                "📋 Новая задача назначена. "
                                "Откройте ‘📝 Мои задачи’, чтобы посмотреть список."
                            ),
                            data={"plan_id": plan.id},
                            priority=NotificationPriority.NORMAL,
                            scheduled_at=None,
                        )
                        if n and getattr(n, "id", None):
                            created_ids.append(int(n.id))

                    for nid in created_ids:
                        send_notification_now.apply_async(args=[nid], queue="notifications")
                    if created_ids:
                        logger.info(
                            "Enqueued send_notification_now (edit) for created notifications",
                            plan_id=plan.id,
                            total=len(created_ids),
                        )
                except Exception as _e:
                    from core.logging.logger import logger as _logger
                    _logger.error("Failed to enqueue universal notifications (edit)", plan_id=plan.id, error=str(_e))
    except Exception as e:
        from core.logging.logger import logger as _logger
        _logger.error("Failed to ensure/notify on plan edit", plan_id=plan.id, error=str(e))
    
    await session.commit()
    logger.info(f"Updated TaskPlanV2: {plan_id}")
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.post("/owner/tasks/plan/{plan_id}/delete")
async def owner_tasks_plan_delete(
    request: Request,
    plan_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Удалить план задачи."""
    from domain.entities.task_plan import TaskPlanV2
    from core.logging.logger import logger
    
    plan = await session.get(TaskPlanV2, plan_id)
    if plan and plan.owner_id == current_user.id:
        await session.delete(plan)
        await session.commit()
        logger.info(f"Deleted TaskPlanV2: {plan_id}")
    
    return RedirectResponse(url="/owner/tasks/plan", status_code=303)


@router.get("/owner/tasks/entries")
async def owner_tasks_entries(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Выполнение и аудит задач."""
    from domain.entities.task_entry import TaskEntryV2
    from domain.entities.task_plan import TaskPlanV2
    from domain.entities.task_template import TaskTemplateV2
    from domain.entities.object import Object
    from sqlalchemy.orm import selectinload
    
    owner_id = current_user.id
    
    # Получаем entries с eager loading всех связей
    entries_query = (
        select(TaskEntryV2)
        .join(TaskPlanV2, TaskEntryV2.plan_id == TaskPlanV2.id, isouter=True)
        .join(TaskTemplateV2, TaskEntryV2.template_id == TaskTemplateV2.id, isouter=True)
        .where(or_(TaskPlanV2.owner_id == owner_id, TaskTemplateV2.owner_id == owner_id))
        .options(
            selectinload(TaskEntryV2.template),
            selectinload(TaskEntryV2.plan).selectinload(TaskPlanV2.object),
            selectinload(TaskEntryV2.employee)
        )
        .order_by(TaskEntryV2.created_at.desc())
        .limit(100)
    )
    entries_result = await session.execute(entries_query)
    entries = entries_result.scalars().all()
    
    return templates.TemplateResponse(
        "owner/tasks/entries.html",
        {"request": request, "entries": entries}
    )


@router.post("/owner/tasks/entries/create")
async def owner_tasks_entries_create(
    request: Request,
    plan_id: int = Form(None),
    template_id: int = Form(...),
    shift_schedule_id: int = Form(None),
    employee_id: int = Form(None),
    notes: str = Form(None),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Создать запись выполнения задачи (вручную)."""
    from domain.entities.task_entry import TaskEntryV2
    from domain.entities.task_template import TaskTemplateV2
    from core.logging.logger import logger
    
    # Проверяем, что шаблон принадлежит владельцу
    template = await session.get(TaskTemplateV2, template_id)
    if not template or template.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/entries", status_code=303)
    
    entry = TaskEntryV2(
        plan_id=plan_id,
        template_id=template_id,
        shift_schedule_id=shift_schedule_id,
        employee_id=employee_id,
        notes=notes,
        requires_media=template.requires_media,
        is_completed=False
    )
    session.add(entry)
    await session.commit()
    logger.info(f"Created TaskEntryV2 manually: {entry.id}, template={template_id}")

    # Создаём In‑App и Telegram уведомления сотруднику (если указан)
    try:
        if employee_id:
            from shared.services.notification_service import NotificationService
            from domain.entities.notification import (
                NotificationType,
                NotificationChannel,
                NotificationPriority,
            )
            from core.celery.tasks.notification_tasks import send_notification_now

            notif_service = NotificationService()
            # In‑App
            await notif_service.create_notification(
                user_id=int(employee_id),
                type=NotificationType.FEATURE_ANNOUNCEMENT,
                channel=NotificationChannel.IN_APP,
                title="Новая задача",
                message=(
                    "📋 Новая задача назначена. "
                    "Откройте ‘📝 Мои задачи’, чтобы посмотреть список."
                ),
                data={"entry_id": entry.id, "template_id": template_id},
                priority=NotificationPriority.NORMAL,
                scheduled_at=None,
            )
            # Telegram
            n = await notif_service.create_notification(
                user_id=int(employee_id),
                type=NotificationType.FEATURE_ANNOUNCEMENT,
                channel=NotificationChannel.TELEGRAM,
                title="Новая задача",
                message=(
                    "📋 Новая задача назначена. "
                    "Откройте ‘📝 Мои задачи’, чтобы посмотреть список."
                ),
                data={"entry_id": entry.id, "template_id": template_id},
                priority=NotificationPriority.NORMAL,
                scheduled_at=None,
            )
            if n and getattr(n, "id", None):
                send_notification_now.apply_async(args=[int(n.id)], queue='notifications')
                logger.info("Enqueued send_notification_now for manual entry", entry_id=entry.id, notification_id=int(n.id))
    except Exception as _e:
        from core.logging.logger import logger as _logger
        _logger.error("Failed to create notifications for manual entry", entry_id=entry.id, error=str(_e))
    
    return RedirectResponse(url="/owner/tasks/entries", status_code=303)


@router.post("/owner/tasks/entries/{entry_id}/complete")
async def owner_tasks_entries_complete(
    request: Request,
    entry_id: int,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Отметить задачу как выполненную."""
    from domain.entities.task_entry import TaskEntryV2
    from domain.entities.task_template import TaskTemplateV2
    from shared.services.payroll_adjustment_service import PayrollAdjustmentService
    from core.logging.logger import logger
    
    # Получаем entry с template
    entry_query = select(TaskEntryV2).where(TaskEntryV2.id == entry_id).options(
        selectinload(TaskEntryV2.template)
    )
    entry_result = await session.execute(entry_query)
    entry = entry_result.scalar_one_or_none()
    
    if not entry or entry.template.owner_id != current_user.id:
        return RedirectResponse(url="/owner/tasks/entries", status_code=303)
    
    if not entry.is_completed:
        entry.is_completed = True
        
        # Если есть начисление по задаче - создаём adjustment
        if entry.template.default_bonus_amount and entry.shift_schedule_id and entry.employee_id:
            adj_service = PayrollAdjustmentService(session)
            await adj_service.create_task_adjustment(
                shift_schedule_id=entry.shift_schedule_id,
                employee_id=entry.employee_id,
                task_code=entry.template.code,
                task_title=entry.template.title,
                amount=entry.template.default_bonus_amount,
                notes=f"Задача выполнена: {entry.template.title}"
            )
            logger.info(f"Created adjustment for TaskEntryV2: {entry_id}, amount={entry.template.default_bonus_amount}")
        
        await session.commit()
        logger.info(f"TaskEntryV2 completed: {entry_id}")
    
    return RedirectResponse(url="/owner/tasks/entries", status_code=303)

