"""Сервис расчета штрафов за опоздание с наследованием настроек от организационной структуры."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.shift import Shift
from domain.entities.object import Object
from domain.entities.org_structure import OrgStructureUnit
from core.logging.logger import logger


class LatePenaltyCalculator:
    """Калькулятор штрафов за опоздание с учетом наследования настроек."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_late_penalty_settings(
        self,
        obj: Object
    ) -> Dict[str, Any]:
        """
        Получить настройки штрафа за опоздание с учетом наследования.
        
        Логика наследования:
        1. Если object.inherit_late_settings == False → использовать настройки объекта
        2. Если True → получить org_unit и вызвать org_unit.get_inherited_late_settings()
        3. Подняться по иерархии до тех пор, пока не найдем настройки
        
        Args:
            obj: Объект
            
        Returns:
            dict: {
                'threshold_minutes': int or None,  # Допустимое опоздание (может быть отрицательным)
                'penalty_per_minute': Decimal or None,  # Стоимость минуты штрафа
                'inherited_from': str or None  # Название источника настроек
            }
        """
        # Если объект НЕ наследует настройки, используем его собственные
        if not obj.inherit_late_settings:
            if obj.late_threshold_minutes is not None and obj.late_penalty_per_minute is not None:
                logger.debug(
                    "Используются настройки объекта",
                    object_id=obj.id,
                    threshold=obj.late_threshold_minutes,
                    penalty=float(obj.late_penalty_per_minute)
                )
                return {
                    'threshold_minutes': obj.late_threshold_minutes,
                    'penalty_per_minute': obj.late_penalty_per_minute,
                    'inherited_from': None  # Собственные настройки
                }
            else:
                # Настройки не заданы
                logger.warning(
                    "Объект не наследует настройки, но они не заданы",
                    object_id=obj.id
                )
                return {
                    'threshold_minutes': None,
                    'penalty_per_minute': None,
                    'inherited_from': None
                }
        
        # Если объект наследует настройки, идем по иерархии org_unit
        if not obj.org_unit_id:
            logger.warning(
                "Объект наследует настройки, но не привязан к подразделению",
                object_id=obj.id
            )
            return {
                'threshold_minutes': None,
                'penalty_per_minute': None,
                'inherited_from': None
            }
        
        # Загружаем org_unit (если еще не загружен)
        if not hasattr(obj, 'org_unit') or obj.org_unit is None:
            query = select(OrgStructureUnit).where(OrgStructureUnit.id == obj.org_unit_id)
            result = await self.session.execute(query)
            org_unit = result.scalar_one_or_none()
            
            if not org_unit:
                logger.warning(
                    "Подразделение не найдено",
                    org_unit_id=obj.org_unit_id,
                    object_id=obj.id
                )
                return {
                    'threshold_minutes': None,
                    'penalty_per_minute': None,
                    'inherited_from': None
                }
        else:
            org_unit = obj.org_unit
        
        # Используем метод модели OrgStructureUnit для получения настроек с наследованием
        inherited_settings = await self._get_org_unit_late_settings_recursive(org_unit)
        
        logger.debug(
            "Настройки получены с наследованием",
            object_id=obj.id,
            org_unit_id=org_unit.id,
            inherited_from=inherited_settings.get('inherited_from'),
            threshold=inherited_settings.get('threshold_minutes'),
            penalty=float(inherited_settings.get('penalty_per_minute') or 0)
        )
        
        return inherited_settings
    
    async def _get_org_unit_late_settings_recursive(
        self,
        org_unit: OrgStructureUnit
    ) -> Dict[str, Any]:
        """
        Рекурсивно получить настройки штрафов из org_unit с учетом наследования.
        
        Args:
            org_unit: Подразделение
            
        Returns:
            dict: Настройки штрафов
        """
        # Если подразделение НЕ наследует настройки и они заданы, возвращаем их
        if (not org_unit.inherit_late_settings and 
            org_unit.late_threshold_minutes is not None and 
            org_unit.late_penalty_per_minute is not None):
            return {
                'threshold_minutes': org_unit.late_threshold_minutes,
                'penalty_per_minute': org_unit.late_penalty_per_minute,
                'inherited_from': org_unit.name
            }
        
        # Если наследует или настройки не заданы, идем к родителю
        if org_unit.parent_id:
            # Загружаем родителя
            if not hasattr(org_unit, 'parent') or org_unit.parent is None:
                query = select(OrgStructureUnit).where(OrgStructureUnit.id == org_unit.parent_id)
                result = await self.session.execute(query)
                parent = result.scalar_one_or_none()
                
                if parent:
                    return await self._get_org_unit_late_settings_recursive(parent)
            elif org_unit.parent:
                return await self._get_org_unit_late_settings_recursive(org_unit.parent)
        
        # Настройки нигде не определены
        return {
            'threshold_minutes': None,
            'penalty_per_minute': None,
            'inherited_from': None
        }
    
    async def calculate_late_penalty(
        self,
        shift: Shift,
        obj: Optional[Object] = None
    ) -> Tuple[int, Decimal]:
        """
        Рассчитать штраф за опоздание.
        
        Args:
            shift: Смена
            obj: Объект (если не передан, загружается из shift.object)
            
        Returns:
            tuple: (late_minutes, penalty_amount)
                - late_minutes: количество минут опоздания (0 если нет опоздания)
                - penalty_amount: сумма штрафа (Decimal, 0.00 если нет штрафа)
        """
        # Загружаем объект если не передан
        if not obj:
            if hasattr(shift, 'object') and shift.object:
                obj = shift.object
            else:
                query = select(Object).where(Object.id == shift.object_id).options(
                    selectinload(Object.org_unit)
                )
                result = await self.session.execute(query)
                obj = result.scalar_one_or_none()
                
                if not obj:
                    logger.warning(
                        "Объект не найден для расчета штрафа",
                        shift_id=shift.id,
                        object_id=shift.object_id
                    )
                    return (0, Decimal('0.00'))
        
        # Получаем настройки штрафа
        settings = await self.get_late_penalty_settings(obj)
        
        threshold_minutes = settings.get('threshold_minutes')
        penalty_per_minute = settings.get('penalty_per_minute')
        
        # Если настройки не определены, штрафа нет
        if threshold_minutes is None or penalty_per_minute is None:
            logger.debug(
                "Настройки штрафа не определены",
                shift_id=shift.id,
                object_id=obj.id
            )
            return (0, Decimal('0.00'))
        
        # Проверяем наличие planned_start (для расчета опоздания)
        if not hasattr(shift, 'planned_start') or not shift.planned_start:
            # Для Shift без planned_start (не из ShiftSchedule) штраф не применяется
            logger.debug(
                "Смена без planned_start, штраф не применяется",
                shift_id=shift.id
            )
            return (0, Decimal('0.00'))
        
        # Рассчитываем фактическое опоздание
        planned_start = shift.planned_start
        actual_start = shift.start_time
        
        if not actual_start:
            logger.warning(
                "Смена без start_time",
                shift_id=shift.id
            )
            return (0, Decimal('0.00'))
        
        # Разница в минутах
        delta = actual_start - planned_start
        late_minutes = int(delta.total_seconds() / 60)
        
        # Если опоздание меньше или равно допустимому, штрафа нет
        if late_minutes <= threshold_minutes:
            logger.debug(
                "Опоздание в пределах допустимого",
                shift_id=shift.id,
                late_minutes=late_minutes,
                threshold=threshold_minutes
            )
            return (0, Decimal('0.00'))
        
        # Рассчитываем сумму штрафа
        # Штрафуем только за минуты сверх допустимого порога
        penalized_minutes = late_minutes - threshold_minutes
        penalty_amount = Decimal(str(penalized_minutes)) * Decimal(str(penalty_per_minute))
        
        logger.info(
            "Рассчитан штраф за опоздание",
            shift_id=shift.id,
            late_minutes=late_minutes,
            threshold=threshold_minutes,
            penalized_minutes=penalized_minutes,
            penalty_per_minute=float(penalty_per_minute),
            penalty_amount=float(penalty_amount),
            inherited_from=settings.get('inherited_from')
        )
        
        return (late_minutes, penalty_amount)

