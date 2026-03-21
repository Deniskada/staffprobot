"""Предпочтения владельца для групповых рассылок (праздники / toggles)."""

import pytest

from shared.services.report_group_broadcast import (
    REPORT_GROUP_MESSENGERS_KEY,
    owner_wants_holiday_report_group_broadcast,
)

pytestmark = pytest.mark.ci_smoke


def test_holiday_broadcast_default_true():
    assert owner_wants_holiday_report_group_broadcast({}) is True


def test_holiday_broadcast_report_group_both_off():
    prefs = {REPORT_GROUP_MESSENGERS_KEY: {"telegram": False, "max": False}}
    assert owner_wants_holiday_report_group_broadcast(prefs) is False


def test_holiday_broadcast_report_group_tg_on():
    prefs = {REPORT_GROUP_MESSENGERS_KEY: {"telegram": True, "max": False}}
    assert owner_wants_holiday_report_group_broadcast(prefs) is True


def test_holiday_broadcast_report_group_max_on():
    prefs = {REPORT_GROUP_MESSENGERS_KEY: {"telegram": False, "max": True}}
    assert owner_wants_holiday_report_group_broadcast(prefs) is True


def test_holiday_broadcast_legacy_employee_holiday_greeting():
    prefs = {"employee_holiday_greeting": {"telegram": False}}
    assert owner_wants_holiday_report_group_broadcast(prefs) is False
