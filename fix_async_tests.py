#!/usr/bin/env python3
"""
Скрипт для автоматического добавления @pytest.mark.asyncio к async тестам
"""
import os
import re

def fix_async_tests(file_path):
    """Добавляет @pytest.mark.asyncio к async тестам в файле"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Паттерн для поиска async def test_* функций без @pytest.mark.asyncio
    pattern = r'(\s+)(async def test_\w+\([^)]*\):)'
    
    def replace_func(match):
        indent = match.group(1)
        func_def = match.group(2)
        return f'{indent}@pytest.mark.asyncio\n{indent}{func_def}'
    
    # Заменяем все async def test_* на @pytest.mark.asyncio + async def test_*
    new_content = re.sub(pattern, replace_func, content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Fixed async tests in {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False

def main():
    """Основная функция"""
    test_files = [
        'tests/unit/test_admin_notification_service.py',
        'tests/unit/test_notification_template_service.py',
        'tests/integration/test_admin_notifications_routes.py',
        'tests/integration/test_template_crud_operations.py'
    ]
    
    fixed_count = 0
    for file_path in test_files:
        if os.path.exists(file_path):
            if fix_async_tests(file_path):
                fixed_count += 1
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
