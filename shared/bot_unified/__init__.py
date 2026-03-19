"""Unified bot layer: NormalizedUpdate, Messenger, Router, Adapters."""

from .normalized_update import NormalizedUpdate
from .messenger import Messenger, MessengerFeatures
from .router import UnifiedBotRouter, unified_router
from .tg_adapter import TgAdapter, TgMessenger
from .max_adapter import MaxAdapter
from .max_client import MaxClient, MaxMessenger

__all__ = [
    "NormalizedUpdate",
    "Messenger",
    "MessengerFeatures",
    "UnifiedBotRouter",
    "unified_router",
    "TgAdapter",
    "TgMessenger",
    "MaxAdapter",
    "MaxClient",
    "MaxMessenger",
]
