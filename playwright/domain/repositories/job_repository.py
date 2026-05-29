from abc import ABC, abstractmethod

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
