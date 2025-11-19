#!/usr/bin/env python3
"""
Нативная версия main.py для MVP StaffProBot
Использует официальный способ запуска python-telegram-bot
"""

import sys
import os

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Основная функция запуска бота."""
    print("🚀 Запуск StaffProBot MVP")
    
    try:
        # Простой импорт без сложных зависимостей
        from core.config.settings import settings
        print(f"✅ Настройки загружены: {settings.app_name}")
        
        from core.logging.logger import logger
        print("✅ Логгер инициализирован")
        
        # Проверяем токен бота
        if not settings.telegram_bot_token:
            print("❌ TELEGRAM_BOT_TOKEN не обнаружен!")
            print("📝 Укажите TELEGRAM_BOT_TOKEN_DEV (dev) или TELEGRAM_BOT_TOKEN_PROD в .env/.env.prod, либо TELEGRAM_BOT_TOKEN_OVERRIDE")
            return
        
        print("✅ TELEGRAM_BOT_TOKEN найден")
        
        # Импортируем бота напрямую
        from apps.bot.bot import StaffProBot
        print("✅ Модули бота импортированы")
        
        # Создаем экземпляр бота
        bot = StaffProBot()
        print("🤖 Инициализация Telegram бота...")
        
        # Инициализируем бота
        import asyncio
        
        try:
            # Основная функция запуска
            async def run_app():
                try:
                    # Проверяем доступность критических сервисов
                    from core.health.health_check import health_checker
                    print("🔍 Проверка доступности сервисов...")
                    
                    services_ready = await health_checker.wait_for_services(
                        ['postgresql', 'redis'], max_attempts=10, delay=3
                    )
                    
                    if not services_ready:
                        print("❌ Критические сервисы недоступны!")
                        print("💡 Убедитесь что запущены Docker контейнеры:")
                        print("   docker-compose up -d postgres redis")
                        return
                    
                    print("✅ Все сервисы доступны")
                    
                    # Инициализируем кэш
                    from core.cache.redis_cache import init_cache
                    await init_cache()
                    print("✅ Redis кэш инициализирован")
                    
                    # Инициализируем бота
                    await bot.initialize()
                    print("✅ Бот инициализирован")
                    
                    # Запускаем в polling режиме
                    print("🔄 Запуск в polling режиме...")
                    print("📱 Бот запущен! Отправьте /start в Telegram")
                    print("⏹️ Для остановки нажмите Ctrl+C")
                    
                    # Запускаем polling через start_polling
                    await bot.application.initialize()
                    await bot.application.start()
                    await bot.application.updater.start_polling(
                        allowed_updates=["message", "callback_query"],
                        drop_pending_updates=True
                    )
                    
                    # Ждем в бесконечном цикле
                    while True:
                        await asyncio.sleep(1)
                    
                except KeyboardInterrupt:
                    print("\n⏹️ Получен сигнал остановки")
                except Exception as e:
                    print(f"❌ Ошибка в run_app: {e}")
                    raise
                finally:
                    # Закрываем кэш при завершении
                    try:
                        from core.cache.redis_cache import close_cache
                        await close_cache()
                        print("✅ Redis кэш закрыт")
                    except Exception as e:
                        print(f"⚠️ Ошибка при закрытии кэша: {e}")
            
            # Запускаем приложение
            asyncio.run(run_app())
            
        except KeyboardInterrupt:
            print("\n⏹️ Получен сигнал остановки")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # asyncio.run() сам управляет event loop и закрывает все ресурсы
            print("🔄 Завершение работы...")
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("👋 До свидания!")

if __name__ == "__main__":
    main()


