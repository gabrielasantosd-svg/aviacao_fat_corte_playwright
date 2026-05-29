from abc import ABC, abstractmethod
from typing import Any


class AbstractJobDispatcher(ABC):
    """Port: enfileira um job sem saber nada de Celery/Redis."""

    @abstractmethod
    def dispatch(self, job_id: str, workflow_id: str, variables: dict[str, Any]) -> None: ...
