"""Unit-тесты для IncidentService."""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from shared.services.incident_service import IncidentService
from domain.entities.incident import Incident


@pytest.fixture
def mock_session():
    """Мок AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    session.delete = MagicMock()
    return session


@pytest.fixture
def incident_service(mock_session):
    return IncidentService(mock_session)


def _make_incident(
    id_=1,
    owner_id=10,
    object_id=5,
    employee_id=20,
    incident_type="deduction",
    category="damage",
    severity="medium",
    status="new",
    damage_amount=None,
    custom_number=None,
    custom_date=None,
    compensate_purchase=False,
    created_by=10,
    notes=None,
):
    inc = Incident(
        owner_id=owner_id,
        object_id=object_id,
        employee_id=employee_id,
        incident_type=incident_type,
        category=category,
        severity=severity,
        status=status,
        damage_amount=damage_amount,
        custom_number=custom_number,
        custom_date=custom_date,
        compensate_purchase=compensate_purchase,
        created_by=created_by,
        notes=notes,
    )
    inc.id = id_
    return inc


# --- get_incident_by_id ---


@pytest.mark.asyncio
async def test_get_incident_by_id_found(incident_service, mock_session):
    """get_incident_by_id возвращает инцидент при наличии."""
    inc = _make_incident(id_=42)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = inc
    mock_session.execute.return_value = result_mock

    out = await incident_service.get_incident_by_id(42)
    assert out is inc
    assert out.id == 42


@pytest.mark.asyncio
async def test_get_incident_by_id_not_found(incident_service, mock_session):
    """get_incident_by_id возвращает None при отсутствии."""
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = result_mock

    out = await incident_service.get_incident_by_id(999)
    assert out is None


# --- get_incidents_for_role ---


@pytest.mark.asyncio
async def test_get_incidents_for_role_owner(incident_service, mock_session):
    """get_incidents_for_role для owner фильтрует по owner_id."""
    incs = [_make_incident(id_=1), _make_incident(id_=2)]
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = incs
    mock_session.execute.return_value = result_mock

    out = await incident_service.get_incidents_for_role(user_id=10, role="owner")
    assert len(out) == 2
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_incidents_for_role_owner_with_incident_type(incident_service, mock_session):
    """get_incidents_for_role с incident_type добавляет фильтр."""
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result_mock

    await incident_service.get_incidents_for_role(
        user_id=10, role="owner", incident_type="request"
    )
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_incidents_for_role_employee(incident_service, mock_session):
    """get_incidents_for_role для employee фильтрует по employee_id."""
    incs = [_make_incident(id_=1, employee_id=7)]
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = incs
    mock_session.execute.return_value = result_mock

    out = await incident_service.get_incidents_for_role(user_id=7, role="employee")
    assert len(out) == 1
    assert out[0].employee_id == 7


@pytest.mark.asyncio
async def test_get_incidents_for_role_unknown(incident_service, mock_session):
    """get_incidents_for_role для неизвестной роли возвращает []."""
    out = await incident_service.get_incidents_for_role(user_id=10, role="unknown")
    assert out == []
    mock_session.execute.assert_not_called()


# --- create_incident ---


@pytest.mark.asyncio
async def test_create_incident_deduction_default_severity(incident_service, mock_session):
    """create_incident для deduction по умолчанию ставит severity medium."""
    with patch.object(incident_service, "_notify_incident_created", new_callable=AsyncMock):
        def _set_id_on_incident(obj):
            if isinstance(obj, Incident):
                obj.id = 1

        mock_session.add.side_effect = _set_id_on_incident

        inc = await incident_service.create_incident(
            owner_id=10,
            category="damage",
            created_by=10,
            incident_type="deduction",
        )
        assert inc.severity == "medium"
        assert inc.incident_type == "deduction"
        assert inc.status == "new"
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_create_incident_request_default_severity(incident_service, mock_session):
    """create_incident для request по умолчанию ставит severity low."""
    with patch.object(incident_service, "_notify_incident_created", new_callable=AsyncMock):
        def _set_id_on_incident(obj):
            if isinstance(obj, Incident):
                obj.id = 1

        mock_session.add.side_effect = _set_id_on_incident

        inc = await incident_service.create_incident(
            owner_id=10,
            category="Закупка материалов",
            created_by=10,
            incident_type="request",
        )
        assert inc.severity == "low"
        assert inc.incident_type == "request"


# --- update_incident_status ---


@pytest.mark.asyncio
async def test_update_incident_status_not_found(incident_service, mock_session):
    """update_incident_status возвращает None, если инцидент не найден."""
    mock_session.get.return_value = None
    out = await incident_service.update_incident_status(
        incident_id=999, new_status="resolved", changed_by=10
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_incident_status_success(incident_service, mock_session):
    """update_incident_status обновляет статус и пишет историю."""
    inc = _make_incident(id_=1, status="new")
    mock_session.get.return_value = inc
    with patch.object(incident_service, "_notify_incident_resolved", new_callable=AsyncMock):
        with patch.object(incident_service, "_notify_incident_rejected", new_callable=AsyncMock):
            out = await incident_service.update_incident_status(
                incident_id=1, new_status="resolved", changed_by=10
            )
    assert out is inc
    assert inc.status == "resolved"
    mock_session.commit.assert_called()


# --- update_incident ---


@pytest.mark.asyncio
async def test_update_incident_not_found(incident_service, mock_session):
    """update_incident возвращает None, если инцидент не найден."""
    mock_session.get.return_value = None
    out = await incident_service.update_incident(
        incident_id=999, data={"category": "new_cat"}, changed_by=10
    )
    assert out is None


@pytest.mark.asyncio
async def test_update_incident_resolved_raises(incident_service, mock_session):
    """update_incident выбрасывает ValueError для resolved."""
    inc = _make_incident(id_=1, status="resolved")
    mock_session.get.return_value = inc
    with pytest.raises(ValueError, match="Нельзя редактировать инцидент со статусом 'resolved'"):
        await incident_service.update_incident(
            incident_id=1, data={"category": "x"}, changed_by=10
        )


@pytest.mark.asyncio
async def test_update_incident_rejected_raises(incident_service, mock_session):
    """update_incident выбрасывает ValueError для rejected."""
    inc = _make_incident(id_=1, status="rejected")
    mock_session.get.return_value = inc
    with pytest.raises(ValueError, match="Нельзя редактировать инцидент со статусом 'rejected'"):
        await incident_service.update_incident(
            incident_id=1, data={"notes": "x"}, changed_by=10
        )


@pytest.mark.asyncio
async def test_update_incident_compensate_purchase(incident_service, mock_session):
    """update_incident обновляет compensate_purchase для request."""
    inc = _make_incident(id_=1, status="new", incident_type="request", compensate_purchase=False)
    mock_session.get.return_value = inc
    out = await incident_service.update_incident(
        incident_id=1,
        data={"compensate_purchase": True},
        changed_by=10,
    )
    assert out is inc
    assert inc.compensate_purchase is True
    mock_session.commit.assert_called()


# --- cancel_incident ---


@pytest.mark.asyncio
async def test_cancel_incident_not_found(incident_service, mock_session):
    """cancel_incident возвращает None, если инцидент не найден."""
    mock_session.get.return_value = None
    out = await incident_service.cancel_incident(
        incident_id=999,
        cancellation_reason="duplicate",
        cancelled_by=10,
    )
    assert out is None


@pytest.mark.asyncio
async def test_cancel_incident_resolved_raises(incident_service, mock_session):
    """cancel_incident выбрасывает ValueError для уже решённого."""
    inc = _make_incident(id_=1, status="resolved")
    mock_session.get.return_value = inc
    with pytest.raises(ValueError, match="Нельзя отменить инцидент со статусом 'resolved'"):
        await incident_service.cancel_incident(
            incident_id=1,
            cancellation_reason="duplicate",
            cancelled_by=10,
        )


@pytest.mark.asyncio
async def test_cancel_incident_success(incident_service, mock_session):
    """cancel_incident переводит в cancelled и дополняет notes."""
    inc = _make_incident(id_=1, status="new", notes="Исходно")
    mock_session.get.return_value = inc
    with patch.object(incident_service, "_notify_incident_cancelled", new_callable=AsyncMock):
        out = await incident_service.cancel_incident(
            incident_id=1,
            cancellation_reason="duplicate",
            cancelled_by=10,
        )
    assert out is inc
    assert inc.status == "cancelled"
    assert "[ОТМЕНЕН]" in (inc.notes or "")
    mock_session.commit.assert_called()


# --- get_adjustments_by_incident ---


@pytest.mark.asyncio
async def test_get_adjustments_by_incident(incident_service, mock_session):
    """get_adjustments_by_incident возвращает список корректировок."""
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = result_mock

    out = await incident_service.get_adjustments_by_incident(incident_id=1)
    assert out == []
    mock_session.execute.assert_called_once()
