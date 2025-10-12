"""Сервис для работы с начислениями и выплатами."""

from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload

from core.logging.logger import logger
from domain.entities.payroll_entry import PayrollEntry
from domain.entities.employee_payment import EmployeePayment
from domain.entities.contract import Contract
from domain.entities.shift import Shift
from domain.entities.user import User


class PayrollService:
    """Сервис для учета начислений и выплат."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ================== PAYROLL ENTRIES ==================
    
    async def create_payroll_entry(
        self,
        employee_id: int,
        contract_id: Optional[int],
        object_id: Optional[int],
        period_start: date,
        period_end: date,
        hours_worked: Decimal,
        hourly_rate: Decimal,
        created_by_id: int,
        notes: Optional[str] = None,
        calculation_details: Optional[Dict[str, Any]] = None
    ) -> PayrollEntry:
        """
        Создать запись начисления зарплаты.
        
        Args:
            employee_id: ID сотрудника
            contract_id: ID договора
            object_id: ID объекта
            period_start: Начало периода
            period_end: Конец периода
            hours_worked: Часов отработано
            hourly_rate: Часовая ставка
            created_by_id: Кто создал
            notes: Комментарий
            calculation_details: Детали расчета
            
        Returns:
            Созданная запись начисления
        """
        try:
            # Рассчитать gross_amount
            gross_amount = hours_worked * hourly_rate
            
            # Создать entry
            entry = PayrollEntry(
                employee_id=employee_id,
                contract_id=contract_id,
                object_id=object_id,
                period_start=period_start,
                period_end=period_end,
                hours_worked=hours_worked,
                hourly_rate=hourly_rate,
                gross_amount=gross_amount,
                total_deductions=Decimal(0),
                total_bonuses=Decimal(0),
                net_amount=gross_amount,
                calculation_details=calculation_details,
                notes=notes,
                created_by_id=created_by_id
            )
            
            self.db.add(entry)
            await self.db.commit()
            await self.db.refresh(entry)
            
            logger.info(
                f"Payroll entry created",
                entry_id=entry.id,
                employee_id=employee_id,
                period=f"{period_start} - {period_end}",
                net_amount=float(entry.net_amount)
            )
            
            return entry
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating payroll entry: {e}", employee_id=employee_id)
            raise
    
    async def get_payroll_entries_by_employee(
        self,
        employee_id: int,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[PayrollEntry]:
        """
        Получить начисления сотрудника за период.
        
        Args:
            employee_id: ID сотрудника
            period_start: Начало периода (опционально)
            period_end: Конец периода (опционально)
            limit: Лимит результатов
            offset: Смещение
            
        Returns:
            Список начислений
        """
        try:
            query = select(PayrollEntry).where(
                PayrollEntry.employee_id == employee_id
            )
            
            # Логика пересечения периодов:
            # Начисление пересекается с запрошенным периодом, если:
            # - начало начисления <= конец запрошенного периода
            # - конец начисления >= начало запрошенного периода
            if period_start and period_end:
                query = query.where(
                    PayrollEntry.period_start <= period_end,
                    PayrollEntry.period_end >= period_start
                )
            elif period_start:
                query = query.where(PayrollEntry.period_end >= period_start)
            elif period_end:
                query = query.where(PayrollEntry.period_start <= period_end)
            
            query = query.order_by(PayrollEntry.period_end.desc())
            query = query.limit(limit).offset(offset)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting payroll entries: {e}", employee_id=employee_id)
            return []
    
    async def get_payroll_entry_by_id(self, entry_id: int) -> Optional[PayrollEntry]:
        """Получить начисление по ID с загрузкой связей."""
        query = select(PayrollEntry).where(PayrollEntry.id == entry_id).options(
            selectinload(PayrollEntry.employee)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def recalculate_payroll_entry(self, entry_id: int) -> PayrollEntry:
        """
        Пересчитать итоговую сумму начисления после изменения удержаний/доплат.
        
        Args:
            entry_id: ID записи начисления
            
        Returns:
            Обновленная запись
        """
        try:
            entry = await self.get_payroll_entry_by_id(entry_id)
            if not entry:
                raise ValueError(f"Payroll entry {entry_id} not found")
            
            # Пересчитать суммы удержаний и доплат
            total_deductions = sum(d.amount for d in entry.deductions)
            total_bonuses = sum(b.amount for b in entry.bonuses)
            
            entry.total_deductions = Decimal(total_deductions)
            entry.total_bonuses = Decimal(total_bonuses)
            entry.calculate_net_amount()
            
            await self.db.commit()
            await self.db.refresh(entry)
            
            logger.info(
                f"Payroll entry recalculated",
                entry_id=entry_id,
                total_deductions=float(entry.total_deductions),
                total_bonuses=float(entry.total_bonuses),
                net_amount=float(entry.net_amount)
            )
            
            return entry
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error recalculating payroll entry: {e}", entry_id=entry_id)
            raise
    
    # ================== DEDUCTIONS & BONUSES ==================
    # Phase 4A: Методы add_deduction и add_bonus удалены
    # Используйте PayrollAdjustmentService из shared/services/payroll_adjustment_service.py
    
    # ================== PAYMENTS ==================
    
    async def create_payment(
        self,
        payroll_entry_id: int,
        amount: Decimal,
        payment_date: date,
        payment_method: str,
        created_by_id: int,
        payment_details: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> EmployeePayment:
        """
        Создать выплату сотруднику.
        
        Args:
            payroll_entry_id: ID начисления
            amount: Сумма
            payment_date: Дата выплаты
            payment_method: Способ выплаты
            created_by_id: Кто создал
            payment_details: Детали выплаты
            notes: Комментарий
            
        Returns:
            Созданная выплата
        """
        try:
            # Получить entry для employee_id
            entry = await self.get_payroll_entry_by_id(payroll_entry_id)
            if not entry:
                raise ValueError(f"Payroll entry {payroll_entry_id} not found")
            
            payment = EmployeePayment(
                payroll_entry_id=payroll_entry_id,
                employee_id=entry.employee_id,
                amount=amount,
                payment_date=payment_date,
                payment_method=payment_method,
                status='pending',
                payment_details=payment_details,
                notes=notes,
                created_by_id=created_by_id
            )
            
            self.db.add(payment)
            await self.db.commit()
            await self.db.refresh(payment)
            
            logger.info(
                f"Payment created",
                payment_id=payment.id,
                payroll_entry_id=payroll_entry_id,
                amount=float(amount),
                status=payment.status
            )
            
            return payment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating payment: {e}", payroll_entry_id=payroll_entry_id)
            raise
    
    async def mark_payment_completed(
        self,
        payment_id: int,
        confirmation_code: Optional[str] = None
    ) -> EmployeePayment:
        """
        Отметить выплату как завершенную.
        
        Args:
            payment_id: ID выплаты
            confirmation_code: Код подтверждения
            
        Returns:
            Обновленная выплата
        """
        try:
            query = select(EmployeePayment).where(EmployeePayment.id == payment_id)
            result = await self.db.execute(query)
            payment = result.scalar_one_or_none()
            
            if not payment:
                raise ValueError(f"Payment {payment_id} not found")
            
            payment.mark_completed()
            if confirmation_code:
                payment.confirmation_code = confirmation_code
            
            await self.db.commit()
            await self.db.refresh(payment)
            
            logger.info(
                f"Payment marked completed",
                payment_id=payment_id,
                confirmation_code=confirmation_code
            )
            
            return payment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error marking payment completed: {e}", payment_id=payment_id)
            raise
    
    # ================== REPORTS ==================
    
    async def get_employee_payroll_summary(
        self,
        employee_id: int,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """
        Получить сводку по начислениям сотрудника за период.
        
        Args:
            employee_id: ID сотрудника
            period_start: Начало периода
            period_end: Конец периода
            
        Returns:
            Сводка в виде словаря
        """
        try:
            entries = await self.get_payroll_entries_by_employee(
                employee_id,
                period_start,
                period_end
            )
            
            total_hours = sum(e.hours_worked for e in entries)
            total_gross = sum(e.gross_amount for e in entries)
            total_deductions = sum(e.total_deductions for e in entries)
            total_bonuses = sum(e.total_bonuses for e in entries)
            total_net = sum(e.net_amount for e in entries)
            
            # Статистика по выплатам
            all_payments = []
            for entry in entries:
                query = select(EmployeePayment).where(
                    EmployeePayment.payroll_entry_id == entry.id
                )
                result = await self.db.execute(query)
                all_payments.extend(result.scalars().all())
            
            total_paid = sum(p.amount for p in all_payments if p.status == 'completed')
            total_pending = sum(p.amount for p in all_payments if p.status == 'pending')
            
            return {
                "employee_id": employee_id,
                "period_start": period_start.isoformat(),
                "period_end": period_end.isoformat(),
                "total_hours": float(total_hours),
                "total_gross": float(total_gross),
                "total_deductions": float(total_deductions),
                "total_bonuses": float(total_bonuses),
                "total_net": float(total_net),
                "total_paid": float(total_paid),
                "total_pending": float(total_pending),
                "entries_count": len(entries),
                "payments_count": len(all_payments)
            }
            
        except Exception as e:
            logger.error(f"Error getting payroll summary: {e}", employee_id=employee_id)
            return {}

