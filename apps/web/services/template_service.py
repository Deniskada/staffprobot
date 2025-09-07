"""
Сервис для работы с шаблонами планирования
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from domain.entities.planning_template import PlanningTemplate, TemplateTimeSlot
from domain.entities.object import Object
from core.logging.logger import logger


class TemplateService:
    """Сервис для работы с шаблонами планирования"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_template(
        self, 
        template_data: Dict[str, Any], 
        owner_telegram_id: int
    ) -> Optional[PlanningTemplate]:
        """Создание нового шаблона планирования"""
        try:
            # Создаем шаблон (универсальный, без привязки к объекту)
            template = PlanningTemplate(
                name=template_data["name"],
                description=template_data.get("description", ""),
                owner_telegram_id=owner_telegram_id,
                object_id=template_data.get("object_id"),  # Может быть None
                start_time=template_data["start_time"],
                end_time=template_data["end_time"],
                hourly_rate=template_data["hourly_rate"],
                repeat_type=template_data.get("repeat_type", "none"),
                repeat_days=template_data.get("repeat_days", ""),
                repeat_interval=template_data.get("repeat_interval", 1),
                repeat_end_date=template_data.get("repeat_end_date"),
                is_active=template_data.get("is_active", True),
                is_public=template_data.get("is_public", False)
            )
            
            self.db.add(template)
            await self.db.flush()  # Получаем ID шаблона
            
            # Создаем тайм-слоты для шаблона
            if "time_slots" in template_data:
                for slot_data in template_data["time_slots"]:
                    template_slot = TemplateTimeSlot(
                        template_id=template.id,
                        day_of_week=slot_data["day_of_week"],
                        start_time=slot_data["start_time"],
                        end_time=slot_data["end_time"],
                        hourly_rate=slot_data["hourly_rate"],
                        is_active=slot_data.get("is_active", True)
                    )
                    self.db.add(template_slot)
            
            await self.db.commit()
            logger.info(f"Created planning template {template.id} for owner {owner_telegram_id}")
            return template
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating template: {e}")
            return None
    
    async def get_templates_by_owner(
        self, 
        owner_telegram_id: int,
        include_public: bool = True
    ) -> List[PlanningTemplate]:
        """Получение шаблонов владельца"""
        try:
            # Получаем шаблоны владельца
            owner_query = select(PlanningTemplate).where(
                and_(
                    PlanningTemplate.owner_telegram_id == owner_telegram_id,
                    PlanningTemplate.is_active == True
                )
            )
            owner_result = await self.db.execute(owner_query)
            owner_templates = owner_result.scalars().all()
            
            templates = list(owner_templates)
            
            # Добавляем публичные шаблоны, если нужно
            if include_public:
                public_query = select(PlanningTemplate).where(
                    and_(
                        PlanningTemplate.is_public == True,
                        PlanningTemplate.is_active == True,
                        PlanningTemplate.owner_telegram_id != owner_telegram_id
                    )
                )
                public_result = await self.db.execute(public_query)
                public_templates = public_result.scalars().all()
                templates.extend(public_templates)
            
            return templates
            
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []
    
    async def get_template_by_id(
        self, 
        template_id: int, 
        owner_telegram_id: int
    ) -> Optional[PlanningTemplate]:
        """Получение шаблона по ID"""
        try:
            query = select(PlanningTemplate).where(
                and_(
                    PlanningTemplate.id == template_id,
                    or_(
                        PlanningTemplate.owner_telegram_id == owner_telegram_id,
                        PlanningTemplate.is_public == True
                    ),
                    PlanningTemplate.is_active == True
                )
            ).options(
                selectinload(PlanningTemplate.template_slots)
            )
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    async def update_template(
        self, 
        template_id: int, 
        template_data: Dict[str, Any], 
        owner_telegram_id: int
    ) -> Optional[PlanningTemplate]:
        """Обновление шаблона"""
        try:
            template = await self.get_template_by_id(template_id, owner_telegram_id)
            if not template:
                return None
            
            # Обновляем поля шаблона
            for key, value in template_data.items():
                if hasattr(template, key) and key != "id":
                    setattr(template, key, value)
            
            template.updated_at = datetime.now()
            await self.db.commit()
            
            logger.info(f"Updated template {template_id}")
            return template
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating template {template_id}: {e}")
            return None
    
    async def delete_template(
        self, 
        template_id: int, 
        owner_telegram_id: int
    ) -> bool:
        """Удаление шаблона (мягкое удаление)"""
        try:
            template = await self.get_template_by_id(template_id, owner_telegram_id)
            if not template:
                return False
            
            # Мягкое удаление
            template.is_active = False
            template.updated_at = datetime.now()
            
            # Также деактивируем все тайм-слоты
            for slot in template.template_slots:
                slot.is_active = False
            
            await self.db.commit()
            logger.info(f"Deleted template {template_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting template {template_id}: {e}")
            return False
    
    async def apply_template(
        self, 
        template_id: int, 
        start_date: date, 
        end_date: date,
        owner_telegram_id: int
    ) -> Dict[str, Any]:
        """Применение шаблона к периоду"""
        try:
            template = await self.get_template_by_id(template_id, owner_telegram_id)
            if not template:
                return {"success": False, "error": "Шаблон не найден"}
            
            created_slots = []
            current_date = start_date
            
            while current_date <= end_date:
                # Проверяем, нужно ли создавать слоты для этого дня
                if self._should_create_slots_for_date(template, current_date):
                    for slot in template.template_slots:
                        if slot.is_active and slot.day_of_week == current_date.weekday():
                            # Создаем тайм-слот
                            timeslot_data = {
                                "slot_date": current_date,
                                "start_time": slot.start_time,
                                "end_time": slot.end_time,
                                "hourly_rate": slot.hourly_rate,
                                "is_active": True
                            }
                            
                            # Здесь нужно будет интегрироваться с TimeSlotService
                            # Пока просто логируем
                            logger.info(f"Would create timeslot for {current_date} with template slot {slot.id}")
                            created_slots.append({
                                "date": current_date.strftime("%Y-%m-%d"),
                                "start_time": slot.start_time,
                                "end_time": slot.end_time,
                                "hourly_rate": slot.hourly_rate
                            })
                
                current_date += timedelta(days=1)
            
            return {
                "success": True,
                "created_slots": created_slots,
                "template_name": template.name
            }
            
        except Exception as e:
            logger.error(f"Error applying template {template_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _should_create_slots_for_date(self, template: PlanningTemplate, check_date: date) -> bool:
        """Проверка, нужно ли создавать слоты для указанной даты"""
        if template.repeat_type == "none":
            return False
        elif template.repeat_type == "daily":
            return True
        elif template.repeat_type == "weekly":
            if not template.repeat_days:
                return True
            day_numbers = [int(d) for d in template.repeat_days.split(",") if d.strip()]
            return check_date.weekday() in day_numbers
        elif template.repeat_type == "monthly":
            # Для месячного повторения пока просто каждый день
            return True
        
        return False
    
    async def apply_template_to_objects(
        self, 
        template_id: int, 
        start_date: date, 
        end_date: date,
        object_ids: List[int],
        owner_telegram_id: int
    ) -> Dict[str, Any]:
        """Применение шаблона к нескольким объектам"""
        try:
            template = await self.get_template_by_id(template_id, owner_telegram_id)
            if not template:
                return {"success": False, "error": "Шаблон не найден"}
            
            created_slots = []
            total_created = 0
            
            # Применяем шаблон к каждому объекту
            for object_id_str in object_ids:
                # Преобразуем строку в число
                try:
                    object_id = int(object_id_str)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid object_id: {object_id_str}")
                    continue
                
                # Проверяем, что объект принадлежит владельцу
                from apps.web.services.object_service import ObjectService
                object_service = ObjectService(self.db)
                obj = await object_service.get_object_by_id(object_id, owner_telegram_id)
                if not obj:
                    logger.warning(f"Object {object_id} not found for owner {owner_telegram_id}")
                    continue
                
                # Создаем слоты для этого объекта
                current_date = start_date
                while current_date <= end_date:
                    if self._should_create_slots_for_date(template, current_date):
                        # Создаем тайм-слот для объекта
                        timeslot_data = {
                            "slot_date": current_date,
                            "start_time": template.start_time,
                            "end_time": template.end_time,
                            "hourly_rate": template.hourly_rate,
                            "is_active": True
                        }
                        
                        # Создаем тайм-слот через ObjectService
                        from apps.web.services.object_service import TimeSlotService
                        timeslot_service = TimeSlotService(self.db)
                        timeslot = await timeslot_service.create_timeslot(timeslot_data, object_id, owner_telegram_id)
                        
                        if timeslot:
                            created_slots.append({
                                "id": timeslot.id,
                                "object_id": object_id,
                                "object_name": obj.name,
                                "slot_date": current_date.isoformat(),
                                "start_time": template.start_time,
                                "end_time": template.end_time,
                                "hourly_rate": template.hourly_rate
                            })
                            total_created += 1
                    
                    current_date += timedelta(days=1)
            
            return {
                "success": True,
                "created_slots_count": total_created,
                "created_slots": created_slots,
                "message": f"Шаблон применен к {len(object_ids)} объектам. Создано {total_created} тайм-слотов."
            }
            
        except Exception as e:
            logger.error(f"Error applying template to objects: {e}")
            return {"success": False, "error": f"Ошибка применения шаблона: {str(e)}"}

    async def _get_user_internal_id(self, telegram_id: int) -> int:
        """Получение внутреннего ID пользователя по Telegram ID"""
        try:
            from domain.entities.user import User
            query = select(User.id).where(User.telegram_id == telegram_id)
            result = await self.db.execute(query)
            user_id = result.scalar_one_or_none()
            return user_id if user_id else telegram_id
        except Exception as e:
            logger.error(f"Error getting user internal ID: {e}")
            return telegram_id
