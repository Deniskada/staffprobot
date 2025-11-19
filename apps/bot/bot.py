"""Основной модуль бота StaffProBot."""

import asyncio
import json
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Optional

from telegram import Update
from telegram.error import Conflict
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from core.cache.redis_cache import cache
from core.config.settings import settings
from core.monitoring.metrics import (
    bot_polling_conflicts_total,
    bot_polling_heartbeat_timestamp,
)
from apps.scheduler.reminder_scheduler import ReminderScheduler
from .handlers_div import (
    start_command,
    handle_message,
    button_callback,
    handle_location,
    support_menu_command,
    support_faq_callback,
    get_support_conversation_handler,
    morning_command,
    devops_command
)
from .handlers import (
    help_command,
    status_command,
    get_chat_id_command
)
# Импорты удаленных файлов убраны
# from .analytics_handlers import AnalyticsHandlers
# from .time_slot_handlers import TimeSlotHandlers


logger = logging.getLogger(__name__)


class StaffProBot:
    """Основной класс бота StaffProBot."""
    
    LOCK_KEY = "bot_polling_lock"
    HEARTBEAT_KEY = "bot_polling_heartbeat"
    LOCK_TTL_SECONDS = 60
    HEARTBEAT_INTERVAL_SECONDS = 20
    
    def __init__(self):
        self.application: Optional[Application] = None
        self._bot_token = None  # Ленивая инициализация
        self.reminder_scheduler: Optional[ReminderScheduler] = None
        self._lock_refresh_task: Optional[asyncio.Task] = None
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
            
            # Инициализация Redis для UserState (если включен)
            if settings.state_backend == 'redis':
                logger.info("Initializing Redis for UserState...")
                from core.cache.redis_cache import cache
                try:
                    if not cache.is_connected:
                        await cache.connect()
                    logger.info("Redis for UserState initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize Redis for UserState: {e}")
                    logger.warning("Falling back to in-memory UserState")
            
            # Инициализация URLHelper для динамических URL
            logger.info("Starting URLHelper initialization...")
            from apps.web.services.system_settings_service import SystemSettingsService
            from core.utils.url_helper import URLHelper
            from core.database.session import get_async_session
            
            try:
                async with get_async_session() as session:
                    logger.info("Database session created for URLHelper initialization")
                    settings_service = SystemSettingsService(session)
                    await settings_service.initialize_default_settings()
                    URLHelper.set_settings_service(settings_service)
                    logger.info("URLHelper initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize URLHelper: {e}")
                logger.info("Continuing without URLHelper initialization")
            
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
        self.application.add_handler(CommandHandler("get_chat_id", get_chat_id_command))
        self.application.add_handler(CommandHandler("support", support_menu_command))
        
        # Admin команды
        self.application.add_handler(CommandHandler("morning", morning_command))
        self.application.add_handler(CommandHandler("devops", devops_command))
        
        # Support handlers
        self.application.add_handler(CallbackQueryHandler(support_faq_callback, pattern="^support_faq$"))
        self.application.add_handler(get_support_conversation_handler())
        
        # Обработка геопозиции (ВАЖНО: до ConversationHandler!)
        self.application.add_handler(
            MessageHandler(filters.LOCATION, handle_location)
        )
        
        # Обработка фото/видео для отчетов по задачам
        from .handlers_div.shift_handlers import _handle_received_media
        self.application.add_handler(
            MessageHandler(filters.PHOTO | filters.VIDEO, _handle_received_media)
        )
        
        # Обработка открытия/закрытия объектов
        from .handlers_div.object_state_handlers import (
            _handle_open_object,
            _handle_close_object,
            _handle_select_object_to_open
        )
        self.application.add_handler(CallbackQueryHandler(_handle_open_object, pattern="^open_object$"))
        self.application.add_handler(CallbackQueryHandler(_handle_close_object, pattern="^close_object$"))
        self.application.add_handler(CallbackQueryHandler(_handle_select_object_to_open, pattern="^select_object_to_open:.*$"))
        
        # Обработка отмены смен (включаем явные хендлеры)
        from .handlers_div.schedule_handlers import handle_cancel_shift, handle_cancel_reason_selection, handle_cancellation_skip_photo, handle_cancellation_document_input, handle_cancellation_photo_upload
        self.application.add_handler(CallbackQueryHandler(handle_cancel_shift, pattern="^cancel_shift_.*$"))
        self.application.add_handler(CallbackQueryHandler(handle_cancel_reason_selection, pattern="^cancel_reason_.*$"))
        self.application.add_handler(CallbackQueryHandler(handle_cancellation_skip_photo, pattern="^cancel_skip_photo$"))
        
        # Обработка ввода документа для отмены смены
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cancellation_document_input))
        # Обработка загрузки фото для отмены смены
        self.application.add_handler(MessageHandler(filters.PHOTO, handle_cancellation_photo_upload))
        
        # Добавляем ConversationHandler для отчетов
        # Временно отключаем для исправления проблемы с геолокацией
        # self.application.add_handler(self.analytics_handlers.get_conversation_handler())
        
        # Добавляем ConversationHandler для тайм-слотов
        # self.application.add_handler(self.time_slot_handlers.get_conversation_handler())
        
        # Обработка текстовых сообщений
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Обработка callback-кнопок (общий хендлер в самом конце)
        self.application.add_handler(CallbackQueryHandler(button_callback))
        
        # Обработка ошибок
        self.application.add_error_handler(self._error_handler)
        
        logger.info("Bot handlers configured successfully")
    
    async def _error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок бота."""
        if isinstance(context.error, Conflict):
            bot_polling_conflicts_total.inc()
            logger.error(
                "Telegram polling conflict detected",
                extra={
                    "error": str(context.error),
                    "category": "telegram_conflict"
                }
            )
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

            await self._acquire_polling_lock()

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
        finally:
            await self._release_polling_lock()
    
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

    async def _acquire_polling_lock(self) -> None:
        """Гарантировать единственный polling-инстанс."""
        if not cache.is_connected:
            logger.warning("Redis cache not connected, skipping polling lock")
            return
        payload = self._build_lock_payload()
        lock_acquired = await cache.redis.set(
            self.LOCK_KEY,
            payload,
            nx=True,
            ex=self.LOCK_TTL_SECONDS
        )
        if not lock_acquired:
            existing = await cache.redis.get(self.LOCK_KEY)
            details = existing.decode("utf-8") if existing else "unknown"
            raise RuntimeError(f"Polling already running by another instance: {details}")
        logger.info("Polling lock acquired", extra={"lock": payload})
        self._lock_refresh_task = asyncio.create_task(self._lock_refresh_loop())

    async def _release_polling_lock(self) -> None:
        """Освободить lock и heartbeat."""
        if self._lock_refresh_task:
            self._lock_refresh_task.cancel()
            try:
                await self._lock_refresh_task
            except asyncio.CancelledError:
                pass
            self._lock_refresh_task = None
        if cache.is_connected:
            await cache.delete(self.LOCK_KEY)
            await cache.delete(self.HEARTBEAT_KEY)
            logger.info("Polling lock released")

    async def _lock_refresh_loop(self) -> None:
        """Обновление TTL lock и heartbeat."""
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL_SECONDS)
                if not cache.is_connected:
                    continue
                await cache.redis.expire(self.LOCK_KEY, self.LOCK_TTL_SECONDS)
                await cache.redis.set(
                    self.HEARTBEAT_KEY,
                    self._build_lock_payload(include_timestamp=True),
                    ex=self.LOCK_TTL_SECONDS
                )
                bot_polling_heartbeat_timestamp.set(datetime.now(timezone.utc).timestamp())
        except asyncio.CancelledError:
            logger.debug("Polling lock refresh cancelled")
        except Exception as exc:
            logger.error("Failed to refresh polling lock", exc_info=exc)

    def _build_lock_payload(self, include_timestamp: bool = True) -> str:
        payload = {
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "env": settings.environment,
        }
        if include_timestamp:
            payload["ts"] = datetime.now(timezone.utc).isoformat()
        return json.dumps(payload)


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





