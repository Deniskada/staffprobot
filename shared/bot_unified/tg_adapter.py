"""Telegram → NormalizedUpdate + TgMessenger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .normalized_update import NormalizedUpdate
from .messenger import Messenger, MessengerFeatures

if TYPE_CHECKING:
    from telegram import Update
    from telegram.ext import ContextTypes


class TgAdapter:
    """Парсинг telegram.Update → NormalizedUpdate."""

    @staticmethod
    def parse(update: "Update") -> Optional[NormalizedUpdate]:
        """Update → NormalizedUpdate. None если тип не поддерживается."""
        if update.message:
            msg = update.message
            user = msg.from_user
            loc = None
            if msg.location:
                loc = {"lat": msg.location.latitude, "lon": msg.location.longitude}
            photo_id = None
            if msg.photo:
                photo_id = msg.photo[-1].file_id
            return NormalizedUpdate(
                type="message",
                chat_id=str(msg.chat_id),
                text=(msg.text or msg.caption or "").strip(),
                external_user_id=str(user.id) if user else None,
                from_username=user.username if user else None,
                first_name=user.first_name if user else None,
                last_name=user.last_name if user else None,
                contact_phone=msg.contact.phone_number if msg.contact else None,
                photo_file_id=photo_id,
                location=loc,
            )
        if update.callback_query:
            cb = update.callback_query
            user = cb.from_user
            return NormalizedUpdate(
                type="callback",
                chat_id=str(cb.message.chat_id) if cb.message else "",
                text="",
                callback_data=cb.data,
                callback_id=cb.id,
                external_user_id=str(user.id) if user else None,
                from_username=user.username if user else None,
                first_name=user.first_name if user else None,
                last_name=user.last_name if user else None,
            )
        return None


class TgMessenger:
    """Messenger-реализация для Telegram."""

    name = "telegram"
    features = MessengerFeatures(supports_contact_request=True, supports_webapp=True)

    def __init__(self, update: "Update", context: "ContextTypes.DEFAULT_TYPE"):
        self._bot = context.bot
        self._update = update
        self._context = context

    async def send_text(
        self,
        chat_id: str,
        text: str,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
        parse_mode: Optional[str] = "HTML",
    ) -> None:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = None
        if keyboard:
            rows = []
            for row in keyboard:
                buttons = []
                for btn in row:
                    if "url" in btn:
                        buttons.append(InlineKeyboardButton(btn["text"], url=btn["url"]))
                    else:
                        buttons.append(
                            InlineKeyboardButton(
                                btn["text"],
                                callback_data=btn.get("callback_data", ""),
                            )
                        )
                rows.append(buttons)
            reply_markup = InlineKeyboardMarkup(rows)
        await self._bot.send_message(
            chat_id=int(chat_id),
            text=text,
            parse_mode=parse_mode or None,
            reply_markup=reply_markup,
        )

    async def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: Optional[str] = None,
        keyboard: Optional[list[list[dict[str, Any]]]] = None,
    ) -> None:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        reply_markup = None
        if keyboard:
            rows = []
            for row in keyboard:
                buttons = []
                for b in row:
                    if b.get("url"):
                        buttons.append(InlineKeyboardButton(b["text"], url=b["url"]))
                    else:
                        buttons.append(
                            InlineKeyboardButton(b["text"], callback_data=b.get("callback_data", ""))
                        )
                rows.append(buttons)
            reply_markup = InlineKeyboardMarkup(rows)
        await self._bot.send_photo(
            chat_id=int(chat_id),
            photo=photo,
            caption=caption,
            reply_markup=reply_markup,
        )

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        # callback_id в TG — это id из CallbackQuery
        await self._context.bot.answer_callback_query(callback_id=callback_id, text=text or None)
