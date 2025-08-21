#!/usr/bin/env python3
"""
Скрипт запуска простого API сервера StaffProBot
"""
import sys
import os

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Основная функция запуска простого API сервера."""
    print("🚀 Запуск StaffProBot Simple API")
    
    try:
        from core.config.settings import settings
        print(f"✅ Настройки загружены: {settings.app_name}")
        
        from core.logging.logger import logger
        print("✅ Логгер инициализирован")
        
        print(f"🌐 API будет доступен по адресу: http://{settings.api_host}:{settings.api_port}")
        print(f"🔍 Health check: http://{settings.api_host}:{settings.api_port}/health")
        print(f"📝 API endpoints: http://{settings.api_host}:{settings.api_port}/api/v1/objects")
        
        # Запускаем простой API сервер
        from apps.api.simple_api import run_simple_api
        run_simple_api()
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
