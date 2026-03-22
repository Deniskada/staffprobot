"""Smoke: user_state_storage_key — выбор ключа хранения состояния по мессенджеру."""

import pytest

from shared.bot_unified.user_resolver import user_state_storage_key

pytestmark = pytest.mark.ci_smoke


def test_telegram_uses_telegram_id():
    assert user_state_storage_key("telegram", 42, 999) == 999


def test_telegram_without_telegram_id_falls_back():
    assert user_state_storage_key("telegram", 42, None) == 42


def test_max_uses_internal_id():
    assert user_state_storage_key("max", 42, None) == 42


def test_max_ignores_telegram_id():
    assert user_state_storage_key("max", 42, 999) == 42


def test_unknown_messenger_uses_internal_id():
    assert user_state_storage_key("vk", 77, 888) == 77
