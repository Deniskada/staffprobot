"""Интеграционные тесты для начислений при увольнении."""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from core.celery.tasks.payroll_tasks import (
    create_payroll_entries_by_schedule,
    create_final_settlements_by_termination_date,
)


class TestPayrollWithTerminatedContracts:
    """Тесты начислений для terminated контрактов."""
    
    @pytest.mark.asyncio
    async def test_schedule_payroll_includes_terminated_with_schedule_policy(self):
        """
        Проверка: выплата по вторникам включает terminated контракты с policy='schedule'.
        """
        # Имитируем вторник
        test_tuesday = date(2025, 10, 21)
        
        with patch('core.celery.tasks.payroll_tasks.date') as mock_date:
            mock_date.today.return_value = test_tuesday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            
            result = create_payroll_entries_by_schedule()
            
            assert result['success'] is True
            assert result['entries_created'] > 0
            assert result['adjustments_applied'] > 0
    
    @pytest.mark.asyncio
    async def test_final_settlement_on_termination_date(self):
        """
        Проверка: финальный расчёт создаётся в дату увольнения для policy='termination_date'.
        """
        # Для этого теста потребуется создать тестовый контракт с termination_date=сегодня
        # и settlement_policy='termination_date', а также adjustments для него
        # TODO: реализовать с фикстурами
        pass
    
    @pytest.mark.asyncio
    async def test_all_owner_objects_included_in_payroll(self):
        """
        Проверка: начисления захватывают ВСЕ активные объекты владельца.
        """
        test_tuesday = date(2025, 10, 21)
        
        with patch('core.celery.tasks.payroll_tasks.date') as mock_date:
            mock_date.today.return_value = test_tuesday
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            
            result = create_payroll_entries_by_schedule()
            
            # Должны быть созданы начисления для всех объектов владельца
            assert result['success'] is True
            assert result['entries_created'] >= 20  # Минимум для 8 объектов владельца


class TestContractTerminationLogic:
    """Тесты логики расторжения договора."""
    
    @pytest.mark.asyncio
    async def test_planned_shifts_cancelled_after_termination_date(self):
        """
        Проверка: плановые смены отменяются после даты увольнения.
        """
        # TODO: создать тестовый контракт и плановые смены
        # Расторгнуть с termination_date
        # Проверить, что смены после даты отменены
        pass
    
    @pytest.mark.asyncio
    async def test_termination_date_and_policy_saved(self):
        """
        Проверка: termination_date и settlement_policy сохраняются при расторжении.
        """
        # TODO: расторгнуть тестовый контракт с параметрами
        # Проверить, что поля сохранены в БД
        pass

