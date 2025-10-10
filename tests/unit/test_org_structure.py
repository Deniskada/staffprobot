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

