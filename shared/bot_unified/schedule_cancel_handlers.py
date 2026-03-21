"""Unified handlers отмены смен (MAX)."""

from __future__ import annotations

from typing import Optional

from core.database.session import get_async_session
from core.utils.timezone_helper import timezone_helper
from domain.entities.object import Object
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.user import User
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from .messenger import Messenger
from .normalized_update import NormalizedUpdate
from .router import START_KEYBOARD


async def handle_cancel_shift(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    shift_id: int,
) -> bool:
    """Показать причины отмены смены."""
    from shared.services.cancellation_policy_service import CancellationPolicyService

    chat_id = update.chat_id
    if update.callback_id:
        await messenger.answer_callback(update.callback_id, "✅")

    async with get_async_session() as session:
        shift_res = await session.execute(
            select(ShiftSchedule).where(
                ShiftSchedule.id == shift_id,
                ShiftSchedule.user_id == internal_user_id,
                ShiftSchedule.status == "planned",
            )
        )
        shift = shift_res.scalar_one_or_none()
        if not shift:
            await messenger.send_text(chat_id, "❌ Смена не найдена или уже отменена.", keyboard=START_KEYBOARD)
            return True

        obj_res = await session.execute(select(Object).where(Object.id == shift.object_id))
        obj = obj_res.scalar_one_or_none()
        owner_id = obj.owner_id if obj else None
        reasons = await CancellationPolicyService.get_owner_reasons(session, owner_id) if owner_id else []

    obj_name = obj.name if obj else "Объект"
    tz = getattr(obj, "timezone", None) or "Europe/Moscow"
    start_str = timezone_helper.format_local_time(shift.planned_start, tz, "%d.%m %H:%M")
    end_str = timezone_helper.format_local_time(shift.planned_end, tz, "%H:%M")

    keyboard = []
    for r in reasons:
        keyboard.append([{"text": r.title, "callback_data": f"cancel_reason:{shift_id}:{r.code}"}])
    keyboard.append([{"text": "🔙 Назад", "callback_data": "view_schedule"}])

    await messenger.send_text(
        chat_id,
        f"❌ <b>Отмена смены</b>\n\n"
        f"🏢 {obj_name}\n📅 {start_str}–{end_str}\n\n"
        f"Выберите причину отмены:",
        keyboard=keyboard,
    )
    return True


async def handle_cancel_reason(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    shift_id: int,
    reason: str,
) -> bool:
    """Обработка выбора причины. Ветвление: requires_document → INPUT_DOCUMENT, иначе execute."""
    from core.state import user_state_manager, UserAction, UserStep
    from shared.services.cancellation_policy_service import CancellationPolicyService
    from shared.services.notification_target_service import get_telegram_report_chat_id_for_object
    from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig

    chat_id = update.chat_id
    if update.callback_id:
        await messenger.answer_callback(update.callback_id, "✅")

    async with get_async_session() as session:
        shift_res = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
        shift = shift_res.scalar_one_or_none()
        if not shift:
            await messenger.send_text(chat_id, "❌ Смена не найдена.", keyboard=START_KEYBOARD)
            return True

        obj_res = await session.execute(
            select(Object).where(Object.id == shift.object_id).options(
                joinedload(Object.org_unit).joinedload("parent").joinedload("parent").joinedload("parent"),
            )
        )
        obj = obj_res.scalar_one_or_none()
        if not obj:
            await messenger.send_text(chat_id, "❌ Объект не найден.", keyboard=START_KEYBOARD)
            return True

        reason_map = await CancellationPolicyService.get_reason_map(session, obj.owner_id)
        policy = reason_map.get(reason)
        requires_document = bool(policy and policy.requires_document)
        report_chat_id = await get_telegram_report_chat_id_for_object(session, obj)

    if reason == "other":
        await user_state_manager.create_state(
            internal_user_id,
            action=UserAction.CANCEL_SCHEDULE,
            step=UserStep.INPUT_DOCUMENT,
            data={
                "cancelling_shift_id": shift_id,
                "cancel_reason": reason,
                "report_chat_id": report_chat_id,
            },
        )
        await messenger.send_text(
            chat_id,
            "✍️ <b>Объяснение причины отмены</b>\n\nОпишите причину. Ваше объяснение будет рассмотрено владельцем.",
        )
        return True

    if requires_document:
        title = policy.title if policy else "документа"
        await user_state_manager.create_state(
            internal_user_id,
            action=UserAction.CANCEL_SCHEDULE,
            step=UserStep.INPUT_DOCUMENT,
            data={
                "cancelling_shift_id": shift_id,
                "cancel_reason": reason,
                "report_chat_id": report_chat_id,
            },
        )
        await messenger.send_text(
            chat_id,
            f"📄 <b>Описание {title}</b>\n\n"
            f"Укажите номер и дату документа.\nНапример: №123 от 10.10.2025\n\n"
            f"Справка будет проверена владельцем.",
        )
        return True

    await _execute_cancellation_unified(
        messenger, update.chat_id, internal_user_id, shift_id, reason,
        reason_notes=None, document_description=None, media=None,
    )
    return True


async def handle_cancel_document_input(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    text: str,
) -> bool:
    """Обработка ввода документа/объяснения. Проверка report_chat_id → INPUT_PHOTO или execute."""
    from core.state import user_state_manager, UserAction, UserStep
    from shared.services.media_orchestrator import MediaOrchestrator, MediaFlowConfig

    chat_id = update.chat_id
    state = await user_state_manager.get_state(internal_user_id)
    if not state or state.action != UserAction.CANCEL_SCHEDULE or state.step != UserStep.INPUT_DOCUMENT:
        return False

    data = state.data or {}
    shift_id = data.get("cancelling_shift_id")
    reason = data.get("cancel_reason")
    report_chat_id = data.get("report_chat_id")

    if not shift_id or not reason:
        await messenger.send_text(chat_id, "❌ Данные отмены не найдены.", keyboard=START_KEYBOARD)
        return True

    if reason == "other":
        data["cancel_reason_notes"] = text
    else:
        data["cancel_document_description"] = text
    await user_state_manager.update_state(internal_user_id, data=data)

    if report_chat_id:
        ext_id = update.external_user_id or ""
        orchestrator = MediaOrchestrator()
        await orchestrator.begin_flow(
            MediaFlowConfig(
                user_id=0,
                context_type="cancellation_doc",
                context_id=shift_id,
                messenger="max",
                external_id=ext_id,
                require_text=False,
                require_photo=False,
                max_photos=5,
                allow_skip=True,
            )
        )
        await orchestrator.close()

        await user_state_manager.update_state(
            internal_user_id,
            step=UserStep.INPUT_PHOTO,
        )

        keyboard = [
            [{"text": "✅ Готово", "callback_data": "cancel_done_photo"}, {"text": "⏩ Пропустить", "callback_data": "cancel_skip_photo"}],
        ]
        await messenger.send_text(
            chat_id,
            "📸 <b>Фото подтверждения</b> (опционально)\n\n"
            "Отправьте фото документа или нажмите Готово / Пропустить.",
            keyboard=keyboard,
        )
    else:
        await _execute_cancellation_unified(
            messenger, update.chat_id, internal_user_id, shift_id, reason,
            reason_notes=data.get("cancel_reason_notes"),
            document_description=data.get("cancel_document_description"),
            media=None,
        )
        await user_state_manager.clear_state(internal_user_id)
    return True


async def handle_cancel_photo_message(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
    external_user_id: str,
    photo_ref: str,
) -> bool:
    """Добавить фото в поток отмены (MAX)."""
    from core.state import user_state_manager, UserAction, UserStep
    from shared.services.media_orchestrator import MediaOrchestrator

    chat_id = update.chat_id
    state = await user_state_manager.get_state(internal_user_id)
    if not state or state.action != UserAction.CANCEL_SCHEDULE or state.step != UserStep.INPUT_PHOTO:
        return False

    orchestrator = MediaOrchestrator()
    ok = await orchestrator.add_photo(
        file_id=photo_ref,
        messenger="max",
        external_id=external_user_id,
    )
    if not ok:
        await orchestrator.close()
        await messenger.send_text(chat_id, "❌ Достигнут лимит файлов.")
        return True

    count = await orchestrator.get_collected_count(messenger="max", external_id=external_user_id)
    can_add = await orchestrator.can_add_more(messenger="max", external_id=external_user_id)
    await orchestrator.close()

    keyboard = [
        [{"text": "✅ Готово", "callback_data": "cancel_done_photo"}, {"text": "⏩ Пропустить", "callback_data": "cancel_skip_photo"}],
    ]
    text = f"📸 Добавлено фото ({count}). Отправьте ещё или нажмите Готово / Пропустить."
    if not can_add:
        text = f"📸 Добавлено фото ({count}). Лимит достигнут. Нажмите Готово."
    await messenger.send_text(chat_id, text, keyboard=keyboard)
    return True


async def handle_cancel_done_photo(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
) -> bool:
    """Готово с фото: finish → отмена смены с медиа."""
    from core.state import user_state_manager
    from shared.services.media_orchestrator import MediaOrchestrator
    from shared.services.owner_media_storage_service import get_storage_mode
    from shared.services.notification_target_service import get_telegram_report_chat_id_for_object
    from shared.services.telegram_report_sender import send_media_to_telegram_group

    chat_id = update.chat_id
    ext_id = update.external_user_id or ""
    if update.callback_id:
        await messenger.answer_callback(update.callback_id, "✅")

    state = await user_state_manager.get_state(internal_user_id)
    if not state:
        await messenger.send_text(chat_id, "❌ Состояние утеряно.", keyboard=START_KEYBOARD)
        return True

    data = state.data or {}
    shift_id = data.get("cancelling_shift_id")
    reason = data.get("cancel_reason")
    report_chat_id = data.get("report_chat_id")

    if not shift_id or not reason:
        await messenger.send_text(chat_id, "❌ Данные отмены не найдены.", keyboard=START_KEYBOARD)
        return True

    orchestrator = MediaOrchestrator()
    flow = await orchestrator.get_flow(messenger="max", external_id=ext_id)
    if not flow or flow.context_type != "cancellation_doc" or flow.context_id != shift_id:
        flow = None

    async with get_async_session() as session:
        shift_res = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
        shift = shift_res.scalar_one_or_none()
        obj = None
        if shift:
            obj_res = await session.execute(select(Object).where(Object.id == shift.object_id))
            obj = obj_res.scalar_one_or_none()
        storage_mode = await get_storage_mode(session, obj.owner_id, "cancellations") if obj else "storage"
        if not report_chat_id and obj:
            report_chat_id = await get_telegram_report_chat_id_for_object(session, obj)

    final_flow = await orchestrator.finish(
        messenger="max",
        external_id=ext_id,
        storage_mode=storage_mode,
    )
    await orchestrator.close()
    await user_state_manager.clear_state(internal_user_id)

    media_list = None
    if final_flow and final_flow.uploaded_media:
        media_list = [{"url": m.url, "type": getattr(m, "type", "photo")} for m in final_flow.uploaded_media]
    elif final_flow and final_flow.collected_photos:
        media_list = []
        for fid in final_flow.collected_photos:
            url = fid.replace("max:url:", "") if fid.startswith("max:url:") else None
            if url:
                media_list.append({"url": url, "type": "photo"})

    if report_chat_id and media_list:
        async with get_async_session() as session:
            user_res = await session.execute(select(User).where(User.id == internal_user_id))
            user = user_res.scalar_one_or_none()
            shift_res = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
            shift = shift_res.scalar_one_or_none()
            obj = None
            if shift:
                obj_res = await session.execute(select(Object).where(Object.id == shift.object_id))
                obj = obj_res.scalar_one_or_none()
            user_name = user.full_name if user else "Сотрудник"
            obj_name = obj.name if obj else "Объект"
            tz = getattr(obj, "timezone", None) or "Europe/Moscow"
            from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local
            user_tz = get_user_timezone(user) if user else "Europe/Moscow"
            local_start = convert_utc_to_local(shift.planned_start, user_tz) if shift else None
            reason_labels = {"medical_cert": "🏥 Медсправка", "emergency_cert": "🚨 МЧС", "police_cert": "👮 Полиция", "other": "❓ Другое"}
            caption = (
                f"❌ Отмена смены\n\n"
                f"👤 {user_name}\n🏢 {obj_name}\n"
                f"📅 {local_start.strftime('%d.%m.%Y %H:%M') if local_start else '—'}\n"
                f"📋 {reason_labels.get(reason, reason)}\n"
            )
            if data.get("cancel_document_description"):
                caption += f"📄 {data['cancel_document_description']}\n"
            if data.get("cancel_reason_notes"):
                caption += f"✍️ {data['cancel_reason_notes']}\n"
            await send_media_to_telegram_group(str(report_chat_id), media_list, caption, bot=None)

    await _execute_cancellation_unified(
        messenger, internal_user_id, shift_id, reason,
        reason_notes=data.get("cancel_reason_notes"),
        document_description=data.get("cancel_document_description"),
        media=media_list,
    )
    return True


async def handle_cancel_skip_photo(
    update: NormalizedUpdate,
    messenger: Messenger,
    internal_user_id: int,
) -> bool:
    """Пропустить фото → отмена без медиа."""
    from core.state import user_state_manager
    from shared.services.media_orchestrator import MediaOrchestrator

    chat_id = update.chat_id
    if update.callback_id:
        await messenger.answer_callback(update.callback_id, "✅")

    state = await user_state_manager.get_state(internal_user_id)
    if not state:
        await messenger.send_text(chat_id, "❌ Состояние утеряно.", keyboard=START_KEYBOARD)
        return True

    data = state.data or {}
    shift_id = data.get("cancelling_shift_id")
    reason = data.get("cancel_reason")

    if not shift_id or not reason:
        await messenger.send_text(chat_id, "❌ Данные отмены не найдены.", keyboard=START_KEYBOARD)
        return True

    orchestrator = MediaOrchestrator()
    await orchestrator.cancel(messenger="max", external_id=update.external_user_id or "")
    await orchestrator.close()
    await user_state_manager.clear_state(internal_user_id)

    await _execute_cancellation_unified(
        messenger, internal_user_id, shift_id, reason,
        reason_notes=data.get("cancel_reason_notes"),
        document_description=data.get("cancel_document_description"),
        media=None,
    )
    return True


async def _execute_cancellation_unified(
    messenger: Messenger,
    internal_user_id: int,
    shift_id: int,
    reason: str,
    reason_notes: Optional[str],
    document_description: Optional[str],
    media: Optional[list],
) -> None:
    """Выполнить отмену смены и отправить результат через messenger."""
    from shared.services.shift_cancellation_service import ShiftCancellationService
    from core.utils.timezone_helper import get_user_timezone, convert_utc_to_local

    chat_id = messenger.chat_id if hasattr(messenger, "chat_id") else None
    if not chat_id and hasattr(messenger, "_chat_id"):
        chat_id = messenger._chat_id

    async with get_async_session() as session:
        user_res = await session.execute(select(User).where(User.id == internal_user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            await messenger.send_text(chat_id or "", "❌ Пользователь не найден.", keyboard=START_KEYBOARD)
            return

        service = ShiftCancellationService(session)
        result = await service.cancel_shift(
            shift_schedule_id=shift_id,
            cancelled_by_user_id=internal_user_id,
            cancelled_by_type="employee",
            cancellation_reason=reason,
            reason_notes=reason_notes,
            document_description=document_description,
            actor_role="employee",
            source="bot",
            extra_payload={"bot_flow": True, "messenger": "max"},
            media=media,
        )

        if result["success"]:
            shift_res = await session.execute(select(ShiftSchedule).where(ShiftSchedule.id == shift_id))
            shift = shift_res.scalar_one_or_none()
            obj = None
            if shift:
                obj_res = await session.execute(select(Object).where(Object.id == shift.object_id))
                obj = obj_res.scalar_one_or_none()
            obj_name = obj.name if obj else "Объект"
            tz = getattr(obj, "timezone", None) or "Europe/Moscow"
            user_tz = get_user_timezone(user)
            local_start = convert_utc_to_local(shift.planned_start, user_tz) if shift else None
            local_end = convert_utc_to_local(shift.planned_end, user_tz) if shift else None
            msg = result.get("message") or "Смена отменена."
            text = (
                f"✅ Смена отменена\n\n"
                f"🏢 {obj_name}\n"
                f"📅 {local_start.strftime('%d.%m.%Y %H:%M') if local_start else ''}\n"
                f"🕐 До {local_end.strftime('%H:%M') if local_end else ''}\n\n{msg}"
            )
        else:
            text = f"❌ {result.get('message', 'Ошибка отмены')}"

    await messenger.send_text(
        chat_id or "",
        text,
        keyboard=[[{"text": "🏠 Главное меню", "callback_data": "main_menu"}]],
    )
