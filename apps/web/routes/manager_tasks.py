"""Роуты управляющего для задач - использует shared TaskService."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from apps.web.jinja import templates
from apps.web.dependencies import get_current_user_dependency, require_role
from core.database.session import get_db_session
from domain.entities.user import User
from shared.services.task_service import TaskService
from shared.services.manager_permission_service import ManagerPermissionService
from sqlalchemy import select


router = APIRouter()


async def get_user_id_from_current_user(current_user, session: AsyncSession) -> int:
    """Получить внутренний user_id из current_user (может быть dict или User)."""
    if isinstance(current_user, dict):
        telegram_id = current_user.get("telegram_id") or current_user.get("id")
        result = await session.execute(
            select(User.id).where(User.telegram_id == telegram_id)
        )
        user_id = result.scalar_one_or_none()
        if not user_id:
            raise ValueError(f"User with telegram_id={telegram_id} not found")
        return user_id
    return current_user.id


@router.get("/manager/tasks/templates")
async def manager_tasks_templates(
    request: Request,
    show_inactive: int = 0,
    object_id: str | None = Query(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["manager", "owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Библиотека шаблонов задач (фильтр по объектам управляющего)."""
    user_id = await get_user_id_from_current_user(current_user, session)
    task_service = TaskService(session)
    
    # Для manager передаём owner_id из контракта
    owner_id = current_user.get("owner_id") if isinstance(current_user, dict) else None
    
    # Явная фильтрация: show_inactive=1 показывает все, иначе только активные
    active_only = not bool(show_inactive)
    
    # Определяем владельцев по доступным объектам
    perm_service = ManagerPermissionService(session)
    accessible_objects = await perm_service.get_user_accessible_objects(user_id)
    owner_ids = sorted({getattr(o, 'owner_id', None) for o in accessible_objects if getattr(o, 'owner_id', None) is not None})

    # Сбор шаблонов по всем владельцам, доступным менеджеру
    templates_list = []
    seen_ids = set()
    if selected_object_id:
        # Фильтр по конкретному объекту
        # Находим owner объекта
        obj_owner_id = next((o.owner_id for o in accessible_objects if o.id == selected_object_id), None)
        if obj_owner_id:
            tpl = await task_service.get_templates_for_role(
                user_id=user_id,
                role="manager",
                owner_id=obj_owner_id,
                object_id=selected_object_id,
                active_only=active_only
            )
            for t in tpl:
                if t.id not in seen_ids:
                    seen_ids.add(t.id)
                    templates_list.append(t)
    else:
        # Без фильтра объекта — объединяем по всем owner_id
        for oid in owner_ids:
            tpl = await task_service.get_templates_for_role(
                user_id=user_id,
                role="manager",
                owner_id=oid,
                active_only=active_only
            )
            for t in tpl:
                if t.id not in seen_ids:
                    seen_ids.add(t.id)
                    templates_list.append(t)
    # Доступные объекты для менеджера (для фильтра)
    # perm_service уже инициализирован выше
    accessible_objects = accessible_objects
    selected_object_id = None
    if object_id is not None and object_id != "":
        try:
            selected_object_id = int(object_id)
        except ValueError:
            selected_object_id = None
    # Серверная фильтрация по объекту (пытаемся определить поле связи)
    if selected_object_id:
        filtered = []
        for t in templates_list:
            oid = getattr(t, 'object_id', None)
            if oid == selected_object_id:
                filtered.append(t)
                continue
            # Списки применимости
            obj_ids = getattr(t, 'object_ids', None) or getattr(t, 'applicable_object_ids', None)
            if obj_ids and selected_object_id in list(obj_ids):
                filtered.append(t)
        templates_list = filtered
    return templates.TemplateResponse(
        "manager/tasks/templates.html",
        {
            "request": request, 
            "templates_list": templates_list,
            "show_inactive": show_inactive,
            "objects": accessible_objects,
            "selected_object_id": selected_object_id
        }
    )


@router.get("/manager/tasks/entries")
async def manager_tasks_entries(
    request: Request,
    object_id: str | None = Query(None),
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["manager", "owner", "superadmin"])),
    session: AsyncSession = Depends(get_db_session)
):
    """Выполнение и аудит задач (фильтр по объектам управляющего)."""
    user_id = await get_user_id_from_current_user(current_user, session)
    task_service = TaskService(session)
    
    owner_id = current_user.get("owner_id") if isinstance(current_user, dict) else None
    
    # Определяем владельцев по доступным объектам
    perm_service = ManagerPermissionService(session)
    accessible_objects = await perm_service.get_user_accessible_objects(user_id)
    owner_ids = sorted({getattr(o, 'owner_id', None) for o in accessible_objects if getattr(o, 'owner_id', None) is not None})

    # Собираем записи задач по всем доступным владельцам
    entries = []
    seen_ids = set()
    for oid in owner_ids:
        part = await task_service.get_entries_for_role(
            user_id=user_id,
            role="manager",
            owner_id=oid,
            limit=1000
        )
        for e in part:
            if e.id not in seen_ids:
                seen_ids.add(e.id)
                entries.append(e)
    # Доступные объекты и фильтр
    # accessible_objects уже получены
    selected_object_id = None
    if object_id is not None and object_id != "":
        try:
            selected_object_id = int(object_id)
        except ValueError:
            selected_object_id = None
    if selected_object_id:
        def extract_object_id(e):
            oid = getattr(e, 'object_id', None)
            if oid:
                return oid
            obj = getattr(e, 'object', None)
            return getattr(obj, 'id', None)
        entries = [e for e in entries if extract_object_id(e) == selected_object_id]
    return templates.TemplateResponse(
        "manager/tasks/entries.html",
        {"request": request, "entries": entries, "objects": accessible_objects, "selected_object_id": selected_object_id}
    )


@router.get("/manager/tasks/plan")
async def manager_tasks_plan(
    request: Request,
    current_user: User = Depends(get_current_user_dependency()),
    _: User = Depends(require_role(["manager", "owner", "superadmin"]))
):
    """Планирование задач (страница-заглушка для менеджера)."""
    return templates.TemplateResponse(
        "manager/tasks/plan.html",
        {"request": request}
    )

