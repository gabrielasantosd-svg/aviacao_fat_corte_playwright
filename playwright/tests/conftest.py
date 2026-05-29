import sys
from pathlib import Path
from typing import Any

import pytest

# Adiciona o diretório 'playwright' ao path de busca para garantir a importabilidade dos módulos
playwright_dir = Path(__file__).resolve().parent.parent
if str(playwright_dir) not in sys.path:
    sys.path.insert(0, str(playwright_dir))

from application.ports import AbstractJobDispatcher
from domain.entities import Job
from domain.repositories import AbstractJobRepository
from domain.value_objects import JobStatus


class InMemoryJobRepository(AbstractJobRepository):
    def __init__(self):
        self.jobs = {}
        self.idempotency_keys = {}
        self.step_logs = []

    def save(self, job: Job) -> None:
        self.jobs[job.id] = job

    def get(self, job_id: str) -> Job | None:
        return self.jobs.get(job_id)

    def list_recent(self, limit: int = 50) -> list[Job]:
        # Ordenar por data de criação se disponível (simulado por timestamp no ID ou ordem de inserção)
        return list(self.jobs.values())[:limit]

    def log_step(
        self, job_id: str, step: str, status: str, duration_ms: int, detail: str = ""
    ) -> None:
        self.step_logs.append({
            "job_id": job_id,
            "step": step,
            "status": status,
            "duration_ms": duration_ms,
            "detail": detail
        })

    def get_job_by_idempotency_key(self, key: str) -> Job | None:
        job_id = self.idempotency_keys.get(key)
        if job_id:
            return self.get(job_id)
        return None

    def store_idempotency_key(self, key: str, job_id: str, ttl_hours: int = 24) -> None:
        _ = ttl_hours
        self.idempotency_keys[key] = job_id


class FakeJobDispatcher(AbstractJobDispatcher):
    def __init__(self):
        self.dispatched_jobs = []

    def dispatch(self, job_id: str, workflow_id: str, variables: dict[str, Any]) -> None:
        self.dispatched_jobs.append({
            "job_id": job_id,
            "workflow_id": workflow_id,
            "variables": variables
        })


@pytest.fixture
def in_memory_job_repo() -> InMemoryJobRepository:
    return InMemoryJobRepository()


@pytest.fixture
def fake_job_dispatcher() -> FakeJobDispatcher:
    return FakeJobDispatcher()
