"""Модели данных для календаря."""

from dataclasses import dataclass
from datetime import datetime, date, time
from typing import List, Optional, Dict, Any
from enum import Enum


class ShiftType(str, Enum):
    """Типы смен."""
    PLANNED = "planned"      # Запланированная смена (ShiftSchedule)
    ACTIVE = "active"        # Активная смена (Shift)
    COMPLETED = "completed"  # Завершенная смена (Shift)
    CANCELLED = "cancelled"  # Отмененная смена


class ShiftStatus(str, Enum):
    """Статусы смен."""
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TimeslotStatus(str, Enum):
    """Статусы тайм-слотов."""
    AVAILABLE = "available"      # Доступен для планирования
    PARTIALLY_FILLED = "partially_filled"  # Частично заполнен
    FULLY_FILLED = "fully_filled"  # Полностью заполнен
    HIDDEN = "hidden"           # Скрыт (заполнен)


@dataclass
class CalendarTimeslot:
    """Унифицированная модель тайм-слота для календаря."""
    
    # Основные данные
    id: int
    object_id: int
    object_name: str
    date: date
    start_time: time
    end_time: time
    hourly_rate: float
    max_employees: int
    is_active: bool
    notes: Optional[str] = None
    
    # Статус и доступность
    status: TimeslotStatus = TimeslotStatus.AVAILABLE
    current_employees: int = 0
    available_slots: int = 0
    
    # Дополнительная информация
    work_conditions: Optional[str] = None
    shift_tasks: Optional[List[str]] = None
    coordinates: Optional[str] = None  # "lat,lon" формат
    
    # Права доступа
    can_edit: bool = False
    can_plan: bool = False
    can_view: bool = True
    
    def __post_init__(self):
        """Вычисляем доступные слоты после инициализации."""
        self.available_slots = max(0, self.max_employees - self.current_employees)
        
        # Определяем статус
        if self.current_employees == 0:
            self.status = TimeslotStatus.AVAILABLE
        elif self.current_employees < self.max_employees:
            self.status = TimeslotStatus.PARTIALLY_FILLED
        else:
            self.status = TimeslotStatus.FULLY_FILLED


@dataclass
class CalendarShift:
    """Унифицированная модель смены для календаря."""
    
    # Основные данные (обязательные поля)
    id: int
    user_id: int
    user_name: str  # "Имя Фамилия"
    object_id: int
    object_name: str
    start_time: datetime
    shift_type: ShiftType
    status: ShiftStatus
    hourly_rate: float
    
    # Опциональные поля
    time_slot_id: Optional[int] = None
    end_time: Optional[datetime] = None
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    total_hours: Optional[float] = None
    total_payment: Optional[float] = None
    
    # Дополнительная информация
    notes: Optional[str] = None
    is_planned: bool = False  # Была ли смена запланирована
    schedule_id: Optional[int] = None  # ID запланированной смены
    actual_shift_id: Optional[int] = None  # ID фактической смены
    
    # Координаты
    start_coordinates: Optional[str] = None  # "lat,lon" формат
    end_coordinates: Optional[str] = None    # "lat,lon" формат
    
    # Права доступа
    can_edit: bool = False
    can_cancel: bool = False
    can_view: bool = True
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Длительность смены в часах."""
        if self.end_time and self.start_time:
            duration = self.end_time - self.start_time
            return round(duration.total_seconds() / 3600, 2)
        return None
    
    @property
    def planned_duration_hours(self) -> Optional[float]:
        """Запланированная длительность смены в часах."""
        if self.planned_start and self.planned_end:
            duration = self.planned_end - self.planned_start
            return round(duration.total_seconds() / 3600, 2)
        return None
    
    @property
    def is_upcoming(self) -> bool:
        """Проверка, предстоящая ли смена."""
        now = datetime.now()
        if self.shift_type == ShiftType.PLANNED:
            return self.planned_start and self.planned_start > now
        return False
    
    @property
    def is_today(self) -> bool:
        """Проверка, запланирована ли смена на сегодня."""
        today = date.today()
        if self.shift_type == ShiftType.PLANNED:
            return self.planned_start and self.planned_start.date() == today
        return self.start_time.date() == today


@dataclass
class CalendarData:
    """Контейнер для всех данных календаря."""
    
    # Основные данные
    timeslots: List[CalendarTimeslot]
    shifts: List[CalendarShift]
    
    # Метаданные
    date_range_start: date
    date_range_end: date
    user_role: str
    accessible_objects: List[Dict[str, Any]]  # Список доступных объектов
    
    # Статистика
    total_timeslots: int = 0
    total_shifts: int = 0
    planned_shifts: int = 0
    active_shifts: int = 0
    completed_shifts: int = 0
    
    def __post_init__(self):
        """Вычисляем статистику после инициализации."""
        self.total_timeslots = len(self.timeslots)
        self.total_shifts = len(self.shifts)
        
        # Подсчитываем смены по типам
        self.planned_shifts = len([s for s in self.shifts if s.shift_type == ShiftType.PLANNED])
        self.active_shifts = len([s for s in self.shifts if s.shift_type == ShiftType.ACTIVE])
        self.completed_shifts = len([s for s in self.shifts if s.shift_type == ShiftType.COMPLETED])
    
    def get_timeslots_by_date(self, target_date: date) -> List[CalendarTimeslot]:
        """Получить тайм-слоты для конкретной даты."""
        return [ts for ts in self.timeslots if ts.date == target_date]
    
    def get_shifts_by_date(self, target_date: date) -> List[CalendarShift]:
        """Получить смены для конкретной даты."""
        return [s for s in self.shifts if s.start_time.date() == target_date or 
                (s.planned_start and s.planned_start.date() == target_date)]
    
    def get_shifts_by_timeslot(self, timeslot_id: int) -> List[CalendarShift]:
        """Получить смены для конкретного тайм-слота."""
        return [s for s in self.shifts if s.time_slot_id == timeslot_id]
    
    def get_shifts_by_object(self, object_id: int) -> List[CalendarShift]:
        """Получить смены для конкретного объекта."""
        return [s for s in self.shifts if s.object_id == object_id]
    
    def get_timeslots_by_object(self, object_id: int) -> List[CalendarTimeslot]:
        """Получить тайм-слоты для конкретного объекта."""
        return [ts for ts in self.timeslots if ts.object_id == object_id]


@dataclass
class CalendarFilter:
    """Фильтр для данных календаря."""
    
    # Временной диапазон
    start_date: date
    end_date: date
    
    # Фильтры
    object_ids: Optional[List[int]] = None
    user_ids: Optional[List[int]] = None
    shift_types: Optional[List[ShiftType]] = None
    shift_statuses: Optional[List[ShiftStatus]] = None
    timeslot_statuses: Optional[List[TimeslotStatus]] = None
    
    # Дополнительные параметры
    include_cancelled: bool = False
    include_hidden_timeslots: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать фильтр в словарь для API."""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'object_ids': self.object_ids,
            'user_ids': self.user_ids,
            'shift_types': [t.value for t in self.shift_types] if self.shift_types else None,
            'shift_statuses': [s.value for s in self.shift_statuses] if self.shift_statuses else None,
            'timeslot_statuses': [s.value for s in self.timeslot_statuses] if self.timeslot_statuses else None,
            'include_cancelled': self.include_cancelled,
            'include_hidden_timeslots': self.include_hidden_timeslots
        }


@dataclass
class CalendarStats:
    """Статистика календаря."""
    
    # Общая статистика
    total_timeslots: int
    total_shifts: int
    total_objects: int
    
    # Статистика по сменам
    planned_shifts: int
    active_shifts: int
    completed_shifts: int
    cancelled_shifts: int
    
    # Статистика по тайм-слотам
    available_timeslots: int
    partially_filled_timeslots: int
    fully_filled_timeslots: int
    
    # Финансовая статистика
    total_hours: float
    total_payment: float
    average_hourly_rate: float
    
    # Статистика по объектам
    objects_with_shifts: int
    objects_with_timeslots: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать статистику в словарь."""
        return {
            'total_timeslots': self.total_timeslots,
            'total_shifts': self.total_shifts,
            'total_objects': self.total_objects,
            'planned_shifts': self.planned_shifts,
            'active_shifts': self.active_shifts,
            'completed_shifts': self.completed_shifts,
            'cancelled_shifts': self.cancelled_shifts,
            'available_timeslots': self.available_timeslots,
            'partially_filled_timeslots': self.partially_filled_timeslots,
            'fully_filled_timeslots': self.fully_filled_timeslots,
            'total_hours': self.total_hours,
            'total_payment': self.total_payment,
            'average_hourly_rate': self.average_hourly_rate,
            'objects_with_shifts': self.objects_with_shifts,
            'objects_with_timeslots': self.objects_with_timeslots
        }
