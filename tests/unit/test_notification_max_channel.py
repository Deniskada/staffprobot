"""Смоук: канал MAX в домене и шаблонах (план max-bot / tests-and-rollout)."""

import pytest

from domain.entities.notification import Notification, NotificationChannel, NotificationType
from shared.templates.notifications.base_templates import NotificationTemplateManager

pytestmark = pytest.mark.ci_smoke


def test_notification_channel_max_value():
    assert NotificationChannel.MAX.value == "max"


def test_notification_channel_enum_from_string():
    n = Notification(
        user_id=1,
        type=NotificationType.SHIFT_REMINDER.value,
        channel="max",
        title="t",
        message="m",
    )
    assert n.channel_enum == NotificationChannel.MAX


def test_template_render_max_matches_telegram_body():
    """MAX использует тот же текст, что telegram-вариант (в т.ч. $link_url)."""
    variables = {
        "user_name": "Иван",
        "time_until": "1 ч",
        "object_name": "ТЦ",
        "object_address": "ул. 1",
        "shift_time": "10:00–18:00",
        "link_url": "https://example.test/l",
    }
    tg = NotificationTemplateManager.render(
        NotificationType.SHIFT_REMINDER,
        NotificationChannel.TELEGRAM,
        variables,
    )
    mx = NotificationTemplateManager.render(
        NotificationType.SHIFT_REMINDER,
        NotificationChannel.MAX,
        variables,
    )
    assert tg["title"] == mx["title"]
    assert tg["message"] == mx["message"]
    assert "https://example.test/l" in mx["message"]
