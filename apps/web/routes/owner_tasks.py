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
from domain.entities.user import User
from shared.services.task_service import TaskService


router = APIRouter()


@router.get("/owner/tasks")
async def owner_tasks_index(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_role(["owner", "superadmin"]))
):
    """Главная страница задач."""
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


@router.post("/owner/tasks/plan/create")
async def owner_tasks_plan_create(
    request: Request,
    creation_mode: str = Form("template"),
    template_id: str = Form(None),
    task_title: str = Form(None),
    task_description: str = Form(None),
    task_mandatory: int = Form(0),
    task_media: int = Form(0),
    task_amount: str = Form(None),
    task_code: str = Form(None),
    object_id: str = Form(None),
    planned_date: str = Form(None),
    planned_time_start: str = Form(None),
    recurrence_type: str = Form(None),
    weekday: list[str] = Form(None),
    day_interval: int = Form(None),
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
    obj_id = int(object_id) if object_id else None
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
            default_amount=Decimal(task_amount) if task_amount else None,
            is_active=True,
            object_id=None  # Шаблоны без привязки к объекту
        )
        session.add(new_template)
        await session.flush()
        final_template_id = new_template.id
        logger.info(f"Created on-the-fly template: {new_template.id} ({task_code})")
    
    # Формируем recurrence_config
    recurrence_config = None
    if recurrence_type == "weekdays" and weekday:
        recurrence_config = {"weekdays": [int(d) for d in weekday]}
    elif recurrence_type == "day_interval" and day_interval:
        recurrence_config = {"interval": day_interval}
    
    # Создаём план
    plan = TaskPlanV2(
        template_id=final_template_id,
        owner_id=owner_id,
        object_id=obj_id,
        planned_date=p_date,
        planned_time_start=p_time,
        recurrence_type=recurrence_type if recurrence_type else None,
        recurrence_config=recurrence_config,
        recurrence_end_date=end_date,
        is_active=True
    )
    session.add(plan)
    await session.flush()  # Получаем plan.id
    logger.info(f"Created TaskPlanV2: {plan.id}, template={final_template_id}, object={obj_id}, recurrence={recurrence_type}")
    
    # Мгновенное создание TaskEntry для уже активных смен
    from core.celery.tasks.task_assignment import create_task_entries_for_active_shifts
    created_entries = await create_task_entries_for_active_shifts(session, plan)
    logger.info(f"Created {created_entries} TaskEntryV2 for active shifts of plan {plan.id}")
    
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

