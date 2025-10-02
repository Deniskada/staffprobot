"""Shared routes package."""

from .calendar_api import router as calendar_api_router

__all__ = [
    'calendar_api_router'
]
