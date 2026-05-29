from domain.entities import Job
from domain.repositories import AbstractJobRepository


class GetJobStatusUseCase:
    def __init__(self, job_repo: AbstractJobRepository):
        self._repo = job_repo

    def execute(self, job_id: str) -> Job | None:
        return self._repo.get(job_id)


class ListJobsUseCase:
    def __init__(self, job_repo: AbstractJobRepository):
        self._repo = job_repo

    def execute(self, limit: int = 50) -> list[Job]:
        return self._repo.list_recent(limit=limit)
