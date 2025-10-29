"""Сервис для проверки и корректировки начислений."""

from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.shift import Shift
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.timeslot_task_template import TimeslotTaskTemplate
from core.logging.logger import logger


class PayrollVerificationService:
    """Сервис проверки и корректировки начислений."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def verify_and_fix_adjustments(
        self,
        owner_id: int,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """
        Проверить и исправить начисления для владельца.
        
        Args:
            owner_id: ID владельца
            start_date: Дата начала проверки (по умолчанию: начало времен)
            end_date: Дата окончания проверки (по умолчанию: сегодня)
            
        Returns:
            Отчет о проверке и исправлениях
        """
        report = {
            "shifts_checked": 0,
            "missing_adjustments_created": 0,
            "penalties_corrected": 0,
            "total_amount_added": Decimal("0"),
            "total_amount_corrected": Decimal("0"),
            "details": []
        }
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = date(2024, 10, 1)  # С начала октября
        
        # 1. Найти все завершенные смены владельца без начислений
        missing_report = await self._create_missing_adjustments(owner_id, start_date, end_date)
        report["shifts_checked"] = missing_report["shifts_checked"]
        report["missing_adjustments_created"] = missing_report["adjustments_created"]
        report["total_amount_added"] = missing_report["total_amount"]
        report["details"].extend(missing_report["details"])
        
        # 2. Проверить и исправить штрафы за задачи
        penalties_report = await self._fix_task_penalties(owner_id, start_date, end_date)
        report["penalties_corrected"] = penalties_report["penalties_corrected"]
        report["total_amount_corrected"] = penalties_report["total_corrected"]
        report["details"].extend(penalties_report["details"])
        
        await self.session.commit()
        
        return report
    
    async def _create_missing_adjustments(
        self,
        owner_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Создать недостающие начисления за завершенные смены."""
        report = {
            "shifts_checked": 0,
            "adjustments_created": 0,
            "total_amount": Decimal("0"),
            "details": []
        }
        
        logger.info(
            f"Starting missing adjustments check",
            owner_id=owner_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Получить все объекты владельца
        objects_query = select(Object).where(Object.owner_id == owner_id)
        objects_result = await self.session.execute(objects_query)
        owner_objects = {obj.id: obj for obj in objects_result.scalars().all()}
        
        logger.info(f"Found {len(owner_objects)} objects for owner {owner_id}")
        
        if not owner_objects:
            logger.warning(f"No objects found for owner {owner_id}")
            return report
        
        # Найти все завершенные смены на объектах владельца
        shifts_query = select(Shift).options(
            selectinload(Shift.object),
            selectinload(Shift.time_slot),
            selectinload(Shift.user)
        ).where(
            and_(
                Shift.object_id.in_(owner_objects.keys()),
                Shift.status.in_(['completed', 'closed']),
                Shift.end_time.isnot(None),
                Shift.end_time >= datetime.combine(start_date, datetime.min.time()),
                Shift.end_time <= datetime.combine(end_date, datetime.max.time())
            )
        ).order_by(Shift.end_time)
        
        shifts_result = await self.session.execute(shifts_query)
        shifts = shifts_result.scalars().all()
        
        report["shifts_checked"] = len(shifts)
        
        logger.info(
            f"Found {len(shifts)} completed shifts for verification",
            owner_id=owner_id,
            object_ids=list(owner_objects.keys())
        )
        
        for shift in shifts:
            # Проверить, есть ли уже начисление shift_base
            existing_query = select(PayrollAdjustment).where(
                and_(
                    PayrollAdjustment.shift_id == shift.id,
                    PayrollAdjustment.adjustment_type == 'shift_base'
                )
            )
            existing_result = await self.session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                logger.debug(
                    f"Shift {shift.id} already has shift_base adjustment {existing.id}, skipping"
                )
                continue  # Уже есть начисление
            
            # Создать базовое начисление
            amount = shift.total_payment or Decimal('0.00')
            shift_base = PayrollAdjustment(
                shift_id=shift.id,
                employee_id=shift.user_id,
                object_id=shift.object_id,
                adjustment_type='shift_base',
                amount=amount,
                description=f'Базовая оплата за смену #{shift.id} (восстановлено)',
                details={
                    'shift_id': shift.id,
                    'hours': float(shift.total_hours or 0),
                    'hourly_rate': float(shift.hourly_rate or 0),
                    'restored': True,
                    'restored_at': datetime.now().isoformat()
                },
                created_by=shift.user_id,
                is_applied=False,
                created_at=shift.end_time  # Используем дату закрытия смены
            )
            self.session.add(shift_base)
            report["adjustments_created"] += 1
            report["total_amount"] += amount
            
            employee_name = f"{shift.user.last_name} {shift.user.first_name}" if shift.user else f"ID {shift.user_id}"
            object_name = shift.object.name if shift.object else f"ID {shift.object_id}"
            
            report["details"].append({
                "type": "missing_shift_base",
                "shift_id": shift.id,
                "employee": employee_name,
                "object": object_name,
                "date": shift.end_time.date().isoformat(),
                "amount": float(amount),
                "message": f"Создано базовое начисление за смену #{shift.id} от {shift.end_time.date().isoformat()}"
            })
            
            logger.info(
                f"Created missing shift_base adjustment",
                shift_id=shift.id,
                employee_id=shift.user_id,
                amount=float(amount)
            )
        
        return report
    
    async def _fix_task_penalties(
        self,
        owner_id: int,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Исправить штрафы за задачи на основе текущих настроек."""
        report = {
            "penalties_corrected": 0,
            "total_corrected": Decimal("0"),
            "details": []
        }
        
        logger.info(
            f"Starting task penalties check",
            owner_id=owner_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        # Получить все объекты владельца
        objects_query = select(Object).where(Object.owner_id == owner_id)
        objects_result = await self.session.execute(objects_query)
        owner_objects = {obj.id: obj for obj in objects_result.scalars().all()}
        
        logger.info(f"Found {len(owner_objects)} objects for penalties check")
        
        if not owner_objects:
            logger.warning(f"No objects found for owner {owner_id} in penalties check")
            return report
        
        # Найти все штрафы за задачи
        penalties_query = select(PayrollAdjustment).options(
            selectinload(PayrollAdjustment.shift).selectinload(Shift.object),
            selectinload(PayrollAdjustment.shift).selectinload(Shift.time_slot),
            selectinload(PayrollAdjustment.employee)
        ).where(
            and_(
                PayrollAdjustment.adjustment_type == 'task_penalty',
                PayrollAdjustment.object_id.in_(owner_objects.keys()),
                PayrollAdjustment.created_at >= datetime.combine(start_date, datetime.min.time()),
                PayrollAdjustment.created_at <= datetime.combine(end_date, datetime.max.time())
            )
        )
        
        penalties_result = await self.session.execute(penalties_query)
        penalties = penalties_result.scalars().all()
        
        logger.info(
            f"Found {len(penalties)} task penalties for verification",
            owner_id=owner_id,
            object_ids=list(owner_objects.keys())
        )
        
        for penalty in penalties:
            shift = penalty.shift
            if not shift:
                continue
            
            # Получить текущую сумму штрафа из details
            task_text = penalty.details.get('task_name') if penalty.details else None
            if not task_text:
                continue
            
            # Определить откуда взять актуальную сумму штрафа
            current_penalty_amount = None
            source = None
            
            # Если смена была запланирована - проверить тайм-слот
            if shift.time_slot_id and shift.time_slot:
                # Проверить задачи тайм-слота
                template_query = select(TimeslotTaskTemplate).where(
                    and_(
                        TimeslotTaskTemplate.timeslot_id == shift.time_slot_id,
                        TimeslotTaskTemplate.task_text == task_text
                    )
                )
                template_result = await self.session.execute(template_query)
                template = template_result.scalar_one_or_none()
                
                if template:
                    current_penalty_amount = template.deduction_amount or Decimal('0')
                    source = 'timeslot'
                elif not shift.time_slot.ignore_object_tasks and shift.object and shift.object.shift_tasks:
                    # Проверить задачи объекта
                    for task in shift.object.shift_tasks:
                        if task.get('text') == task_text:
                            current_penalty_amount = Decimal(str(task.get('deduction_amount', 0)))
                            source = 'object'
                            break
            else:
                # Спонтанная смена - задачи объекта
                if shift.object and shift.object.shift_tasks:
                    for task in shift.object.shift_tasks:
                        if task.get('text') == task_text:
                            current_penalty_amount = Decimal(str(task.get('deduction_amount', 0)))
                            source = 'object'
                            break
            
            if current_penalty_amount is None:
                continue  # Задача не найдена в текущих настройках
            
            # Сравнить с текущим штрафом
            old_amount = abs(Decimal(str(penalty.amount)))
            new_amount = abs(current_penalty_amount)
            
            if old_amount != new_amount:
                logger.info(
                    f"Correcting penalty for shift {shift.id}",
                    penalty_id=penalty.id,
                    task=task_text,
                    old_amount=float(old_amount),
                    new_amount=float(new_amount),
                    source=source
                )
                
                # Обновить штраф
                difference = new_amount - old_amount
                penalty.amount = -abs(new_amount)
                
                # Добавить запись в историю изменений
                if not penalty.edit_history:
                    penalty.edit_history = []
                
                penalty.edit_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'user_id': owner_id,
                    'field': 'amount',
                    'old_value': str(-old_amount),
                    'new_value': str(-new_amount),
                    'reason': 'Автоматическая корректировка на основе текущих настроек'
                })
                
                penalty.updated_by = owner_id
                penalty.updated_at = datetime.now()
                
                if penalty.details:
                    penalty.details['corrected'] = True
                    penalty.details['corrected_at'] = datetime.now().isoformat()
                    penalty.details['old_amount'] = float(old_amount)
                    penalty.details['new_amount'] = float(new_amount)
                    penalty.details['current_source'] = source
                
                report["penalties_corrected"] += 1
                report["total_corrected"] += difference
                
                employee_name = f"{penalty.employee.last_name} {penalty.employee.first_name}" if penalty.employee else f"ID {penalty.employee_id}"
                
                report["details"].append({
                    "type": "task_penalty_corrected",
                    "adjustment_id": penalty.id,
                    "shift_id": shift.id,
                    "employee": employee_name,
                    "task": task_text,
                    "old_amount": float(-old_amount),
                    "new_amount": float(-new_amount),
                    "difference": float(difference),
                    "source": source,
                    "message": f"Штраф за '{task_text}' изменен с {old_amount}₽ на {new_amount}₽"
                })
                
                logger.info(
                    f"Corrected task penalty",
                    adjustment_id=penalty.id,
                    shift_id=shift.id,
                    old_amount=float(old_amount),
                    new_amount=float(new_amount),
                    difference=float(difference)
                )
            else:
                logger.debug(
                    f"Penalty {penalty.id} for shift {shift.id} is already correct",
                    task=task_text,
                    amount=float(old_amount),
                    source=source
                )
        
        logger.info(
            f"Penalties check completed",
            total_penalties=len(penalties),
            corrected=report["penalties_corrected"]
        )
        
        return report

