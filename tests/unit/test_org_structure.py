"""
Unit-тесты для OrgStructureService.

Тестируем:
- Создание подразделений
- Построение дерева
- Перемещение подразделений
- Валидация циклических ссылок
- Наследование настроек
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from apps.web.services.org_structure_service import OrgStructureService
from domain.entities.org_structure import OrgStructureUnit


@pytest.fixture
def mock_db_session():
    """Mock для AsyncSession."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def org_service(mock_db_session):
    """Фикстура для OrgStructureService."""
    return OrgStructureService(mock_db_session)


@pytest.fixture
def sample_root_unit():
    """Корневое подразделение."""
    return OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Основное подразделение",
        level=0,
        is_active=True
    )


@pytest.fixture
def sample_child_unit():
    """Дочернее подразделение."""
    return OrgStructureUnit(
        id=2,
        owner_id=100,
        parent_id=1,
        name="Отдел продаж",
        level=1,
        payment_system_id=3,
        is_active=True
    )


@pytest.mark.asyncio
async def test_get_unit_by_id(org_service, mock_db_session, sample_root_unit):
    """Тест получения подразделения по ID."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_root_unit
    mock_db_session.execute.return_value = mock_result
    
    # Act
    unit = await org_service.get_unit_by_id(1)
    
    # Assert
    assert unit is not None
    assert unit.id == 1
    assert unit.name == "Основное подразделение"


@pytest.mark.asyncio
async def test_get_units_by_owner(org_service, mock_db_session, sample_root_unit, sample_child_unit):
    """Тест получения всех подразделений владельца."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_root_unit, sample_child_unit]
    mock_db_session.execute.return_value = mock_result
    
    # Act
    units = await org_service.get_units_by_owner(100)
    
    # Assert
    assert len(units) == 2
    assert units[0].level == 0
    assert units[1].level == 1


@pytest.mark.asyncio
async def test_get_root_unit(org_service, mock_db_session, sample_root_unit):
    """Тест получения корневого подразделения."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_root_unit
    mock_db_session.execute.return_value = mock_result
    
    # Act
    root = await org_service.get_root_unit(100)
    
    # Assert
    assert root is not None
    assert root.parent_id is None
    assert root.level == 0


@pytest.mark.asyncio
async def test_create_root_unit(org_service, mock_db_session):
    """Тест создания корневого подразделения."""
    # Act
    unit = await org_service.create_unit(
        owner_id=100,
        name="Новое подразделение",
        parent_id=None
    )
    
    # Assert
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_create_child_unit(org_service, mock_db_session, sample_root_unit):
    """Тест создания дочернего подразделения."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_root_unit
    mock_db_session.execute.return_value = mock_result
    
    # Act
    unit = await org_service.create_unit(
        owner_id=100,
        name="Дочернее подразделение",
        parent_id=1
    )
    
    # Assert
    assert mock_db_session.add.called
    assert mock_db_session.commit.called


@pytest.mark.asyncio
async def test_validate_no_cycles_self_reference(org_service):
    """Тест валидации: нельзя установить себя родителем."""
    # Act
    result = await org_service.validate_no_cycles(1, 1)
    
    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_get_inherited_payment_system_direct(org_service, mock_db_session, sample_child_unit):
    """Тест получения системы оплаты: прямое указание."""
    # Arrange
    payment_system = MagicMock(id=3, name="Повременно-премиальная")
    
    # Mock для get_unit_by_id
    mock_unit_result = MagicMock()
    mock_unit_result.scalar_one_or_none.return_value = sample_child_unit
    
    # Mock для PaymentSystem
    mock_system_result = MagicMock()
    mock_system_result.scalar_one_or_none.return_value = payment_system
    
    mock_db_session.execute.side_effect = [mock_unit_result, mock_system_result]
    
    # Act
    system = await org_service.get_inherited_payment_system(2)
    
    # Assert
    assert system is not None
    assert system.id == 3


@pytest.mark.asyncio
async def test_get_org_tree_simple(org_service, mock_db_session, sample_root_unit, sample_child_unit):
    """Тест построения дерева: простая иерархия."""
    # Arrange
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_root_unit, sample_child_unit]
    mock_db_session.execute.return_value = mock_result
    
    # Act
    tree = await org_service.get_org_tree(100)
    
    # Assert
    assert len(tree) == 1  # Один корневой узел
    assert tree[0]['id'] == 1
    assert tree[0]['name'] == "Основное подразделение"
    assert len(tree[0]['children']) == 1  # Один дочерний узел
    assert tree[0]['children'][0]['id'] == 2
    assert tree[0]['children'][0]['name'] == "Отдел продаж"


@pytest.mark.asyncio
async def test_inheritance_payment_system():
    """Тест наследования системы оплаты."""
    # Arrange
    root = OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Корень",
        payment_system_id=1,  # Простая повременная
        level=0
    )
    
    child_with_own = OrgStructureUnit(
        id=2,
        owner_id=100,
        parent_id=1,
        name="Дочерний с собственной",
        payment_system_id=3,  # Повременно-премиальная
        level=1
    )
    child_with_own.parent = root
    
    child_inherited = OrgStructureUnit(
        id=3,
        owner_id=100,
        parent_id=1,
        name="Дочерний наследует",
        payment_system_id=None,  # Наследует
        level=1
    )
    child_inherited.parent = root
    
    # Act & Assert
    assert child_with_own.get_inherited_payment_system_id() == 3  # Свое значение
    assert child_inherited.get_inherited_payment_system_id() == 1  # От родителя


@pytest.mark.asyncio
async def test_inheritance_payment_schedule():
    """Тест наследования графика выплат."""
    # Arrange
    root = OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Корень",
        payment_schedule_id=5,  # Ежемесячно
        level=0
    )
    
    child = OrgStructureUnit(
        id=2,
        owner_id=100,
        parent_id=1,
        name="Дочерний",
        payment_schedule_id=None,
        level=1
    )
    child.parent = root
    
    # Act & Assert
    assert child.get_inherited_payment_schedule_id() == 5  # От родителя


@pytest.mark.asyncio
async def test_inheritance_late_settings():
    """Тест наследования настроек штрафов."""
    # Arrange
    root = OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Корень",
        inherit_late_settings=False,
        late_threshold_minutes=10,
        late_penalty_per_minute=Decimal("5.00"),
        level=0
    )
    
    # Дочерний с наследованием
    child_inherit = OrgStructureUnit(
        id=2,
        owner_id=100,
        parent_id=1,
        name="Дочерний наследует",
        inherit_late_settings=True,
        late_threshold_minutes=None,
        late_penalty_per_minute=None,
        level=1
    )
    child_inherit.parent = root
    
    # Дочерний с собственными настройками
    child_own = OrgStructureUnit(
        id=3,
        owner_id=100,
        parent_id=1,
        name="Дочерний собственные",
        inherit_late_settings=False,
        late_threshold_minutes=15,
        late_penalty_per_minute=Decimal("10.00"),
        level=1
    )
    child_own.parent = root
    
    # Act
    inherited_settings = child_inherit.get_inherited_late_settings()
    own_settings = child_own.get_inherited_late_settings()
    
    # Assert
    assert inherited_settings['threshold_minutes'] == 10  # От родителя
    assert inherited_settings['penalty_per_minute'] == Decimal("5.00")
    assert inherited_settings['inherited_from'] == "Корень"
    
    assert own_settings['threshold_minutes'] == 15  # Собственные
    assert own_settings['penalty_per_minute'] == Decimal("10.00")
    assert own_settings['inherited_from'] is None


@pytest.mark.asyncio
async def test_inheritance_chain_three_levels():
    """Тест наследования через 3 уровня."""
    # Arrange
    grandparent = OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Дедушка",
        payment_system_id=1,
        payment_schedule_id=5,
        level=0
    )
    
    parent = OrgStructureUnit(
        id=2,
        owner_id=100,
        parent_id=1,
        name="Родитель",
        payment_system_id=None,  # Наследует
        payment_schedule_id=None,  # Наследует
        level=1
    )
    parent.parent = grandparent
    
    child = OrgStructureUnit(
        id=3,
        owner_id=100,
        parent_id=2,
        name="Ребенок",
        payment_system_id=None,  # Наследует
        payment_schedule_id=None,  # Наследует
        level=2
    )
    child.parent = parent
    
    # Act & Assert
    # Ребенок должен унаследовать от дедушки (через родителя)
    assert child.get_inherited_payment_system_id() == 1
    assert child.get_inherited_payment_schedule_id() == 5


@pytest.mark.asyncio
async def test_full_path_single_level():
    """Тест получения полного пути: один уровень."""
    # Arrange
    root = OrgStructureUnit(
        id=1,
        owner_id=100,
        parent_id=None,
        name="Компания",
        level=0
    )
    
    # Act
    path = root.get_full_path()
    
    # Assert
    assert path == "Компания"


@pytest.mark.asyncio
async def test_full_path_multi_level():
    """Тест получения полного пути: несколько уровней."""
    # Arrange
    root = OrgStructureUnit(id=1, name="Компания", parent_id=None, level=0, owner_id=100)
    
    parent = OrgStructureUnit(id=2, name="Отдел продаж", parent_id=1, level=1, owner_id=100)
    parent.parent = root
    
    child = OrgStructureUnit(id=3, name="Московский офис", parent_id=2, level=2, owner_id=100)
    child.parent = parent
    
    # Act
    path = child.get_full_path()
    
    # Assert
    assert path == "Компания / Отдел продаж / Московский офис"


@pytest.mark.asyncio
async def test_update_unit_payment_settings(org_service, mock_db_session):
    """Тест обновления финансовых настроек подразделения."""
    # Arrange
    unit = MagicMock()
    unit.id = 1
    unit.owner_id = 100
    unit.payment_system_id = None
    unit.payment_schedule_id = None
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = unit
    mock_db_session.execute.return_value = mock_result
    
    # Act
    updated = await org_service.update_unit(
        unit_id=1,
        owner_id=100,
        data={
            "payment_system_id": 3,
            "payment_schedule_id": 5
        }
    )
    
    # Assert
    assert unit.payment_system_id == 3
    assert unit.payment_schedule_id == 5
    assert mock_db_session.commit.called

