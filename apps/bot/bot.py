"""Основной класс Telegram бота."""

import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)
from typing import Optional
from core.config.settings import settings
from core.logging.logger import logger
from .handlers import (
    start_command,
    help_command,
    status_command,
    handle_message,
    button_callback,
    handle_location
)


class StaffProBot:
    """Основной класс бота StaffProBot."""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self._bot_token = None  # Ленивая инициализация
    
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
        
        # Обработка геопозиции
        self.application.add_handler(
            MessageHandler(filters.LOCATION, handle_location)
        )
        
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
        """Запуск бота в режиме polling."""
        if not self.application:
            raise RuntimeError("Application not initialized")
        
        try:
            logger.info("Starting bot in polling mode")
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
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
            
            await self.application.bot.set_webhook(url=webhook_url)
            await self.application.run_webhook(
                listen="0.0.0.0",
                port=8000,
                webhook_url=webhook_url,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.error(f"Error in webhook mode: {e}")
            raise
    
    async def stop(self) -> None:
        """Остановка бота."""
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





