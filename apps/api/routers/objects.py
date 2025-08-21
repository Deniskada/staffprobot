"""
API роутер для управления объектами
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from core.database.connection import get_db
from apps.api.schemas import (
    ObjectCreate, ObjectUpdate, ObjectResponse, 
    ObjectListResponse, ObjectFilter, ErrorResponse
)
from apps.api.services.object_service import ObjectService

router = APIRouter(prefix="/objects", tags=["objects"])


@router.post("/", response_model=ObjectResponse, status_code=status.HTTP_201_CREATED)
async def create_object(
    object_data: ObjectCreate,
    db: Session = Depends(get_db)
):
    """Создание нового объекта."""
    try:
        object_service = ObjectService(db)
        db_object = object_service.create_object(object_data)
        return db_object
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при создании объекта: {str(e)}"
        )


@router.get("/{object_id}", response_model=ObjectResponse)
async def get_object(
    object_id: int,
    db: Session = Depends(get_db)
):
    """Получение объекта по ID."""
    object_service = ObjectService(db)
    db_object = object_service.get_object(object_id)
    
    if not db_object:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Объект не найден"
        )
    
    return db_object


@router.get("/", response_model=ObjectListResponse)
async def get_objects(
    name: str = Query(None, description="Фильтр по названию"),
    owner_id: int = Query(None, description="Фильтр по владельцу"),
    is_active: bool = Query(None, description="Фильтр по активности"),
    min_hourly_rate: float = Query(None, description="Минимальная почасовая ставка"),
    max_hourly_rate: float = Query(None, description="Максимальная почасовая ставка"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(10, ge=1, le=100, description="Размер страницы"),
    db: Session = Depends(get_db)
):
    """Получение списка объектов с фильтрацией и пагинацией."""
    try:
        # Создаем фильтр
        filter_params = ObjectFilter(
            name=name,
            owner_id=owner_id,
            is_active=is_active,
            min_hourly_rate=min_hourly_rate,
            max_hourly_rate=max_hourly_rate,
            page=page,
            size=size
        )
        
        object_service = ObjectService(db)
        skip = (page - 1) * size
        
        objects, total = object_service.get_objects(filter_params, skip, size)
        
        return ObjectListResponse(
            objects=objects,
            total=total,
            page=page,
            size=size
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при получении объектов: {str(e)}"
        )


@router.put("/{object_id}", response_model=ObjectResponse)
async def update_object(
    object_id: int,
    object_data: ObjectUpdate,
    db: Session = Depends(get_db)
):
    """Обновление объекта."""
    try:
        object_service = ObjectService(db)
        db_object = object_service.update_object(object_id, object_data)
        
        if not db_object:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объект не найден"
            )
        
        return db_object
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при обновлении объекта: {str(e)}"
        )


@router.delete("/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    object_id: int,
    db: Session = Depends(get_db)
):
    """Удаление объекта."""
    try:
        object_service = ObjectService(db)
        success = object_service.delete_object(object_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объект не найден"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при удалении объекта: {str(e)}"
        )


@router.patch("/{object_id}/deactivate", response_model=ObjectResponse)
async def deactivate_object(
    object_id: int,
    db: Session = Depends(get_db)
):
    """Деактивация объекта."""
    try:
        object_service = ObjectService(db)
        success = object_service.deactivate_object(object_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объект не найден"
            )
        
        return object_service.get_object(object_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при деактивации объекта: {str(e)}"
        )


@router.patch("/{object_id}/activate", response_model=ObjectResponse)
async def activate_object(
    object_id: int,
    db: Session = Depends(get_db)
):
    """Активация объекта."""
    try:
        object_service = ObjectService(db)
        success = object_service.activate_object(object_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Объект не найден"
            )
        
        return object_service.get_object(object_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при активации объекта: {str(e)}"
        )


@router.get("/owner/{owner_id}", response_model=List[ObjectResponse])
async def get_objects_by_owner(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """Получение объектов по владельцу."""
    try:
        object_service = ObjectService(db)
        objects = object_service.get_objects_by_owner(owner_id)
        return objects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при получении объектов владельца: {str(e)}"
        )


@router.get("/search/{name}", response_model=List[ObjectResponse])
async def search_objects_by_name(
    name: str,
    db: Session = Depends(get_db)
):
    """Поиск объектов по названию."""
    try:
        object_service = ObjectService(db)
        objects = object_service.search_objects_by_name(name)
        return objects
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ошибка при поиске объектов: {str(e)}"
        )

