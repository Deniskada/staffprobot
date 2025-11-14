"""Сервис для работы с отменой смен."""

from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift_cancellation import ShiftCancellation
from domain.entities.object import Object
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.user import User
from core.logging.logger import logger
from shared.services.cancellation_policy_service import CancellationPolicyService
from shared.services.shift_history_service import ShiftHistoryService


class ShiftCancellationService:
    """Сервис для управления отменой смен."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def cancel_shift(
        self,
        shift_schedule_id: int,
        cancelled_by_user_id: int,
        cancelled_by_type: str,  # 'employee', 'owner', 'manager', 'system'
        cancellation_reason: str,
        reason_notes: Optional[str] = None,
        document_description: Optional[str] = None,
        contract_id: Optional[int] = None,
        *,
        actor_role: Optional[str] = None,
        source: str = "web",
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Отменить запланированную смену.
        
        Args:
            shift_schedule_id: ID запланированной смены
            cancelled_by_user_id: ID пользователя, отменившего смену
            cancelled_by_type: Тип отменившего (employee, owner, manager, system)
            cancellation_reason: Причина отмены
            reason_notes: Дополнительные заметки
            document_description: Описание документа (для справок)
            contract_id: ID договора (для автоотмены)
            
        Returns:
            Dict с результатом: {
                'success': bool,
                'cancellation_id': int or None,
                'fine_amount': Decimal or None,
                'message': str
            }
        """
        try:
            # Получаем смену
            shift_query = select(ShiftSchedule).where(ShiftSchedule.id == shift_schedule_id)
            shift_result = await self.session.execute(shift_query)
            shift = shift_result.scalar_one_or_none()
            
            if not shift:
                return {
                    'success': False,
                    'cancellation_id': None,
                    'fine_amount': None,
                    'message': 'Смена не найдена'
                }
            
            if shift.status != 'planned':
                return {
                    'success': False,
                    'cancellation_id': None,
                    'fine_amount': None,
                    'message': f'Смена уже имеет статус: {shift.status}'
                }
            
            # Рассчитываем часы до начала смены
            now_utc = datetime.now(timezone.utc)
            time_delta = shift.planned_start - now_utc
            hours_before_shift = Decimal(str(round(time_delta.total_seconds() / 3600, 2)))
            
            # Получаем объект для настроек штрафов (с eager loading org_unit и цепочки parent'ов)
            object_query = select(Object).where(Object.id == shift.object_id).options(
                joinedload(Object.org_unit).joinedload('parent').joinedload('parent').joinedload('parent').joinedload('parent')
            )
            object_result = await self.session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            # Определяем политику причины (уважительная/нет)
            is_respectful = False
            if obj:
                try:
                    reason_map = await CancellationPolicyService.get_reason_map(self.session, obj.owner_id)
                    policy = reason_map.get(cancellation_reason)
                    # Уважительная причина определяется флагом treated_as_valid
                    is_respectful = bool(policy and getattr(policy, 'treated_as_valid', False))
                except Exception as _:
                    # Фолбэк по коду причины (б/у для совместимости)
                    is_respectful = cancellation_reason in {'medical_cert', 'emergency_cert', 'police_cert'}

            # Отменяем смену
            previous_status = shift.status
            shift.status = 'cancelled'

            # Создаем запись об отмене
            cancellation = ShiftCancellation(
                shift_schedule_id=shift_schedule_id,
                employee_id=shift.user_id,
                object_id=shift.object_id,
                cancelled_by_id=cancelled_by_user_id,
                cancelled_by_type=cancelled_by_type,
                cancellation_reason=cancellation_reason,
                reason_notes=reason_notes,
                hours_before_shift=hours_before_shift,
                document_description=document_description,
                document_verified=False,
                fine_amount=None,
                fine_reason=None,
                fine_applied=False,
                contract_id=contract_id
            )

            self.session.add(cancellation)
            await self.session.flush()

            # Если причина уважительная — уходим на модерацию без мгновенных штрафов
            history_service = ShiftHistoryService(self.session)

            if is_respectful:
                await history_service.log_event(
                    operation="schedule_cancel",
                    source=source,
                    actor_id=cancelled_by_user_id,
                    actor_role=actor_role or cancelled_by_type,
                    schedule_id=shift_schedule_id,
                    shift_id=None,
                    old_status=previous_status,
                    new_status=shift.status,
                    payload={
                        "reason_code": cancellation_reason,
                        "notes": reason_notes,
                        "document_description": document_description,
                        "hours_before_shift": float(hours_before_shift) if hours_before_shift is not None else None,
                        **(extra_payload or {}),
                    },
                )
                await self.session.commit()
                logger.info(
                    f"Shift {shift_schedule_id} cancelled by {cancelled_by_type} (user_id={cancelled_by_user_id}), pending moderation"
                )
                return {
                    'success': True,
                    'cancellation_id': cancellation.id,
                    'fine_amount': None,
                    'message': 'Ваша заявка на модерации. Владелец проверит документ.'
                }

            # Неуважительная отмена — сначала пробуем Rules Engine (если есть правила)
            total_fine = Decimal('0')
            applied_parts: list[str] = []
            if obj:
                try:
                    from shared.services.rules_engine import RulesEngine
                    engine = RulesEngine(self.session)
                    actions = await engine.evaluate(obj.owner_id, 'cancellation', {
                        'cancellation_reason': cancellation_reason,
                        'hours_before_shift': float(hours_before_shift) if hours_before_shift is not None else None,
                        'object_id': obj.id,
                    })
                    for act in actions:
                        if act.get('type') == 'fine':
                            amount = Decimal(str(act.get('amount', 0)))
                            if amount and amount > 0:
                                await self._create_specific_payroll_adjustment(
                                    cancellation,
                                    shift,
                                    amount,
                                    act.get('fine_code', 'invalid_reason'),
                                    hours_before_shift,
                                    cancelled_by_user_id,
                                )
                                total_fine += amount
                                applied_parts.append(act.get('label', 'правило'))
                except Exception as _:
                    pass

            # Базовая логика по настройкам объекта (для совместимости)
            if obj and total_fine == 0:
                settings = obj.get_cancellation_settings()
                short_notice_hours = settings.get('short_notice_hours')
                short_notice_fine = settings.get('short_notice_fine')
                invalid_reason_fine = settings.get('invalid_reason_fine')

                # Штраф за короткий срок
                if (
                    short_notice_hours
                    and short_notice_fine
                    and hours_before_shift is not None
                    and float(hours_before_shift) < float(short_notice_hours)
                ):
                    await self._create_specific_payroll_adjustment(
                        cancellation,
                        shift,
                        short_notice_fine,
                        'short_notice',
                        hours_before_shift,
                        cancelled_by_user_id,
                    )
                    total_fine += Decimal(str(short_notice_fine))
                    applied_parts.append('короткий срок')

                # Штраф за неуважительную причину
                if invalid_reason_fine:
                    await self._create_specific_payroll_adjustment(
                        cancellation,
                        shift,
                        invalid_reason_fine,
                        'invalid_reason',
                        hours_before_shift,
                        cancelled_by_user_id,
                    )
                    total_fine += Decimal(str(invalid_reason_fine))
                    applied_parts.append('неуважительная причина')

            # Обновляем запись отмены
            cancellation.fine_amount = total_fine if total_fine > 0 else None
            cancellation.fine_applied = total_fine > 0
            if len(applied_parts) == 2:
                cancellation.fine_reason = 'both'
            elif applied_parts:
                cancellation.fine_reason = 'short_notice' if applied_parts[0] == 'короткий срок' else 'invalid_reason'

            payload = {
                "reason_code": cancellation_reason,
                "notes": reason_notes,
                "document_description": document_description,
                "hours_before_shift": float(hours_before_shift) if hours_before_shift is not None else None,
                "fine_amount": float(total_fine) if total_fine > 0 else None,
                "fine_reason": cancellation.fine_reason,
            }
            if extra_payload:
                payload.update(extra_payload)

            await history_service.log_event(
                operation="schedule_cancel",
                source=source,
                actor_id=cancelled_by_user_id,
                actor_role=actor_role or cancelled_by_type,
                schedule_id=shift_schedule_id,
                shift_id=None,
                old_status=previous_status,
                new_status=shift.status,
                payload=payload,
            )

            await self.session.commit()

            # Сообщение для пользователя
            if total_fine > 0:
                if len(applied_parts) == 2:
                    user_message = (
                        f"Смена отменена. Применены штрафы: за короткий срок и за неуважительную причину (итого {abs(float(total_fine)):.2f} ₽)."
                    )
                else:
                    user_message = (
                        f"Смена отменена. Применен штраф за {applied_parts[0]} ({abs(float(total_fine)):.2f} ₽)."
                    )
            else:
                user_message = "Смена отменена. Штрафы не применены."

            logger.info(
                f"Shift {shift_schedule_id} cancelled by {cancelled_by_type} (user_id={cancelled_by_user_id}), immediate processing, fine={total_fine}"
            )
            return {
                'success': True,
                'cancellation_id': cancellation.id,
                'fine_amount': total_fine if total_fine > 0 else None,
                'message': user_message
            }
            
        except Exception as e:
            logger.error(f"Error cancelling shift {shift_schedule_id}: {e}")
            await self.session.rollback()
            return {
                'success': False,
                'cancellation_id': None,
                'fine_amount': None,
                'message': f'Ошибка отмены смены: {str(e)}'
            }
    
    async def _create_payroll_adjustment(
        self,
        cancellation: ShiftCancellation,
        shift: ShiftSchedule,
        fine_amount: Decimal,
        created_by_id: int
    ) -> PayrollAdjustment:
        """Создать корректировку начислений для штрафа за отмену."""
        
        # Определяем тип корректировки
        if cancellation.fine_reason == 'short_notice':
            adjustment_type = 'cancellation_fine_short_notice'
            description = f"Штраф за отмену смены менее чем за {cancellation.hours_before_shift}ч"
        elif cancellation.fine_reason == 'invalid_reason':
            adjustment_type = 'cancellation_fine_invalid_reason'
            description = "Штраф за отмену смены без уважительной причины"
        else:
            adjustment_type = 'cancellation_fine'
            description = "Штраф за отмену смены"
        
        adjustment = PayrollAdjustment(
            shift_id=None,  # Смена не была открыта
            employee_id=cancellation.employee_id,
            object_id=cancellation.object_id,
            adjustment_type=adjustment_type,
            amount=-abs(float(fine_amount)),  # Отрицательная сумма (вычет)
            description=description,
            details={
                'cancellation_id': cancellation.id,
                'shift_schedule_id': cancellation.shift_schedule_id,
                'cancellation_reason': cancellation.cancellation_reason,
                'hours_before_shift': float(cancellation.hours_before_shift) if cancellation.hours_before_shift else None,
                'planned_start': shift.planned_start.isoformat() if shift.planned_start else None
            },
            created_by=created_by_id,
            is_applied=False  # Будет применено при расчете зарплаты
        )
        
        self.session.add(adjustment)
        await self.session.flush()
        
        return adjustment
    
    async def _create_specific_payroll_adjustment(
        self,
        cancellation: ShiftCancellation,
        shift: ShiftSchedule,
        fine_amount: Decimal,
        fine_type: str,  # 'short_notice' or 'invalid_reason'
        hours_before_shift: Decimal,
        created_by_id: int,
        description_suffix: str = ""  # Дополнительное описание (например, объяснение)
    ) -> PayrollAdjustment:
        """Создать конкретную корректировку начислений для определенного типа штрафа."""
        
        # Определяем тип корректировки и описание
        if fine_type == 'short_notice':
            adjustment_type = 'cancellation_fine_short_notice'
            description = f"Штраф за отмену смены менее чем за {abs(float(hours_before_shift)):.1f}ч"
        elif fine_type == 'invalid_reason':
            adjustment_type = 'cancellation_fine_invalid_reason'
            description = "Штраф за отмену смены без уважительной причины"
        else:
            adjustment_type = 'cancellation_fine'
            description = "Штраф за отмену смены"
        
        # Добавляем суффикс к описанию (если есть)
        description += description_suffix
        
        adjustment = PayrollAdjustment(
            shift_id=None,  # Смена не была открыта
            employee_id=cancellation.employee_id,
            object_id=cancellation.object_id,
            adjustment_type=adjustment_type,
            amount=-abs(float(fine_amount)),  # Отрицательная сумма (вычет)
            description=description,
            details={
                'cancellation_id': cancellation.id,
                'shift_schedule_id': cancellation.shift_schedule_id,
                'cancellation_reason': cancellation.cancellation_reason,
                'fine_type': fine_type,
                'hours_before_shift': float(hours_before_shift) if hours_before_shift else None,
                'planned_start': shift.planned_start.isoformat() if shift.planned_start else None
            },
            created_by=created_by_id,
            is_applied=False  # Будет применено при расчете зарплаты
        )
        
        self.session.add(adjustment)
        await self.session.flush()
        
        return adjustment
    
    async def verify_cancellation_document(
        self,
        cancellation_id: int,
        verified_by_user_id: int,
        is_approved: bool
    ) -> Dict[str, Any]:
        """
        Верифицировать документ (справку) для уважительной причины.
        
        Args:
            cancellation_id: ID отмены
            verified_by_user_id: ID верифицирующего (владелец/управляющий)
            is_approved: Подтверждена ли справка
            
        Returns:
            Dict с результатом
        """
        try:
            # Получаем отмену
            cancellation_query = select(ShiftCancellation).where(ShiftCancellation.id == cancellation_id)
            cancellation_result = await self.session.execute(cancellation_query)
            cancellation = cancellation_result.scalar_one_or_none()
            
            if not cancellation:
                return {'success': False, 'message': 'Отмена не найдена'}
            
            cancellation.document_verified = is_approved
            cancellation.verified_by_id = verified_by_user_id
            cancellation.verified_at = datetime.now(timezone.utc)
            
            # Проверяем причину через CancellationPolicyService
            from shared.services.cancellation_policy_service import CancellationPolicyService
            
            # Получаем объект для owner_id
            object_query_for_reason = select(Object).where(Object.id == cancellation.object_id)
            object_result_for_reason = await self.session.execute(object_query_for_reason)
            obj_for_reason = object_result_for_reason.scalar_one_or_none()
            
            policy_service = CancellationPolicyService(self.session)
            reason_obj = await policy_service.get_reason_by_code(
                code=cancellation.cancellation_reason,
                owner_id=obj_for_reason.owner_id if obj_for_reason else None
            )
            
            # Если справка подтверждена И причина уважительная - штрафов нет
            if is_approved and reason_obj and reason_obj.treated_as_valid:
                logger.info(f"Cancellation {cancellation_id} approved with respectful reason '{reason_obj.code}' - no fines")
            
            # Если справка отклонена ИЛИ причина не уважительная - создаем штрафы
            elif not is_approved or (reason_obj and not reason_obj.treated_as_valid):
                # Получаем объект для настроек (с eager loading org_unit и цепочки parent'ов)
                object_query = select(Object).where(Object.id == cancellation.object_id).options(
                    joinedload(Object.org_unit).joinedload('parent').joinedload('parent').joinedload('parent').joinedload('parent')
                )
                object_result = await self.session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if obj:
                    cancellation_settings = obj.get_cancellation_settings()
                    short_notice_hours = cancellation_settings.get('short_notice_hours')
                    short_notice_fine = cancellation_settings.get('short_notice_fine')
                    invalid_reason_fine = cancellation_settings.get('invalid_reason_fine')
                    
                    # Получаем смену для деталей
                    shift_query = select(ShiftSchedule).where(
                        ShiftSchedule.id == cancellation.shift_schedule_id
                    )
                    shift_result = await self.session.execute(shift_query)
                    shift = shift_result.scalar_one_or_none()
                    
                    if shift:
                        total_fine = Decimal('0')
                        
                        # Создаем штраф за короткий срок (если применимо)
                        if short_notice_hours and short_notice_fine and cancellation.hours_before_shift and float(cancellation.hours_before_shift) < short_notice_hours:
                            await self._create_specific_payroll_adjustment(
                                cancellation, shift, short_notice_fine,
                                'short_notice', cancellation.hours_before_shift, verified_by_user_id
                            )
                            total_fine += short_notice_fine
                            logger.info(f"Created short_notice fine {short_notice_fine} for cancellation {cancellation_id}")
                        
                        # Создаем штраф за недействительную причину (всегда при отклонении)
                        if invalid_reason_fine:
                            # Для "Другая причина" добавляем объяснение в описание
                            description_suffix = ""
                            if cancellation.cancellation_reason == 'other' and cancellation.reason_notes:
                                description_suffix = f". Объяснение: {cancellation.reason_notes}"
                            
                            await self._create_specific_payroll_adjustment(
                                cancellation, shift, invalid_reason_fine,
                                'invalid_reason', cancellation.hours_before_shift, verified_by_user_id,
                                description_suffix
                            )
                            total_fine += invalid_reason_fine
                            logger.info(f"Created invalid_reason fine {invalid_reason_fine} for cancellation {cancellation_id}")
                        
                        # Обновляем cancellation
                        cancellation.fine_amount = total_fine if total_fine > 0 else None
                        cancellation.fine_applied = total_fine > 0
                        cancellation.fine_reason = 'both' if total_fine > 0 else None
                        
                        logger.info(f"Created total fines {total_fine} for cancellation {cancellation_id} - document rejected")
            
            await self.session.commit()
            
            return {'success': True, 'message': 'Верификация выполнена'}
            
        except Exception as e:
            logger.error(f"Error verifying cancellation {cancellation_id}: {e}")
            await self.session.rollback()
            return {'success': False, 'message': f'Ошибка верификации: {str(e)}'}

