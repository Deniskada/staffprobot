#!/usr/bin/env python3
"""Тест main.py для MVP."""

import sys
import os

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_main_import():
    """Тестирует импорт main.py."""
    try:
        import main
        print("✅ main.py импортируется успешно")
        print(f"✅ Приложение: {main.app.title}")
        print(f"✅ Версия: {main.app.version}")
        return True
    except Exception as e:
        print(f"❌ Ошибка импорта main.py: {e}")
        return False

def test_fastapi_app():
    """Тестирует FastAPI приложение."""
    try:
        import main
        from fastapi import FastAPI
        
        if isinstance(main.app, FastAPI):
            print("✅ FastAPI приложение создано корректно")
            return True
        else:
            print("❌ main.app не является FastAPI приложением")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки FastAPI: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Тестирование main.py")
    print("=" * 40)
    
    import_ok = test_main_import()
    fastapi_ok = test_fastapi_app()
    
    print("\n" + "=" * 40)
    if import_ok and fastapi_ok:
        print("🎉 main.py готов к запуску!")
        print("\n📋 Следующие шаги:")
        print("1. Создайте .env с TELEGRAM_BOT_TOKEN")
        print("2. Запустите: python main.py")
    else:
        print("❌ main.py требует доработки")


