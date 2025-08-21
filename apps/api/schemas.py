"""
Схемы Pydantic для API StaffProBot
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import time, datetime


class ObjectBase(BaseModel):
    """Базовая схема объекта."""
    name: str = Field(..., min_length=1, max_length=255, description="Название объекта")
    address: Optional[str] = Field(None, description="Адрес объекта")
    coordinates: str = Field(..., description="Координаты в формате 'lat,lon'")
    opening_time: time = Field(..., description="Время открытия")
    closing_time: time = Field(..., description="Время закрытия")
    hourly_rate: float = Field(..., gt=0, description="Почасовая ставка")
    required_employees: Optional[str] = Field(None, description="Требуемые сотрудники (JSON)")
    is_active: bool = Field(True, description="Активен ли объект")

    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Валидация координат."""
        try:
            lat, lon = v.split(',')
            lat_val, lon_val = float(lat.strip()), float(lon.strip())
            if not (-90 <= lat_val <= 90):
                raise ValueError("Широта должна быть от -90 до 90")
            if not (-180 <= lon_val <= 180):
                raise ValueError("Долгота должна быть от -180 до 180")
            return v
        except (ValueError, AttributeError):
            raise ValueError("Координаты должны быть в формате 'lat,lon'")

    @validator('closing_time')
    def validate_closing_time(cls, v, values):
        """Валидация времени закрытия."""
        if 'opening_time' in values and v <= values['opening_time']:
            raise ValueError("Время закрытия должно быть позже времени открытия")
        return v


class ObjectCreate(ObjectBase):
    """Схема для создания объекта."""
    owner_id: int = Field(..., description="ID владельца объекта")


class ObjectUpdate(BaseModel):
    """Схема для обновления объекта."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    address: Optional[str] = None
    coordinates: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    hourly_rate: Optional[float] = Field(None, gt=0)
    required_employees: Optional[str] = None
    is_active: Optional[bool] = None

    @validator('coordinates')
    def validate_coordinates(cls, v):
        """Валидация координат."""
        if v is None:
            return v
        try:
            lat, lon = v.split(',')
            lat_val, lon_val = float(lat.strip()), float(lon.strip())
            if not (-90 <= lat_val <= 90):
                raise ValueError("Широта должна быть от -90 до 90")
            if not (-180 <= lon_val <= 180):
                raise ValueError("Долгота должна быть от -180 до 180")
            return v
        except (ValueError, AttributeError):
            raise ValueError("Координаты должны быть в формате 'lat,lon'")


class ObjectResponse(ObjectBase):
    """Схема для ответа с объектом."""
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    working_hours: str

    class Config:
        orm_mode = True


class ObjectListResponse(BaseModel):
    """Схема для списка объектов."""
    objects: List[ObjectResponse]
    total: int
    page: int
    size: int


class ObjectFilter(BaseModel):
    """Схема для фильтрации объектов."""
    name: Optional[str] = None
    owner_id: Optional[int] = None
    is_active: Optional[bool] = None
    min_hourly_rate: Optional[float] = None
    max_hourly_rate: Optional[float] = None
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)


class ErrorResponse(BaseModel):
    """Схема для ошибок API."""
    error: str
    message: str
    details: Optional[dict] = None
