"""
Сервис для работы с объектами
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime

from domain.entities.object import Object
from apps.api.schemas import ObjectCreate, ObjectUpdate, ObjectFilter


class ObjectService:
    """Сервис для управления объектами."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_object(self, object_data: ObjectCreate) -> Object:
        """Создание нового объекта."""
        db_object = Object(
            name=object_data.name,
            owner_id=object_data.owner_id,
            address=object_data.address,
            coordinates=object_data.coordinates,
            opening_time=object_data.opening_time,
            closing_time=object_data.closing_time,
            hourly_rate=object_data.hourly_rate,
            required_employees=object_data.required_employees,
            is_active=object_data.is_active
        )
        
        self.db.add(db_object)
        self.db.commit()
        self.db.refresh(db_object)
        
        return db_object
    
    def get_object(self, object_id: int) -> Optional[Object]:
        """Получение объекта по ID."""
        return self.db.query(Object).filter(Object.id == object_id).first()
    
    def get_objects(
        self, 
        filter_params: ObjectFilter,
        skip: int = 0, 
        limit: int = 100
    ) -> Tuple[List[Object], int]:
        """Получение списка объектов с фильтрацией."""
        query = self.db.query(Object)
        
        # Применяем фильтры
        if filter_params.name:
            query = query.filter(Object.name.ilike(f"%{filter_params.name}%"))
        
        if filter_params.owner_id is not None:
            query = query.filter(Object.owner_id == filter_params.owner_id)
        
        if filter_params.is_active is not None:
            query = query.filter(Object.is_active == filter_params.is_active)
        
        if filter_params.min_hourly_rate is not None:
            query = query.filter(Object.hourly_rate >= filter_params.min_hourly_rate)
        
        if filter_params.max_hourly_rate is not None:
            query = query.filter(Object.hourly_rate <= filter_params.max_hourly_rate)
        
        # Получаем общее количество
        total = query.count()
        
        # Применяем пагинацию
        objects = query.offset(skip).limit(limit).all()
        
        return objects, total
    
    def update_object(self, object_id: int, object_data: ObjectUpdate) -> Optional[Object]:
        """Обновление объекта."""
        db_object = self.get_object(object_id)
        if not db_object:
            return None
        
        # Обновляем только переданные поля
        update_data = object_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_object, field, value)
        
        db_object.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(db_object)
        
        return db_object
    
    def delete_object(self, object_id: int) -> bool:
        """Удаление объекта."""
        db_object = self.get_object(object_id)
        if not db_object:
            return False
        
        self.db.delete(db_object)
        self.db.commit()
        
        return True
    
    def deactivate_object(self, object_id: int) -> bool:
        """Деактивация объекта."""
        db_object = self.get_object(object_id)
        if not db_object:
            return False
        
        db_object.is_active = False
        db_object.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(db_object)
        
        return True
    
    def activate_object(self, object_id: int) -> bool:
        """Активация объекта."""
        db_object = self.get_object(object_id)
        if not db_object:
            return False
        
        db_object.is_active = True
        db_object.updated_at = datetime.now()
        
        self.db.commit()
        self.db.refresh(db_object)
        
        return True
    
    def get_objects_by_owner(self, owner_id: int) -> List[Object]:
        """Получение объектов по владельцу."""
        return self.db.query(Object).filter(Object.owner_id == owner_id).all()
    
    def get_active_objects(self) -> List[Object]:
        """Получение всех активных объектов."""
        return self.db.query(Object).filter(Object.is_active == True).all()
    
    def search_objects_by_name(self, name: str) -> List[Object]:
        """Поиск объектов по названию."""
        return self.db.query(Object).filter(
            Object.name.ilike(f"%{name}%")
        ).all()
