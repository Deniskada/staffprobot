"""Сервис для работы с корректировками начислений."""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.shift import Shift
from domain.entities.user import User
from domain.entities.object import Object
from core.logging.logger import logger


class PayrollAdjustmentService:
    """Сервис для работы с корректировками начислений."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_shift_base_adjustment(
        self,
        shift: Shift,
        employee_id: int,
        object_id: int,
        created_by: int,
        description: Optional[str] = None
    ) -> PayrollAdjustment:
        """
        Создать базовую оплату за смену.
        
        Args:
            shift: Смена
            employee_id: ID сотрудника
            object_id: ID объекта
            created_by: ID пользователя, создавшего запись
            description: Дополнительное описание
            
        Returns:
            PayrollAdjustment: Созданная корректировка
        """
        amount = shift.total_payment or Decimal('0.00')
        
        adjustment = PayrollAdjustment(
            shift_id=shift.id,
            employee_id=employee_id,
            object_id=object_id,
            adjustment_type='shift_base',
            amount=amount,
            description=description or f'Базовая оплата за смену #{shift.id}',
            details={
                'shift_id': shift.id,
                'hours': float(shift.total_hours or 0),
                'hourly_rate': float(shift.hourly_rate or 0),
                'start_time': shift.start_time.isoformat() if shift.start_time else None,
                'end_time': shift.end_time.isoformat() if shift.end_time else None
            },
            created_by=created_by,
            is_applied=False
        )
        
        self.session.add(adjustment)
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            "Базовая оплата за смену создана",
            adjustment_id=adjustment.id,
            shift_id=shift.id,
            employee_id=employee_id,
            amount=float(amount)
        )
        
        return adjustment
    
    async def create_late_start_adjustment(
        self,
        shift: Shift,
        late_minutes: int,
        penalty_amount: Decimal,
        created_by: int,
        description: Optional[str] = None
    ) -> PayrollAdjustment:
        """
        Создать штраф за опоздание.
        
        Args:
            shift: Смена
            late_minutes: Количество минут опоздания
            penalty_amount: Сумма штрафа (положительное число, будет сделано отрицательным)
            created_by: ID пользователя, создавшего запись
            description: Дополнительное описание
            
        Returns:
            PayrollAdjustment: Созданная корректировка
        """
        # Штраф - это отрицательная сумма
        amount = -abs(penalty_amount)
        
        adjustment = PayrollAdjustment(
            shift_id=shift.id,
            employee_id=shift.user_id,
            object_id=shift.object_id,
            adjustment_type='late_start',
            amount=amount,
            description=description or f'Штраф за опоздание на {late_minutes} мин',
            details={
                'shift_id': shift.id,
                'late_minutes': late_minutes,
                'penalty_per_minute': float(penalty_amount / late_minutes) if late_minutes > 0 else 0
            },
            created_by=created_by,
            is_applied=False
        )
        
        self.session.add(adjustment)
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            "Штраф за опоздание создан",
            adjustment_id=adjustment.id,
            shift_id=shift.id,
            late_minutes=late_minutes,
            amount=float(amount)
        )
        
        return adjustment
    
    async def create_task_adjustment(
        self,
        shift: Shift,
        task_name: str,
        amount: Decimal,
        is_bonus: bool,
        created_by: int,
        description: Optional[str] = None
    ) -> PayrollAdjustment:
        """
        Создать премию или штраф за задачу.
        
        Args:
            shift: Смена
            task_name: Название задачи
            amount: Сумма (для премии - положительная, для штрафа - будет отрицательной)
            is_bonus: True для премии, False для штрафа
            created_by: ID пользователя, создавшего запись
            description: Дополнительное описание
            
        Returns:
            PayrollAdjustment: Созданная корректировка
        """
        adjustment_type = 'task_bonus' if is_bonus else 'task_penalty'
        
        # Для штрафа делаем сумму отрицательной
        final_amount = amount if is_bonus else -abs(amount)
        
        default_desc = f"{'Премия' if is_bonus else 'Штраф'} за задачу: {task_name}"
        
        adjustment = PayrollAdjustment(
            shift_id=shift.id,
            employee_id=shift.user_id,
            object_id=shift.object_id,
            adjustment_type=adjustment_type,
            amount=final_amount,
            description=description or default_desc,
            details={
                'shift_id': shift.id,
                'task_name': task_name
            },
            created_by=created_by,
            is_applied=False
        )
        
        self.session.add(adjustment)
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            f"{'Премия' if is_bonus else 'Штраф'} за задачу создан",
            adjustment_id=adjustment.id,
            shift_id=shift.id,
            task_name=task_name,
            amount=float(final_amount)
        )
        
        return adjustment
    
    async def create_manual_adjustment(
        self,
        employee_id: int,
        amount: Decimal,
        adjustment_type: str,  # 'manual_bonus' или 'manual_deduction'
        description: str,
        created_by: int,
        object_id: Optional[int] = None,
        shift_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        adjustment_date: Optional[date] = None
    ) -> PayrollAdjustment:
        """
        Создать ручную корректировку (премию или штраф).
        
        Args:
            employee_id: ID сотрудника
            amount: Сумма (для премии - положительная, для штрафа - отрицательная)
            adjustment_type: Тип корректировки ('manual_bonus' или 'manual_deduction')
            description: Описание корректировки
            created_by: ID пользователя, создавшего запись
            object_id: ID объекта (опционально)
            shift_id: ID смены (опционально)
            details: Дополнительные данные (опционально)
            adjustment_date: Дата начисления (опционально, по умолчанию текущая дата)
            
        Returns:
            PayrollAdjustment: Созданная корректировка
        """
        if adjustment_type not in ['manual_bonus', 'manual_deduction']:
            raise ValueError(f"Неверный тип корректировки: {adjustment_type}")
        
        # Для manual_deduction делаем сумму отрицательной
        if adjustment_type == 'manual_deduction':
            amount = -abs(amount)
        
        adjustment = PayrollAdjustment(
            shift_id=shift_id,
            employee_id=employee_id,
            object_id=object_id,
            adjustment_type=adjustment_type,
            amount=amount,
            description=description,
            details=details or {},
            created_by=created_by,
            is_applied=False
        )
        
        # Устанавливаем дату начисления если указана
        if adjustment_date:
            from datetime import datetime, timezone
            # Создаём timezone-aware datetime в UTC
            naive_dt = datetime.combine(adjustment_date, datetime.min.time())
            adjustment.created_at = naive_dt.replace(tzinfo=timezone.utc)
        
        self.session.add(adjustment)
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            "Ручная корректировка создана",
            adjustment_id=adjustment.id,
            employee_id=employee_id,
            type=adjustment_type,
            amount=float(amount),
            created_by=created_by
        )
        
        return adjustment
    
    async def get_adjustments_for_period(
        self,
        employee_id: int,
        start_date: date,
        end_date: date,
        adjustment_type: Optional[str] = None,
        object_id: Optional[int] = None,
        is_applied: Optional[bool] = None
    ) -> List[PayrollAdjustment]:
        """
        Получить корректировки за период.
        
        Args:
            employee_id: ID сотрудника
            start_date: Дата начала периода
            end_date: Дата окончания периода
            adjustment_type: Фильтр по типу корректировки (опционально)
            object_id: Фильтр по объекту (опционально)
            is_applied: Фильтр по статусу применения (опционально)
            
        Returns:
            List[PayrollAdjustment]: Список корректировок
        """
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.employee_id == employee_id,
            func.date(PayrollAdjustment.created_at) >= start_date,
            func.date(PayrollAdjustment.created_at) <= end_date
        ).options(
            selectinload(PayrollAdjustment.shift),
            selectinload(PayrollAdjustment.object),
            selectinload(PayrollAdjustment.creator)
        ).order_by(desc(PayrollAdjustment.created_at))
        
        if adjustment_type:
            query = query.where(PayrollAdjustment.adjustment_type == adjustment_type)
        
        if object_id:
            query = query.where(PayrollAdjustment.object_id == object_id)
        
        if is_applied is not None:
            query = query.where(PayrollAdjustment.is_applied == is_applied)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_unapplied_adjustments(
        self,
        employee_id: int,
        period_start: date,
        period_end: date
    ) -> List[PayrollAdjustment]:
        """
        Получить неприменённые корректировки за период (для Celery).
        
        Args:
            employee_id: ID сотрудника
            period_start: Дата начала периода выплаты
            period_end: Дата окончания периода выплаты
            
        Returns:
            List[PayrollAdjustment]: Список неприменённых корректировок
        """
        # Для корректировок, связанных со сменами (shift_base/late_start/task_*),
        # используем дату завершения смены. Для прочих (manual_*), используем created_at.
        from sqlalchemy import or_, and_
        from domain.entities.shift import Shift

        query = (
            select(PayrollAdjustment)
            .outerjoin(Shift, PayrollAdjustment.shift_id == Shift.id)
            .where(
                PayrollAdjustment.employee_id == employee_id,
                PayrollAdjustment.is_applied == False,
                or_(
                    # Если есть привязка к смене — фильтруем по дате смены
                    and_(
                        PayrollAdjustment.shift_id.isnot(None),
                        func.date(Shift.end_time) >= period_start,
                        func.date(Shift.end_time) <= period_end,
                    ),
                    # Если нет привязки к смене — фильтруем по дате создания корректировки
                    and_(
                        PayrollAdjustment.shift_id.is_(None),
                        func.date(PayrollAdjustment.created_at) >= period_start,
                        func.date(PayrollAdjustment.created_at) <= period_end,
                    ),
                ),
            )
            .options(
                selectinload(PayrollAdjustment.shift),
                selectinload(PayrollAdjustment.object),
            )
            .order_by(PayrollAdjustment.created_at)
        )
        
        # DEBUG: логирование SQL и параметров
        from core.logging.logger import logger
        compiled = query.compile(compile_kwargs={"literal_binds": True})
        logger.debug(
            f"get_unapplied_adjustments SQL",
            employee_id=employee_id,
            period_start=period_start,
            period_end=period_end,
            sql=str(compiled)[:500]
        )
        
        result = await self.session.execute(query)
        adjustments_list = list(result.scalars().all())
        
        logger.debug(
            f"get_unapplied_adjustments result",
            employee_id=employee_id,
            found_count=len(adjustments_list),
            adjustment_ids=[a.id for a in adjustments_list[:5]] if adjustments_list else []
        )
        
        return adjustments_list
    
    async def get_unapplied_adjustments_until(
        self,
        employee_id: int,
        until_date: date
    ) -> List[PayrollAdjustment]:
        """
        Получить все неприменённые корректировки до указанной даты включительно.
        Используется для финального расчёта при увольнении.
        
        Args:
            employee_id: ID сотрудника
            until_date: Дата увольнения (включительно)
            
        Returns:
            List[PayrollAdjustment]: Список неприменённых корректировок
        """
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.employee_id == employee_id,
            PayrollAdjustment.is_applied == False,
            func.date(PayrollAdjustment.created_at) <= until_date
        ).options(
            selectinload(PayrollAdjustment.shift),
            selectinload(PayrollAdjustment.object)
        ).order_by(PayrollAdjustment.created_at)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_adjustment(
        self,
        adjustment_id: int,
        updates: Dict[str, Any],
        updated_by: int
    ) -> PayrollAdjustment:
        """
        Обновить корректировку с логированием истории изменений.
        
        Args:
            adjustment_id: ID корректировки
            updates: Словарь с обновлениями
            updated_by: ID пользователя, сделавшего изменения
            
        Returns:
            PayrollAdjustment: Обновленная корректировка
            
        Raises:
            ValueError: Если корректировка не найдена
        """
        query = select(PayrollAdjustment).where(PayrollAdjustment.id == adjustment_id)
        result = await self.session.execute(query)
        adjustment = result.scalar_one_or_none()
        
        if not adjustment:
            raise ValueError(f"Корректировка с ID {adjustment_id} не найдена")
        
        # Логирование изменений
        edit_history = adjustment.edit_history or []
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        timestamp = now_utc.isoformat()
        
        for field, new_value in updates.items():
            if field in ['amount', 'description', 'adjustment_type']:
                old_value = getattr(adjustment, field)
                
                if old_value != new_value:
                    edit_history.append({
                        'timestamp': timestamp,
                        'user_id': updated_by,
                        'field': field,
                        'old_value': str(old_value) if old_value is not None else None,
                        'new_value': str(new_value) if new_value is not None else None
                    })
                    
                    setattr(adjustment, field, new_value)
        
        adjustment.edit_history = edit_history
        adjustment.updated_by = updated_by
        adjustment.updated_at = now_utc
        
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            "Корректировка обновлена",
            adjustment_id=adjustment_id,
            updated_by=updated_by,
            changes=len([e for e in edit_history if e['timestamp'] == timestamp])
        )
        
        return adjustment
    
    async def mark_adjustments_as_applied(
        self,
        adjustment_ids: List[int],
        payroll_entry_id: int
    ) -> int:
        """
        Отметить корректировки как применённые к payroll_entry.
        
        Args:
            adjustment_ids: Список ID корректировок
            payroll_entry_id: ID записи начисления
            
        Returns:
            int: Количество обновленных записей
        """
        if not adjustment_ids:
            return 0
        
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.id.in_(adjustment_ids)
        )
        result = await self.session.execute(query)
        adjustments = result.scalars().all()
        
        count = 0
        for adjustment in adjustments:
            adjustment.payroll_entry_id = payroll_entry_id
            adjustment.is_applied = True
            count += 1
        
        # Не используем flush() - commit будет в вызывающем коде
        
        logger.info(
            "Корректировки отмечены как применённые",
            payroll_entry_id=payroll_entry_id,
            count=count
        )
        
        return count
    
    async def get_adjustment_by_id(
        self,
        adjustment_id: int
    ) -> Optional[PayrollAdjustment]:
        """
        Получить корректировку по ID.
        
        Args:
            adjustment_id: ID корректировки
            
        Returns:
            Optional[PayrollAdjustment]: Корректировка или None
        """
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.id == adjustment_id
        ).options(
            selectinload(PayrollAdjustment.shift),
            selectinload(PayrollAdjustment.employee),
            selectinload(PayrollAdjustment.object),
            selectinload(PayrollAdjustment.creator),
            selectinload(PayrollAdjustment.updater),
            selectinload(PayrollAdjustment.payroll_entry)
        )
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

