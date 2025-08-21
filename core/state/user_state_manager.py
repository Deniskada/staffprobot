"""
Управление состоянием пользователей в диалогах бота.
"""

from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum


class UserAction(str, Enum):
    """Возможные действия пользователя."""
    OPEN_SHIFT = "open_shift"
    CLOSE_SHIFT = "close_shift"
    CREATE_OBJECT = "create_object"
    EDIT_OBJECT = "edit_object"


class UserStep(str, Enum):
    """Шаги в диалоге."""
    OBJECT_SELECTION = "object_selection"
    SHIFT_SELECTION = "shift_selection"
    LOCATION_REQUEST = "location_request"
    PROCESSING = "processing"
    INPUT_MAX_DISTANCE = "input_max_distance"
    INPUT_FIELD_VALUE = "input_field_value"


class UserState:
    """Состояние пользователя в диалоге."""
    
    def __init__(
        self,
        user_id: int,
        action: UserAction,
        step: UserStep,
        selected_object_id: Optional[int] = None,
        selected_shift_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout_minutes: int = 5
    ):
        self.user_id = user_id
        self.action = action
        self.step = step
        self.selected_object_id = selected_object_id
        self.selected_shift_id = selected_shift_id
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


class UserStateManager:
    """Менеджер состояний пользователей."""
    
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
        if 'data' in kwargs:
            for key, value in kwargs['data'].items():
                state.add_data(key, value)
        
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


# Глобальный экземпляр менеджера состояний
user_state_manager = UserStateManager()
