"""Unit-тесты для BillingService: цены хранения, лог опций (restruct1 Фаза 1.6)."""

import json
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from apps.web.services.billing_service import BillingService
from domain.entities.owner_profile import OwnerProfile
from domain.entities.tariff_plan import TariffPlan
from domain.entities.user_subscription import UserSubscription
from domain.entities.subscription_option_log import SubscriptionOptionLog


@pytest.fixture
def mock_session():
    s = AsyncMock()
    s.execute = AsyncMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    s.add = MagicMock()
    s.get = AsyncMock()
    s.refresh = AsyncMock()
    return s


def _mk_tariff(price: float, storage_option_price: float = 0, features=None):
    t = MagicMock(spec=TariffPlan)
    t.price = Decimal(str(price))
    t.storage_option_price = Decimal(str(storage_option_price))
    t.features = features or []
    return t


def _mk_sub(user_id: int, tariff_plan):
    s = MagicMock(spec=UserSubscription)
    s.user_id = user_id
    s.tariff_plan = tariff_plan
    s.id = 1
    return s


@pytest.mark.asyncio
async def test_compute_subscription_amount_base_only(mock_session):
    """База тарифа без опции: storage_option_price = 0."""
    svc = BillingService(mock_session)
    tariff = _mk_tariff(100.0, 0)
    sub = _mk_sub(1, tariff)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 100.0
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_compute_subscription_amount_option_added(mock_session):
    """Опция в тарифе и включена у владельца → база + доплата."""
    tariff = _mk_tariff(100.0, 50.0, ["secure_media_storage"])
    sub = _mk_sub(1, tariff)
    profile = MagicMock(spec=OwnerProfile)
    profile.enabled_features = ["secure_media_storage"]
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = profile
    mock_session.execute.return_value = mock_res

    svc = BillingService(mock_session)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 150.0
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_compute_subscription_amount_option_not_enabled(mock_session):
    """Опция в тарифе, но не включена у владельца → только база."""
    tariff = _mk_tariff(100.0, 50.0, ["secure_media_storage"])
    sub = _mk_sub(1, tariff)
    profile = MagicMock(spec=OwnerProfile)
    profile.enabled_features = []
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = profile
    mock_session.execute.return_value = mock_res

    svc = BillingService(mock_session)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 100.0


@pytest.mark.asyncio
async def test_compute_subscription_amount_option_not_in_tariff(mock_session):
    """Опция включена у владельца, но не в тарифе → только база."""
    tariff = _mk_tariff(100.0, 50.0, ["other_feature"])
    sub = _mk_sub(1, tariff)
    profile = MagicMock(spec=OwnerProfile)
    profile.enabled_features = ["secure_media_storage"]
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = profile
    mock_session.execute.return_value = mock_res

    svc = BillingService(mock_session)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 100.0


@pytest.mark.asyncio
async def test_compute_subscription_amount_enabled_features_str(mock_session):
    """enabled_features как JSON-строка."""
    tariff = _mk_tariff(100.0, 50.0, ["secure_media_storage"])
    sub = _mk_sub(1, tariff)
    profile = MagicMock(spec=OwnerProfile)
    profile.enabled_features = json.dumps(["secure_media_storage"])
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = profile
    mock_session.execute.return_value = mock_res

    svc = BillingService(mock_session)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 150.0


@pytest.mark.asyncio
async def test_compute_subscription_amount_no_profile(mock_session):
    """Нет профиля → только база."""
    tariff = _mk_tariff(100.0, 50.0, ["secure_media_storage"])
    sub = _mk_sub(1, tariff)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res

    svc = BillingService(mock_session)
    amount = await svc.compute_subscription_amount(1, sub, tariff)
    assert amount == 100.0


@pytest.mark.asyncio
async def test_log_option_change_creates_row(mock_session):
    """log_option_change добавляет запись и коммитит."""
    svc = BillingService(mock_session)
    await svc.log_option_change(1, options_enabled=["secure_media_storage"])
    mock_session.add.assert_called_once()
    call_arg = mock_session.add.call_args[0][0]
    assert isinstance(call_arg, SubscriptionOptionLog)
    assert call_arg.subscription_id == 1
    assert call_arg.options_enabled == ["secure_media_storage"]
    assert call_arg.options_disabled == []
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_log_option_change_disabled(mock_session):
    """log_option_change с options_disabled."""
    svc = BillingService(mock_session)
    await svc.log_option_change(2, options_disabled=["secure_media_storage"])
    mock_session.add.assert_called_once()
    call_arg = mock_session.add.call_args[0][0]
    assert call_arg.options_enabled == []
    assert call_arg.options_disabled == ["secure_media_storage"]


@pytest.mark.asyncio
async def test_log_option_change_noop_when_empty(mock_session):
    """Пустые enabled и disabled → add/commit не вызываются."""
    svc = BillingService(mock_session)
    await svc.log_option_change(1)
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()
