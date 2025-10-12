"""Модуль обработчиков бота StaffProBot."""

# Основные обработчики
from .core_handlers import (
    start_command,
    handle_location,
    button_callback
)
from .utils import get_location_keyboard

# Обработчики смен
from .shift_handlers import (
    _handle_open_shift,
    _handle_close_shift,
    _handle_open_shift_object_selection,
    _handle_close_shift_selection,
    _handle_retry_location_open,
    _handle_retry_location_close
)

# Обработчики объектов
from .object_handlers import (
    _handle_manage_objects,
    _handle_edit_object,
    _handle_edit_field,
    _handle_edit_object_input,
    _show_updated_object_info
)

# Обработчики состояния объектов
from .object_state_handlers import (
    _handle_open_object,
    _handle_close_object,
    _handle_select_object_to_open
)

# Обработчики тайм-слотов
from .timeslot_handlers import (
    _handle_manage_timeslots,
    _handle_create_timeslot,
    _handle_view_timeslots,
    _handle_edit_timeslots,
    _handle_edit_single_timeslot,
    _handle_edit_timeslot_time,
    _handle_edit_timeslot_rate,
    _handle_edit_timeslot_employees,
    _handle_edit_timeslot_notes,
    _handle_toggle_timeslot_status,
    _handle_delete_timeslot,
    _handle_confirm_delete_timeslot,
    _handle_delete_timeslots,
    _handle_create_regular_slot,
    _handle_create_additional_slot,
    _handle_create_slot_date,
    _handle_create_slot_custom_date,
    _handle_create_slot_week,
    _handle_edit_slot_date,
    _handle_edit_slot_custom_date,
    _handle_edit_slot_week,
    _handle_delete_slot_date,
    _handle_delete_slot_custom_date,
    _handle_delete_slot_week
)

# Служебные обработчики
from .utility_handlers import (
    _handle_help_callback,
    _handle_status_callback,
    handle_message,
    handle_cancel
)

__all__ = [
    # Основные обработчики
    'start_command',
    'get_location_keyboard',
    'handle_location',
    'button_callback',
    
    # Обработчики смен
    '_handle_open_shift',
    '_handle_close_shift',
    '_handle_open_shift_object_selection',
    '_handle_close_shift_selection',
    '_handle_retry_location_open',
    '_handle_retry_location_close',
    
    # Обработчики объектов
    '_handle_manage_objects',
    '_handle_edit_object',
    '_handle_edit_field',
    '_handle_edit_object_input',
    '_show_updated_object_info',
    
    # Обработчики состояния объектов
    '_handle_open_object',
    '_handle_close_object',
    '_handle_select_object_to_open',
    
    # Обработчики тайм-слотов
    '_handle_manage_timeslots',
    '_handle_create_timeslot',
    '_handle_view_timeslots',
    '_handle_edit_timeslots',
    '_handle_edit_single_timeslot',
    '_handle_edit_timeslot_time',
    '_handle_edit_timeslot_rate',
    '_handle_edit_timeslot_employees',
    '_handle_edit_timeslot_notes',
    '_handle_toggle_timeslot_status',
    '_handle_delete_timeslot',
    '_handle_confirm_delete_timeslot',
    '_handle_delete_timeslots',
    '_handle_create_regular_slot',
    '_handle_create_additional_slot',
    '_handle_create_slot_date',
    '_handle_create_slot_custom_date',
    '_handle_create_slot_week',
    '_handle_edit_slot_date',
    '_handle_edit_slot_custom_date',
    '_handle_edit_slot_week',
    '_handle_delete_slot_date',
    '_handle_delete_slot_custom_date',
    '_handle_delete_slot_week',
    
    # Служебные обработчики
    '_handle_help_callback',
    '_handle_status_callback',
    'handle_message',
    'handle_cancel'
]
