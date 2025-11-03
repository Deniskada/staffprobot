#!/usr/bin/env python3
"""
Скрипт для тестирования логики штрафов за опоздание на вечернюю смену.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database.session import get_async_session
from sqlalchemy import select as sql_select, and_, func
from sqlalchemy.orm import selectinload
from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.time_slot import TimeSlot
from domain.entities.payroll_adjustment import PayrollAdjustment
from shared.services.rules_engine import RulesEngine


async def test_penalty_logic():
    """Тестирование логики штрафов."""
    
    async with get_async_session() as session:
        print("=" * 80)
        print("ТЕСТИРОВАНИЕ ЛОГИКИ ШТРАФОВ ЗА ОПОЗДАНИЕ НА ВЕЧЕРНЮЮ СМЕНУ")
        print("=" * 80)
        
        # Получаем правило
        rules_engine = RulesEngine(session)
        # Проверяем правило для системного уровня (owner_id = None)
        from domain.entities.rule import Rule
        rule_query = sql_select(Rule).where(
            Rule.code == 'penalty_non_standard_shift',
            Rule.is_active == True
        )
        rule_result = await session.execute(rule_query)
        rule = rule_result.scalar_one_or_none()
        
        if rule:
            print(f"✅ Правило 'penalty_non_standard_shift' найдено и активно")
            import json
            cond = json.loads(rule.condition_json)
            act = json.loads(rule.action_json)
            print(f"   Condition: {cond}")
            print(f"   Action: {act}")
            
            # Проверяем правило для конкретного владельца (если есть)
            test_owner_id = 1  # Первый владелец
            rule_actions = await rules_engine.evaluate(test_owner_id, 'late', {
                'planned_start_matches_opening_time': False,
                'object_id': 1,
            })
            
            rule_found = False
            for action in rule_actions:
                if action.get('code') == 'penalty_non_standard_shift':
                    rule_found = True
                    break
        else:
            rule_found = False
            print("❌ Правило 'penalty_non_standard_shift' не найдено")
        
        rule_found = False
        for action in rule_actions:
            if action.get('code') == 'penalty_non_standard_shift':
                rule_found = True
                print(f"✅ Правило 'penalty_non_standard_shift' найдено и активно")
                print(f"   Action: {action}")
                break
        
        if not rule_found:
            print("❌ Правило 'penalty_non_standard_shift' не найдено или неактивно")
        
        print("\n" + "-" * 80)
        
        # Тестовый сценарий 1: Смена в opening_time объекта
        print("\n📋 ТЕСТОВЫЙ СЦЕНАРИЙ 1: Смена в opening_time объекта")
        print("-" * 80)
        
        query1 = (
            sql_select(Shift)
            .options(
                selectinload(Shift.object),
                selectinload(Shift.time_slot)
            )
            .join(Object)
            .where(
                and_(
                    Shift.planned_start.isnot(None),
                    Shift.actual_start.isnot(None),
                    Shift.status == 'completed',
                    Shift.actual_start > Shift.planned_start
                )
            )
            .limit(5)
        )
        
        result1 = await session.execute(query1)
        shifts1 = result1.scalars().all()
        
        for shift in shifts1:
            planned_time = shift.planned_start.time()
            opening_time = shift.object.opening_time
            matches = planned_time == opening_time
            
            print(f"\nСмена {shift.id}:")
            print(f"  Объект: {shift.object.name} (opening_time={opening_time})")
            print(f"  planned_start время: {planned_time}")
            print(f"  Совпадение: {'✅ ДА' if matches else '❌ НЕТ'}")
            
            if matches:
                if shift.is_planned and shift.time_slot:
                    print(f"  ✅ Тип: Стандартная смена → используется флаг тайм-слота")
                    print(f"     penalize_late_start={shift.time_slot.penalize_late_start}")
                else:
                    print(f"  ⚠️  Смена не имеет тайм-слота или не запланирована")
            else:
                print(f"  ✅ Тип: Нестандартная смена → проверяется автоправило")
                if shift.is_planned and shift.time_slot:
                    if shift.time_slot.penalize_late_start:
                        print(f"     ⚠️  В тайм-слоте явно указан штраф → всегда штрафуется")
                    else:
                        print(f"     Правило {'✅ включено' if rule_found else '❌ выключено'} → {'штрафуется' if rule_found else 'не штрафуется'}")
        
        print("\n" + "-" * 80)
        
        # Тестовый сценарий 2: Смена НЕ в opening_time объекта
        print("\n📋 ТЕСТОВЫЙ СЦЕНАРИЙ 2: Смена НЕ в opening_time объекта")
        print("-" * 80)
        
        # Проверяем корректировки
        adjustments_query = (
            sql_select(PayrollAdjustment)
            .where(PayrollAdjustment.adjustment_type == 'late_start')
            .order_by(PayrollAdjustment.id.desc())
            .limit(10)
        )
        
        result2 = await session.execute(adjustments_query)
        adjustments = result2.scalars().all()
        
        if adjustments:
            print(f"\n✅ Найдено {len(adjustments)} корректировок за опоздание:")
            for adj in adjustments:
                print(f"  ID={adj.id}, Shift={adj.shift_id}, Amount={adj.amount}, Description={adj.description}")
                if adj.details:
                    print(f"    Details: {adj.details}")
        else:
            print("\n⚠️  Корректировки за опоздание не найдены")
        
        print("\n" + "=" * 80)
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_penalty_logic())

