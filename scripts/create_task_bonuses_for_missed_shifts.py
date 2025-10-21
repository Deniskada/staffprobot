"""Создание премий за задачи для смен, где они были пропущены."""

import asyncio
import json
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database.session import get_async_session
from core.logging.logger import logger
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.timeslot_task_template import TimeslotTaskTemplate


async def create_missed_task_bonuses():
    """Создать премии за задачи для смен где они были пропущены."""
    
    async with get_async_session() as session:
        # Найти completed смены с задачами в notes
        shifts_query = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.time_slot)
        ).where(
            Shift.status == 'completed',
            Shift.notes.isnot(None),
            Shift.notes.like('%[TASKS]%')
        ).order_by(Shift.id)
        
        shifts_result = await session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        print(f"\n{'='*80}")
        print(f"Проверка {len(shifts)} смен с задачами")
        print(f"{'='*80}\n")
        
        missing_bonuses = []
        
        for shift in shifts:
            # Парсим задачи из notes
            marker = '[TASKS]'
            marker_pos = shift.notes.find(marker)
            if marker_pos == -1:
                continue
            
            json_str = shift.notes[marker_pos + len(marker):].strip()
            try:
                tasks_data = json.loads(json_str)
                completed_task_indices = tasks_data.get('completed_tasks', [])
                task_media = tasks_data.get('task_media', {})
            except json.JSONDecodeError:
                continue
            
            if not completed_task_indices:
                continue  # Нет выполненных задач
            
            # Собираем список задач смены
            shift_tasks = []
            
            if shift.time_slot_id and shift.time_slot:
                # Задачи из тайм-слота
                template_query = select(TimeslotTaskTemplate).where(
                    TimeslotTaskTemplate.timeslot_id == shift.time_slot_id
                ).order_by(TimeslotTaskTemplate.display_order)
                template_result = await session.execute(template_query)
                templates = template_result.scalars().all()
                
                for template in templates:
                    shift_tasks.append({
                        'text': template.task_text,
                        'deduction_amount': float(template.deduction_amount) if template.deduction_amount else 0,
                        'source': 'timeslot'
                    })
                
                # Задачи объекта (если не игнорируются)
                if not shift.time_slot.ignore_object_tasks and shift.object and shift.object.shift_tasks:
                    for task in shift.object.shift_tasks:
                        shift_tasks.append({
                            'text': task.get('text', ''),
                            'deduction_amount': task.get('deduction_amount', 0),
                            'source': 'object'
                        })
            else:
                # Спонтанная смена - задачи объекта
                if shift.object and shift.object.shift_tasks:
                    for task in shift.object.shift_tasks:
                        shift_tasks.append({
                            'text': task.get('text', ''),
                            'deduction_amount': task.get('deduction_amount', 0),
                            'source': 'object'
                        })
            
            # Проверяем есть ли уже премии за задачи
            existing_bonuses_query = select(PayrollAdjustment).where(
                PayrollAdjustment.shift_id == shift.id,
                PayrollAdjustment.adjustment_type.in_(['task_bonus', 'task_penalty'])
            )
            existing_bonuses_result = await session.execute(existing_bonuses_query)
            existing_bonuses = existing_bonuses_result.scalars().all()
            existing_count = len(existing_bonuses)
            
            # Определяем сколько премий должно быть
            expected_count = len(completed_task_indices)
            
            if existing_count < expected_count:
                missing_bonuses.append({
                    'shift': shift,
                    'shift_tasks': shift_tasks,
                    'completed_indices': completed_task_indices,
                    'task_media': task_media,
                    'existing_count': existing_count,
                    'expected_count': expected_count
                })
                
                print(f"❌ Смена {shift.id} (объект {shift.object.name}):")
                print(f"   Закрыта: {shift.end_time}")
                print(f"   Задач выполнено: {len(completed_task_indices)}")
                print(f"   Премий начислено: {existing_count}")
                print(f"   Медиа: {len(task_media)} фото/видео")
                print()
        
        print(f"{'='*80}")
        print(f"Найдено смен с пропущенными премиями: {len(missing_bonuses)}")
        print(f"{'='*80}\n")
        
        if not missing_bonuses:
            print("✅ Все премии начислены!")
            return
        
        response = input(f"\nСоздать пропущенные премии? (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Создание отменено")
            return
        
        created_count = 0
        for item in missing_bonuses:
            shift = item['shift']
            shift_tasks = item['shift_tasks']
            completed_indices = item['completed_indices']
            
            for task_idx in completed_indices:
                if task_idx >= len(shift_tasks):
                    continue  # Индекс вне диапазона
                
                task = shift_tasks[task_idx]
                amount = Decimal(str(task['deduction_amount']))
                
                if amount == 0:
                    continue  # Нет премии
                
                # Создаём adjustment
                task_type = 'task_bonus' if amount > 0 else 'task_penalty'
                
                task_adjustment = PayrollAdjustment(
                    shift_id=shift.id,
                    employee_id=shift.user_id,
                    object_id=shift.object_id,
                    adjustment_type=task_type,
                    amount=amount,
                    description=f'Премия за задачу: {task["text"]}',
                    details={
                        'shift_id': shift.id,
                        'task_text': task["text"],
                        'task_index': task_idx,
                        'source': task['source']
                    },
                    created_by=shift.user_id,
                    is_applied=False
                )
                session.add(task_adjustment)
                created_count += 1
                
                print(f"  ✅ Смена {shift.id}: премия {amount}₽ за задачу '{task['text'][:40]}...'")
        
        await session.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ Создано премий: {created_count}")
        print(f"{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(create_missed_task_bonuses())

