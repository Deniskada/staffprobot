"""Юнит-тесты для Rules Engine."""

import pytest
from decimal import Decimal
from shared.services.rules_engine import RulesEngine, RuleContext
from domain.entities.rule import Rule


@pytest.fixture
def rules_engine():
    """Создать экземпляр Rules Engine для тестов."""
    return RulesEngine()


@pytest.fixture
def sample_late_rules():
    """Примеры правил для опозданий."""
    return [
        Rule(
            id=1,
            owner_id=1,
            code="late_15min",
            name="Опоздание до 15 минут",
            scope="late",
            priority=1,
            condition_json={"max_minutes": 15},
            action_json={"penalty_per_minute": 10},
            is_active=True
        ),
        Rule(
            id=2,
            owner_id=1,
            code="late_30min",
            name="Опоздание до 30 минут",
            scope="late",
            priority=2,
            condition_json={"max_minutes": 30},
            action_json={"penalty_per_minute": 20},
            is_active=True
        )
    ]


def test_rules_engine_evaluates_late_penalty(rules_engine, sample_late_rules):
    """Тест расчета штрафа за опоздание."""
    context = RuleContext(
        scope="late",
        late_minutes=10,
        hourly_rate=Decimal("500")
    )
    
    result = rules_engine.evaluate(sample_late_rules, context)
    
    assert result is not None
    assert result["rule_code"] == "late_15min"
    assert result["penalty_amount"] == Decimal("100")  # 10 минут * 10₽


def test_rules_engine_selects_by_priority(rules_engine, sample_late_rules):
    """Тест выбора правила с наивысшим приоритетом."""
    context = RuleContext(
        scope="late",
        late_minutes=20,  # Подходит оба правила
        hourly_rate=Decimal("500")
    )
    
    result = rules_engine.evaluate(sample_late_rules, context)
    
    # Должно выбраться правило с priority=1 (самый высокий)
    assert result["rule_code"] == "late_15min"


def test_rules_engine_inactive_rules_skipped(rules_engine):
    """Тест пропуска неактивных правил."""
    rules = [
        Rule(
            id=1,
            owner_id=1,
            code="late_inactive",
            scope="late",
            priority=1,
            condition_json={"max_minutes": 60},
            action_json={"penalty_per_minute": 50},
            is_active=False  # Неактивное!
        )
    ]
    
    context = RuleContext(scope="late", late_minutes=30)
    result = rules_engine.evaluate(rules, context)
    
    assert result is None  # Нет подходящих активных правил


def test_rules_engine_fallback_to_legacy():
    """Тест fallback на legacy значения."""
    engine = RulesEngine()
    
    context = RuleContext(
        scope="late",
        late_minutes=10,
        # Legacy значения:
        legacy_late_penalty_per_minute=Decimal("15"),
        legacy_late_threshold_minutes=5
    )
    
    # Пустой список правил → fallback
    result = engine.evaluate([], context)
    
    assert result is not None
    assert result["penalty_amount"] == Decimal("150")  # 10 * 15₽
    assert result["rule_code"] == "legacy_fallback"

