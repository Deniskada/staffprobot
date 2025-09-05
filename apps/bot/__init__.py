"""Модуль Telegram бота."""

from .bot import StaffProBot
from .handlers import help_command, status_command
from .handlers_div import start_command, handle_message

__all__ = [
    "StaffProBot",
    "start_command",
    "help_command", 
    "status_command",
    "handle_message"
]





