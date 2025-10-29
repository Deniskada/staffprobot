"""Shared-сервис для управления инцидентами (все роли)."""

from __future__ import annotations
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from decimal import Decimal
import json

from domain.entities.incident import Incident
from domain.entities.contract import Contract
from core.logging.logger import logger


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
        suggested_adjustments: Optional[List[Dict[str, Any]]] = None
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
            created_by=created_by
        )
        self.session.add(incident)
        await self.session.commit()
        await self.session.refresh(incident)
        logger.info(f"Created Incident: {incident.id}, category={category}, owner={owner_id}")
        return incident
    
    async def update_incident_status(
        self,
        incident_id: int,
        new_status: str,
        notes: Optional[str] = None
    ) -> Optional[Incident]:
        """Обновить статус инцидента."""
        incident = await self.session.get(Incident, incident_id)
        if not incident:
            return None
        
        incident.status = new_status
        if notes:
            incident.notes = (incident.notes or "") + f"\n[{new_status}] {notes}"
        
        await self.session.commit()
        await self.session.refresh(incident)
        logger.info(f"Updated Incident {incident_id}: status={new_status}")
        return incident
    
    async def get_incident_by_id(self, incident_id: int) -> Optional[Incident]:
        """Получить инцидент по ID."""
        result = await self.session.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()
    
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

