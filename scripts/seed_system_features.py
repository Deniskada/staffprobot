"""
Seed-скрипт для заполнения справочника функций системы.

Синхронизирует данные из core.config.features с таблицей system_features.
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.system_feature import SystemFeature
from core.config.features import SYSTEM_FEATURES_REGISTRY
from core.logging.logger import logger


async def seed_system_features():
    """Заполнить/обновить справочник функций."""
    async with get_async_session() as session:
        logger.info("Начало синхронизации системных функций")
        
        # Получаем все существующие функции
        result = await session.execute(select(SystemFeature))
        existing_features = {f.key: f for f in result.scalars().all()}
        
        # Синхронизируем с registry
        for key, definition in SYSTEM_FEATURES_REGISTRY.items():
            if key in existing_features:
                # Обновляем существующую
                feature = existing_features[key]
                feature.name = definition['name']
                feature.description = definition['description']
                feature.sort_order = definition['sort_order']
                feature.menu_items = definition['menu_items']
                feature.form_elements = definition['form_elements']
                feature.is_active = True
                logger.info(f"Обновлена функция: {key}")
            else:
                # Создаём новую
                feature = SystemFeature(
                    key=key,
                    name=definition['name'],
                    description=definition['description'],
                    sort_order=definition['sort_order'],
                    menu_items=definition['menu_items'],
                    form_elements=definition['form_elements'],
                    is_active=True,
                    usage_count=0
                )
                session.add(feature)
                logger.info(f"Создана функция: {key}")
        
        await session.commit()
        logger.info("Синхронизация системных функций завершена")
        
        # Выводим итог
        result = await session.execute(select(SystemFeature).order_by(SystemFeature.sort_order))
        all_features = result.scalars().all()
        logger.info(f"Всего функций в БД: {len(all_features)}")
        for feature in all_features:
            logger.info(f"  {feature.sort_order}. {feature.key}: {feature.name}")


if __name__ == "__main__":
    asyncio.run(seed_system_features())

