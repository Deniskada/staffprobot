"""Модель тайм-слота объекта."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, Numeric, ForeignKey, Text, Date
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base
from typing import Optional
from datetime import datetime, time, date


class TimeSlot(Base):
    """Модель тайм-слота объекта."""
    
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    object_id = Column(Integer, ForeignKey("objects.id"), nullable=False, index=True)
    slot_date = Column(Date, nullable=False, index=True)  # Дата тайм-слота
    start_time = Column(Time, nullable=False)  # Время начала (HH:MM)
    end_time = Column(Time, nullable=False)  # Время окончания (HH:MM)
    hourly_rate = Column(Numeric(10, 2), nullable=True)  # Ставка для слота (по умолчанию объекта)
    max_employees = Column(Integer, default=1)  # Максимум сотрудников в слоте
    is_additional = Column(Boolean, default=False)  # Дополнительный слот (вне рабочего времени)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)  # Заметки владельца
    
    # Штрафы за опоздание
    penalize_late_start = Column(Boolean, default=True, nullable=False)  # Штрафовать за опоздание на запланированную смену
    
    # Задачи тайм-слота
    ignore_object_tasks = Column(Boolean, default=False, nullable=False)  # Игнорировать задачи объекта
    shift_tasks = Column(JSONB, nullable=True)  # Собственные задачи тайм-слота (массив объектов)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Отношения
    object = relationship("Object", backref="time_slots")
    task_templates = relationship("TimeslotTaskTemplate", backref="timeslot", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<TimeSlot(id={self.id}, object_id={self.object_id}, date={self.slot_date}, time={self.start_time}-{self.end_time})>"
    
    @property
    def duration_hours(self) -> float:
        """Длительность тайм-слота в часах."""
        if self.start_time and self.end_time:
            start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60
            end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60
            duration_seconds = end_seconds - start_seconds
            return round(duration_seconds / 3600, 2)
        return 0.0
    
    @property
    def is_working_hours(self) -> bool:
        """Проверка, находится ли слот в рабочем времени объекта."""
        if not self.object:
            return False
        return (self.object.opening_time <= self.start_time <= self.object.closing_time and
                self.object.opening_time <= self.end_time <= self.object.closing_time)
    
    @property
    def formatted_time_range(self) -> str:
        """Форматированное время слота."""
        return f"{self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"
    
    @property
    def formatted_date_time(self) -> str:
        """Форматированная дата и время слота."""
        return f"{self.slot_date.strftime('%d.%m.%Y')} {self.formatted_time_range}"
    
    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """Проверка пересечения времени с другим тайм-слотом."""
        if self.slot_date != other.slot_date:
            return False
        
        # Проверяем пересечение времени
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)
    
    def get_available_intervals(self, booked_schedules: list) -> list:
        """
        Получает доступные интервалы в тайм-слоте.
        
        Args:
            booked_schedules: Список забронированных смен в этом слоте
            
        Returns:
            Список доступных интервалов [(start_time, end_time), ...]
        """
        if not booked_schedules:
            return [(self.start_time, self.end_time)]
        
        # Сортируем забронированные смены по времени начала
        sorted_schedules = sorted(booked_schedules, key=lambda x: x.planned_start.time())
        
        available_intervals = []
        current_time = self.start_time
        
        for schedule in sorted_schedules:
            schedule_start = schedule.planned_start.time()
            schedule_end = schedule.planned_end.time()
            
            # Если есть промежуток до начала забронированной смены
            if current_time < schedule_start:
                available_intervals.append((current_time, schedule_start))
            
            # Обновляем текущее время
            current_time = max(current_time, schedule_end)
        
        # Добавляем оставшийся интервал после последней забронированной смены
        if current_time < self.end_time:
            available_intervals.append((current_time, self.end_time))
        
        return available_intervals
    
    def can_accommodate_employee(self, start_time: time, end_time: time, 
                                booked_schedules: list) -> bool:
        """
        Проверяет, может ли слот вместить сотрудника в указанное время.
        
        Args:
            start_time: Время начала работы сотрудника
            end_time: Время окончания работы сотрудника
            booked_schedules: Список забронированных смен
            
        Returns:
            True если можно разместить сотрудника
        """
        if self.slot_date != date.today():  # Пока только для сегодня
            return False
        
        # Проверяем, что время сотрудника находится в пределах слота
        if start_time < self.start_time or end_time > self.end_time:
            return False
        
        # Проверяем пересечения с забронированными сменами
        for schedule in booked_schedules:
            schedule_start = schedule.planned_start.time()
            schedule_end = schedule.planned_end.time()
            
            # Если есть пересечение времени
            if not (end_time <= schedule_start or start_time >= schedule_end):
                return False
        
        return True
