"""Unified handlers для status, view_schedule, schedule_shift, get_report, my_tasks (MAX)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from core.database.session import get_async_session
from core.logging.logger import logger
from core.utils.timezone_helper import timezone_helper
from domain.entities.object import Object
from domain.entities.shift import Shift
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.user import User
from sqlalchemy import select, and_

from .messenger import Messenger
from .normalized_update import NormalizedUpdate
from .router import START_KEYBOARD
from .user_resolver import user_state_storage_key


def _max_media_flow_external_id(update: NormalizedUpdate) -> str:
    """Ключ Redis media_flow:max:* — одинаковый при старте потока, фото и «Готово»."""
    return (update.external_user_id or str(update.chat_id or "")).strip()


async def handle_status(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Статус смен."""
    from apps.bot.services.shift_service import ShiftService

    chat_id = update.chat_id
    shift_service = ShiftService()
    shifts = await shift_service.get_user_shifts(
        user_id=telegram_id or 0,
        status="active",
        internal_user_id=internal_user_id,
    )
    if not shifts:
        text = "📈 <b>Статус смен</b>\n\n✅ <b>Активных смен нет</b>\n\nОткройте смену через главное меню."
    else:
        shift = shifts[0]
        async with get_async_session() as session:
            obj_res = await session.execute(select(Object).where(Object.id == shift["object_id"]))
            obj = obj_res.scalar_one_or_none()
        obj_name = obj.name if obj else "Неизвестный"
        tz = getattr(obj, "timezone", None) or "Europe/Moscow"
        try:
            start_utc = datetime.strptime(shift["start_time"], "%Y-%m-%d %H:%M:%S")
            local_start = timezone_helper.format_local_time(start_utc, tz)
        except Exception:
            local_start = shift.get("start_time", "")
        rate = getattr(obj, "hourly_rate", 0) or 0
        text = (
            f"📈 <b>Статус смен</b>\n\n"
            f"🟢 <b>Активная смена:</b>\n"
            f"🏢 Объект: {obj_name}\n"
            f"🕐 Начало: {local_start}\n"
            f"💰 Ставка: {rate}₽/час\n\n"
            f"Для завершения — кнопка «Закрыть смену»."
        )
    keyboard = [
        [{"text": "🔄 Открыть смену", "callback_data": "open_shift"}, {"text": "🔚 Закрыть смену", "callback_data": "close_shift"}],
        [{"text": "🏠 Главное меню", "callback_data": "main_menu"}],
    ]
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    return True


async def handle_view_schedule(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Мои планы — запланированные смены."""
    chat_id = update.chat_id
    async with get_async_session() as session:
        user_res = await session.execute(select(User).where(User.id == internal_user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            await messenger.send_text(chat_id, "❌ Пользователь не найден.", keyboard=START_KEYBOARD)
            return True

        now_utc = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        q = select(ShiftSchedule).where(
            and_(
                ShiftSchedule.user_id == user.id,
                ShiftSchedule.status.in_(["planned", "confirmed"]),
                ShiftSchedule.planned_start >= today_start,
            )
        ).order_by(ShiftSchedule.planned_start)
        res = await session.execute(q)
        shifts = res.scalars().all()

    if not shifts:
        text = "📅 <b>Ваши запланированные смены</b>\n\nУ вас нет запланированных смен."
        await messenger.send_text(chat_id, text, keyboard=START_KEYBOARD)
        return True

    lines = ["📅 <b>Ваши запланированные смены:</b>\n"]
    keyboard = []
    async with get_async_session() as sess:
        for s in shifts[:10]:
            o = await sess.execute(select(Object).where(Object.id == s.object_id))
            obj = o.scalar_one_or_none()
            obj_name = obj.name if obj else "Объект"
            tz = getattr(obj, "timezone", None) or "Europe/Moscow"
            start_str = timezone_helper.format_local_time(s.planned_start, tz, "%d.%m %H:%M")
            end_str = timezone_helper.format_local_time(s.planned_end, tz, "%H:%M")
            rate = f" • {s.hourly_rate}₽/ч" if s.hourly_rate else ""
            lines.append(f"🏢 {obj_name}\n📅 {start_str}–{end_str}{rate}\n")
            if update.messenger == "max":
                keyboard.append([{"text": f"❌ Отменить {start_str}", "callback_data": f"cancel_shift:{s.id}"}])
    text = "\n".join(lines)
    if len(shifts) > 10:
        text += f"\n... и ещё {len(shifts) - 10}"
    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "main_menu"}])
    await messenger.send_text(chat_id, text, keyboard=keyboard or START_KEYBOARD)
    return True


async def handle_schedule_shift(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Запланировать смену — выбор объекта, затем ссылка на ЛК."""
    from apps.bot.services.employee_objects_service import EmployeeObjectsService
    from core.utils.url_helper import URLHelper

    chat_id = update.chat_id
    emp = EmployeeObjectsService()
    objects = await emp.get_employee_objects(internal_user_id=internal_user_id)
    if not objects:
        await messenger.send_text(
            chat_id,
            "❌ Нет доступных объектов. Нужен активный договор.",
            keyboard=START_KEYBOARD,
        )
        return True

    web_url = await URLHelper.get_web_url()
    text = (
        "📅 <b>Планирование смены</b>\n\n"
        "Полное планирование доступно в личном кабинете.\n\n"
        f"🌐 <a href=\"{web_url}/employee\">Открыть ЛК (расписание)</a>"
    )
    keyboard = [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    return True


async def handle_get_report(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Отчет по заработку — ссылка на ЛК."""
    from core.utils.url_helper import URLHelper

    chat_id = update.chat_id
    web_url = await URLHelper.get_web_url()
    text = (
        "📊 <b>Отчет по заработку</b>\n\n"
        "Детальные отчёты доступны в личном кабинете.\n\n"
        f"🌐 <a href=\"{web_url}/employee/earnings\">Открыть отчёты в ЛК</a>"
    )
    keyboard = [[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]]
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    return True


async def handle_my_tasks(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Мои задачи — список задач активной смены."""
    from sqlalchemy.orm import selectinload

    chat_id = update.chat_id
    async with get_async_session() as session:
        shifts_q = select(Shift).options(
            selectinload(Shift.time_slot),
            selectinload(Shift.object),
        ).where(
            and_(Shift.user_id == internal_user_id, Shift.status == "active")
        )
        shifts_res = await session.execute(shifts_q)
        active = shifts_res.scalars().all()

        if not active:
            text = "📋 <b>Мои задачи</b>\n\n❌ Нет активной смены.\n\nОткройте смену, чтобы увидеть задачи."
            await messenger.send_text(chat_id, text, keyboard=START_KEYBOARD)
            return True

        shift = active[0]
        from apps.bot.handlers_div.shift_handlers import _collect_shift_tasks

        tasks = await _collect_shift_tasks(
            session, shift,
            timeslot=shift.time_slot,
            object_=shift.object,
        )

    if not tasks:
        text = "📋 <b>Мои задачи</b>\n\n✅ Задач нет."
        keyboard = []
    else:
        from core.state import user_state_manager, UserAction, UserStep

        sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
        existing = await user_state_manager.get_state(sk)
        completed = (
            existing.completed_tasks
            if existing and existing.action == UserAction.MY_TASKS and existing.selected_shift_id == shift.id
            else []
        )
        await user_state_manager.create_state(
            sk,
            action=UserAction.MY_TASKS,
            step=UserStep.OBJECT_SELECTION,
            selected_shift_id=shift.id,
            shift_tasks=tasks,
            completed_tasks=completed,
        )
        lines = ["📋 <b>Мои задачи</b>\n\nОтметьте выполненные задачи:\n"]
        keyboard = []
        for idx, t in enumerate(tasks):
            txt = t.get("text") or t.get("task_text", "Задача")
            is_done = t.get("is_completed") if t.get("source") == "task_v2" else (idx in completed)
            done = "✓" if is_done else "☐"
            lines.append(f"{done} {idx + 1}. {txt[:50]}{'...' if len(txt) > 50 else ''}")
            icon = "⚠️" if t.get("is_mandatory", True) else "⭐"
            media_icon = "📸 " if t.get("requires_media") else ""
            btn_text = f"{done}{media_icon}{icon} {txt[:28]}..."
            if t.get("source") == "task_v2" and t.get("entry_id"):
                keyboard.append([{"text": btn_text, "callback_data": f"complete_task_v2:{t['entry_id']}"}])
            else:
                keyboard.append([{"text": btn_text, "callback_data": f"complete_my_task:{shift.id}:{idx}"}])
        text = "\n".join(lines)
    keyboard.append([{"text": "🏠 Главное меню", "callback_data": "main_menu"}])
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    return True


async def handle_complete_task_v2(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    entry_id: int,
) -> bool:
    """Отметка/снятие задачи Tasks v2. Без медиа — переключает is_completed."""
    from domain.entities.task_entry import TaskEntryV2
    from sqlalchemy.orm import selectinload

    chat_id = update.chat_id
    if update.callback_id and update.messenger != "max":
        await messenger.answer_callback(update.callback_id, "✅")

    async with get_async_session() as session:
        entry_q = select(TaskEntryV2).where(TaskEntryV2.id == entry_id).options(
            selectinload(TaskEntryV2.template),
            selectinload(TaskEntryV2.shift_schedule),
        )
        entry_res = await session.execute(entry_q)
        entry = entry_res.scalar_one_or_none()
        if not entry or entry.employee_id != internal_user_id:
            await messenger.send_text(chat_id, "❌ Задача не найдена или не ваша.", keyboard=START_KEYBOARD)
            return True

        template = entry.template
        if entry.is_completed:
            entry.is_completed = False
            entry.completed_at = None
            entry.completion_notes = None
            entry.completion_media = None
            await session.commit()
        else:
            if template and template.requires_media:
                from core.state import user_state_manager, UserAction, UserStep
                from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig

                ext_id = _max_media_flow_external_id(update)
                orchestrator = MediaOrchestrator()
                await orchestrator.begin_flow(
                    MediaFlowConfig(
                        user_id=0,
                        context_type="task_v2_proof",
                        context_id=entry_id,
                        messenger="max",
                        external_id=ext_id,
                        require_text=False,
                        require_photo=True,
                        max_photos=5,
                        allow_skip=False,
                    )
                )
                await orchestrator.close()

                sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
                await user_state_manager.create_state(
                    sk,
                    action=UserAction.MY_TASKS,
                    step=UserStep.TASK_V2_MEDIA_UPLOAD,
                    data={"pending_task_v2_entry_id": entry_id},
                )

                template_title = template.title or "Задача"
                keyboard = [
                    [{"text": "✅ Готово", "callback_data": f"task_v2_done:{entry_id}"}],
                    [{"text": "❌ Отмена", "callback_data": "cancel_task_v2_media"}],
                ]
                await messenger.send_text(
                    chat_id,
                    f"📸 <b>Фотоотчёт</b>\n\n"
                    f"Задача: <b>{template_title}</b>\n"
                    f"{template.description or ''}\n\n"
                    f"📤 Отправьте фото для отчёта.",
                    keyboard=keyboard,
                )
                return True
            from datetime import datetime
            entry.is_completed = True
            entry.completed_at = datetime.utcnow()
            await session.commit()

    await handle_my_tasks(update, messenger, internal_user_id, telegram_id)
    return True


async def handle_complete_my_task(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    shift_id: int,
    task_idx: int,
) -> bool:
    """Отметка legacy-задачи (без медиа)."""
    from core.state import user_state_manager, UserAction

    chat_id = update.chat_id
    if update.callback_id and update.messenger != "max":
        await messenger.answer_callback(update.callback_id, "✅")

    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    state = await user_state_manager.get_state(sk)
    if not state or state.action != UserAction.MY_TASKS or state.selected_shift_id != shift_id:
        await messenger.send_text(chat_id, "❌ Состояние утеряно. Нажмите «Мои задачи» заново.", keyboard=START_KEYBOARD)
        return True

    tasks = getattr(state, "shift_tasks", [])
    completed = list(getattr(state, "completed_tasks", []))
    if task_idx >= len(tasks):
        await messenger.send_text(chat_id, "❌ Задача не найдена.", keyboard=START_KEYBOARD)
        return True

    t = tasks[task_idx]
    if t.get("requires_media"):
        await messenger.send_text(
            chat_id,
            "📸 Задачи с фото пока не поддерживаются в MAX. Отметьте в ЛК.",
            keyboard=START_KEYBOARD,
        )
        return True

    if task_idx in completed:
        completed.remove(task_idx)
    else:
        completed.append(task_idx)
    await user_state_manager.update_state(sk, completed_tasks=completed)

    await handle_my_tasks(update, messenger, internal_user_id, telegram_id)
    return True


async def handle_task_v2_photo_message(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    photo_ref: str,
) -> bool:
    """Обработка фото для задачи v2 (MAX). photo_ref: max:url:... или max:token:..."""
    from core.state import user_state_manager, UserAction, UserStep
    from shared.services.media_orchestrator import MediaOrchestrator

    chat_id = update.chat_id
    ext_id = _max_media_flow_external_id(update)
    if not ext_id:
        return False

    state = await user_state_manager.get_state(internal_user_id)
    if not state or state.action != UserAction.MY_TASKS or state.step != UserStep.TASK_V2_MEDIA_UPLOAD:
        return False

    entry_id = (state.data or {}).get("pending_task_v2_entry_id")
    if not entry_id:
        return False

    orchestrator = MediaOrchestrator()
    flow = await orchestrator.get_flow(messenger="max", external_id=ext_id)
    if (
        not flow
        or flow.context_type != "task_v2_proof"
        or flow.context_id != entry_id
    ):
        await orchestrator.close()
        return False

    ok = await orchestrator.add_photo(
        file_id=photo_ref,
        messenger="max",
        external_id=ext_id,
    )
    if not ok:
        await orchestrator.close()
        await messenger.send_text(chat_id, "❌ Достигнут лимит файлов.")
        return True

    count = await orchestrator.get_collected_count(messenger="max", external_id=ext_id)
    can_add = await orchestrator.can_add_more(messenger="max", external_id=ext_id)
    await orchestrator.close()

    async with get_async_session() as session:
        from domain.entities.task_entry import TaskEntryV2
        from sqlalchemy.orm import selectinload
        entry_res = await session.execute(
            select(TaskEntryV2).where(TaskEntryV2.id == entry_id).options(
                selectinload(TaskEntryV2.template),
            )
        )
        entry = entry_res.scalar_one_or_none()
        template_title = entry.template.title if entry and entry.template else "Задача"

    keyboard = [[{"text": "✅ Готово", "callback_data": f"task_v2_done:{entry_id}"}]]
    if can_add:
        keyboard[0].append({"text": "❌ Отмена", "callback_data": "cancel_task_v2_media"})
    await messenger.send_text(
        chat_id,
        f"✅ Файл добавлен!\n\n📋 Задача: {template_title}\n📸 Загружено: {count}/5\n\n"
        "Отправьте ещё или нажмите «Готово».",
        keyboard=keyboard,
    )
    return True


async def handle_task_v2_done(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
    entry_id: int,
) -> bool:
    """Обработка кнопки «Готово» для задачи v2 с фото (MAX)."""
    from core.state import user_state_manager
    from shared.services.media_orchestrator import MediaOrchestrator
    from shared.services.owner_media_storage_service import get_storage_mode
    from shared.services.max_report_sender import send_media_to_max_group
    from shared.services.report_group_broadcast import resolve_object_report_group_channels
    from shared.services.telegram_report_sender import send_media_to_telegram_group
    from domain.entities.task_entry import TaskEntryV2

    chat_id = update.chat_id
    ext_id = _max_media_flow_external_id(update)
    if not ext_id:
        await messenger.send_text(chat_id, "❌ Не удалось определить пользователя.", keyboard=START_KEYBOARD)
        return True
    if update.callback_id and update.messenger != "max":
        await messenger.answer_callback(update.callback_id, "✅")

    orchestrator = MediaOrchestrator()
    media_flow = await orchestrator.get_flow(messenger="max", external_id=ext_id)
    flow_ctx_ok = (
        media_flow
        and media_flow.context_type == "task_v2_proof"
        and int(media_flow.context_id) == int(entry_id)
    )
    if not flow_ctx_ok:
        await orchestrator.close()
        await messenger.send_text(chat_id, "❌ Медиа-поток не найден.", keyboard=START_KEYBOARD)
        return True

    async with get_async_session() as session:
        from sqlalchemy.orm import selectinload
        entry_res = await session.execute(
            select(TaskEntryV2).where(TaskEntryV2.id == entry_id).options(
                selectinload(TaskEntryV2.template),
                selectinload(TaskEntryV2.shift),
            )
        )
        entry = entry_res.scalar_one_or_none()
        if not entry or not entry.template:
            await orchestrator.close()
            await messenger.send_text(chat_id, "❌ Задача не найдена.", keyboard=START_KEYBOARD)
            return True

        template = entry.template
        shift = entry.shift
        if not shift or not shift.object_id:
            await orchestrator.close()
            await messenger.send_text(chat_id, "❌ Объект не найден.", keyboard=START_KEYBOARD)
            return True

        obj_res = await session.execute(
            select(Object).where(Object.id == shift.object_id).options(
                selectinload(Object.org_unit),
            )
        )
        obj = obj_res.scalar_one_or_none()
        if not obj:
            await orchestrator.close()
            await messenger.send_text(chat_id, "❌ Объект не найден.", keyboard=START_KEYBOARD)
            return True

        channels = await resolve_object_report_group_channels(session, obj)
        storage_mode = await get_storage_mode(session, obj.owner_id, "tasks")

        if not channels.any_ready:
            await orchestrator.close()
            await messenger.send_text(
                chat_id,
                "❌ Нет канала для отчёта: в объекте задайте чат Telegram и/или MAX "
                "и включите соответствующий переключатель в ЛК → "
                "<b>Настройки уведомлений</b> → «Группы отчётов объектов».",
                keyboard=START_KEYBOARD,
            )
            return True

        u_res = await session.execute(select(User).where(User.id == internal_user_id))
        report_user = u_res.scalar_one_or_none()
        fn = (getattr(report_user, "first_name", None) or "").strip() if report_user else ""
        ln = (getattr(report_user, "last_name", None) or "").strip() if report_user else ""
        un = (getattr(report_user, "username", None) or "").strip() if report_user else ""
        if fn or ln:
            report_user_name = f"{fn} {ln}".strip()
        elif un:
            report_user_name = f"@{un}"
        else:
            report_user_name = (
                f"{(update.first_name or '').strip()} {(update.last_name or '').strip()}".strip()
                or "Сотрудник"
            )

        object_name = obj.name or "Объект"

    final_flow = await orchestrator.finish(
        messenger="max",
        external_id=ext_id,
        storage_mode=storage_mode,
        telegram_staging_chat_id=channels.staging_telegram_chat_id,
    )
    await orchestrator.close()

    if not final_flow or not final_flow.collected_photos:
        await messenger.send_text(chat_id, "❌ Нет загруженных файлов.", keyboard=START_KEYBOARD)
        return True

    caption = (
        f"📋 Отчет (Tasks v2): {template.title}\n👤 {report_user_name}\n🏢 {object_name}"
    )

    media_items = []
    if final_flow.uploaded_media:
        for m in final_flow.uploaded_media:
            u = m.url or ""
            if u.startswith("telegram:"):
                media_items.append(
                    {"file_id": m.key, "type": getattr(m, "type", "photo")}
                )
            else:
                media_items.append({"url": u, "type": getattr(m, "type", "photo")})
    else:
        for fid in final_flow.collected_photos:
            url = fid.replace("max:url:", "") if fid.startswith("max:url:") else None
            if url:
                media_items.append({"url": url, "type": "photo"})

    if not media_items:
        await messenger.send_text(chat_id, "❌ Не удалось подготовить медиа.", keyboard=START_KEYBOARD)
        return True

    if final_flow.uploaded_media:
        completion_media = [
            {
                "url": m.url,
                "type": getattr(m, "type", "photo") or "photo",
                "key": m.key,
            }
            for m in final_flow.uploaded_media
        ]
    else:
        completion_media = [
            {"url": m.get("url", ""), "type": m.get("type", "photo")}
            for m in media_items
        ]

    tg_configured = channels.tg_ready
    max_configured = channels.max_ready

    urls: list[str] = []
    if tg_configured:
        try:
            urls = await asyncio.wait_for(
                send_media_to_telegram_group(
                    str(channels.telegram_chat_id), media_items, caption, bot=None
                ),
                timeout=25.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "send_media_to_telegram_group: timeout",
                chat_id=channels.telegram_chat_id,
                entry_id=entry_id,
            )

    telegram_ok = bool(urls) if tg_configured else True

    max_ok = True
    max_links: list[Optional[str]] = []
    if max_configured:
        um_for_max = final_flow.uploaded_media
        if um_for_max and len(um_for_max) != len(media_items):
            um_for_max = None
        max_ok, max_links = await send_media_to_max_group(
            str(channels.max_report_chat_id),
            media_items,
            caption,
            uploaded_media=um_for_max,
        )

    for i, item in enumerate(completion_media):
        deliv: dict[str, Any] = {}
        if tg_configured and telegram_ok and i < len(urls) and urls[i]:
            deliv["telegram"] = urls[i]
        if max_configured and max_ok and i < len(max_links) and max_links[i]:
            deliv["max"] = max_links[i]
        if deliv:
            item["delivery"] = deliv

    async with get_async_session() as session:
        from shared.services.task_service import TaskService

        await TaskService(session).mark_entry_completed(
            entry_id,
            completion_media=completion_media,
        )

    sk_done = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.clear_state(sk_done)

    if telegram_ok and max_ok:
        channels = []
        if tg_configured:
            channels.append("Telegram")
        if max_configured:
            channels.append("MAX")
        ch = " и ".join(channels) if channels else "—"
        done_text = (
            f"✅ Отчёт принят!\n\n📋 Задача: {template.title}\n"
            f"✅ Выполнена, {len(completion_media)} файл(ов) → {ch}\n\n"
            "💡 «Мои задачи» — продолжить."
        )
    else:
        problems = []
        if tg_configured and not telegram_ok:
            problems.append("Telegram (сеть / api.telegram.org / бот в группе)")
        if max_configured and not max_ok:
            problems.append("MAX (chat_id группы / бот в группе / URL фото)")
        prob = "; ".join(problems) if problems else "каналы доставки"
        done_text = (
            f"✅ Задача выполнена, {len(completion_media)} файл(ов) сохранены.\n\n"
            f"📋 {template.title}\n\n"
            f"⚠️ Не доставлено: {prob}."
        )
    await messenger.send_text(
        chat_id,
        done_text,
        keyboard=[
            [{"text": "📋 Мои задачи", "callback_data": "my_tasks"}, {"text": "🏠 Главное меню", "callback_data": "main_menu"}],
        ],
    )
    return True


async def handle_cancel_task_v2_media(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    telegram_id: Optional[int],
) -> bool:
    """Отмена загрузки фото для задачи v2 (MAX)."""
    from core.state import user_state_manager
    from shared.services.media_orchestrator import MediaOrchestrator

    chat_id = update.chat_id
    ext_id = _max_media_flow_external_id(update)
    if update.callback_id and update.messenger != "max":
        await messenger.answer_callback(update.callback_id, "❌")

    orchestrator = MediaOrchestrator()
    if ext_id:
        await orchestrator.cancel(messenger="max", external_id=ext_id)
    await orchestrator.close()

    sk = user_state_storage_key(update.messenger, internal_user_id, telegram_id)
    await user_state_manager.clear_state(sk)

    await messenger.send_text(
        chat_id,
        "❌ Загрузка отменена.",
        keyboard=START_KEYBOARD,
    )
    return True
