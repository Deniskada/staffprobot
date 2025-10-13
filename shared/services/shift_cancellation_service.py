"""Сервис для работы с отменой смен."""

from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.shift_schedule import ShiftSchedule
from domain.entities.shift_cancellation import ShiftCancellation
from domain.entities.object import Object
from domain.entities.payroll_adjustment import PayrollAdjustment
from domain.entities.user import User
from core.logging.logger import logger


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
        contract_id: Optional[int] = None
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
            
            # Получаем объект для настроек штрафов
            object_query = select(Object).where(Object.id == shift.object_id)
            object_result = await self.session.execute(object_query)
            obj = object_result.scalar_one_or_none()
            
            # Вычисляем штрафы (только для отмены сотрудником)
            fine_amount = None
            fine_reason = None
            
            if cancelled_by_type == 'employee' and obj:
                cancellation_settings = obj.get_cancellation_settings()
                
                short_notice_hours = cancellation_settings.get('short_notice_hours')
                short_notice_fine = cancellation_settings.get('short_notice_fine')
                invalid_reason_fine = cancellation_settings.get('invalid_reason_fine')
                
                # Проверяем, является ли причина уважительной (требует верификации)
                is_valid_reason = cancellation_reason in ['medical_cert', 'emergency_cert', 'police_cert']
                
                # Штраф за короткий срок
                if short_notice_hours and short_notice_fine and float(hours_before_shift) < short_notice_hours:
                    fine_amount = short_notice_fine
                    fine_reason = 'short_notice'
                
                # Штраф за неуважительную причину (если нет документа)
                if not is_valid_reason and invalid_reason_fine and cancellation_reason not in ['owner_decision', 'contract_termination']:
                    if fine_amount:
                        fine_amount += invalid_reason_fine
                    else:
                        fine_amount = invalid_reason_fine
                        fine_reason = 'invalid_reason'
            
            # Отменяем смену
            shift.status = 'cancelled'
            
            # Создаем запись о отмене
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
                document_verified=False,  # Требует модерации для уважительных причин
                fine_amount=fine_amount,
                fine_reason=fine_reason,
                fine_applied=False,
                contract_id=contract_id
            )
            
            self.session.add(cancellation)
            await self.session.flush()  # Получаем ID
            
            # Создаем корректировку начислений, если есть штраф
            if fine_amount and float(fine_amount) > 0:
                payroll_adjustment = await self._create_payroll_adjustment(
                    cancellation, shift, fine_amount, cancelled_by_user_id
                )
                cancellation.payroll_adjustment_id = payroll_adjustment.id
                cancellation.fine_applied = True
            
            await self.session.commit()
            
            logger.info(
                f"Shift {shift_schedule_id} cancelled by {cancelled_by_type} "
                f"(user_id={cancelled_by_user_id}), fine={fine_amount}"
            )
            
            return {
                'success': True,
                'cancellation_id': cancellation.id,
                'fine_amount': fine_amount,
                'message': 'Смена отменена'
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
            
            # Если справка подтверждена и был штраф - удаляем его
            if is_approved and cancellation.payroll_adjustment_id:
                adjustment_query = select(PayrollAdjustment).where(
                    PayrollAdjustment.id == cancellation.payroll_adjustment_id
                )
                adjustment_result = await self.session.execute(adjustment_query)
                adjustment = adjustment_result.scalar_one_or_none()
                
                if adjustment and not adjustment.is_applied:
                    # Помечаем корректировку как удаленную (обнуляем сумму)
                    adjustment.amount = Decimal('0')
                    adjustment.description += " (Справка подтверждена, штраф снят)"
                    cancellation.fine_applied = False
                    
                    logger.info(f"Removed fine for cancellation {cancellation_id} - document verified")
            
            # Если справка отклонена и не было штрафа - создаем его
            elif not is_approved and not cancellation.fine_applied:
                # Получаем объект для настроек
                object_query = select(Object).where(Object.id == cancellation.object_id)
                object_result = await self.session.execute(object_query)
                obj = object_result.scalar_one_or_none()
                
                if obj:
                    cancellation_settings = obj.get_cancellation_settings()
                    invalid_reason_fine = cancellation_settings.get('invalid_reason_fine')
                    
                    if invalid_reason_fine:
                        # Получаем смену для деталей
                        shift_query = select(ShiftSchedule).where(
                            ShiftSchedule.id == cancellation.shift_schedule_id
                        )
                        shift_result = await self.session.execute(shift_query)
                        shift = shift_result.scalar_one_or_none()
                        
                        if shift:
                            adjustment = await self._create_payroll_adjustment(
                                cancellation, shift, invalid_reason_fine, verified_by_user_id
                            )
                            cancellation.payroll_adjustment_id = adjustment.id
                            cancellation.fine_applied = True
                            cancellation.fine_amount = invalid_reason_fine
                            cancellation.fine_reason = 'invalid_reason'
                            
                            logger.info(f"Created fine for cancellation {cancellation_id} - document rejected")
            
            await self.session.commit()
            
            return {'success': True, 'message': 'Верификация выполнена'}
            
        except Exception as e:
            logger.error(f"Error verifying cancellation {cancellation_id}: {e}")
            await self.session.rollback()
            return {'success': False, 'message': f'Ошибка верификации: {str(e)}'}

