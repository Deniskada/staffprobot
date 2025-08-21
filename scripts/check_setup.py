#!/usr/bin/env python3
"""Скрипт для проверки настройки MVP."""

import os
import sys
from pathlib import Path

# Добавление корневой директории в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_project_structure():
    """Проверка структуры проекта."""
    print("🔍 Проверка структуры проекта...")
    
    required_dirs = [
        "apps/bot",
        "apps/api", 
        "apps/scheduler",
        "apps/analytics",
        "apps/notification",
        "core/config",
        "core/database",
        "core/security",
        "core/exceptions",
        "core/utils",
        "domain/entities",
        "domain/repositories",
        "domain/services",
        "domain/value_objects",
        "infrastructure/database",
        "infrastructure/external",
        "infrastructure/messaging",
        "infrastructure/storage",
        "shared/schemas",
        "shared/constants",
        "shared/types",
        "tests/unit",
        "tests/integration",
        "tests/e2e",
        "docker/postgres",
        "docker/monitoring/grafana/provisioning",
        "scripts"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Отсутствуют директории: {missing_dirs}")
        return False
    else:
        print("✅ Структура проекта создана корректно")
        return True


def check_required_files():
    """Проверка обязательных файлов."""
    print("\n📁 Проверка обязательных файлов...")
    
    required_files = [
        "main.py",
        "requirements.txt",
        "pyproject.toml",
        "docker-compose.yml",
        "docker/Dockerfile",
        "env.example",
        "README.md",
        "core/config/settings.py",
        "core/logging/logger.py",
        "core/database/connection.py",
        "domain/entities/user.py",
        "domain/entities/object.py",
        "domain/entities/shift.py",
        "apps/bot/bot.py",
        "apps/bot/handlers.py",
        "apps/bot/services/user_service.py",
        "tests/unit/test_bot_handlers.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Отсутствуют файлы: {missing_files}")
        return False
    else:
        print("✅ Все обязательные файлы созданы")
        return True


def check_python_imports():
    """Проверка Python импортов."""
    print("\n🐍 Проверка Python импортов...")
    
    try:
        # Проверка основных модулей
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


def check_environment_variables():
    """Проверка переменных окружения."""
    print("\n🔧 Проверка переменных окружения...")
    
    # Проверка наличия .env файла
    if Path(".env").exists():
        print("✅ Файл .env найден")
        
        # Загрузка переменных
        from dotenv import load_dotenv
        load_dotenv()
        
        # Проверка обязательных переменных
        required_vars = ["TELEGRAM_BOT_TOKEN"]
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Отсутствуют переменные: {missing_vars}")
            print("   Скопируйте env.example в .env и заполните TELEGRAM_BOT_TOKEN")
            return False
        else:
            print("✅ Все обязательные переменные установлены")
            return True
    else:
        print("⚠️  Файл .env не найден")
        print("   Скопируйте env.example в .env и заполните TELEGRAM_BOT_TOKEN")
        return False


def main():
    """Основная функция проверки."""
    print("🚀 StaffProBot MVP - Проверка настройки")
    print("=" * 50)
    
    checks = [
        check_project_structure(),
        check_required_files(),
        check_python_imports(),
        check_environment_variables()
    ]
    
    print("\n" + "=" * 50)
    print("📊 Результаты проверки:")
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"🎉 Все проверки пройдены! ({passed}/{total})")
        print("\n✅ MVP готов к запуску!")
        print("\n📋 Следующие шаги:")
        print("1. Заполните TELEGRAM_BOT_TOKEN в .env файле")
        print("2. Запустите: docker-compose up -d")
        print("3. Или для разработки: python scripts/start_dev.py")
    else:
        print(f"⚠️  Проверки пройдены частично ({passed}/{total})")
        print("\n❌ Необходимо исправить ошибки перед запуском")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())







