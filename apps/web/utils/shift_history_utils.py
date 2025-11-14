"""Вспомогательные функции для отображения истории смен."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from domain.entities.shift_history import ShiftHistory
from apps.web.utils.timezone_utils import web_timezone_helper


HISTORY_META: Dict[str, Dict[str, str]] = {
    "schedule_plan": {
        "title": "Смена запланирована",
        "icon": "bi-calendar-plus",
        "badge": "bg-primary",
    },
    "schedule_cancel": {
        "title": "Смена отменена",
        "icon": "bi-x-circle",
        "badge": "bg-danger",
    },
    "schedule_complete": {
        "title": "Запланированная смена завершена",
        "icon": "bi-check-circle",
        "badge": "bg-success",
    },
    "shift_open": {
        "title": "Смена открыта",
        "icon": "bi-play-circle",
        "badge": "bg-success",
    },
    "shift_close": {
        "title": "Смена закрыта",
        "icon": "bi-stop-circle",
        "badge": "bg-secondary",
    },
    "shift_auto_close": {
        "title": "Смена автоматически закрыта",
        "icon": "bi-robot",
        "badge": "bg-secondary",
    },
    "shift_manual_close": {
        "title": "Смена закрыта вручную",
        "icon": "bi-wrench-adjustable-circle",
        "badge": "bg-secondary",
    },
    "shift_cancel": {
        "title": "Смена отменена",
        "icon": "bi-x-circle",
        "badge": "bg-danger",
    },
    "default": {
        "title": "Операция",
        "icon": "bi-dot",
        "badge": "bg-light text-dark",
    },
}

PAYLOAD_LABELS: Dict[str, str] = {
    "reason_code": "Причина",
    "notes": "Комментарий",
    "document_description": "Документ",
    "object_id": "Объект",
    "employee_id": "Сотрудник",
    "time_slot_id": "Тайм-слот",
    "planned_start": "Плановое начало",
    "planned_end": "Плановое окончание",
    "coordinates": "Координаты",
    "hours": "Часы",
    "hours_before_shift": "До начала",
    "payment": "Выплата",
    "auto_closed_at": "Автозакрытие",
    "contract_id": "Договор",
    "fine_amount": "Сумма штрафа",
    "fine_reason": "Основание штрафа",
    "origin": "Источник данных",
}

PAYLOAD_ORDER: List[str] = [
    "reason_code",
    "notes",
    "document_description",
    "object_id",
    "employee_id",
    "time_slot_id",
    "planned_start",
    "planned_end",
    "coordinates",
    "hours_before_shift",
    "hours",
    "payment",
    "contract_id",
    "fine_amount",
    "fine_reason",
    "auto_closed_at",
    "origin",
]

HIDDEN_KEYS = {"caller", "interface"}

TIME_KEYS = {"planned_start", "planned_end", "auto_closed_at"}

SOURCE_LABELS: Dict[str, str] = {
    "web": "Веб-интерфейс",
    "bot": "Telegram-бот",
    "system": "Система",
}

ROLE_LABELS: Dict[str, str] = {
    "owner": "Владелец",
    "manager": "Управляющий",
    "employee": "Сотрудник",
    "system": "Система",
    "superadmin": "Суперадмин",
}

DEFAULT_REASON_TITLES: Dict[str, str] = {
    "medical_cert": "Медицинская справка",
    "emergency_cert": "Чрезвычайная ситуация",
    "police_cert": "Справка МВД",
    "family_reason": "Семейные обстоятельства",
    "other": "Другая причина",
}


def _format_datetime(value: Any, timezone: str) -> str:
    """Отформатировать дату/время в timezone объекта."""
    if isinstance(value, datetime):
        return web_timezone_helper.format_datetime_with_timezone(value, timezone, "%d.%m.%Y %H:%M")

    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
            return web_timezone_helper.format_datetime_with_timezone(parsed, timezone, "%d.%m.%Y %H:%M")
        except ValueError:
            return value

    return str(value)


def _format_hours(value: Any) -> str:
    try:
        hours_float = float(value)
    except (TypeError, ValueError):
        return str(value)

    total_minutes = int(round(hours_float * 60))
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours and minutes:
        return f"{hours} ч {minutes} мин"
    if hours:
        return f"{hours} ч"
    return f"{minutes} мин"


def _format_payload_value(
    key: str,
    value: Any,
    timezone: str,
) -> str:
    """Привести значение payload к строке для отображения."""
    if key in TIME_KEYS:
        return _format_datetime(value, timezone)

    if key == "hours":
        try:
            return f"{float(value):.2f}"
        except (TypeError, ValueError):
            return str(value)

    if key == "payment":
        try:
            return f"{float(value):.2f} ₽"
        except (TypeError, ValueError):
            return str(value)

    if key == "hours_before_shift":
        return _format_hours(value)

    return str(value)


def build_shift_history_items(
    entries: Iterable[ShiftHistory],
    timezone: str = "Europe/Moscow",
    actor_names: Optional[Dict[int, str]] = None,
    reason_titles: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Подготовить историю смен к отображению в шаблоне."""
    sorted_entries = sorted(
        entries,
        key=lambda entry: entry.created_at or datetime.min,
        reverse=True,
    )

    timeline: List[Dict[str, Any]] = []
    seen_ids: set[int] = set()
    actor_names = actor_names or {}
    reason_titles = reason_titles or {}

    for entry in sorted_entries:
        if entry.id in seen_ids:
            continue
        seen_ids.add(entry.id)

        meta = HISTORY_META.get(entry.operation, HISTORY_META["default"])
        payload = entry.payload or {}

        payload_items: List[Dict[str, str]] = []
        used_keys: set[str] = set()
        for key in PAYLOAD_ORDER:
            if key in payload and payload[key] not in (None, "", []):
                value = payload[key]
                if key == "reason_code":
                    value = reason_titles.get(value, DEFAULT_REASON_TITLES.get(value, value))

                payload_items.append(
                    {
                        "label": PAYLOAD_LABELS.get(key, key),
                        "value": _format_payload_value(key, value, timezone),
                    }
                )
                used_keys.add(key)

        # Добавляем прочие поля payload (если есть)
        for key, value in payload.items():
            if key in used_keys or value in (None, "", []) or key in HIDDEN_KEYS:
                continue
            payload_items.append(
                {
                    "label": PAYLOAD_LABELS.get(key, key),
                    "value": _format_payload_value(key, value, timezone),
                }
            )

        status_change = None
        if entry.old_status or entry.new_status:
            old_status = entry.old_status or "—"
            new_status = entry.new_status or "—"
            status_change = f"{old_status} → {new_status}"

        actor_label = None
        if entry.actor_role:
            role_label = ROLE_LABELS.get(entry.actor_role, entry.actor_role)
            if entry.actor_id:
                actor_name = actor_names.get(entry.actor_id)
                actor_label = f"{role_label} · {actor_name}" if actor_name else f"{role_label} · ID {entry.actor_id}"
            else:
                actor_label = role_label
        elif entry.actor_id:
            actor_name = actor_names.get(entry.actor_id)
            actor_label = actor_name or f"ID {entry.actor_id}"

        source_label = SOURCE_LABELS.get(entry.source or "", entry.source or "—")

        timeline.append(
            {
                "id": entry.id,
                "title": meta["title"],
                "icon": meta["icon"],
                "badge_class": meta["badge"],
                "created_at": _format_datetime(entry.created_at, timezone),
                "status_change": status_change,
                "source_label": source_label,
                "actor_label": actor_label,
                "payload_items": payload_items,
            }
        )

    return timeline

