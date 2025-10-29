"""Юнит-тесты для TaskService (Tasks v2)."""

import pytest
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from shared.services.task_service import TaskService
from domain.entities.task_template import TaskTemplateV2
from domain.entities.task_plan import TaskPlanV2
from domain.entities.task_entry import TaskEntryV2


@pytest.fixture
async def task_service(db_session: AsyncSession):
    """Создать экземпляр TaskService для тестов."""
    return TaskService(db_session)


@pytest.mark.asyncio
async def test_create_template(task_service: TaskService):
    """Тест создания шаблона задачи."""
    template = await task_service.create_template(
        owner_id=1,
        code="test_template",
        title="Тестовая задача",
        description="Описание",
        is_mandatory=True,
        requires_media=True,
        default_bonus_amount=Decimal("100")
    )
    
    assert template.id is not None
    assert template.code == "test_template"
    assert template.is_mandatory is True
    assert template.default_bonus_amount == Decimal("100")


@pytest.mark.asyncio
async def test_get_templates_for_owner(task_service: TaskService, db_session: AsyncSession):
    """Тест получения шаблонов для владельца (все)."""
    # Создаём активный и неактивный
    active = TaskTemplateV2(
        owner_id=1,
        code="active",
        title="Активная",
        is_active=True
    )
    inactive = TaskTemplateV2(
        owner_id=1,
        code="inactive",
        title="Неактивная",
        is_active=False
    )
    db_session.add_all([active, inactive])
    await db_session.commit()
    
    # Owner видит все (по умолчанию)
    templates = await task_service.get_templates_for_role(
        user_id=1,
        role="owner"
    )
    
    assert len(templates) == 2


@pytest.mark.asyncio
async def test_get_templates_for_selection(task_service: TaskService, db_session: AsyncSession):
    """Тест получения шаблонов для форм выбора (только активные)."""
    active = TaskTemplateV2(owner_id=1, code="a1", title="A1", is_active=True)
    inactive = TaskTemplateV2(owner_id=1, code="a2", title="A2", is_active=False)
    db_session.add_all([active, inactive])
    await db_session.commit()
    
    # for_selection=True → только активные
    templates = await task_service.get_templates_for_role(
        user_id=1,
        role="owner",
        for_selection=True
    )
    
    assert len(templates) == 1
    assert templates[0].code == "a1"


@pytest.mark.asyncio
async def test_get_entries_for_shift(task_service: TaskService, db_session: AsyncSession):
    """Тест получения задач для смены по shift_id."""
    # Создаём template, plan, entry
    template = TaskTemplateV2(owner_id=1, code="t1", title="Task 1", is_active=True)
    db_session.add(template)
    await db_session.flush()
    
    plan = TaskPlanV2(template_id=template.id, owner_id=1, is_active=True)
    db_session.add(plan)
    await db_session.flush()
    
    entry = TaskEntryV2(
        template_id=template.id,
        plan_id=plan.id,
        shift_id=999,  # Тестовая смена
        employee_id=2,
        is_completed=False
    )
    db_session.add(entry)
    await db_session.commit()
    
    # Получаем задачи для смены
    entries = await task_service.get_entries_for_shift(shift_id=999)
    
    assert len(entries) == 1
    assert entries[0].shift_id == 999
    assert entries[0].template.title == "Task 1"


@pytest.mark.asyncio
async def test_mark_entry_completed(task_service: TaskService, db_session: AsyncSession):
    """Тест отметки задачи выполненной."""
    template = TaskTemplateV2(owner_id=1, code="t1", title="Task 1", is_active=True)
    db_session.add(template)
    await db_session.flush()
    
    entry = TaskEntryV2(
        template_id=template.id,
        shift_id=999,
        employee_id=2,
        is_completed=False
    )
    db_session.add(entry)
    await db_session.commit()
    
    # Отмечаем выполненной
    success = await task_service.mark_entry_completed(
        entry_id=entry.id,
        completion_notes="Готово",
        completion_media=[{"url": "https://example.com/photo.jpg", "type": "photo"}]
    )
    
    assert success is True
    
    # Проверяем обновление
    await db_session.refresh(entry)
    assert entry.is_completed is True
    assert entry.completion_notes == "Готово"
    assert len(entry.completion_media) == 1

