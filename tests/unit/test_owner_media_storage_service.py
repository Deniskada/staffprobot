"""Unit-тесты для OwnerMediaStorageService (restruct1 Фаза 1.5)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from domain.entities.owner_media_storage_option import OwnerMediaStorageOption
from shared.services import owner_media_storage_service as svc_mod


@pytest.fixture
def mock_session():
    s = AsyncMock()
    s.execute = AsyncMock()
    s.add = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_get_storage_mode_when_disabled(mock_session):
    """Опция выключена → всегда telegram."""
    with patch.object(svc_mod, "is_secure_media_enabled", new_callable=AsyncMock, return_value=False):
        mode = await svc_mod.get_storage_mode(mock_session, 1, "tasks")
    assert mode == "telegram"
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_storage_mode_when_enabled_no_option(mock_session):
    """Опция включена, настроек нет → telegram по умолчанию."""
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res
    with patch.object(svc_mod, "is_secure_media_enabled", new_callable=AsyncMock, return_value=True):
        mode = await svc_mod.get_storage_mode(mock_session, 1, "tasks")
    assert mode == "telegram"
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_storage_mode_when_enabled_with_option(mock_session):
    """Опция включена, есть настройка → возвращаем storage."""
    row = MagicMock(spec=OwnerMediaStorageOption)
    row.storage = "storage"
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = row
    mock_session.execute.return_value = mock_res
    with patch.object(svc_mod, "is_secure_media_enabled", new_callable=AsyncMock, return_value=True):
        mode = await svc_mod.get_storage_mode(mock_session, 1, "tasks")
    assert mode == "storage"


@pytest.mark.asyncio
async def test_set_storage_mode_insert(mock_session):
    """set_storage_mode создаёт новую опцию при commit=False."""
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res
    await svc_mod.set_storage_mode(mock_session, 1, "tasks", "both", commit=False)
    mock_session.add.assert_called_once()
    call_arg = mock_session.add.call_args[0][0]
    assert isinstance(call_arg, OwnerMediaStorageOption)
    assert call_arg.owner_id == 1
    assert call_arg.context == "tasks"
    assert call_arg.storage == "both"
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_set_storage_mode_invalid_context(mock_session):
    """Невалидный context → no-op, add не вызывается."""
    await svc_mod.set_storage_mode(mock_session, 1, "invalid_ctx", "storage")
    mock_session.execute.assert_not_called()
    mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_set_storage_mode_invalid_storage(mock_session):
    """Невалидный storage → no-op."""
    await svc_mod.set_storage_mode(mock_session, 1, "tasks", "invalid")
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_get_all_modes_defaults(mock_session):
    """get_all_modes без опций → все telegram."""
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_res
    modes = await svc_mod.get_all_modes(mock_session, 1)
    assert modes["tasks"] == "telegram"
    assert modes["cancellations"] == "telegram"
    assert modes["incidents"] == "telegram"
    assert modes["contracts"] == "telegram"


@pytest.mark.asyncio
async def test_get_all_modes_partial(mock_session):
    """get_all_modes с частичными опциями."""
    r1 = MagicMock()
    r1.context = "tasks"
    r1.storage = "both"
    r2 = MagicMock()
    r2.context = "cancellations"
    r2.storage = "storage"
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [r1, r2]
    mock_session.execute.return_value = mock_res
    modes = await svc_mod.get_all_modes(mock_session, 1)
    assert modes["tasks"] == "both"
    assert modes["cancellations"] == "storage"
    assert modes["incidents"] == "telegram"
    assert modes["contracts"] == "telegram"


def test_get_context_labels():
    """Метки контекстов для UI."""
    labels = svc_mod.get_context_labels()
    assert isinstance(labels, list)
    assert len(labels) >= 4
    keys = [x["value"] for x in labels]
    assert "tasks" in keys
    assert "cancellations" in keys


def test_get_storage_mode_labels():
    """Метки режимов для UI."""
    labels = svc_mod.get_storage_mode_labels()
    assert isinstance(labels, list)
    assert len(labels) >= 3
    keys = [x["value"] for x in labels]
    assert "telegram" in keys
    assert "storage" in keys
    assert "both" in keys
