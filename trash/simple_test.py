#!/usr/bin/env python3
"""Простой тест MVP StaffProBot."""

import sys
import os
from datetime import datetime

# Добавляем корневую папку в путь для корректных импортов
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тест импортов."""
    print("🔍 Тестирую импорты...")
    
    try:
        import core.config.settings
        print("✅ core.config.settings импортируется")
        
        import core.logging.logger
        print("✅ core.logging.logger импортируется")
        
        import core.database.connection
        print("✅ core.database.connection импортируется")
        
        import domain.entities.user
        print("✅ domain.entities.user импортируется")
        
        import domain.entities.object
        print("✅ domain.entities.object импортируется")
        
        import domain.entities.shift
        print("✅ domain.entities.shift импортируется")
        
        import apps.bot.bot
        print("✅ apps.bot.bot импортируется")
        
        import apps.bot.handlers
        print("✅ apps.bot.handlers импортируется")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_basic_functionality():
    """Тест базовой функциональности."""
    print("\n🔧 Тестирую базовую функциональность...")
    
    try:
        from core.config.settings import settings
        print(f"✅ Настройки загружены: {settings.app_name}")
        
        from core.logging.logger import logger
        print("✅ Логгер инициализирован")
        
        from domain.entities.user import User
        user = User(telegram_id=123, username="test_user", first_name="Test")
        print("✅ Модель User создана")
        
        from domain.entities.object import Object
        obj = Object(name="Test Object", owner_id=1, address="Test Address")
        print("✅ Модель Object создана")
        
        from domain.entities.shift import Shift
        shift = Shift(user_id=1, object_id=1, start_time=datetime.now())
        print("✅ Модель Shift создана")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка функциональности: {e}")
        return False

def main():
    """Основная функция."""
    print("🚀 StaffProBot MVP - Простой тест")
    print("=" * 50)
    
    # Тест импортов
    imports_ok = test_imports()
    
    # Тест функциональности
    functionality_ok = test_basic_functionality()
    
    print("\n" + "=" * 50)
    print("📊 Результаты теста:")
    
    if imports_ok and functionality_ok:
        print("🎉 Все тесты пройдены!")
        print("\n✅ MVP готов к работе!")
        print("\n📋 Следующие шаги:")
        print("1. Создайте файл .env с TELEGRAM_BOT_TOKEN")
        print("2. Запустите: python main.py")
        print("3. Или через Docker: docker-compose up -d")
    else:
        print("❌ Некоторые тесты не пройдены")
        print("Необходимо исправить ошибки перед запуском")
    
    return 0 if imports_ok and functionality_ok else 1

if __name__ == "__main__":
    exit(main())



