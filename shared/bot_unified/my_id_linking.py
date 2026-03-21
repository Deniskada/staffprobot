"""Кнопка «Мой ID» и привязка второго мессенджера (TG ↔ MAX)."""

from __future__ import annotations

from sqlalchemy import and_, select

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.messenger_account import MessengerAccount
from domain.entities.user import User
from shared.services.messenger_link_service import generate_max_link_code


async def _has_messenger_account(user_id: int, provider: str) -> bool:
    async with get_async_session() as session:
        q = select(MessengerAccount.id).where(
            MessengerAccount.user_id == user_id,
            MessengerAccount.provider == provider,
        )
        r = await session.execute(q)
        return r.scalar_one_or_none() is not None


async def _resolve_internal_and_display_id(
    messenger_name: str,
    external_user_id: str | None,
) -> tuple[int | None, str]:
    """internal_user_id и строка ID для показа пользователю."""
    from .user_resolver import resolve_to_internal_user_id

    if not external_user_id or not str(external_user_id).strip():
        return None, ""
    ext = str(external_user_id).strip()
    async with get_async_session() as session:
        internal = await resolve_to_internal_user_id(
            "max" if messenger_name == "max" else "telegram",
            ext,
            session,
        )
    return internal, ext


async def send_my_id_screen(update, messenger) -> None:
    """
    Текст «Мой ID» + опционально кнопка привязки второго мессенджера.
    update: NormalizedUpdate, messenger: Messenger.
    """
    chat_id = update.chat_id
    prov = update.messenger
    ext_raw = update.external_user_id or (str(chat_id) if chat_id else "")
    internal_id, display_id = await _resolve_internal_and_display_id(prov, ext_raw)

    if prov == "max":
        title = "🆔 <b>Ваш MAX ID</b>"
        id_label = "MAX user_id"
    else:
        title = "🆔 <b>Ваш Telegram ID</b>"
        id_label = "Telegram ID"

    lines = [
        title,
        "",
        f"<b>{id_label}:</b> <code>{display_id}</code>",
    ]
    if update.first_name:
        lines.append(f"\n<b>Имя:</b> {update.first_name or '—'}")
    if update.last_name:
        lines.append(f"<b>Фамилия:</b> {update.last_name}")
    if update.from_username:
        lines.append(f"<b>Username:</b> @{update.from_username}")

    keyboard: list[list[dict]] = []
    if internal_id:
        has_max = await _has_messenger_account(internal_id, "max")
        has_tg_ma = await _has_messenger_account(internal_id, "telegram")
        if prov == "telegram" and not has_max:
            keyboard.append([{"text": "Привязать MAX", "callback_data": "link_bind_max"}])
        elif prov == "max" and not has_tg_ma:
            keyboard.append([{"text": "Привязать ТГ", "callback_data": "link_bind_tg"}])

    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "main_menu"}])

    await messenger.send_text(
        chat_id,
        "\n".join(lines),
        keyboard=keyboard,
        parse_mode="HTML",
    )


async def send_link_second_messenger_instructions(
    update,
    messenger,
    target: str,  # "max" | "telegram"
) -> None:
    """Генерация кода и инструкция для привязки другого мессенджера."""
    chat_id = update.chat_id
    prov = update.messenger
    ext_raw = update.external_user_id or str(chat_id)
    internal_id, _ = await _resolve_internal_and_display_id(prov, ext_raw)

    if not internal_id:
        await messenger.send_text(
            chat_id,
            "❌ Не удалось определить аккаунт. Войдите через сайт или напишите /start.",
            keyboard=[[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]],
        )
        return

    if target == "max":
        if await _has_messenger_account(internal_id, "max"):
            await messenger.send_text(chat_id, "✅ MAX уже привязан.", keyboard=None)
            return
    else:
        if await _has_messenger_account(internal_id, "telegram"):
            await messenger.send_text(chat_id, "✅ Telegram уже привязан.", keyboard=None)
            return

    code, ttl = await generate_max_link_code(internal_id)
    if not code:
        await messenger.send_text(
            chat_id,
            "❌ Не удалось выдать код. Попробуйте позже или используйте ЛК → Мессенджеры.",
            keyboard=None,
        )
        return

    if target == "max":
        body = (
            f"🔑 <b>Код для MAX:</b> <code>{code}</code>\n\n"
            f"Действует ~{ttl // 60} мин.\n\n"
            "1) Откройте мессенджер <b>MAX</b>.\n"
            "2) В поиске найдите бота <b>StaffProBot</b> (как в вашей организации).\n"
            "3) Откройте чат с ботом и отправьте сообщение:\n"
            f"<code>/start {code}</code>\n\n"
            "После этого MAX будет привязан к этому же аккаунту."
        )
    else:
        body = (
            f"🔑 <b>Код для Telegram:</b> <code>{code}</code>\n\n"
            f"Действует ~{ttl // 60} мин.\n\n"
            "1) Откройте <b>Telegram</b>.\n"
            "2) Найдите бота <b>@StaffProBot</b> (или тот, что выдаёт ваш работодатель).\n"
            "3) Нажмите Start или отправьте:\n"
            f"<code>/start {code}</code>\n\n"
            "После этого Telegram будет привязан к этому же аккаунту."
        )

    await messenger.send_text(
        chat_id,
        body,
        keyboard=[[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]],
        parse_mode="HTML",
    )


async def apply_telegram_start_link_code(
    telegram_user_id: int,
    telegram_chat_id: str,
    code: str,
    first_name: str | None,
    from_username: str | None,
    last_name: str | None,
) -> tuple[bool, str]:
    """
    Привязка Telegram к user_id по одноразовому коду (симметрично MAX /start CODE).
    Возвращает (ok, message_for_user).
    """
    from shared.services.messenger_link_service import consume_max_link_code

    target_uid = await consume_max_link_code(code)
    if not target_uid:
        return False, "❌ Код недействителен или истёк. Запросите новый в боте (Мой ID → Привязать ТГ) или в ЛК → Мессенджеры."

    try:
        async with get_async_session() as session:
            tid = int(telegram_user_id)
            clash = await session.execute(
                select(User.id).where(User.telegram_id == tid, User.id != target_uid)
            )
            if clash.scalar_one_or_none() is not None:
                return False, "❌ Этот Telegram уже привязан к другому аккаунту."

            target = await session.get(User, target_uid)
            if not target:
                return False, "❌ Внутренняя ошибка: аккаунт не найден."

            target.telegram_id = tid

            q_ma = select(MessengerAccount).where(
                and_(
                    MessengerAccount.user_id == target_uid,
                    MessengerAccount.provider == "telegram",
                )
            )
            ex = await session.execute(q_ma)
            row = ex.scalar_one_or_none()
            if row:
                row.external_user_id = str(tid)
                row.chat_id = str(telegram_chat_id)
                row.username = from_username
            else:
                session.add(
                    MessengerAccount(
                        user_id=target_uid,
                        provider="telegram",
                        external_user_id=str(tid),
                        chat_id=str(telegram_chat_id),
                        username=from_username,
                    )
                )
            await session.commit()
    except Exception as e:
        logger.error(f"apply_telegram_start_link_code: {e}", exc_info=True)
        return False, "❌ Ошибка при привязке. Попробуйте позже."

    return True, "✅ Telegram успешно привязан к вашему аккаунту."
