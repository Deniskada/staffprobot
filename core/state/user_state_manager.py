"""
Управление состоянием пользователей в диалогах бота.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from core.config.settings import settings
from core.logging.logger import logger
from core.cache.redis_cache import cache


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
        timeout_minutes: int = 5
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
    
    def set_selected_object(self, object_id: int):
        """Устанавливает выбранный объект."""
        self.selected_object_id = object_id
    
    def set_selected_shift(self, shift_id: int):
        """Устанавливает выбранную смену."""
        self.selected_shift_id = shift_id
    
    def add_data(self, key: str, value: Any):
        """Добавляет дополнительные данные."""
        self.data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Получает дополнительные данные."""
        return self.data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "action": str(self.action),
            "step": str(self.step),
            "selected_object_id": self.selected_object_id,
            "selected_shift_id": self.selected_shift_id,
            "selected_timeslot_id": self.selected_timeslot_id,
            "selected_schedule_id": self.selected_schedule_id,
            "shift_type": self.shift_type,
            "shift_tasks": self.shift_tasks,
            "completed_tasks": self.completed_tasks,
            "pending_media_task_idx": self.pending_media_task_idx,
            "task_media": self.task_media,
            "data": self.data,
            "expires_at": self.expires_at.isoformat(),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "UserState":
        state = UserState(
            user_id=d["user_id"],
            action=UserAction(d["action"]),
            step=UserStep(d["step"]),
            selected_object_id=d.get("selected_object_id"),
            selected_shift_id=d.get("selected_shift_id"),
            selected_timeslot_id=d.get("selected_timeslot_id"),
            selected_schedule_id=d.get("selected_schedule_id"),
            shift_type=d.get("shift_type"),
            shift_tasks=d.get("shift_tasks") or [],
            completed_tasks=d.get("completed_tasks") or [],
            pending_media_task_idx=d.get("pending_media_task_idx"),
            task_media=d.get("task_media") or {},
            data=d.get("data") or {},
            timeout_minutes=settings.state_ttl_minutes,
        )
        # Обновим expires_at, если есть в данных
        try:
            expires_str = d.get("expires_at")
            if expires_str:
                state.expires_at = datetime.fromisoformat(expires_str)
        except Exception:
            pass
        return state


class UserStateManager:
    """Менеджер состояний пользователей (in-memory)."""
    
    def __init__(self):
        self._states: Dict[int, UserState] = {}
    
    def create_state(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep = UserStep.OBJECT_SELECTION,
        **kwargs
    ) -> UserState:
        """Создает новое состояние пользователя."""
        state = UserState(user_id, action, step, **kwargs)
        self._states[user_id] = state
        return state
    
    # Совместимость со старым API
    def set_state(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep,
        **kwargs
    ) -> UserState:
        """Alias для create_state для совместимости."""
        return self.create_state(user_id=user_id, action=action, step=step, **kwargs)
    
    def get_state(self, user_id: int) -> Optional[UserState]:
        """Получает состояние пользователя."""
        state = self._states.get(user_id)
        if state and state.is_expired():
            # Удаляем истекшее состояние
            del self._states[user_id]
            return None
        return state
    
    def update_state(self, user_id: int, **kwargs) -> Optional[UserState]:
        """Обновляет состояние пользователя."""
        state = self.get_state(user_id)
        if not state:
            return None
        
        if 'step' in kwargs:
            state.update_step(kwargs['step'])
        if 'selected_object_id' in kwargs:
            state.set_selected_object(kwargs['selected_object_id'])
        if 'selected_shift_id' in kwargs:
            state.set_selected_shift(kwargs['selected_shift_id'])
        if 'selected_timeslot_id' in kwargs:
            state.selected_timeslot_id = kwargs['selected_timeslot_id']
        if 'selected_schedule_id' in kwargs:
            state.selected_schedule_id = kwargs['selected_schedule_id']
        if 'shift_type' in kwargs:
            state.shift_type = kwargs['shift_type']
        if 'shift_tasks' in kwargs:
            state.shift_tasks = kwargs['shift_tasks']
        if 'completed_tasks' in kwargs:
            state.completed_tasks = kwargs['completed_tasks']
        if 'pending_media_task_idx' in kwargs:
            state.pending_media_task_idx = kwargs['pending_media_task_idx']
        if 'task_media' in kwargs:
            state.task_media = kwargs['task_media']
        if 'data' in kwargs:
            for key, value in kwargs['data'].items():
                state.add_data(key, value)
        
        # Продлеваем время жизни состояния при каждом обновлении
        state.expires_at = datetime.now() + timedelta(minutes=5)
        
        return state
    
    def clear_state(self, user_id: int) -> bool:
        """Очищает состояние пользователя."""
        if user_id in self._states:
            del self._states[user_id]
            return True
        return False
    
    def cleanup_expired_states(self) -> int:
        """Очищает истекшие состояния."""
        expired_users = [
            user_id for user_id, state in self._states.items()
            if state.is_expired()
        ]
        
        for user_id in expired_users:
            del self._states[user_id]
        
        return len(expired_users)
    
    def get_active_states_count(self) -> int:
        """Возвращает количество активных состояний."""
        return len(self._states)


class RedisUserStateManager:
    """Менеджер состояний на Redis."""

    def __init__(self):
        self.ttl_seconds = settings.state_ttl_minutes * 60

    def _key(self, user_id: int) -> str:
        return f"user_state:{user_id}"

    async def _ensure_connection(self) -> None:
        if not cache.is_connected:
            try:
                await cache.connect()
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                raise

    async def create_state(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep = UserStep.OBJECT_SELECTION,
        **kwargs
    ) -> UserState:
        await self._ensure_connection()
        state = UserState(user_id, action, step, **kwargs)
        await cache.set(self._key(user_id), state.to_dict(), ttl=self.ttl_seconds, serialize="json")
        return state

    # Совместимость
    async def set_state(self, user_id: int, action: UserAction, step: UserStep, **kwargs) -> UserState:
        return await self.create_state(user_id=user_id, action=action, step=step, **kwargs)

    async def get_state(self, user_id: int) -> Optional[UserState]:
        await self._ensure_connection()
        data = await cache.get(self._key(user_id), serialize="json")
        if not data:
            return None
        try:
            state = UserState.from_dict(data)
            if state.is_expired():
                await cache.delete(self._key(user_id))
                return None
            return state
        except Exception as e:
            logger.error(f"Failed to deserialize UserState: {e}")
            await cache.delete(self._key(user_id))
            return None

    async def update_state(self, user_id: int, **kwargs) -> Optional[UserState]:
        state = await self.get_state(user_id)
        if not state:
            return None
        
        if 'step' in kwargs:
            state.update_step(kwargs['step'])
        if 'selected_object_id' in kwargs:
            state.set_selected_object(kwargs['selected_object_id'])
        if 'selected_shift_id' in kwargs:
            state.set_selected_shift(kwargs['selected_shift_id'])
        if 'selected_timeslot_id' in kwargs:
            state.selected_timeslot_id = kwargs['selected_timeslot_id']
        if 'selected_schedule_id' in kwargs:
            state.selected_schedule_id = kwargs['selected_schedule_id']
        if 'shift_type' in kwargs:
            state.shift_type = kwargs['shift_type']
        if 'shift_tasks' in kwargs:
            state.shift_tasks = kwargs['shift_tasks']
        if 'completed_tasks' in kwargs:
            state.completed_tasks = kwargs['completed_tasks']
        if 'pending_media_task_idx' in kwargs:
            state.pending_media_task_idx = kwargs['pending_media_task_idx']
        if 'task_media' in kwargs:
            state.task_media = kwargs['task_media']
        if 'data' in kwargs:
            for key, value in (kwargs['data'] or {}).items():
                state.add_data(key, value)
        
        # Продлеваем TTL
        state.expires_at = datetime.now() + timedelta(minutes=settings.state_ttl_minutes)
        await cache.set(self._key(user_id), state.to_dict(), ttl=self.ttl_seconds, serialize="json")
        return state

    async def clear_state(self, user_id: int) -> bool:
        await self._ensure_connection()
        return await cache.delete(self._key(user_id))

    async def cleanup_expired_states(self) -> int:
        # Redis сам очищает по TTL; метод-"заглушка" для совместимости
        return 0

    async def get_active_states_count(self) -> int:
        # Для Redis не считаем (дорого); можно реализовать через SCAN по префиксу
        return 0


# Глобальный экземпляр менеджера состояний
# Для совместимости с существующим sync-кодом храним адаптер, который вызывает async-методы

class _UserStateFacade:
    def __init__(self):
        self.backend_type = settings.state_backend
        if self.backend_type == "redis":
            self.backend = RedisUserStateManager()
            self.is_async = True
        else:
            self.backend = UserStateManager()
            self.is_async = False

    def _run_async(self, coro):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            # Внутри уже запущенного loop - планируем задачу и ждём результата
            return asyncio.run_coroutine_threadsafe(coro, loop).result()
        else:
            return asyncio.run(coro)

    def create_state(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.create_state(*args, **kwargs))
        return self.backend.create_state(*args, **kwargs)

    def set_state(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.set_state(*args, **kwargs))
        return self.backend.set_state(*args, **kwargs)

    def get_state(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.get_state(*args, **kwargs))
        return self.backend.get_state(*args, **kwargs)

    def update_state(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.update_state(*args, **kwargs))
        return self.backend.update_state(*args, **kwargs)

    def clear_state(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.clear_state(*args, **kwargs))
        return self.backend.clear_state(*args, **kwargs)

    def cleanup_expired_states(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.cleanup_expired_states(*args, **kwargs))
        return self.backend.cleanup_expired_states(*args, **kwargs)

    def get_active_states_count(self, *args, **kwargs):
        if self.is_async:
            return self._run_async(self.backend.get_active_states_count(*args, **kwargs))
        return self.backend.get_active_states_count(*args, **kwargs)


user_state_manager = _UserStateFacade()
