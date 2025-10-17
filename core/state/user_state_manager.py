"""
Управление состоянием пользователей в диалогах бота.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from core.config.settings import settings
from core.logging.logger import logger


class UserAction(str, Enum):
    """Возможные действия пользователя."""
    OPEN_SHIFT = "open_shift"
    CLOSE_SHIFT = "close_shift"
    OPEN_OBJECT = "open_object"  # Открытие объекта
    CLOSE_OBJECT = "close_object"  # Закрытие объекта
    MY_TASKS = "my_tasks"  # Просмотр и выполнение задач во время смены
    CREATE_OBJECT = "create_object"
    EDIT_OBJECT = "edit_object"
    SCHEDULE_SHIFT = "schedule_shift"
    VIEW_SCHEDULE = "view_schedule"
    CANCEL_SCHEDULE = "cancel_schedule"  # Отмена запланированной смены
    CREATE_TIMESLOT = "create_timeslot"
    EDIT_TIMESLOT_TIME = "edit_timeslot_time"
    EDIT_TIMESLOT_RATE = "edit_timeslot_rate"
    EDIT_TIMESLOT_EMPLOYEES = "edit_timeslot_employees"
    EDIT_TIMESLOT_NOTES = "edit_timeslot_notes"
    REPORT_DATES = "report_dates"


class UserStep(str, Enum):
    """Шаги в диалоге."""
    OBJECT_SELECTION = "object_selection"
    SHIFT_SELECTION = "shift_selection"
    TASK_COMPLETION = "task_completion"  # Phase 4A: отметка задач при закрытии смены
    MEDIA_UPLOAD = "media_upload"  # Загрузка фото/видео отчета для задачи
    LOCATION_REQUEST = "location_request"
    OPENING_OBJECT_LOCATION = "opening_object_location"  # Геолокация при открытии объекта
    CLOSING_OBJECT_LOCATION = "closing_object_location"  # Геолокация при закрытии объекта
    PROCESSING = "processing"
    INPUT_MAX_DISTANCE = "input_max_distance"
    INPUT_FIELD_VALUE = "input_field_value"
    INPUT_START_TIME = "input_start_time"
    INPUT_END_TIME = "input_end_time"
    INPUT_DATE = "input_date"
    INPUT_DOCUMENT = "input_document"  # Ввод описания документа (справки) для отмены смены
    INPUT_PHOTO = "input_photo"  # Загрузка фото для подтверждения отмены смены
    CONFIRM_SCHEDULE = "confirm_schedule"
    SCHEDULE_SELECTION = "schedule_selection"
    WAITING_INPUT = "waiting_input"


class UserState:
    """Состояние пользователя в диалоге."""
    
    def __init__(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep,
        selected_object_id: Optional[int] = None,
        selected_shift_id: Optional[int] = None,
        selected_timeslot_id: Optional[int] = None,
        selected_schedule_id: Optional[int] = None,
        shift_type: Optional[str] = None,
        shift_tasks: Optional[list] = None,  # Phase 4A: задачи смены
        completed_tasks: Optional[list] = None,  # Phase 4A: выполненные задачи
        pending_media_task_idx: Optional[int] = None,  # Индекс задачи, ожидающей медиа
        task_media: Optional[dict] = None,  # {task_idx: {media_url, media_type}}
        data: Optional[Dict[str, Any]] = None,
        timeout_minutes: int = 15
    ):
        self.user_id = user_id
        self.action = action
        self.step = step
        self.selected_object_id = selected_object_id
        self.selected_shift_id = selected_shift_id
        self.selected_timeslot_id = selected_timeslot_id
        self.selected_schedule_id = selected_schedule_id
        self.shift_type = shift_type
        self.shift_tasks = shift_tasks or []  # Phase 4A
        self.completed_tasks = completed_tasks or []  # Phase 4A
        self.pending_media_task_idx = pending_media_task_idx
        self.task_media = task_media or {}
        self.data = data or {}
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=timeout_minutes)
    
    def is_expired(self) -> bool:
        """Проверяет, истекло ли время ожидания."""
        return datetime.now() > self.expires_at
    
    def update_step(self, step: UserStep):
        """Обновляет шаг диалога."""
        self.step = step
    
    def to_dict(self) -> dict:
        """Сериализация в словарь для Redis."""
        return {
            'user_id': self.user_id,
            'action': self.action.value if isinstance(self.action, UserAction) else self.action,
            'step': self.step.value if isinstance(self.step, UserStep) else self.step,
            'selected_object_id': self.selected_object_id,
            'selected_shift_id': self.selected_shift_id,
            'selected_timeslot_id': self.selected_timeslot_id,
            'selected_schedule_id': self.selected_schedule_id,
            'shift_type': self.shift_type,
            'shift_tasks': self.shift_tasks,
            'completed_tasks': self.completed_tasks,
            'pending_media_task_idx': self.pending_media_task_idx,
            'task_media': self.task_media,
            'data': self.data,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserState':
        """Десериализация из словаря."""
        state = cls(
            user_id=data['user_id'],
            action=UserAction(data['action']),
            step=UserStep(data['step']),
            selected_object_id=data.get('selected_object_id'),
            selected_shift_id=data.get('selected_shift_id'),
            selected_timeslot_id=data.get('selected_timeslot_id'),
            selected_schedule_id=data.get('selected_schedule_id'),
            shift_type=data.get('shift_type'),
            shift_tasks=data.get('shift_tasks', []),
            completed_tasks=data.get('completed_tasks', []),
            pending_media_task_idx=data.get('pending_media_task_idx'),
            task_media=data.get('task_media', {}),
            data=data.get('data', {})
        )
        state.created_at = datetime.fromisoformat(data['created_at'])
        state.expires_at = datetime.fromisoformat(data['expires_at'])
        return state


class UserStateManager:
    """Менеджер состояний пользователей (in-memory или Redis)."""
    
    def __init__(self):
        self._states: Dict[int, UserState] = {}
        self._backend = getattr(settings, 'state_backend', 'memory')
        self._redis_cache = None
        self._state_ttl = timedelta(minutes=15)
        
        if self._backend == 'redis':
            logger.info("UserStateManager: using Redis backend")
        else:
            logger.info("UserStateManager: using in-memory backend")
    
    def _get_redis_key(self, user_id: int) -> str:
        """Генерация ключа для Redis."""
        return f"user_state:{user_id}"
    
    async def _init_redis(self):
        """Lazy initialization of Redis cache."""
        if self._redis_cache is None and self._backend == 'redis':
            from core.cache.redis_cache import cache
            self._redis_cache = cache
            if not self._redis_cache.is_connected:
                try:
                    await self._redis_cache.connect()
                except Exception as e:
                    logger.error(f"Failed to connect to Redis for UserState: {e}")
                    # Fallback to memory
                    self._backend = 'memory'
                    logger.warning("Falling back to in-memory UserState")
    
    async def create_state(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep = UserStep.OBJECT_SELECTION,
        **kwargs
    ) -> UserState:
        """Создает новое состояние пользователя."""
        state = UserState(user_id, action, step, **kwargs)
        
        if self._backend == 'redis':
            await self._init_redis()
            if self._redis_cache:
                key = self._get_redis_key(user_id)
                await self._redis_cache.set(key, state.to_dict(), ttl=self._state_ttl, serialize='json')
                logger.debug(f"UserState created in Redis: user_id={user_id}, action={action}, step={step}")
        
        # Всегда храним в памяти для быстрого доступа
        self._states[user_id] = state
        return state
    
    async def get_state(self, user_id: int) -> Optional[UserState]:
        """Получает состояние пользователя."""
        # Сначала проверяем память
        if user_id in self._states:
            state = self._states[user_id]
            if not state.is_expired():
                return state
            else:
                # Состояние истекло
                del self._states[user_id]
        
        # Если Redis включен, пробуем оттуда
        if self._backend == 'redis':
            await self._init_redis()
            if self._redis_cache:
                key = self._get_redis_key(user_id)
                data = await self._redis_cache.get(key, serialize='json')
                if data:
                    state = UserState.from_dict(data)
                    if not state.is_expired():
                        self._states[user_id] = state
                        return state
                    else:
                        await self._redis_cache.delete(key)
        
        return None
    
    async def update_state(self, user_id: int, **updates) -> Optional[UserState]:
        """Обновляет состояние пользователя и продлевает TTL."""
        state = await self.get_state(user_id)
        if not state:
            return None
        
        # Обновляем поля
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        # Продлеваем TTL
        state.expires_at = datetime.now() + self._state_ttl
        
        # Сохраняем в Redis
        if self._backend == 'redis':
            await self._init_redis()
            if self._redis_cache:
                key = self._get_redis_key(user_id)
                await self._redis_cache.set(key, state.to_dict(), ttl=self._state_ttl, serialize='json')
        
        self._states[user_id] = state
        return state
    
    async def clear_state(self, user_id: int) -> None:
        """Удаляет состояние пользователя."""
        if user_id in self._states:
            del self._states[user_id]
        
        if self._backend == 'redis':
            await self._init_redis()
            if self._redis_cache:
                key = self._get_redis_key(user_id)
                await self._redis_cache.delete(key)
    
    # Совместимость со старым API
    def set_state(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep = UserStep.OBJECT_SELECTION,
        **kwargs
    ) -> UserState:
        """Устаревший синхронный метод - для совместимости."""
        logger.warning("Using deprecated sync set_state, use async create_state instead")
        state = UserState(user_id, action, step, **kwargs)
        self._states[user_id] = state
        return state


# Глобальный экземпляр менеджера состояний
user_state_manager = UserStateManager()
