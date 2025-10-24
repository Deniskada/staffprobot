#!/usr/bin/env python3
"""Миграция данных Object.shift_tasks JSONB → TaskTemplateV2."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from core.database.session import get_async_session
from domain.entities.object import Object
from domain.entities.task_template import TaskTemplateV2
from decimal import Decimal


async def migrate_shift_tasks():
    """Конвертировать shift_tasks всех объектов в TaskTemplateV2."""
    async with get_async_session() as session:
        # Получаем все объекты с непустыми shift_tasks
        query = select(Object).where(Object.shift_tasks.isnot(None))
        result = await session.execute(query)
        objects = result.scalars().all()
        
        print(f"Найдено {len(objects)} объектов с shift_tasks")
        
        created_count = 0
        skipped_count = 0
        
        for obj in objects:
            if not obj.shift_tasks or not isinstance(obj.shift_tasks, list):
                print(f"Объект {obj.id} ({obj.name}): shift_tasks пустые или неправильный формат, пропуск")
                skipped_count += 1
                continue
            
            print(f"\nОбъект {obj.id} ({obj.name}): {len(obj.shift_tasks)} задач(и)")
            
            for idx, task in enumerate(obj.shift_tasks):
                # task может быть str или dict
                if isinstance(task, str):
                    task_text = task
                    task_bonus = Decimal('100.00')
                    task_mandatory = True
                    task_media = False
                elif isinstance(task, dict):
                    task_text = task.get('text', f'Задача {idx+1}')
                    task_bonus = Decimal(str(task.get('deduction_amount', 100)))
                    task_mandatory = task.get('is_mandatory', True)
                    task_media = task.get('requires_media', False)
                else:
                    print(f"  Задача {idx}: неизвестный формат, пропуск")
                    continue
                
                # Генерируем уникальный код
                code = f"legacy_obj{obj.id}_task{idx}"
                
                # Проверяем, не создан ли уже шаблон с таким кодом
                existing = await session.scalar(
                    select(TaskTemplateV2).where(TaskTemplateV2.code == code)
                )
                if existing:
                    print(f"  Задача {idx} ({task_text[:30]}): уже существует, пропуск")
                    skipped_count += 1
                    continue
                
                # Создаём шаблон
                template = TaskTemplateV2(
                    owner_id=obj.owner_id,
                    object_id=obj.id,
                    code=code,
                    title=task_text[:200],  # Обрезаем до 200 символов
                    description=f"Мигрировано из Object.shift_tasks (объект {obj.name})",
                    is_mandatory=task_mandatory,
                    requires_media=task_media,
                    default_bonus_amount=task_bonus,
                    is_active=True
                )
                session.add(template)
                created_count += 1
                print(f"  ✓ Создан шаблон {code}: {task_text[:50]}")
        
        await session.commit()
        print(f"\n=== Итого ===")
        print(f"Создано: {created_count}")
        print(f"Пропущено: {skipped_count}")
        print(f"Всего объектов: {len(objects)}")


if __name__ == "__main__":
    asyncio.run(migrate_shift_tasks())

