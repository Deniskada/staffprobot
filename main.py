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
            print("❌ TELEGRAM_BOT_TOKEN не установлен!")
            print("📝 Создайте файл .env с TELEGRAM_BOT_TOKEN")
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
        
        # Создаем новый event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Инициализируем бота
            loop.run_until_complete(bot.initialize())
            print("✅ Бот инициализирован")
            
            # Запускаем в polling режиме
            print("🔄 Запуск в polling режиме...")
            print("📱 Бот запущен! Отправьте /start в Telegram")
            print("⏹️ Для остановки нажмите Ctrl+C")
            
            # Запускаем polling напрямую через application
            loop.run_until_complete(
                bot.application.run_polling(
                    allowed_updates=["message", "callback_query"],
                    drop_pending_updates=True
                )
            )
            
        except KeyboardInterrupt:
            print("\n⏹️ Получен сигнал остановки")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Останавливаем бота
            try:
                if hasattr(bot, 'application') and bot.application:
                    if not loop.is_closed():
                        # Пытаемся остановить приложение
                        if bot.application.running:
                            loop.run_until_complete(bot.application.stop())
                        print("✅ Бот остановлен")
                    else:
                        print("⚠️ Event loop уже закрыт")
            except Exception as e:
                print(f"⚠️ Ошибка при остановке бота: {e}")
            
            # Закрываем loop если он еще открыт
            try:
                if not loop.is_closed():
                    loop.close()
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии event loop: {e}")
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("👋 До свидания!")

if __name__ == "__main__":
    main()


