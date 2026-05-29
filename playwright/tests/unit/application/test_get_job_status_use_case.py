import pytest

from application.use_cases import GetJobStatusUseCase, ListJobsUseCase
from domain.entities import Job


def test_get_job_status_found(in_memory_job_repo):
    job = Job(id="job-1", workflow_id="faturar", variables={})
    in_memory_job_repo.save(job)

    use_case = GetJobStatusUseCase(job_repo=in_memory_job_repo)
    result = use_case.execute("job-1")

    assert result == job


def test_get_job_status_not_found(in_memory_job_repo):
    use_case = GetJobStatusUseCase(job_repo=in_memory_job_repo)
    result = use_case.execute("non-existent-id")

    assert result is None


def test_list_jobs_recent(in_memory_job_repo):
    job1 = Job(id="job-1", workflow_id="faturar", variables={})
    job2 = Job(id="job-2", workflow_id="faturar", variables={})
    in_memory_job_repo.save(job1)
    in_memory_job_repo.save(job2)

    use_case = ListJobsUseCase(job_repo=in_memory_job_repo)
    result = use_case.execute(limit=10)

    assert len(result) == 2
    assert job1 in result
    assert job2 in result
