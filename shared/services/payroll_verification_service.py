"""Сервис для проверки и корректировки начислений."""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import pytz

from domain.entities.shift import Shift
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.object import Object
from domain.entities.user import User
from domain.entities.time_slot import TimeSlot
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
            "shifts_force_closed": 0,
            "missing_adjustments_created": 0,
            "penalties_corrected": 0,
            "invalid_late_penalties_removed": 0,
            "total_amount_added": Decimal("0"),
            "total_amount_corrected": Decimal("0"),
            "details": []
        }
        
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = date(2024, 10, 1)  # С начала октября
        
        # 0. Принудительно закрыть незакрытые автоматически смены
        force_close_report = await self._force_close_unclosed_shifts(owner_id)
        report["shifts_force_closed"] = force_close_report["shifts_closed"]
        report["details"].extend(force_close_report["details"])

        # 0б. Пересчитать уже закрытые смены с аномально большой длительностью
        recalc_report = await self._fix_overclosed_shifts(owner_id, start_date, end_date)
        report["shifts_force_closed"] += recalc_report["shifts_fixed"]
        report["details"].extend(recalc_report["details"])

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

        # 3. Удалить штрафы за опоздание для смен с planned_start < opening_time
        late_report = await self._fix_invalid_late_start_penalties(owner_id, start_date, end_date)
        report["invalid_late_penalties_removed"] = late_report["removed"]
        report["details"].extend(late_report["details"])

        await self.session.commit()
        
        return report
    
    async def _force_close_unclosed_shifts(self, owner_id: int) -> Dict[str, Any]:
        """Принудительно закрыть активные смены, которые должны были закрыться автоматически."""
        report: Dict[str, Any] = {"shifts_closed": 0, "details": []}

        objects_query = select(Object).where(Object.owner_id == owner_id)
        objects_result = await self.session.execute(objects_query)
        owner_objects = {obj.id: obj for obj in objects_result.scalars().all()}

        if not owner_objects:
            return report

        active_shifts_query = (
            select(Shift)
            .options(selectinload(Shift.user))
            .where(
                and_(
                    Shift.object_id.in_(owner_objects.keys()),
                    Shift.status == "active",
                )
            )
        )
        result = await self.session.execute(active_shifts_query)
        active_shifts = result.scalars().all()

        now_utc = datetime.now(pytz.UTC)

        for shift in active_shifts:
            try:
                obj = owner_objects[shift.object_id]
                tz_name = getattr(obj, "timezone", None) or "Europe/Moscow"
                obj_tz = pytz.timezone(tz_name)

                if getattr(shift.start_time, "tzinfo", None):
                    start_local = shift.start_time.astimezone(obj_tz)
                else:
                    start_local = obj_tz.localize(shift.start_time)

                # Дедлайн = closing_time объекта + 60 мин (вне зависимости от тайм-слота)
                if not obj.closing_time:
                    continue

                closing_local = obj_tz.localize(
                    datetime.combine(start_local.date(), obj.closing_time)
                )
                planned_end_utc = closing_local.astimezone(pytz.UTC)
                deadline = planned_end_utc + timedelta(minutes=60)

                if now_utc < deadline:
                    continue  # Ещё не пора

                # Закрываем смену
                close_at = planned_end_utc
                duration = close_at - (
                    shift.start_time
                    if getattr(shift.start_time, "tzinfo", None)
                    else pytz.UTC.localize(shift.start_time)
                )
                total_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                total_hours = total_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                total_payment = None
                if shift.hourly_rate is not None:
                    total_payment = (total_hours * Decimal(str(shift.hourly_rate))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                shift.end_time = close_at
                shift.status = "completed"
                shift.total_hours = float(total_hours)
                shift.total_payment = float(total_payment) if total_payment is not None else None

                employee_name = (
                    f"{shift.user.last_name} {shift.user.first_name}"
                    if shift.user
                    else f"ID {shift.user_id}"
                )
                report["shifts_closed"] += 1
                report["details"].append(
                    {
                        "type": "force_closed_shift",
                        "shift_id": shift.id,
                        "employee": employee_name,
                        "object": obj.name,
                        "date": close_at.date().isoformat(),
                        "amount": float(total_payment or 0),
                        "message": (
                            f"Принудительно закрыта смена #{shift.id} "
                            f"от {close_at.date().isoformat()}, "
                            f"{float(total_hours):.2f} ч."
                        ),
                    }
                )
                logger.info(
                    f"Force-closed shift {shift.id} (owner_id={owner_id}), "
                    f"close_at={close_at}, hours={total_hours}"
                )
            except Exception as e:
                logger.error(f"Error force-closing shift {shift.id}: {e}")

        return report

    async def _fix_overclosed_shifts(
        self, owner_id: int, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Пересчитать завершённые смены, закрытые позже времени закрытия объекта более чем на 60 минут.

        Смена считается аномально длинной если фактический end_time превышает
        closing_time объекта + 60 минут — вне зависимости от тайм-слота.
        Пересчитываем end_time = closing_time, total_hours, total_payment и shift_base.
        """
        report: Dict[str, Any] = {"shifts_fixed": 0, "details": []}

        objects_query = select(Object).where(Object.owner_id == owner_id)
        objects_result = await self.session.execute(objects_query)
        owner_objects = {obj.id: obj for obj in objects_result.scalars().all()}

        if not owner_objects:
            return report

        from sqlalchemy import and_

        shifts_query = (
            select(Shift)
            .options(selectinload(Shift.user))
            .where(
                and_(
                    Shift.object_id.in_(owner_objects.keys()),
                    Shift.status.in_(["completed", "closed"]),
                    Shift.end_time.isnot(None),
                    Shift.end_time >= datetime.combine(start_date, datetime.min.time()),
                    Shift.end_time <= datetime.combine(end_date, datetime.max.time()),
                )
            )
        )
        result = await self.session.execute(shifts_query)
        shifts = result.scalars().all()

        for shift in shifts:
            try:
                obj = owner_objects[shift.object_id]
                if not obj.closing_time:
                    continue

                tz_name = getattr(obj, "timezone", None) or "Europe/Moscow"
                obj_tz = pytz.timezone(tz_name)

                if getattr(shift.start_time, "tzinfo", None):
                    start_local = shift.start_time.astimezone(obj_tz)
                else:
                    start_local = obj_tz.localize(shift.start_time)

                # Время закрытия объекта в UTC (на дату начала смены)
                closing_local = obj_tz.localize(
                    datetime.combine(start_local.date(), obj.closing_time)
                )
                closing_utc = closing_local.astimezone(pytz.UTC).replace(tzinfo=None)

                # Фактическое окончание
                actual_end = shift.end_time
                if getattr(actual_end, "tzinfo", None):
                    actual_end = actual_end.astimezone(pytz.UTC).replace(tzinfo=None)

                # Аномалия: смена закрылась позже closing_time + 60 мин
                overrun = (actual_end - closing_utc).total_seconds()
                if overrun <= 3600:
                    continue

                # Пересчитываем по closing_time объекта
                start_utc = shift.start_time
                if getattr(start_utc, "tzinfo", None):
                    start_utc = start_utc.astimezone(pytz.UTC).replace(tzinfo=None)

                duration = closing_utc - start_utc
                new_hours = Decimal(duration.total_seconds()) / Decimal(3600)
                new_hours = new_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                new_payment = None
                if shift.hourly_rate is not None:
                    new_payment = (new_hours * Decimal(str(shift.hourly_rate))).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                old_hours = shift.total_hours
                old_payment = shift.total_payment

                shift.end_time = closing_utc
                shift.total_hours = float(new_hours)
                shift.total_payment = float(new_payment) if new_payment is not None else None

                # Обновляем корректировку shift_base если есть
                adj_result = await self.session.execute(
                    select(PayrollAdjustment).where(
                        PayrollAdjustment.shift_id == shift.id,
                        PayrollAdjustment.adjustment_type == "shift_base",
                    )
                )
                adj = adj_result.scalar_one_or_none()
                if adj and new_payment is not None:
                    adj.amount = new_payment
                    adj.description = (
                        f"Базовое начисление за смену #{shift.id} "
                        f"(пересчитано: {old_payment}→{float(new_payment)})"
                    )

                employee_name = (
                    f"{shift.user.last_name} {shift.user.first_name}"
                    if shift.user
                    else f"ID {shift.user_id}"
                )
                report["shifts_fixed"] += 1
                report["details"].append(
                    {
                        "type": "force_closed_shift",
                        "shift_id": shift.id,
                        "employee": employee_name,
                        "object": obj.name,
                        "date": closing_utc.date().isoformat(),
                        "amount": float(new_payment or 0),
                        "message": (
                            f"Пересчитана смена #{shift.id}: "
                            f"{old_hours:.2f}ч/{old_payment}₽ → "
                            f"{float(new_hours):.2f}ч/{float(new_payment or 0):.2f}₽"
                        ),
                    }
                )
                logger.info(
                    f"Fixed overclosed shift {shift.id}: hours {old_hours}→{float(new_hours)}, "
                    f"payment {old_payment}→{float(new_payment or 0)}"
                )
            except Exception as e:
                logger.error(f"Error fixing overclosed shift {shift.id}: {e}")

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

    async def _fix_invalid_late_start_penalties(
        self,
        owner_id: int,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Удалить штрафы late_start для смен, у которых planned_start (локальное) < opening_time.

        По новой логике штраф за опоздание применяется только если
        planned_start >= opening_time объекта. Устаревшие корректировки удаляются.
        """
        report: Dict[str, Any] = {"removed": 0, "details": []}

        objects_query = select(Object).where(Object.owner_id == owner_id)
        objects_result = await self.session.execute(objects_query)
        owner_objects = {obj.id: obj for obj in objects_result.scalars().all()}

        if not owner_objects:
            return report

        late_query = (
            select(PayrollAdjustment)
            .options(
                selectinload(PayrollAdjustment.shift).selectinload(Shift.time_slot),
                selectinload(PayrollAdjustment.shift).selectinload(Shift.user),
                selectinload(PayrollAdjustment.employee),
            )
            .where(
                and_(
                    PayrollAdjustment.adjustment_type == "late_start",
                    PayrollAdjustment.object_id.in_(owner_objects.keys()),
                    PayrollAdjustment.created_at >= datetime.combine(start_date, datetime.min.time()),
                    PayrollAdjustment.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
        )
        result = await self.session.execute(late_query)
        late_adjustments = result.scalars().all()

        for adj in late_adjustments:
            shift = adj.shift
            if not shift or not shift.planned_start:
                continue
            if not (shift.is_planned and shift.time_slot_id and shift.time_slot):
                continue

            obj = owner_objects.get(adj.object_id)
            if not obj or not obj.opening_time:
                continue

            obj_tz_str = obj.timezone or "Europe/Moscow"
            obj_tz = pytz.timezone(obj_tz_str)
            planned_local_time = shift.planned_start.astimezone(obj_tz).time()

            if planned_local_time >= obj.opening_time:
                continue  # Корректировка легитимна

            # planned_start < opening_time → штраф некорректен, удаляем
            employee_name = (
                f"{adj.employee.last_name} {adj.employee.first_name}"
                if adj.employee
                else f"ID {adj.employee_id}"
            )
            obj_name = obj.name

            logger.info(
                f"Removing invalid late_start adjustment {adj.id} "
                f"(shift {shift.id}, planned={planned_local_time}, opening={obj.opening_time})"
            )
            await self.session.delete(adj)

            report["removed"] += 1
            report["details"].append({
                "type": "invalid_late_penalty_removed",
                "adjustment_id": adj.id,
                "shift_id": shift.id,
                "employee": employee_name,
                "object": obj_name,
                "amount": float(adj.amount),
                "message": (
                    f"Удалён некорректный штраф за опоздание #{adj.id} "
                    f"(смена #{shift.id}, planned {planned_local_time.strftime('%H:%M')} "
                    f"< opening {obj.opening_time.strftime('%H:%M')})"
                ),
            })

        logger.info(
            f"Invalid late penalties check completed",
            owner_id=owner_id,
            removed=report["removed"],
        )
        return report

