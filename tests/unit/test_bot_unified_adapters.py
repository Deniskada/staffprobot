"""Smoke тесты парсинга TgAdapter и MaxAdapter."""

import pytest
from unittest.mock import MagicMock

from shared.bot_unified import NormalizedUpdate, TgAdapter, MaxAdapter

pytestmark = pytest.mark.ci_smoke


class TestTgAdapter:
    """TgAdapter.parse(Update) -> NormalizedUpdate."""

    def test_parse_message(self):
        update = MagicMock()
        update.message = MagicMock()
        update.message.chat_id = 123
        update.message.text = "/start"
        update.message.caption = None
        update.message.location = None
        update.message.photo = []
        update.message.contact = None
        update.message.from_user = MagicMock()
        update.message.from_user.id = 456
        update.message.from_user.username = "user"
        update.message.from_user.first_name = "Test"
        update.message.from_user.last_name = "User"
        update.callback_query = None

        nu = TgAdapter.parse(update)
        assert nu is not None
        assert nu.type == "message"
        assert nu.chat_id == "123"
        assert nu.text == "/start"
        assert nu.external_user_id == "456"
        assert nu.first_name == "Test"

    def test_parse_callback(self):
        update = MagicMock()
        update.message = None
        update.callback_query = MagicMock()
        update.callback_query.id = "cb_99"
        update.callback_query.data = "main_menu"
        update.callback_query.message = MagicMock()
        update.callback_query.message.chat_id = 777
        update.callback_query.from_user = MagicMock()
        update.callback_query.from_user.id = 555

        nu = TgAdapter.parse(update)
        assert nu is not None
        assert nu.type == "callback"
        assert nu.chat_id == "777"
        assert nu.callback_data == "main_menu"
        assert nu.callback_id == "cb_99"
        assert nu.external_user_id == "555"

    def test_parse_empty_returns_none(self):
        update = MagicMock()
        update.message = None
        update.callback_query = None
        assert TgAdapter.parse(update) is None


class TestMaxAdapter:
    """MaxAdapter.parse(raw) -> NormalizedUpdate."""

    def test_parse_message_created(self):
        raw = {
            "update_type": "message_created",
            "message": {
                "recipient": {"chat_id": 12345},
                "body": {"text": "привет", "attachments": []},
            },
        }
        nu = MaxAdapter.parse(raw)
        assert nu is not None
        assert nu.type == "message"
        assert nu.chat_id == "12345"
        assert nu.text == "привет"

    def test_parse_message_callback(self):
        raw = {
            "update_type": "message_callback",
            "callback": {"callback_id": "cb_99", "payload": "m"},
            "message": {"recipient": {"chat_id": 777}},
        }
        nu = MaxAdapter.parse(raw)
        assert nu is not None
        assert nu.type == "callback"
        assert nu.chat_id == "777"
        assert nu.callback_data == "m"
        assert nu.callback_id == "cb_99"

    def test_parse_bot_started(self):
        raw = {
            "update_type": "bot_started",
            "chat_id": 555,
            "user_id": "max_user_123",
            "payload": "auth_abc",
        }
        nu = MaxAdapter.parse(raw)
        assert nu is not None
        assert nu.type == "message"
        assert nu.chat_id == "555"
        assert nu.text == "/start auth_abc"
        assert nu.messenger == "max"
        assert nu.external_user_id == "max_user_123"

    def test_parse_location_attachment(self):
        raw = {
            "update_type": "message_created",
            "message": {
                "recipient": {"chat_id": 42},
                "sender": {"user_id": "u1"},
                "body": {
                    "text": "",
                    "attachments": [
                        {
                            "type": "location",
                            "payload": {"latitude": 55.75, "longitude": 37.61},
                        }
                    ],
                },
            },
        }
        nu = MaxAdapter.parse(raw)
        assert nu is not None
        assert nu.location == {"latitude": 55.75, "longitude": 37.61}
        assert nu.messenger == "max"

    def test_parse_location_text_coordinates(self):
        raw = {
            "update_type": "message_created",
            "message": {
                "recipient": {"chat_id": 42},
                "sender": {"user_id": "u1"},
                "body": {"text": "55.75,37.61", "attachments": []},
            },
        }
        nu = MaxAdapter.parse(raw)
        assert nu is not None
        assert nu.text == "55.75,37.61"
        assert nu.location is None

    def test_parse_unknown_returns_none(self):
        assert MaxAdapter.parse({}) is None
        assert MaxAdapter.parse({"update_type": "unknown"}) is None
