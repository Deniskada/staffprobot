#!/usr/bin/env python3
"""
Скрипт для заполнения базовых категорий задач.
"""

import asyncio
import sys
import os

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.session import get_async_session
from domain.entities.task_category import TaskCategory
from sqlalchemy import select


async def seed_task_categories():
    """Заполнение базовых категорий задач."""
    
    # Базовые категории задач
    categories = [
        {
            "name": "Уборка и санитария",
            "description": "Задачи по уборке помещений, поддержанию чистоты и санитарных норм",
            "icon": "broom",
            "color": "#28a745",
            "sort_order": 1
        },
        {
            "name": "Обслуживание клиентов",
            "description": "Работа с клиентами, консультации, помощь в выборе товаров",
            "icon": "person-hearts",
            "color": "#007bff",
            "sort_order": 2
        },
        {
            "name": "Безопасность",
            "description": "Обеспечение безопасности объекта, контроль доступа, мониторинг",
            "icon": "shield-check",
            "color": "#dc3545",
            "sort_order": 3
        },
        {
            "name": "Техническое обслуживание",
            "description": "Обслуживание оборудования, ремонт, техническая поддержка",
            "icon": "tools",
            "color": "#6c757d",
            "sort_order": 4
        },
        {
            "name": "Административные задачи",
            "description": "Ведение документации, отчетность, планирование",
            "icon": "file-text",
            "color": "#17a2b8",
            "sort_order": 5
        },
        {
            "name": "Продажи и маркетинг",
            "description": "Продажа товаров и услуг, маркетинговые мероприятия",
            "icon": "graph-up",
            "color": "#ffc107",
            "sort_order": 6
        },
        {
            "name": "Складские операции",
            "description": "Приемка товаров, складирование, инвентаризация",
            "icon": "box",
            "color": "#fd7e14",
            "sort_order": 7
        },
        {
            "name": "Специализированные задачи",
            "description": "Специфические задачи, требующие специальных навыков",
            "icon": "gear",
            "color": "#6f42c1",
            "sort_order": 8
        }
    ]
    
    async with get_async_session() as session:
        try:
            # Проверяем, есть ли уже категории
            existing_categories = await session.execute(select(TaskCategory))
            if existing_categories.scalars().first():
                print("Категории задач уже существуют, пропускаем заполнение")
                return
            
            # Создаем категории
            for category_data in categories:
                category = TaskCategory(**category_data)
                session.add(category)
            
            await session.commit()
            print(f"Создано {len(categories)} категорий задач")
            
            # Выводим созданные категории
            result = await session.execute(select(TaskCategory).order_by(TaskCategory.sort_order))
            created_categories = result.scalars().all()
            
            print("\nСозданные категории:")
            for category in created_categories:
                print(f"- {category.name} (иконка: {category.icon}, цвет: {category.color})")
                
        except Exception as e:
            print(f"Ошибка при создании категорий: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(seed_task_categories())
