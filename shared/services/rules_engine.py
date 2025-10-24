from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.entities.rule import Rule


class RulesEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_rules(self, owner_id: int | None, scope: str) -> List[Rule]:
        query = select(Rule).where(Rule.scope == scope, Rule.is_active == True)
        if owner_id is not None:
            query = query.where((Rule.owner_id == owner_id) | (Rule.owner_id.is_(None)))
        query = query.order_by(Rule.priority, Rule.id)
        res = await self.session.execute(query)
        return res.scalars().all()

    async def evaluate(self, owner_id: int | None, scope: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Возвращает список действий (action dict) для применимых правил.
        Минимальная реализация: простая фильтрация по ключам context.
        condition_json/action_json - JSON-словари.
        """
        actions: List[Dict[str, Any]] = []
        rules = await self.load_rules(owner_id, scope)
        for r in rules:
            try:
                import json
                cond = json.loads(r.condition_json)
                act = json.loads(r.action_json)
            except Exception:
                continue

            if self._matches(cond, context):
                actions.append(act)
        return actions

    def _matches(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # Простой матчер: все пары key==value должны совпасть в context
        for k, v in condition.items():
            if context.get(k) != v:
                return False
        return True


