from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MediaFlowConfig:
    user_id: int
    context_type: str  # cancellation_doc | task_proof | incident_evidence
    context_id: int
    require_text: bool = False
    require_photo: bool = False
    max_photos: int = 1
    allow_skip: bool = True


class MediaOrchestrator:
    """Тонкий каркас для унифицированного потока медиа. Логику хранения/валидации будем расширять по мере внедрения."""

    def __init__(self):
        self._flows: dict[int, MediaFlowConfig] = {}

    def begin_flow(self, cfg: MediaFlowConfig) -> None:
        self._flows[cfg.user_id] = cfg

    def get_flow(self, user_id: int) -> Optional[MediaFlowConfig]:
        return self._flows.get(user_id)

    def finish(self, user_id: int) -> None:
        self._flows.pop(user_id, None)


