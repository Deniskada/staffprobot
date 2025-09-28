"""Основной модуль бота StaffProBot."""

import logging
from typing import Optional
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from core.config.settings import settings
from apps.scheduler.reminder_scheduler import ReminderScheduler
from .handlers_div import (
    start_command,
    handle_message,
    button_callback,
    handle_location
)
from .handlers import (
    help_command,
    status_command
)
# Импорты удаленных файлов убраны
# from .analytics_handlers import AnalyticsHandlers
# from .time_slot_handlers import TimeSlotHandlers


logger = logging.getLogger(__name__)


class StaffProBot:
    """Основной класс бота StaffProBot."""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self._bot_token = None  # Ленивая инициализация
        self.reminder_scheduler: Optional[ReminderScheduler] = None
        from .handlers_div.analytics_handlers import AnalyticsHandlers
        self.analytics_handlers = AnalyticsHandlers()

    
    @property
    def bot_token(self) -> str:
        """Получение токена бота с проверкой."""
        if self._bot_token is None:
            self._bot_token = settings.telegram_bot_token
            if not self._bot_token:
                raise ValueError("TELEGRAM_BOT_TOKEN не установлен в переменных окружения")
        return self._bot_token
    
    async def initialize(self) -> None:
        """Инициализация бота."""
        try:
            # Создание приложения
            self.application = Application.builder().token(self.bot_token).build()
            
            # Добавление обработчиков команд
            self._setup_handlers()
            
            # Инициализация планировщика напоминаний
            self.reminder_scheduler = ReminderScheduler(self.bot_token)
            
            # Инициализация URLHelper для динамических URL
            from apps.web.services.system_settings_service import SystemSettingsService
            from core.utils.url_helper import URLHelper
            from core.database.session import get_async_session
            
            async with get_async_session() as session:
                settings_service = SystemSettingsService(session)
                await settings_service.initialize_default_settings()
                URLHelper.set_settings_service(settings_service)
            
            logger.info("Telegram bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise
    
    def _setup_handlers(self) -> None:
        """Настройка обработчиков команд и сообщений."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        # Базовые команды
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("status", status_command))
        
        # Обработка геопозиции (ВАЖНО: до ConversationHandler!)
        self.application.add_handler(
            MessageHandler(filters.LOCATION, handle_location)
        )
        
        # Добавляем ConversationHandler для отчетов
        # Временно отключаем для исправления проблемы с геолокацией
        # self.application.add_handler(self.analytics_handlers.get_conversation_handler())
        
        # Добавляем ConversationHandler для тайм-слотов
        # self.application.add_handler(self.time_slot_handlers.get_conversation_handler())
        
        # Обработка текстовых сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Обработка callback-кнопок
        self.application.add_handler(
            CallbackQueryHandler(button_callback)
        )
        
        # Обработка ошибок
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot handlers configured successfully")
    
    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок бота."""
        logger.error(
            "Exception while handling an update",
            extra={
                "update": str(update),
                "context": str(context)
            },
            exc_info=context.error
        )
    
    async def start_polling(self) -> None:
        """Запуск бота в режиме polling без управления внешним event loop."""
        if not self.application:
            raise RuntimeError("Application not initialized")

        try:
            logger.info("Starting bot in polling mode")

            # Инициализация и старт приложения
            await self.application.initialize()

            if self.reminder_scheduler:
                await self.reminder_scheduler.start()

            await self.application.start()

            # Старт polling через updater, без закрытия внешнего event loop
            if self.application.updater is None:
                raise RuntimeError("Application updater is not available")

            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
            )

            # Блокируемся, пока процесс не будет остановлен (без закрытия внешнего event loop)
            stop_event = asyncio.Event()
            await stop_event.wait()

        except Exception as e:
            logger.error(f"Error in polling mode: {e}")
            raise
    
    async def start_webhook(self) -> None:
        """Запуск бота в режиме webhook."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        if not settings.telegram_webhook_url:
            raise ValueError("TELEGRAM_WEBHOOK_URL не установлен для webhook режима")
        
        try:
            webhook_url = f"{settings.telegram_webhook_url}{settings.telegram_webhook_path}"
            
            logger.info(f"Starting bot in webhook mode: {webhook_url}")
            
            # Запускаем планировщик напоминаний
            if self.reminder_scheduler:
                await self.reminder_scheduler.start()
            
            await self.application.bot.set_webhook(url=webhook_url)
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=8000,
                webhook_url=webhook_url,
                drop_pending_updates=True,
                close_loop=False,
                stop_signals=None,
            )
        except Exception as e:
            logger.error(f"Error in webhook mode: {e}")
            raise
    
    async def stop(self) -> None:
        """Остановка бота."""
        # Останавливаем планировщик напоминаний
        if self.reminder_scheduler:
            await self.reminder_scheduler.stop()
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Bot stopped successfully")


# Глобальный экземпляр бота
bot = StaffProBot()


async def start_bot() -> None:
    """Запуск бота."""
    try:
        await bot.initialize()
        
        if settings.environment == "production" and settings.telegram_webhook_url:
            await bot.start_webhook()
        else:
            await bot.start_polling()
            
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


async def stop_bot() -> None:
    """Остановка бота."""
    await bot.stop()





