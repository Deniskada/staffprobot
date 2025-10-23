#!/usr/bin/env python3
"""
Скрипт для создания базовых тарифных планов в системе StaffProBot
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.database.session import get_async_session
from apps.web.services.tariff_service import TariffService
from core.logging.logger import logger

async def seed_tariffs():
    """Создает базовые тарифные планы в системе"""
    try:
        logger.info("Начинаю создание тарифных планов...")
        
        async with get_async_session() as session:
            tariff_service = TariffService(session)
            
            # Проверяем, есть ли уже тарифы
            existing_tariffs = await tariff_service.get_all_tariff_plans()
            if existing_tariffs:
                logger.info(f"Найдено {len(existing_tariffs)} существующих тарифов. Пропускаю создание.")
                return
            
            tariffs = [
                {
                    "name": "Базовый",
                    "description": "Базовый тариф для начинающих владельцев",
                    "price": 0.00,
                    "currency": "RUB",
                    "billing_period": "month",
                    "max_objects": 2,
                    "max_employees": 5,
                    "max_managers": 0,
                    "features": ["telegram_bot", "basic_reports", "basic_support"],
                    "is_popular": False,
                    "is_active": True
                },
                {
                    "name": "Стандартный", 
                    "description": "Стандартный тариф для растущего бизнеса",
                    "price": 1990.00,
                    "currency": "RUB",
                    "billing_period": "month",
                    "max_objects": 10,
                    "max_employees": 25,
                    "max_managers": 2,
                    "features": ["telegram_bot", "basic_reports", "advanced_reports", "priority_support", "analytics", "applications"],
                    "is_popular": True,
                    "is_active": True
                },
                {
                    "name": "Премиум",
                    "description": "Премиум тариф для крупного бизнеса", 
                    "price": 4990.00,
                    "currency": "RUB",
                    "billing_period": "month",
                    "max_objects": -1,  # Безлимитный
                    "max_employees": -1,
                    "max_managers": -1,
                    "features": ["telegram_bot", "basic_reports", "advanced_reports", "priority_support", "analytics", "applications", "payroll_accruals", "moderation_cancellations", "analytics_cancellations"],
                    "is_popular": False,
                    "is_active": True
                }
            ]
            
            created_count = 0
            for tariff_data in tariffs:
                try:
                    tariff = await tariff_service.create_tariff_plan(tariff_data)
                    logger.info(f"Создан тариф: {tariff.name} (ID: {tariff.id})")
                    created_count += 1
                except Exception as e:
                    logger.error(f"Ошибка создания тарифа {tariff_data['name']}: {e}")
            
            logger.info(f"Успешно создано {created_count} тарифных планов")
            
    except Exception as e:
        logger.error(f"Критическая ошибка при создании тарифов: {e}")
        raise

async def main():
    """Основная функция"""
    try:
        await seed_tariffs()
        print("✅ Тарифные планы успешно созданы!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())