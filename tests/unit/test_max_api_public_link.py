"""Парсинг публичной ссылки из ответа MAX POST /messages."""

import pytest

from shared.bot_unified.max_client import _max_api_public_link

pytestmark = pytest.mark.ci_smoke


@pytest.mark.parametrize(
    "payload,expected",
    [
        (None, None),
        ({}, None),
        ({"message": {"link": "https://max.ru/m/1"}}, "https://max.ru/m/1"),
        ({"message": {"body": {"url": "https://x/y"}}}, "https://x/y"),
        ({"body": {"message": {"permalink": "https://p/q"}}}, "https://p/q"),
        ({"url": "https://root"}, "https://root"),
    ],
)
def test_max_api_public_link(payload, expected):
    assert _max_api_public_link(payload) == expected
