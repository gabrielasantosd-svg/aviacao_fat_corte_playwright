from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from domain.value_objects import JobStatus, StepResult


@dataclass
class Job:
    """Aggregate root que representa uma execucao de workflow."""

    id: str
    workflow_id: str
    variables: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    worker_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    completed_step_ids: set[str] = field(default_factory=set)  # Para idempotencia de steps.

    # Domain behaviours

    def start(self, worker_id: str) -> None:
        self.status = JobStatus.RUNNING
        self.worker_id = worker_id
        self.started_at = datetime.utcnow()

    def succeed(self, result: dict[str, Any]) -> None:
        self.status = JobStatus.SUCCESS
        self.result = result
        self.finished_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        self.status = JobStatus.FAILED
        self.error = error
        self.finished_at = datetime.utcnow()

    def mark_retrying(self) -> None:
        self.status = JobStatus.RETRYING

    def add_step(self, step: StepResult) -> None:
        self.steps.append(step)

    def is_step_completed(self, step_id: str) -> bool:
        """Verifica se um step ja foi completado, para idempotencia."""
        return step_id in self.completed_step_ids

    def mark_step_completed(self, step_id: str) -> None:
        """Marca um step como completado (checkpointing)."""
        self.completed_step_ids.add(step_id)
