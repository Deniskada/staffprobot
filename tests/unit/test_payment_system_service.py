"""Unit-тесты для PaymentSystemService."""

import pytest
from apps.web.services.payment_system_service import PaymentSystemService


class TestPaymentSystemService:
    """Тесты для PaymentSystemService."""
    
    @pytest.mark.asyncio
    async def test_get_active_systems(self, db_session):
        """Тест получения активных систем оплаты."""
        service = PaymentSystemService(db_session)
        
        systems = await service.get_active_systems()
        
        assert len(systems) == 3, "Должно быть 3 активные системы"
        assert systems[0].code == 'simple_hourly'
        assert systems[1].code == 'salary'
        assert systems[2].code == 'hourly_bonus'
    
    @pytest.mark.asyncio
    async def test_get_system_by_code(self, db_session):
        """Тест получения системы по коду."""
        service = PaymentSystemService(db_session)
        
        system = await service.get_system_by_code('simple_hourly')
        
        assert system is not None
        assert system.name == 'Простая повременная'
        assert system.calculation_type == 'hourly'
    
    @pytest.mark.asyncio
    async def test_get_default_system(self, db_session):
        """Тест получения системы по умолчанию."""
        service = PaymentSystemService(db_session)
        
        system = await service.get_default_system()
        
        assert system is not None
        assert system.code == 'simple_hourly'
    
    def test_calculate_payment_simple(self):
        """Тест простого расчета оплаты."""
        service = PaymentSystemService(None)  # session не нужна для расчета
        
        payment = service.calculate_payment(
            system_code='simple_hourly',
            hours=8.0,
            base_rate=500.0
        )
        
        assert payment == 4000.0, "8 часов * 500₽ = 4000₽"
    
    def test_calculate_payment_with_bonuses(self):
        """Тест расчета с доплатами."""
        service = PaymentSystemService(None)
        
        payment = service.calculate_payment(
            system_code='hourly_bonus',
            hours=8.0,
            base_rate=500.0,
            bonuses=[
                {'amount': 1000.0, 'description': 'Премия за качество'},
                {'amount': 500.0, 'description': 'Доплата за переработку'}
            ]
        )
        
        assert payment == 5500.0, "4000₽ + 1000₽ + 500₽ = 5500₽"
    
    def test_calculate_payment_with_deductions(self):
        """Тест расчета с удержаниями."""
        service = PaymentSystemService(None)
        
        payment = service.calculate_payment(
            system_code='simple_hourly',
            hours=8.0,
            base_rate=500.0,
            deductions=[
                {'amount': 200.0, 'description': 'Опоздание'},
                {'amount': 300.0, 'description': 'Невыполненная задача'}
            ]
        )
        
        assert payment == 3500.0, "4000₽ - 200₽ - 300₽ = 3500₽"
    
    def test_calculate_payment_complex(self):
        """Тест сложного расчета с доплатами и удержаниями."""
        service = PaymentSystemService(None)
        
        payment = service.calculate_payment(
            system_code='hourly_bonus',
            hours=10.5,
            base_rate=350.0,
            bonuses=[{'amount': 1000.0, 'description': 'Премия'}],
            deductions=[{'amount': 500.0, 'description': 'Удержание'}]
        )
        
        # 10.5 * 350 = 3675
        # 3675 + 1000 - 500 = 4175
        assert payment == 4175.0

