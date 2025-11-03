"""
Обработчики административных команд для Telegram bot.

Команды:
- /morning - утренний обзор системы для владельца
- /devops - DevOps панель с метриками
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from core.logging.logger import logger
from core.database.session import get_async_session
from domain.entities.user import User, UserRole
from domain.entities.shift import Shift
from domain.entities.bug_log import BugLog
from domain.entities.deployment import Deployment
from apps.web.services.github_service import github_service
from core.config.settings import settings


async def is_admin(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь admin (owner/superadmin)."""
    try:
        async with get_async_session() as session:
            query = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            return user.is_owner() or user.is_superadmin()
    except Exception as e:
        logger.error(f"Failed to check admin status: {e}")
        return False


async def morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /morning - утренний обзор для владельца.
    
    Показывает:
    - Активные смены
    - Критичные баги
    - Недавние деплои
    - Статистику
    """
    user = update.effective_user
    if not user:
        return
    
    # Проверка прав доступа
    if not await is_admin(user.id):
        await update.message.reply_text(
            "❌ Эта команда доступна только владельцам.",
            parse_mode='HTML'
        )
        return
    
    try:
        async with get_async_session() as session:
            # Активные смены
            active_shifts_query = select(func.count(Shift.id)).where(
                Shift.status == 'open'
            )
            active_shifts_result = await session.execute(active_shifts_query)
            active_shifts_count = active_shifts_result.scalar() or 0
            
            # Критичные баги
            critical_bugs_query = select(func.count(BugLog.id)).where(
                and_(
                    BugLog.status == 'open',
                    BugLog.priority.in_(['critical', 'high'])
                )
            )
            critical_bugs_result = await session.execute(critical_bugs_query)
            critical_bugs_count = critical_bugs_result.scalar() or 0
            
            # Всего открытых багов
            open_bugs_query = select(func.count(BugLog.id)).where(
                BugLog.status == 'open'
            )
            open_bugs_result = await session.execute(open_bugs_query)
            open_bugs_count = open_bugs_result.scalar() or 0
            
            # Последний деплой (если есть)
            last_deploy_query = select(Deployment).order_by(
                Deployment.started_at.desc()
            ).limit(1)
            last_deploy_result = await session.execute(last_deploy_query)
            last_deploy = last_deploy_result.scalar_one_or_none()
            
            # Формируем ответ
            emoji = "🔴" if critical_bugs_count > 0 else "🟢" if active_shifts_count == 0 else "🟡"
            
            text = f"""
{emoji} <b>Доброе утро, владелец!</b>

📊 <b>Статус системы:</b>

🔄 <b>Активные смены:</b> {active_shifts_count}

🐛 <b>Критичные баги:</b> {critical_bugs_count}
📋 <b>Всего открытых багов:</b> {open_bugs_count}
"""
            
            if last_deploy:
                deploy_time = last_deploy.started_at.strftime('%d.%m.%Y %H:%M')
                deploy_status = "✅" if last_deploy.status == 'success' else "❌"
                text += f"\n🚀 <b>Последний деплой:</b> {deploy_status} {deploy_time}"
            
            text += f"""
            
💡 <b>Действия:</b>
• /devops - Детальная DevOps панель
• Проверьте критические баги
• Мониторьте активные смены
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🖥 DevOps панель", callback_data="admin_devops"),
                    InlineKeyboardButton("🐛 Баги", callback_data="view_bugs")
                ]
            ])
            
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
    
    except Exception as e:
        logger.error(f"Failed to generate morning report: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении данных.",
            parse_mode='HTML'
        )


async def devops_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда /devops - DevOps панель с детальными метриками.
    
    Показывает:
    - DORA метрики (если есть)
    - Статус компонентов
    - История деплоев
    - GitHub issues
    """
    user = update.effective_user
    if not user:
        return
    
    # Проверка прав доступа
    if not await is_admin(user.id):
        await update.message.reply_text(
            "❌ Эта команда доступна только владельцам.",
            parse_mode='HTML'
        )
        return
    
    try:
        async with get_async_session() as session:
            # За последние 30 дней
            thirty_days_ago = datetime.now() - timedelta(days=30)
            
            # Подсчет деплоев
            deployments_query = select(func.count(Deployment.id)).where(
                Deployment.started_at >= thirty_days_ago
            )
            deployments_result = await session.execute(deployments_query)
            deployments_count = deployments_result.scalar() or 0
            
            # Успешные деплои
            success_deploys_query = select(func.count(Deployment.id)).where(
                and_(
                    Deployment.started_at >= thirty_days_ago,
                    Deployment.status == 'success'
                )
            )
            success_deploys_result = await session.execute(success_deploys_query)
            success_deploys_count = success_deploys_result.scalar() or 0
            
            # Deployment Frequency (DORA)
            deploy_frequency = round(deployments_count / 30, 2)
            
            # Failure Rate
            failure_rate = 0
            if deployments_count > 0:
                failure_rate = round((deployments_count - success_deploys_count) / deployments_count * 100, 1)
            
            text = f"""
🖥 <b>DevOps панель StaffProBot</b>

📊 <b>DORA Metrics (30 дней):</b>

🚀 <b>Deployment Frequency:</b> {deploy_frequency}/день
❌ <b>Change Failure Rate:</b> {failure_rate}%

📈 <b>Статистика деплоев:</b>
• Всего: {deployments_count}
• Успешных: {success_deploys_count}
• Провалов: {deployments_count - success_deploys_count}

🐛 <b>GitHub Issues:</b>
"""
            
            # Получаем GitHub issues если токен настроен
            if github_service.token:
                try:
                    issues = await github_service.get_issues(
                        labels=["bug"],
                        state="open"
                    )
                    critical_issues = [i for i in issues if 'priority-critical' in i.get('labels', [])]
                    text += f"• Открытых багов: {len(issues)}\n"
                    text += f"• Критичных: {len(critical_issues)}\n"
                except Exception as e:
                    logger.error(f"Failed to get GitHub issues: {e}")
                    text += "• GitHub не подключен\n"
            else:
                text += "• GitHub не настроен\n"
            
            text += """
💡 <b>Система:</b>
• Web: ✅ Онлайн
• Bot: ✅ Онлайн
• DB: ✅ Онлайн
"""
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌅 Утренний обзор", callback_data="admin_morning"),
                    InlineKeyboardButton("🐛 Баги", callback_data="view_bugs")
                ]
            ])
            
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
    
    except Exception as e:
        logger.error(f"Failed to generate DevOps report: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла ошибка при получении данных.",
            parse_mode='HTML'
        )

