"""
Обработчики для Support Hub (поддержка сотрудников).

Команды:
- /support - меню поддержки
- /bug - репорт бага (FSM)
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, 
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging.logger import logger
from core.database.session import get_async_session
from domain.entities.user import User
from domain.entities.bug_log import BugLog
from apps.web.services.github_service import github_service
from core.config.settings import settings


# FSM состояния для репорта бага
BUG_WHAT_DOING, BUG_EXPECTED, BUG_ACTUAL, BUG_PRIORITY, BUG_PHOTO = range(5)


async def get_user_id_from_telegram(telegram_id: int, session: AsyncSession) -> int:
    """Получает внутренний user_id из telegram_id."""
    query = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()
    return user.id if user else None


async def support_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /support - меню поддержки.
    
    Показывает:
    - FAQ
    - Форма отчета о баге
    - Ссылку на веб-интерфейс
    """
    user = update.effective_user
    if not user:
        return
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 FAQ", callback_data="support_faq"),
            InlineKeyboardButton("🐛 Сообщить о баге", callback_data="support_bug")
        ]
    ])
    
    text = """
🆘 <b>Центр поддержки StaffProBot</b>

Выберите нужное действие:

📋 <b>FAQ</b> - ответы на частые вопросы
🐛 <b>Сообщить о баге</b> - репорт о проблеме

💡 <b>Веб-интерфейс доступен на</b>: {domain}/support
""".format(domain=settings.domain)
    
    await update.message.reply_text(
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )


async def support_faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показ FAQ через бота."""
    await update.callback_query.answer()
    
    faq_text = """
📋 <b>Частые вопросы</b>

<b>Как открыть смену?</b>
Нажмите кнопку 'Открыть смену' и отправьте геолокацию.
Система проверит, что вы находитесь на объекте.

<b>Как закрыть смену?</b>
Нажмите 'Закрыть смену'.
Система автоматически рассчитает отработанное время.

<b>Что делать, если забыл закрыть смену?</b>
Обратитесь к менеджеру или владельцу для ручного закрытия.

<b>Когда начисляется зарплата?</b>
Расчеты производятся автоматически после закрытия смены.

<b>Не работает геолокация</b>
Убедитесь, что разрешили доступ в настройках телефона
и включите GPS.

🌐 <b>Полная база знаний:</b> {domain}/support/faq
""".format(domain=settings.domain)
    
    await update.callback_query.message.edit_text(
        faq_text,
        parse_mode='HTML'
    )


async def support_bug_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало процесса репорта бага."""
    await update.callback_query.answer()
    
    await update.callback_query.message.edit_text(
        """
🐛 <b>Репорт бага</b>

Помогите нам улучшить систему!
Опишите проблему подробно.

<b>Шаг 1/4:</b> Что вы делали, когда произошла ошибка?
        """,
        parse_mode='HTML'
    )
    
    return BUG_WHAT_DOING


async def bug_what_doing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа 'что делали'."""
    context.user_data['bug_what_doing'] = update.message.text
    
    await update.message.reply_text(
        """
<b>Шаг 2/4:</b> Что вы ожидали увидеть?
        """,
        parse_mode='HTML'
    )
    
    return BUG_EXPECTED


async def bug_expected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа 'что ожидали'."""
    context.user_data['bug_expected'] = update.message.text
    
    await update.message.reply_text(
        """
<b>Шаг 3/4:</b> Что произошло вместо этого?

(или отправьте /skip если не хотите указывать)
        """,
        parse_mode='HTML'
    )
    
    return BUG_ACTUAL


async def bug_actual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ответа 'что произошло'."""
    context.user_data['bug_actual'] = update.message.text
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Низкий", callback_data="priority_low")],
        [InlineKeyboardButton("🟡 Средний", callback_data="priority_medium")],
        [InlineKeyboardButton("🟠 Высокий", callback_data="priority_high")],
        [InlineKeyboardButton("🔴 Критичный", callback_data="priority_critical")]
    ])
    
    await update.message.reply_text(
        """
<b>Шаг 4/4:</b> Насколько это срочно?

Выберите приоритет:
        """,
        parse_mode='HTML',
        reply_markup=keyboard
    )
    
    return BUG_PRIORITY


async def bug_priority_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора приоритета и завершение репорта."""
    await update.callback_query.answer()
    
    priority_map = {
        'priority_low': 'low',
        'priority_medium': 'medium',
        'priority_high': 'high',
        'priority_critical': 'critical'
    }
    
    priority = priority_map.get(update.callback_query.data, 'medium')
    context.user_data['bug_priority'] = priority
    
    # Собираем данные
    what_doing = context.user_data.get('bug_what_doing')
    expected = context.user_data.get('bug_expected')
    actual = context.user_data.get('bug_actual')
    telegram_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Сохраняем в БД
    try:
        async with get_async_session() as session:
            # Получаем user_id
            user_id = await get_user_id_from_telegram(telegram_id, session)
            if not user_id:
                await update.callback_query.message.edit_text(
                    "❌ Ошибка: пользователь не найден в системе."
                )
                return ConversationHandler.END
            
            # Создаем bug_log
            bug_log = BugLog(
                user_id=user_id,
                title=f"Bug: {what_doing[:50]}",
                what_doing=what_doing,
                expected=expected,
                actual=actual,
                priority=priority,
                status='open'
            )
            session.add(bug_log)
            await session.commit()
            
            # Создаем GitHub Issue
            issue_number = None
            try:
                issue_body = f"""
## 🐛 Bug Report (from Telegram Bot)

**Reporter:** @{username} (Telegram ID: {telegram_id})
**Priority:** {priority}
**Date:** {bug_log.created_at.isoformat()}

### What was doing
{what_doing}

### Expected
{expected}

### Actual
{actual}
                """
                
                issue = await github_service.create_issue(
                    title=f"Bug: {what_doing[:50]}",
                    body=issue_body,
                    labels=["bug", "from-telegram", f"priority-{priority}", "needs-triage"]
                )
                issue_number = issue['number']
                
                # Обновляем bug_log
                bug_log.github_issue_number = issue_number
                await session.commit()
            except Exception as e:
                logger.error(f"Failed to create GitHub issue: {e}")
            
            # Успешный ответ
            response_text = f"""
✅ <b>Баг зарегистрирован!</b>

Спасибо за обратную связь. Мы займемся этим как можно скорее.
            """
            
            if issue_number:
                response_text += f"\n🎫 GitHub Issue: #{issue_number}"
            
            await update.callback_query.message.edit_text(
                response_text,
                parse_mode='HTML'
            )
            
            logger.info(
                "Bug report created via Telegram",
                user_id=user_id,
                priority=priority,
                github_issue=issue_number
            )
    
    except Exception as e:
        logger.error(f"Failed to create bug report: {e}", exc_info=True)
        await update.callback_query.message.edit_text(
            "❌ Произошла ошибка при сохранении отчета. Попробуйте позже."
        )
    
    # Очищаем user_data
    context.user_data.clear()
    
    return ConversationHandler.END


async def bug_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена репорта бага."""
    context.user_data.clear()
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            "❌ Отменено.",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ Отменено.",
            parse_mode='HTML'
        )
    
    return ConversationHandler.END


def get_support_conversation_handler() -> ConversationHandler:
    """Возвращает ConversationHandler для поддержки."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(support_bug_callback, pattern="^support_bug$")
        ],
        states={
            BUG_WHAT_DOING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bug_what_doing)
            ],
            BUG_EXPECTED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bug_expected)
            ],
            BUG_ACTUAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, bug_actual),
                CommandHandler("skip", bug_actual)
            ],
            BUG_PRIORITY: [
                CallbackQueryHandler(bug_priority_selected, pattern="^priority_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", bug_cancel),
            CallbackQueryHandler(bug_cancel, pattern="^cancel$")
        ]
    )

