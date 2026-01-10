"""Shared-сервис для управления инцидентами (все роли)."""

from __future__ import annotations
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from decimal import Decimal
import json

from domain.entities.incident import Incident
from domain.entities.contract import Contract
from domain.entities.user import User
from core.logging.logger import logger

if TYPE_CHECKING:
    from shared.services.notification_service import NotificationService


class IncidentService:
    """Универсальный сервис для инцидентов (owner/manager/employee)."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_incidents_for_role(
        self,
        user_id: int,
        role: str,
        owner_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Incident]:
        """Получить инциденты с учётом роли."""
        query = select(Incident)
        
        if role == "owner":
            query = query.where(Incident.owner_id == user_id)
        elif role == "manager":
            # Manager видит инциденты на своих объектах
            if not owner_id:
                return []
            contract_query = select(Contract.allowed_objects).where(
                and_(
                    Contract.employee_id == user_id,
                    Contract.owner_id == owner_id,
                    Contract.role == "manager",
                    Contract.is_active == True
                )
            )
            contract_result = await self.session.execute(contract_query)
            contract = contract_result.scalar_one_or_none()
            if not contract or not contract.allowed_objects:
                return []
            allowed_obj_ids = contract.allowed_objects
            query = query.where(Incident.object_id.in_(allowed_obj_ids))
        elif role == "employee":
            # Employee видит только свои инциденты
            query = query.where(Incident.employee_id == user_id)
        else:
            return []
        
        if status_filter:
            query = query.where(Incident.status == status_filter)
        
        query = query.order_by(Incident.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create_incident(
        self,
        owner_id: int,
        category: str,
        created_by: int,
        object_id: Optional[int] = None,
        shift_schedule_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        severity: Optional[str] = None,
        reason_code: Optional[str] = None,
        notes: Optional[str] = None,
        evidence_media_ids: Optional[List[int]] = None,
        suggested_adjustments: Optional[List[Dict[str, Any]]] = None,
        custom_number: Optional[str] = None,
        custom_date: Optional["date"] = None,
        damage_amount: Optional["Decimal"] = None
    ) -> Incident:
        """Создать инцидент."""
        incident = Incident(
            owner_id=owner_id,
            object_id=object_id,
            shift_schedule_id=shift_schedule_id,
            employee_id=employee_id,
            category=category,
            severity=severity or "medium",
            status="new",
            reason_code=reason_code,
            notes=notes,
            evidence_media_ids=json.dumps(evidence_media_ids) if evidence_media_ids else None,
            suggested_adjustments=json.dumps(suggested_adjustments) if suggested_adjustments else None,
            created_by=created_by,
            custom_number=custom_number,
            custom_date=custom_date,
            damage_amount=damage_amount
        )
        self.session.add(incident)
        await self.session.commit()
        await self.session.refresh(incident)
        logger.info(f"Created Incident: {incident.id}, category={category}, owner={owner_id}")

        # История создания
        try:
            from domain.entities.incident_history import IncidentHistory
            self.session.add(IncidentHistory(
                incident_id=incident.id,
                changed_by=created_by,
                field="create",
                old_value=None,
                new_value=f"created with category={category}"
            ))
            await self.session.commit()
        except Exception:
            pass

        # Автоудержание по ущербу
        if damage_amount and employee_id:
            from shared.services.payroll_adjustment_service import PayrollAdjustmentService
            adj_service = PayrollAdjustmentService(self.session)
            desc = (
                f"Ущерб по инциденту {custom_number}" if custom_number else "Ущерб по инциденту"
            )
            await adj_service.create_incident_deduction(
                employee_id=employee_id,
                object_id=object_id,
                amount=damage_amount,
                adjustment_date=custom_date or None,
                description=desc,
                created_by=created_by,
                incident_id=incident.id
            )
            await self.session.commit()
        
        # Отправляем уведомления о создании инцидента
        try:
            await self._notify_incident_created(incident)
        except Exception as notification_error:
            logger.warning(
                "Failed to send incident created notifications",
                incident_id=incident.id,
                error=str(notification_error),
            )
        
        return incident
    
    async def update_incident_status(
        self,
        incident_id: int,
        new_status: str,
        notes: Optional[str] = None,
        changed_by: Optional[int] = None
    ) -> Optional[Incident]:
        """Обновить статус инцидента."""
        incident = await self.session.get(Incident, incident_id)
        if not incident:
            return None
        
        old_status = incident.status
        incident.status = new_status
        if notes:
            incident.notes = (incident.notes or "") + f"\n[{new_status}] {notes}"
        
        # История
        changed_by_id = changed_by or incident.created_by
        try:
            from domain.entities.incident_history import IncidentHistory
            history_entry = IncidentHistory(
                incident_id=incident.id,
                changed_by=changed_by_id,
                field="status",
                old_value=old_status,
                new_value=new_status
            )
            self.session.add(history_entry)
        except Exception:
            pass

        await self.session.commit()
        await self.session.refresh(incident)
        logger.info(f"Updated Incident {incident_id}: status={new_status}")

        # Отправляем уведомления об изменении статуса
        try:
            if new_status == "resolved":
                await self._notify_incident_resolved(incident, changed_by=changed_by_id)
            elif new_status == "rejected":
                await self._notify_incident_rejected(incident, changed_by=changed_by_id)
        except Exception as notification_error:
            logger.warning(
                "Failed to send incident status change notifications",
                incident_id=incident.id,
                new_status=new_status,
                error=str(notification_error),
            )

        # Автокорректировки по статусам
        if new_status == "resolved" and incident.damage_amount and incident.employee_id:
            from shared.services.payroll_adjustment_service import PayrollAdjustmentService
            from datetime import date as date_type
            adj_service = PayrollAdjustmentService(self.session)
            desc = (
                f"Возврат удержания по инциденту {incident.custom_number}" if incident.custom_number else "Возврат удержания по инциденту"
            )
            # Логика: если custom_date указана и она больше текущей даты, использовать её, иначе текущую дату/время
            adjustment_date = None
            if incident.custom_date:
                today = date_type.today()
                if incident.custom_date > today:
                    adjustment_date = incident.custom_date
            await adj_service.create_incident_refund(
                employee_id=incident.employee_id,
                object_id=incident.object_id,
                amount=incident.damage_amount,
                adjustment_date=adjustment_date,
                description=desc,
                created_by=incident.created_by or 0,
                incident_id=incident.id
            )
            await self.session.commit()
        
        if old_status == "resolved" and new_status == "in_review" and incident.employee_id:
            # Откат: проверить возвраты
            from sqlalchemy import select
            from domain.entities.payroll_adjustment import PayrollAdjustment
            res = await self.session.execute(
                select(PayrollAdjustment).where(
                    PayrollAdjustment.employee_id == incident.employee_id,
                    PayrollAdjustment.adjustment_type == 'incident_refund'
                ).order_by(PayrollAdjustment.created_at.desc()).limit(50)
            )
            refunds = [a for a in res.scalars().all() if (a.details or {}).get('incident_id') == incident.id]
            if refunds:
                # Если есть непримененные — удалить
                unapplied = [r for r in refunds if not r.is_applied]
                if unapplied:
                    for r in unapplied:
                        await self.session.delete(r)
                    await self.session.commit()
                else:
                    # Создать новое удержание
                    from shared.services.payroll_adjustment_service import PayrollAdjustmentService
                    adj_service = PayrollAdjustmentService(self.session)
                    desc2 = (
                        f"Удержание по инциденту {incident.custom_number}" if incident.custom_number else "Удержание по инциденту"
                    )
                    await adj_service.create_incident_deduction(
                        employee_id=incident.employee_id,
                        object_id=incident.object_id,
                        amount=incident.damage_amount or Decimal('0.00'),
                        adjustment_date=incident.custom_date or None,
                        description=desc2,
                        created_by=incident.created_by or 0,
                        incident_id=incident.id
                    )
                    await self.session.commit()
        
        return incident

    async def update_incident(
        self,
        incident_id: int,
        data: Dict[str, Any],
        changed_by: int
    ) -> Optional[Incident]:
        """Обновить произвольные поля инцидента с записью истории."""
        incident = await self.session.get(Incident, incident_id)
        if not incident:
            return None
        
        # Проверка статуса: решенные и отклоненные инциденты нельзя редактировать
        if incident.status in ['resolved', 'rejected']:
            raise ValueError(f"Нельзя редактировать инцидент со статусом '{incident.status}'")
        
        from domain.entities.incident_history import IncidentHistory
        old_employee_id = incident.employee_id
        old_damage_amount = incident.damage_amount
        old_custom_date = incident.custom_date
        custom_date_changed = False
        
        changed_fields = [
            'category', 'severity', 'status', 'reason_code', 'notes',
            'object_id', 'shift_schedule_id', 'employee_id',
            'custom_number', 'custom_date', 'damage_amount'
        ]
        for field in changed_fields:
            if field in data:
                old_value = getattr(incident, field)
                new_value = data[field]
                if old_value != new_value:
                    if field == "custom_date":
                        custom_date_changed = True
                    setattr(incident, field, new_value)
                    self.session.add(IncidentHistory(
                        incident_id=incident.id,
                        changed_by=changed_by,
                        field=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None
                    ))
        
        # Обработка изменения сотрудника: перераспределение корректировок
        new_employee_id = incident.employee_id
        new_damage_amount = incident.damage_amount
        
        if old_employee_id != new_employee_id and old_employee_id and new_employee_id:
            # Старый сотрудник: создаем доплату (возврат удержания)
            if old_damage_amount:
                from shared.services.payroll_adjustment_service import PayrollAdjustmentService
                from datetime import date as date_type
                adj_service = PayrollAdjustmentService(self.session)
                desc_refund = (
                    f"Возврат удержания по инциденту {incident.custom_number}" if incident.custom_number else "Возврат удержания по инциденту"
                )
                # Логика даты для доплат: если custom_date указана и она больше текущей даты, использовать её, иначе текущую дату/время
                adjustment_date_refund = None
                if incident.custom_date:
                    today = date_type.today()
                    if incident.custom_date > today:
                        adjustment_date_refund = incident.custom_date
                await adj_service.create_incident_refund(
                    employee_id=old_employee_id,
                    object_id=incident.object_id,
                    amount=old_damage_amount,
                    adjustment_date=adjustment_date_refund,
                    description=desc_refund,
                    created_by=changed_by,
                    incident_id=incident.id
                )
                logger.info(f"Создана доплата старому сотруднику {old_employee_id} при изменении инцидента {incident_id}")
            
            # Новый сотрудник: создаем удержание
            if new_damage_amount:
                from shared.services.payroll_adjustment_service import PayrollAdjustmentService
                adj_service = PayrollAdjustmentService(self.session)
                desc_deduction = (
                    f"Удержание по инциденту {incident.custom_number}" if incident.custom_number else "Удержание по инциденту"
                )
                await adj_service.create_incident_deduction(
                    employee_id=new_employee_id,
                    object_id=incident.object_id,
                    amount=new_damage_amount,
                    adjustment_date=incident.custom_date or None,
                    description=desc_deduction,
                    created_by=changed_by,
                    incident_id=incident.id
                )
                logger.info(f"Создано удержание новому сотруднику {new_employee_id} при изменении инцидента {incident_id}")
        
        if custom_date_changed:
            await self._update_incident_adjustment_dates(
                incident_id=incident.id,
                new_date=incident.custom_date
            )
        
        await self.session.commit()
        await self.session.refresh(incident)
        return incident
    
    async def _update_incident_adjustment_dates(
        self,
        *,
        incident_id: int,
        new_date: Optional[date]
    ) -> None:
        """Обновить created_at корректировок, связанных с инцидентом."""
        from datetime import datetime, timezone
        from domain.entities.payroll_adjustment import PayrollAdjustment
        from sqlalchemy import select
        
        incident = await self.session.get(Incident, incident_id)
        if not incident:
            return
        
        query = select(PayrollAdjustment).where(
            PayrollAdjustment.details.isnot(None),
            PayrollAdjustment.details['incident_id'].astext == str(incident_id),
            PayrollAdjustment.employee_id == incident.employee_id
        )
        result = await self.session.execute(query)
        adjustments = result.scalars().all()
        if not adjustments:
            return
        
        if new_date:
            naive_dt = datetime.combine(new_date, datetime.min.time())
            new_created_at = naive_dt.replace(tzinfo=timezone.utc)
        else:
            new_created_at = datetime.now(timezone.utc)
        
        now_ts = datetime.now(timezone.utc)
        updated_count = 0
        for adj in adjustments:
            adj.created_at = new_created_at
            adj.updated_at = now_ts
            if adj.is_applied or adj.payroll_entry_id:
                adj.is_applied = False
                adj.payroll_entry_id = None
            updated_count += 1
        
        logger.info(
            "Обновлены даты корректировок по инциденту",
            incident_id=incident_id,
            adjustments=updated_count,
            employee_id=incident.employee_id,
            new_date=new_date.isoformat() if new_date else None
        )
    
    async def get_incident_by_id(self, incident_id: int) -> Optional[Incident]:
        """Получить инцидент по ID."""
        result = await self.session.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()
    
    async def get_adjustments_by_incident(self, incident_id: int) -> List["PayrollAdjustment"]:
        """Получить корректировки, связанные с инцидентом."""
        from domain.entities.payroll_adjustment import PayrollAdjustment
        query = (
            select(PayrollAdjustment)
            .where(
                PayrollAdjustment.details.isnot(None),
                PayrollAdjustment.details['incident_id'].astext == str(incident_id)
            )
            .order_by(PayrollAdjustment.created_at.desc())
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def apply_suggested_adjustments(
        self,
        incident_id: int
    ) -> bool:
        """Применить предложенные корректировки к payroll."""
        from shared.services.payroll_adjustment_service import PayrollAdjustmentService
        
        incident = await self.get_incident_by_id(incident_id)
        if not incident or not incident.suggested_adjustments:
            return False
        
        adjustments = json.loads(incident.suggested_adjustments)
        adj_service = PayrollAdjustmentService(self.session)
        
        for adj in adjustments:
            await adj_service.create_adjustment(
                shift_schedule_id=incident.shift_schedule_id,
                employee_id=incident.employee_id,
                type=adj.get("type", "penalty"),
                reason=adj.get("reason", f"Incident #{incident.id}"),
                amount=Decimal(str(adj["amount"])),
                notes=adj.get("notes", "")
            )
        
        logger.info(f"Applied {len(adjustments)} adjustments for Incident {incident_id}")
        return True
    
    async def cancel_incident(
        self,
        incident_id: int,
        cancellation_reason: str,
        cancelled_by: int,
        notes: Optional[str] = None
    ) -> Optional[Incident]:
        """Отменить инцидент с указанием причины отмены."""
        incident = await self.session.get(Incident, incident_id)
        if not incident:
            return None
        
        # Проверка: нельзя отменить уже отмененный, решенный или отклоненный инцидент
        if incident.status in ['cancelled', 'resolved', 'rejected']:
            raise ValueError(f"Нельзя отменить инцидент со статусом '{incident.status}'")
        
        old_status = incident.status
        incident.status = "cancelled"
        
        # Сохраняем причину отмены в notes
        cancellation_note = f"\n[ОТМЕНЕН] Причина: {cancellation_reason}"
        if notes:
            cancellation_note += f"\nКомментарий: {notes}"
        incident.notes = (incident.notes or "") + cancellation_note
        
        # История
        try:
            from domain.entities.incident_history import IncidentHistory
            history_entry = IncidentHistory(
                incident_id=incident.id,
                changed_by=cancelled_by,
                field="status",
                old_value=old_status,
                new_value="cancelled"
            )
            # Причина отмены сохраняется в notes инцидента
            self.session.add(history_entry)
        except Exception:
            pass
        
        await self.session.commit()
        await self.session.refresh(incident)
        logger.info(f"Cancelled Incident {incident_id}: reason={cancellation_reason}")
        
        # Отправляем уведомления об отмене
        try:
            await self._notify_incident_cancelled(incident, cancellation_reason, changed_by=cancelled_by)
        except Exception as notification_error:
            logger.warning(
                "Failed to send incident cancelled notifications",
                incident_id=incident.id,
                error=str(notification_error),
            )
        
        return incident
    
    async def _notify_incident_created(self, incident: Incident) -> None:
        """Отправить уведомления о создании инцидента."""
        from shared.services.notification_service import NotificationService
        from shared.templates.notifications.base_templates import NotificationTemplateManager
        from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority
        from domain.entities.user import User
        from domain.entities.object import Object
        from sqlalchemy.orm import selectinload
        from datetime import datetime, timezone
        
        # Загружаем инцидент с отношениями
        incident_result = await self.session.execute(
            select(Incident)
            .options(
                selectinload(Incident.owner),
                selectinload(Incident.employee),
                selectinload(Incident.object)
            )
            .where(Incident.id == incident.id)
        )
        incident_with_relations = incident_result.scalar_one_or_none()
        if not incident_with_relations:
            return
        
        # Получаем категорию для отображения
        category_display = self._get_category_display(incident_with_relations.category)
        severity_display = self._get_severity_display(incident_with_relations.severity)
        incident_date = incident_with_relations.custom_date.strftime('%d.%m.%Y') if incident_with_relations.custom_date else datetime.now(timezone.utc).strftime('%d.%m.%Y')
        incident_number = incident_with_relations.custom_number or str(incident_with_relations.id)
        object_name = incident_with_relations.object.name if incident_with_relations.object else "Не указан"
        employee_name = (
            f"{incident_with_relations.employee.first_name} {incident_with_relations.employee.last_name}".strip()
            if incident_with_relations.employee
            else "Не указан"
        )
        
        template_vars = {
            "incident_number": incident_number,
            "category": category_display,
            "severity": severity_display,
            "object_name": object_name,
            "employee_name": employee_name,
            "incident_date": incident_date
        }
        
        notification_service = NotificationService()
        
        # Уведомляем владельца
        if incident_with_relations.owner:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_CREATED,
                incident_with_relations.owner.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.HIGH
            )
        
        # Уведомляем сотрудника (если есть)
        if incident_with_relations.employee and incident_with_relations.employee.id != incident_with_relations.owner.id:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_CREATED,
                incident_with_relations.employee.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.HIGH
            )
        
        # Уведомляем управляющих объекта (если есть объект)
        if incident_with_relations.object:
            managers = await self._get_managers_for_object(incident_with_relations.object_id)
            for manager_id in managers:
                if manager_id != incident_with_relations.owner.id and manager_id != (incident_with_relations.employee_id or 0):
                    await self._send_incident_notification(
                        notification_service,
                        NotificationType.INCIDENT_CREATED,
                        manager_id,
                        template_vars,
                        {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                        NotificationPriority.HIGH
                    )
    
    async def _notify_incident_resolved(self, incident: Incident, changed_by: int) -> None:
        """Отправить уведомления о решении инцидента."""
        from shared.services.notification_service import NotificationService
        from shared.templates.notifications.base_templates import NotificationTemplateManager
        from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority
        from domain.entities.user import User
        from domain.entities.object import Object
        from sqlalchemy.orm import selectinload
        from datetime import datetime, timezone
        
        incident_result = await self.session.execute(
            select(Incident)
            .options(
                selectinload(Incident.owner),
                selectinload(Incident.employee),
                selectinload(Incident.object)
            )
            .where(Incident.id == incident.id)
        )
        incident_with_relations = incident_result.scalar_one_or_none()
        if not incident_with_relations:
            return
        
        category_display = self._get_category_display(incident_with_relations.category)
        incident_number = incident_with_relations.custom_number or str(incident_with_relations.id)
        object_name = incident_with_relations.object.name if incident_with_relations.object else "Не указан"
        employee_name = (
            f"{incident_with_relations.employee.first_name} {incident_with_relations.employee.last_name}".strip()
            if incident_with_relations.employee
            else "Не указан"
        )
        resolved_date = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')
        
        template_vars = {
            "incident_number": incident_number,
            "category": category_display,
            "object_name": object_name,
            "employee_name": employee_name,
            "resolved_date": resolved_date
        }
        
        notification_service = NotificationService()
        
        # Уведомляем владельца
        if incident_with_relations.owner:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_RESOLVED,
                incident_with_relations.owner.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем сотрудника
        if incident_with_relations.employee and incident_with_relations.employee.id != incident_with_relations.owner.id:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_RESOLVED,
                incident_with_relations.employee.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем управляющих
        if incident_with_relations.object:
            managers = await self._get_managers_for_object(incident_with_relations.object_id)
            for manager_id in managers:
                if manager_id != incident_with_relations.owner.id and manager_id != (incident_with_relations.employee_id or 0):
                    await self._send_incident_notification(
                        notification_service,
                        NotificationType.INCIDENT_RESOLVED,
                        manager_id,
                        template_vars,
                        {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                        NotificationPriority.NORMAL
                    )
    
    async def _notify_incident_rejected(self, incident: Incident, changed_by: int) -> None:
        """Отправить уведомления об отклонении инцидента."""
        from shared.services.notification_service import NotificationService
        from shared.templates.notifications.base_templates import NotificationTemplateManager
        from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority
        from domain.entities.user import User
        from domain.entities.object import Object
        from sqlalchemy.orm import selectinload
        from datetime import datetime, timezone
        
        incident_result = await self.session.execute(
            select(Incident)
            .options(
                selectinload(Incident.owner),
                selectinload(Incident.employee),
                selectinload(Incident.object)
            )
            .where(Incident.id == incident.id)
        )
        incident_with_relations = incident_result.scalar_one_or_none()
        if not incident_with_relations:
            return
        
        category_display = self._get_category_display(incident_with_relations.category)
        incident_number = incident_with_relations.custom_number or str(incident_with_relations.id)
        object_name = incident_with_relations.object.name if incident_with_relations.object else "Не указан"
        employee_name = (
            f"{incident_with_relations.employee.first_name} {incident_with_relations.employee.last_name}".strip()
            if incident_with_relations.employee
            else "Не указан"
        )
        rejected_date = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')
        
        template_vars = {
            "incident_number": incident_number,
            "category": category_display,
            "object_name": object_name,
            "employee_name": employee_name,
            "rejected_date": rejected_date
        }
        
        notification_service = NotificationService()
        
        # Уведомляем владельца
        if incident_with_relations.owner:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_REJECTED,
                incident_with_relations.owner.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем сотрудника
        if incident_with_relations.employee and incident_with_relations.employee.id != incident_with_relations.owner.id:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_REJECTED,
                incident_with_relations.employee.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем управляющих
        if incident_with_relations.object:
            managers = await self._get_managers_for_object(incident_with_relations.object_id)
            for manager_id in managers:
                if manager_id != incident_with_relations.owner.id and manager_id != (incident_with_relations.employee_id or 0):
                    await self._send_incident_notification(
                        notification_service,
                        NotificationType.INCIDENT_REJECTED,
                        manager_id,
                        template_vars,
                        {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                        NotificationPriority.NORMAL
                    )
    
    async def _notify_incident_cancelled(
        self,
        incident: Incident,
        cancellation_reason: str,
        changed_by: int
    ) -> None:
        """Отправить уведомления об отмене инцидента."""
        from shared.services.notification_service import NotificationService
        from shared.templates.notifications.base_templates import NotificationTemplateManager
        from domain.entities.notification import NotificationType, NotificationChannel, NotificationPriority
        from domain.entities.user import User
        from domain.entities.object import Object
        from sqlalchemy.orm import selectinload
        from datetime import datetime, timezone
        
        incident_result = await self.session.execute(
            select(Incident)
            .options(
                selectinload(Incident.owner),
                selectinload(Incident.employee),
                selectinload(Incident.object)
            )
            .where(Incident.id == incident.id)
        )
        incident_with_relations = incident_result.scalar_one_or_none()
        if not incident_with_relations:
            return
        
        category_display = self._get_category_display(incident_with_relations.category)
        incident_number = incident_with_relations.custom_number or str(incident_with_relations.id)
        object_name = incident_with_relations.object.name if incident_with_relations.object else "Не указан"
        employee_name = (
            f"{incident_with_relations.employee.first_name} {incident_with_relations.employee.last_name}".strip()
            if incident_with_relations.employee
            else "Не указан"
        )
        cancelled_date = datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')
        cancellation_reason_display = self._get_cancellation_reason_display(cancellation_reason)
        
        template_vars = {
            "incident_number": incident_number,
            "cancellation_reason": cancellation_reason_display,
            "category": category_display,
            "object_name": object_name,
            "employee_name": employee_name,
            "cancelled_date": cancelled_date
        }
        
        notification_service = NotificationService()
        
        # Уведомляем владельца
        if incident_with_relations.owner:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_CANCELLED,
                incident_with_relations.owner.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем сотрудника
        if incident_with_relations.employee and incident_with_relations.employee.id != incident_with_relations.owner.id:
            await self._send_incident_notification(
                notification_service,
                NotificationType.INCIDENT_CANCELLED,
                incident_with_relations.employee.id,
                template_vars,
                {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                NotificationPriority.NORMAL
            )
        
        # Уведомляем управляющих
        if incident_with_relations.object:
            managers = await self._get_managers_for_object(incident_with_relations.object_id)
            for manager_id in managers:
                if manager_id != incident_with_relations.owner.id and manager_id != (incident_with_relations.employee_id or 0):
                    await self._send_incident_notification(
                        notification_service,
                        NotificationType.INCIDENT_CANCELLED,
                        manager_id,
                        template_vars,
                        {"incident_id": incident_with_relations.id, "object_id": incident_with_relations.object_id},
                        NotificationPriority.NORMAL
                    )
    
    async def _send_incident_notification(
        self,
        notification_service: "NotificationService",
        notif_type: "NotificationType",
        user_id: int,
        template_vars: Dict[str, str],
        data: Dict[str, Any],
        priority: "NotificationPriority"
    ) -> None:
        """Отправить уведомление об инциденте с учетом настроек пользователя."""
        from shared.templates.notifications.base_templates import NotificationTemplateManager
        from domain.entities.notification import NotificationChannel, NotificationStatus
        from domain.entities.user import User
        from core.celery.tasks.notification_tasks import send_notification_now
        
        # Проверяем настройки пользователя
        user_result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return
        
        prefs = user.notification_preferences or {}
        type_code = notif_type.value
        type_prefs = prefs.get(type_code, {})
        telegram_enabled = type_prefs.get("telegram", True) if type_code in prefs else True
        inapp_enabled = type_prefs.get("inapp", True) if type_code in prefs else True
        
        if not telegram_enabled and not inapp_enabled:
            logger.debug(f"Incident notifications disabled for user {user_id}, type {type_code}")
            return
        
        # Отправляем Telegram уведомление
        if telegram_enabled:
            rendered_tg = NotificationTemplateManager.render(notif_type, NotificationChannel.TELEGRAM, template_vars)
            notification_tg = await notification_service.create_notification(
                user_id=user_id,
                type=notif_type,
                channel=NotificationChannel.TELEGRAM,
                title=rendered_tg["title"],
                message=rendered_tg["message"],
                data=data,
                priority=priority,
                scheduled_at=None
            )
            
            if notification_tg and hasattr(notification_tg, 'id') and notification_tg.id:
                try:
                    send_notification_now.apply_async(
                        args=[notification_tg.id],
                        queue="notifications"
                    )
                    logger.debug(
                        "Enqueued incident Telegram notification for sending",
                        notification_id=notification_tg.id,
                        user_id=user_id,
                        notification_type=notif_type.value,
                    )
                except Exception as send_exc:
                    logger.warning(
                        "Failed to enqueue incident Telegram notification",
                        notification_id=notification_tg.id if notification_tg else None,
                        error=str(send_exc),
                    )
        
        # Отправляем In-App уведомление
        if inapp_enabled:
            rendered_inapp = NotificationTemplateManager.render(notif_type, NotificationChannel.IN_APP, template_vars)
            await notification_service.create_notification(
                user_id=user_id,
                type=notif_type,
                channel=NotificationChannel.IN_APP,
                title=rendered_inapp["title"],
                message=rendered_inapp["message"],
                data=data,
                priority=priority,
                scheduled_at=None
            )
    
    async def _get_managers_for_object(self, object_id: Optional[int]) -> List[int]:
        """Получить список user_id управляющих, имеющих доступ к объекту."""
        if not object_id:
            return []
        
        try:
            from shared.services.manager_permission_service import ManagerPermissionService
            permission_service = ManagerPermissionService(self.session)
            permissions = await permission_service.get_object_permissions(object_id)
            
            manager_user_ids: List[int] = []
            for permission in permissions:
                if not permission.has_any_permission():
                    continue
                if not permission.contract or not permission.contract.is_active:
                    continue
                manager_user_ids.append(permission.contract.employee_id)
            
            return list(set(manager_user_ids))
        except Exception as exc:
            logger.error(
                "Failed to get managers for object",
                object_id=object_id,
                error=str(exc),
            )
            return []
    
    def _get_category_display(self, category: str) -> str:
        """Получить отображаемое название категории."""
        category_map = {
            "late_arrival": "Опоздание",
            "task_non_completion": "Невыполнение задачи",
            "damage": "Повреждение",
            "violation": "Нарушение"
        }
        return category_map.get(category, category)
    
    def _get_severity_display(self, severity: Optional[str]) -> str:
        """Получить отображаемое название критичности."""
        if not severity:
            return "Средняя"
        severity_map = {
            "low": "Низкая",
            "medium": "Средняя",
            "high": "Высокая",
            "critical": "Критично"
        }
        return severity_map.get(severity, severity)
    
    def _get_cancellation_reason_display(self, reason: str) -> str:
        """Получить отображаемое название причины отмены."""
        reason_map = {
            "duplicate": "Ошибочно заведен (дубль)",
            "not_confirmed": "Инцидент не подтвердился",
            "owner_decision": "Решение владельца"
        }
        return reason_map.get(reason, reason)

