"""Unit-тесты для логики определения эффективной ставки договора."""

import pytest
from domain.entities.contract import Contract
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON, Numeric


class TestContractEffectiveRate:
    """Тесты для метода Contract.get_effective_hourly_rate()."""
    
    def test_contract_rate_priority_when_flag_enabled(self):
        """Ставка договора имеет приоритет когда use_contract_rate=True."""
        contract = Contract()
        contract.hourly_rate = 300.0
        contract.use_contract_rate = True
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=250.0,
            object_rate=200.0
        )
        
        assert rate == 300.0, "Должна использоваться ставка договора"
    
    def test_timeslot_rate_when_contract_flag_disabled(self):
        """Ставка тайм-слота используется когда use_contract_rate=False."""
        contract = Contract()
        contract.hourly_rate = 300.0
        contract.use_contract_rate = False
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=250.0,
            object_rate=200.0
        )
        
        assert rate == 250.0, "Должна использоваться ставка тайм-слота"
    
    def test_object_rate_fallback(self):
        """Ставка объекта используется как fallback."""
        contract = Contract()
        contract.hourly_rate = None
        contract.use_contract_rate = False
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=None,
            object_rate=200.0
        )
        
        assert rate == 200.0, "Должна использоваться ставка объекта"
    
    def test_contract_rate_fallback_when_flag_disabled(self):
        """Ставка договора используется как последний fallback."""
        contract = Contract()
        contract.hourly_rate = 300.0
        contract.use_contract_rate = False
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=None,
            object_rate=None
        )
        
        assert rate == 300.0, "Должна использоваться ставка договора как fallback"
    
    def test_none_when_no_rates(self):
        """Возвращается None когда нет ни одной ставки."""
        contract = Contract()
        contract.hourly_rate = None
        contract.use_contract_rate = False
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=None,
            object_rate=None
        )
        
        assert rate is None, "Должен вернуться None"
    
    def test_contract_rate_ignored_when_flag_enabled_but_rate_is_none(self):
        """Флаг игнорируется если ставка договора None."""
        contract = Contract()
        contract.hourly_rate = None
        contract.use_contract_rate = True
        
        rate = contract.get_effective_hourly_rate(
            timeslot_rate=250.0,
            object_rate=200.0
        )
        
        assert rate == 250.0, "Должна использоваться ставка тайм-слота, так как ставка договора None"
    
    def test_float_conversion(self):
        """Numeric значения корректно преобразуются в float."""
        from decimal import Decimal
        
        contract = Contract()
        contract.hourly_rate = Decimal('350.50')
        contract.use_contract_rate = True
        
        rate = contract.get_effective_hourly_rate()
        
        assert isinstance(rate, float), "Должен вернуться float"
        assert rate == 350.50, "Значение должно сохраниться"
    
    def test_priority_order(self):
        """Проверка полного порядка приоритетов."""
        # Приоритет 1: contract (when use_contract_rate=True)
        contract = Contract()
        contract.hourly_rate = 400.0
        contract.use_contract_rate = True
        assert contract.get_effective_hourly_rate(300.0, 200.0) == 400.0
        
        # Приоритет 2: timeslot
        contract.use_contract_rate = False
        assert contract.get_effective_hourly_rate(300.0, 200.0) == 300.0
        
        # Приоритет 3: object
        assert contract.get_effective_hourly_rate(None, 200.0) == 200.0
        
        # Приоритет 4: contract (fallback)
        assert contract.get_effective_hourly_rate(None, None) == 400.0

