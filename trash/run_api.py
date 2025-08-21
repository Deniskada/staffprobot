#!/usr/bin/env python3
"""
Скрипт запуска API сервера StaffProBot
"""
import sys
import os
import uvicorn

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Основная функция запуска API сервера."""
    print("🚀 Запуск StaffProBot API")
    
    try:
        from core.config.settings import settings
        print(f"✅ Настройки загружены: {settings.app_name}")
        
        from core.logging.logger import logger
        print("✅ Логгер инициализирован")
        
        print(f"🌐 API будет доступен по адресу: http://{settings.api_host}:{settings.api_port}")
        print(f"📚 Документация: http://{settings.api_host}:{settings.api_port}/docs")
        print(f"🔍 Health check: http://{settings.api_host}:{settings.api_port}/health")
        
        # Запускаем сервер
        uvicorn.run(
            "apps.api.app:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=settings.api_reload,
            log_level=settings.log_level.lower()
        )
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

