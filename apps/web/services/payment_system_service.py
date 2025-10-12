"""Сервис для работы с системами оплаты труда."""

from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.payment_system import PaymentSystem
from core.logging.logger import logger


class PaymentSystemService:
    """Сервис для работы с системами оплаты труда."""
    
    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.
        
        Args:
            session: Асинхронная сессия БД
        """
        self.session = session
    
    async def get_all_systems(self) -> List[PaymentSystem]:
        """
        Получить все системы оплаты.
        
        Returns:
            Список всех систем оплаты
        """
        query = select(PaymentSystem).order_by(PaymentSystem.display_order)
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_active_systems(self) -> List[PaymentSystem]:
        """
        Получить активные системы оплаты.
        
        Returns:
            Список активных систем оплаты
        """
        query = select(PaymentSystem).where(
            PaymentSystem.is_active == True
        ).order_by(PaymentSystem.display_order)
        
        result = await self.session.execute(query)
        systems = result.scalars().all()
        
        logger.info(f"Found {len(systems)} active payment systems")
        return systems
    
    async def get_system_by_id(self, system_id: int) -> Optional[PaymentSystem]:
        """
        Получить систему оплаты по ID.
        
        Args:
            system_id: ID системы оплаты
            
        Returns:
            Система оплаты или None
        """
        result = await self.session.get(PaymentSystem, system_id)
        return result
    
    async def get_system_by_code(self, code: str) -> Optional[PaymentSystem]:
        """
        Получить систему оплаты по коду.
        
        Args:
            code: Код системы (simple_hourly, salary, hourly_bonus)
            
        Returns:
            Система оплаты или None
        """
        query = select(PaymentSystem).where(PaymentSystem.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    def calculate_payment(
        self,
        system_code: str,
        hours: float,
        base_rate: float,
        bonuses: Optional[List[Dict]] = None,
        deductions: Optional[List[Dict]] = None
    ) -> float:
        """
        Рассчитать выплату по системе оплаты.
        
        Это заглушка для будущей логики. На данном этапе поддерживается
        только простая повременная оплата.
        
        Args:
            system_code: Код системы оплаты
            hours: Количество часов
            base_rate: Базовая ставка
            bonuses: Список доплат [{amount: float, description: str}]
            deductions: Список удержаний [{amount: float, description: str}]
            
        Returns:
            Сумма к выплате
        """
        # Базовая оплата
        base_amount = hours * base_rate
        
        # Доплаты
        bonus_amount = sum([b.get('amount', 0) for b in (bonuses or [])])
        
        # Удержания
        deduction_amount = sum([d.get('amount', 0) for d in (deductions or [])])
        
        # Итого
        total = base_amount + bonus_amount - deduction_amount
        
        logger.info(
            f"Payment calculated for {system_code}: "
            f"base={base_amount}, bonuses={bonus_amount}, "
            f"deductions={deduction_amount}, total={total}"
        )
        
        return round(total, 2)
    
    async def get_default_system(self) -> Optional[PaymentSystem]:
        """
        Получить систему оплаты по умолчанию (simple_hourly).
        
        Returns:
            Система оплаты "Простая повременная"
        """
        return await self.get_system_by_code('simple_hourly')

