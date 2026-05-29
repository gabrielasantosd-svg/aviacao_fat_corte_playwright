from abc import ABC, abstractmethod
from typing import Any

from domain.entities import Job


class AbstractJobRepository(ABC):
    @abstractmethod
    def save(self, job: Job) -> None: ...

    @abstractmethod
    def get(self, job_id: str) -> Job | None: ...

    @abstractmethod
    def list_recent(self, limit: int = 50) -> list[Job]: ...

    @abstractmethod
    def log_step(
        self, job_id: str, step: str, status: str, duration_ms: int, detail: str = ""
    ) -> None: ...

    @abstractmethod
    def get_job_by_idempotency_key(self, key: str) -> Job | None: ...

    @abstractmethod
    def store_idempotency_key(self, key: str, job_id: str, ttl_hours: int = 24) -> None: ...

    def save_to_dead_letter(
        self,
        job: Job,
        retry_count: int,
        original_task_id: str | None = None,
    ) -> None:
        _ = (job, retry_count, original_task_id)

    def list(self, limit: int = 50, status: Any | None = None) -> list[Job]:
        _ = status
        return self.list_recent(limit=limit)
