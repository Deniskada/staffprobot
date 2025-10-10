"""Сервис для автоматических удержаний."""

from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logging.logger import logger
from domain.entities.shift import Shift
from domain.entities.shift_task import ShiftTask
from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.time_slot import TimeSlot


class AutoDeductionService:
    """
    Сервис для расчета автоматических удержаний.
    
    ВАЖНО: Премии и штрафы за задачи применяются только для
    "Повременно-премиальной" системы оплаты труда (payment_system_id=3).
    Проверка системы оплаты выполняется в Celery задаче process_automatic_deductions.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # Константы для расчета
    LATE_START_THRESHOLD_MINUTES = 15  # Опоздание более 15 минут
    LATE_START_PENALTY_PER_MINUTE = Decimal("10.0")  # 10₽ за каждую минуту опоздания
    INCOMPLETE_TASK_PENALTY = Decimal("100.0")  # 100₽ за каждую невыполненную задачу
    
    async def calculate_deductions_for_shift(
        self,
        shift_id: int
    ) -> List[Tuple[str, Decimal, str, dict]]:
        """
        Рассчитать автоудержания для смены.
        
        Args:
            shift_id: ID смены
            
        Returns:
            Список кортежей: (type, amount, description, details)
        """
        try:
            deductions = []
            
            # Получить смену
            shift_query = select(Shift).where(Shift.id == shift_id)
            shift_result = await self.db.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            
            if not shift:
                return deductions
            
            # 1. Проверить опоздание (только для запланированных смен)
            if shift.is_planned and shift.schedule_id:
                late_deduction = await self._calculate_late_start_penalty(shift)
                if late_deduction:
                    deductions.append(late_deduction)
            
            # 2. Проверить невыполненные задачи
            task_deductions = await self._calculate_incomplete_task_penalties(shift_id)
            deductions.extend(task_deductions)
            
            logger.info(
                f"Calculated {len(deductions)} auto-deductions for shift",
                shift_id=shift_id,
                total_amount=sum(d[1] for d in deductions)
            )
            
            return deductions
            
        except Exception as e:
            logger.error(f"Error calculating deductions: {e}", shift_id=shift_id)
            return []
    
    async def _calculate_late_start_penalty(
        self,
        shift: Shift
    ) -> Optional[Tuple[str, Decimal, str, dict]]:
        """
        Рассчитать штраф за опоздание.
        
        Использует настройки объекта (late_threshold_minutes, late_penalty_per_minute).
        Если настройки не указаны (наследуются от подразделения), использует константы.
        
        Args:
            shift: Объект смены
            
        Returns:
            Кортеж (type, amount, description, details) или None
        """
        try:
            if not shift.schedule_id or not shift.object_id:
                return None
            
            # Получить объект для настроек штрафов
            from domain.entities.object import Object
            object_query = select(Object).where(Object.id == shift.object_id)
            object_result = await self.db.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            if not obj:
                return None
            
            # Определить настройки штрафа (из объекта или по умолчанию)
            if obj.inherit_late_settings or obj.late_threshold_minutes is None or obj.late_penalty_per_minute is None:
                # Наследуем настройки (в будущем - от подразделения), пока используем константы
                threshold_minutes = self.LATE_START_THRESHOLD_MINUTES
                penalty_per_minute = self.LATE_START_PENALTY_PER_MINUTE
                logger.info(f"Using default late settings for object {obj.id}: threshold={threshold_minutes}, penalty={penalty_per_minute}")
            else:
                # Используем настройки объекта
                threshold_minutes = obj.late_threshold_minutes
                penalty_per_minute = Decimal(str(obj.late_penalty_per_minute))
                logger.info(f"Using object late settings for object {obj.id}: threshold={threshold_minutes}, penalty={penalty_per_minute}")
            
            # Получить запланированное время начала
            schedule_query = select(ShiftSchedule).where(ShiftSchedule.id == shift.schedule_id)
            schedule_result = await self.db.execute(schedule_query)
            schedule = schedule_result.scalar_one_or_none()
            
            if not schedule or not schedule.planned_start:
                return None
            
            # Рассчитать опоздание
            planned_start = schedule.planned_start
            actual_start = shift.start_time
            
            if actual_start <= planned_start:
                return None  # Не опоздал
            
            late_minutes = int((actual_start - planned_start).total_seconds() / 60)
            
            if late_minutes <= threshold_minutes:
                return None  # Опоздание в пределах допустимого
            
            # Рассчитать штраф
            penalty_minutes = late_minutes - threshold_minutes
            penalty_amount = Decimal(penalty_minutes) * penalty_per_minute
            
            description = (
                f"Опоздание на {late_minutes} минут "
                f"(допустимо {threshold_minutes} мин)"
            )
            
            details = {
                "planned_start": planned_start.isoformat(),
                "actual_start": actual_start.isoformat(),
                "late_minutes": late_minutes,
                "penalty_minutes": penalty_minutes,
                "penalty_per_minute": float(penalty_per_minute),
                "threshold_minutes": threshold_minutes
            }
            
            return ("late_start", penalty_amount, description, details)
            
        except Exception as e:
            logger.error(f"Error calculating late start penalty: {e}", shift_id=shift.id)
            return None
    
    async def _calculate_incomplete_task_penalties(
        self,
        shift_id: int
    ) -> List[Tuple[str, Decimal, str, dict]]:
        """
        Рассчитать начисления (штрафы/премии) за задачи смены.
        
        Логика:
        - Обязательная задача НЕ выполнена → штраф (отрицательное значение deduction_amount)
        - Необязательная задача ВЫПОЛНЕНА → премия (положительное значение deduction_amount)
        
        Args:
            shift_id: ID смены
            
        Returns:
            Список кортежей (type, amount, description, details)
            amount может быть отрицательным (штраф) или положительным (премия)
        """
        try:
            adjustments = []
            
            # Получить все задачи смены
            tasks_query = select(ShiftTask).where(ShiftTask.shift_id == shift_id)
            tasks_result = await self.db.execute(tasks_query)
            tasks = tasks_result.scalars().all()
            
            for task in tasks:
                # Пропускаем задачи без суммы начисления
                if not task.deduction_amount or task.deduction_amount == 0:
                    continue
                
                # Обязательная задача не выполнена → штраф
                if task.is_mandatory and not task.is_completed:
                    # deduction_amount < 0 → штраф
                    # deduction_amount > 0 → тоже штраф (инверсия в минус)
                    amount = -abs(Decimal(str(task.deduction_amount)))
                    description = f"Штраф: не выполнена обязательная задача '{task.task_text[:50]}'"
                    adjustment_type = "task_penalty"
                    
                    details = {
                        "task_id": task.id,
                        "task_text": task.task_text,
                        "source": task.source,
                        "is_mandatory": True,
                        "is_completed": False
                    }
                    
                    adjustments.append((adjustment_type, amount, description, details))
                
                # Необязательная задача выполнена → премия
                elif not task.is_mandatory and task.is_completed and task.deduction_amount > 0:
                    # deduction_amount > 0 → премия
                    amount = abs(Decimal(str(task.deduction_amount)))
                    description = f"Премия: выполнена необязательная задача '{task.task_text[:50]}'"
                    adjustment_type = "task_bonus"
                    
                    details = {
                        "task_id": task.id,
                        "task_text": task.task_text,
                        "source": task.source,
                        "is_mandatory": False,
                        "is_completed": True
                    }
                    
                    adjustments.append((adjustment_type, amount, description, details))
            
            return adjustments
            
        except Exception as e:
            logger.error(f"Error calculating task adjustments: {e}", shift_id=shift_id)
            return []

