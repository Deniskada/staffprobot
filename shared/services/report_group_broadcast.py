"""Текстовые сообщения в группы отчётов объекта: Telegram и MAX (targets + legacy)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config.settings import settings
from core.logging.logger import logger
from domain.entities.object import Object
from domain.entities.user import User
from shared.services.notification_target_service import (
    get_max_report_chat_id_for_object,
    get_telegram_report_chat_id_for_object,
)

# Ключ в users.notification_preferences: переключатели каналов для групповых рассылок по объектам владельца
REPORT_GROUP_MESSENGERS_KEY = "report_group_messengers"


@dataclass(frozen=True)
class ObjectReportGroupChannels:
    """Чаты отчётов объекта с учётом переключателей владельца (ЛК → группы отчётов)."""

    telegram_chat_id: Optional[str]
    max_report_chat_id: Optional[str]
    allow_telegram: bool
    allow_max: bool

    @property
    def tg_ready(self) -> bool:
        return bool(self.telegram_chat_id and self.allow_telegram)

    @property
    def max_ready(self) -> bool:
        return bool(self.max_report_chat_id and self.allow_max)

    @property
    def any_ready(self) -> bool:
        return self.tg_ready or self.max_ready

    @property
    def staging_telegram_chat_id(self) -> Optional[str]:
        """Чат для stage в TG при MAX-потоке (только если канал TG для отчётов включён)."""
        return self.telegram_chat_id if self.tg_ready else None


async def resolve_object_report_group_channels(
    session: AsyncSession,
    obj: Object,
) -> ObjectReportGroupChannels:
    """Единая точка: target + legacy + report_group_messengers."""
    tg_raw = await get_telegram_report_chat_id_for_object(session, obj)
    mx_raw = await get_max_report_chat_id_for_object(session, obj)
    allow_tg, allow_mx = await get_owner_report_group_messenger_flags(session, obj.owner_id)
    tg_s = str(tg_raw).strip() if tg_raw else ""
    mx_s = str(mx_raw).strip() if mx_raw else ""
    return ObjectReportGroupChannels(
        telegram_chat_id=tg_s or None,
        max_report_chat_id=mx_s or None,
        allow_telegram=allow_tg,
        allow_max=allow_mx,
    )


class _ChannelResult(TypedDict):
    ok: bool
    chat_id: Optional[str]


class ReportGroupSendResult(TypedDict):
    telegram: _ChannelResult
    max: _ChannelResult


def owner_wants_holiday_report_group_broadcast(prefs: dict) -> bool:
    """
    Отправлять ли праздничные поздравления в группы объектов для этого владельца.
    Если задан report_group_messengers — смотрим его; иначе legacy: employee_holiday_greeting.telegram.
    """
    rg = prefs.get(REPORT_GROUP_MESSENGERS_KEY)
    if isinstance(rg, dict):
        return bool(rg.get("telegram", True) or rg.get("max", True))
    hp = prefs.get("employee_holiday_greeting") or {}
    return hp.get("telegram", True) is not False


async def get_owner_report_group_messenger_flags(
    session: AsyncSession,
    owner_id: int,
) -> Tuple[bool, bool]:
    """
    Разрешения владельца на отправку в группы отчётов: (telegram, max).
    Если ключа нет — оба True (как до появления переключателей).
    """
    result = await session.execute(select(User).where(User.id == owner_id))
    user = result.scalar_one_or_none()
    prefs = (user.notification_preferences or {}) if user else {}
    ch = prefs.get(REPORT_GROUP_MESSENGERS_KEY)
    if not isinstance(ch, dict):
        return True, True
    return ch.get("telegram", True), ch.get("max", True)


async def send_object_report_group_text(
    session: AsyncSession,
    obj: Object,
    text: str,
    *,
    telegram_parse_mode: Optional[str] = "Markdown",
) -> ReportGroupSendResult:
    """
    Отправить текст в TG и/или MAX по настроенным чатам объекта.
    Дублирование по объектам обрабатывает вызывающий (разные chat_id).
    """
    ch = await resolve_object_report_group_channels(session, obj)
    tg_s = ch.telegram_chat_id or ""
    max_s = ch.max_report_chat_id or ""

    out: ReportGroupSendResult = {
        "telegram": {"ok": False, "chat_id": ch.telegram_chat_id},
        "max": {"ok": False, "chat_id": ch.max_report_chat_id},
    }

    if ch.allow_telegram and tg_s and settings.telegram_bot_token:
        try:
            from telegram import Bot

            bot = Bot(token=settings.telegram_bot_token)
            await bot.send_message(
                chat_id=tg_s,
                text=text,
                parse_mode=telegram_parse_mode,
            )
            out["telegram"]["ok"] = True
        except Exception as e:
            logger.warning(
                "report_group_broadcast: TG send failed",
                object_id=obj.id,
                error=str(e),
            )

    if ch.allow_max and max_s and settings.max_bot_token and settings.max_features_enabled:
        try:
            from shared.bot_unified.max_client import MaxClient

            await MaxClient().send_text(max_s, text)
            out["max"]["ok"] = True
        except Exception as e:
            logger.warning(
                "report_group_broadcast: MAX send failed",
                object_id=obj.id,
                error=str(e),
            )

    return out
