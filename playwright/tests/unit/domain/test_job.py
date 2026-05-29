from datetime import datetime, timezone

import pytest

from domain.entities import Job
from domain.value_objects import JobStatus, StepResult


def test_job_initialization():
    job = Job(
        id="job-123",
        workflow_id="faturar_pedido",
        variables={"pedido": "P-001"}
    )

    assert job.id == "job-123"
    assert job.workflow_id == "faturar_pedido"
    assert job.variables == {"pedido": "P-001"}
    assert job.status == JobStatus.PENDING
    assert job.worker_id is None
    assert job.started_at is None
    assert job.finished_at is None
    assert job.result is None
    assert job.error is None
    assert len(job.steps) == 0
    assert len(job.completed_step_ids) == 0


def test_job_start():
    job = Job(id="job-123", workflow_id="faturar", variables={})

    job.start(worker_id="worker-abc")

    assert job.status == JobStatus.RUNNING
    assert job.worker_id == "worker-abc"
    assert isinstance(job.started_at, datetime)


def test_job_succeed():
    job = Job(id="job-123", workflow_id="faturar", variables={})
    job.start("worker-1")

    result_data = {"processed": True, "items": 5}
    job.succeed(result=result_data)

    assert job.status == JobStatus.SUCCESS
    assert job.result == result_data
    assert isinstance(job.finished_at, datetime)
    assert job.started_at is not None
    assert job.finished_at >= job.started_at


def test_job_fail():
    job = Job(id="job-123", workflow_id="faturar", variables={})
    job.start("worker-1")

    error_msg = "Timeout loading routine"
    job.fail(error=error_msg)

    assert job.status == JobStatus.FAILED
    assert job.error == error_msg
    assert isinstance(job.finished_at, datetime)
    assert job.started_at is not None
    assert job.finished_at >= job.started_at


def test_job_mark_retrying():
    job = Job(id="job-123", workflow_id="faturar", variables={})

    job.mark_retrying()

    assert job.status == JobStatus.RETRYING


def test_job_add_step():
    job = Job(id="job-123", workflow_id="faturar", variables={})
    step = StepResult(
        step="login",
        status="success",
        duration_ms=1200,
        output={"user": "admin"}
    )

    job.add_step(step)

    assert len(job.steps) == 1
    assert job.steps[0] == step


def test_job_step_checkpointing():
    job = Job(id="job-123", workflow_id="faturar", variables={})

    assert not job.is_step_completed("step-1")

    job.mark_step_completed("step-1")
    assert job.is_step_completed("step-1")

    # Outro step não deve estar completo
    assert not job.is_step_completed("step-2")

    job.mark_step_completed("step-2")
    assert job.is_step_completed("step-2")
