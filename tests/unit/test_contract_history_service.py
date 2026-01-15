"""Unit-тесты для ContractHistoryService."""

import pytest
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from shared.services.contract_history_service import ContractHistoryService
from domain.entities.contract_history import ContractHistory, ContractChangeType
from domain.entities.contract import Contract
from domain.entities.user import User


@pytest.fixture
def mock_session():
    """Мок сессии SQLAlchemy."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def history_service(mock_session):
    """Создает экземпляр ContractHistoryService с мок-сессией."""
    return ContractHistoryService(mock_session)


@pytest.fixture
def sample_contract():
    """Образец договора для тестов."""
    contract = Contract()
    contract.id = 1
    contract.hourly_rate = Decimal('250.00')
    contract.use_contract_rate = True
    contract.payment_schedule_id = 1
    contract.status = 'active'
    return contract


@pytest.mark.asyncio
async def test_log_contract_change(history_service, mock_session):
    """Тест записи одного изменения договора."""
    # Вызов метода
    history_entry = await history_service.log_contract_change(
        contract_id=1,
        changed_by=7,
        change_type=ContractChangeType.UPDATED,
        field_name='hourly_rate',
        old_value=Decimal('250.00'),
        new_value=Decimal('300.00'),
        change_reason='Повышение ставки'
    )
    
    # Проверки
    assert history_entry is not None
    assert history_entry.contract_id == 1
    assert history_entry.changed_by == 7
    assert history_entry.change_type == 'updated'
    assert history_entry.field_name == 'hourly_rate'
    assert history_entry.change_reason == 'Повышение ставки'
    mock_session.add.assert_called_once()
    await mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_log_contract_changes_batch(history_service, mock_session):
    """Тест записи множественных изменений договора."""
    # Вызов метода
    changes = {
        'hourly_rate': {'old': Decimal('250.00'), 'new': Decimal('300.00')},
        'use_contract_rate': {'old': False, 'new': True},
        'status': {'old': 'draft', 'new': 'active'}
    }
    
    history_entries = await history_service.log_contract_changes(
        contract_id=1,
        changed_by=7,
        changes=changes,
        change_type=ContractChangeType.UPDATED,
        change_reason='Обновление договора'
    )
    
    # Проверки
    assert len(history_entries) == 3
    assert mock_session.add.call_count == 3
    await mock_session.flush.assert_called()


@pytest.mark.asyncio
async def test_get_contract_history(history_service, mock_session):
    """Тест получения истории изменений договора."""
    # Создаем мок-записи истории
    history_entry1 = ContractHistory()
    history_entry1.id = 1
    history_entry1.contract_id = 1
    history_entry1.changed_at = datetime(2026, 1, 15, 10, 0, 0)
    history_entry1.field_name = 'hourly_rate'
    history_entry1.change_type = 'updated'
    history_entry1.changed_by = 7
    
    history_entry2 = ContractHistory()
    history_entry2.id = 2
    history_entry2.contract_id = 1
    history_entry2.changed_at = datetime(2026, 1, 14, 10, 0, 0)
    history_entry2.field_name = 'status'
    history_entry2.change_type = 'status_changed'
    history_entry2.changed_by = 7
    
    # Настройка мока для загрузки пользователей
    user = User()
    user.id = 7
    user.first_name = 'Test'
    user.last_name = 'User'
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [history_entry1, history_entry2]
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value.all.return_value = [user]
    
    async def execute_side_effect(query):
        # Первый вызов - получение истории
        if 'contract_history' in str(query):
            return mock_result
        # Второй вызов - получение пользователей
        elif 'users' in str(query):
            return mock_result2
        return mock_result
    
    mock_session.execute.side_effect = execute_side_effect
    
    # Вызов метода
    history = await history_service.get_contract_history(
        contract_id=1,
        limit=10,
        offset=0
    )
    
    # Проверки
    assert len(history) == 2
    assert history[0].id == 1
    assert history[1].id == 2


@pytest.mark.asyncio
async def test_get_contract_snapshot(history_service, mock_session, sample_contract):
    """Тест получения снимка договора на дату."""
    # Настройка мока для получения договора
    contract_result = MagicMock()
    contract_result.scalar_one_or_none.return_value = sample_contract
    mock_session.execute.return_value = contract_result
    
    # Вызов метода
    snapshot = await history_service.get_contract_snapshot(
        contract_id=1,
        target_date=date(2026, 1, 15)
    )
    
    # Проверки
    assert snapshot is not None
    assert 'hourly_rate' in snapshot
    assert 'use_contract_rate' in snapshot
    assert 'status' in snapshot
    assert snapshot['hourly_rate'] == 250.0
    assert snapshot['use_contract_rate'] is True
    assert snapshot['status'] == 'active'


@pytest.mark.asyncio
async def test_get_field_history(history_service, mock_session):
    """Тест получения истории конкретного поля."""
    # Создаем мок-записи истории
    history_entry = ContractHistory()
    history_entry.id = 1
    history_entry.contract_id = 1
    history_entry.field_name = 'hourly_rate'
    history_entry.changed_at = datetime(2026, 1, 15, 10, 0, 0)
    
    user = User()
    user.id = 7
    user.first_name = 'Test'
    user.last_name = 'User'
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [history_entry]
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value.all.return_value = [user]
    
    async def execute_side_effect(query):
        if 'contract_history' in str(query):
            return mock_result
        elif 'users' in str(query):
            return mock_result2
        return mock_result
    
    mock_session.execute.side_effect = execute_side_effect
    
    # Вызов метода
    field_history = await history_service.get_field_history(
        contract_id=1,
        field_name='hourly_rate'
    )
    
    # Проверки
    assert len(field_history) == 1
    assert field_history[0].field_name == 'hourly_rate'


@pytest.mark.asyncio
async def test_serialize_value(history_service):
    """Тест сериализации значений для JSONB."""
    # Тестируем различные типы значений
    assert history_service._serialize_value(Decimal('250.00')) == 250.0
    assert history_service._serialize_value(date(2026, 1, 15)) == '2026-01-15'
    assert history_service._serialize_value([1, 2, 3]) == [1, 2, 3]
    assert history_service._serialize_value({'key': 'value'}) == {'key': 'value'}
    assert history_service._serialize_value(None) is None
    assert history_service._serialize_value('string') == 'string'
