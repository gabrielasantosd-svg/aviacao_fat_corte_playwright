from unittest.mock import MagicMock

import pytest

from application.use_cases import SubmitJobCommand, SubmitJobUseCase
from domain.entities import Job
from domain.value_objects import JobStatus


def test_submit_job_success(in_memory_job_repo, fake_job_dispatcher):
    use_case = SubmitJobUseCase(
        job_repo=in_memory_job_repo,
        dispatcher=fake_job_dispatcher
    )

    command = SubmitJobCommand(
        workflow_id="faturar_pedido",
        variables={"pedido": "P-001"},
        idempotency_key="unique-key-123"
    )

    result = use_case.execute(command)

    # 1. Verifica retorno do caso de uso
    assert result.job_id is not None
    assert result.status == JobStatus.PENDING

    # 2. Verifica se foi salvo no repo
    job = in_memory_job_repo.get(result.job_id)
    assert job is not None
    assert job.workflow_id == "faturar_pedido"
    assert job.variables == {"pedido": "P-001"}

    # 3. Verifica se idempotency key foi salva
    assert in_memory_job_repo.get_job_by_idempotency_key("unique-key-123") == job

    # 4. Verifica se dispatcher foi chamado
    assert len(fake_job_dispatcher.dispatched_jobs) == 1
    assert fake_job_dispatcher.dispatched_jobs[0]["job_id"] == result.job_id
    assert fake_job_dispatcher.dispatched_jobs[0]["workflow_id"] == "faturar_pedido"
    assert fake_job_dispatcher.dispatched_jobs[0]["variables"] == {"pedido": "P-001"}


def test_submit_job_idempotency_existing(in_memory_job_repo, fake_job_dispatcher):
    use_case = SubmitJobUseCase(
        job_repo=in_memory_job_repo,
        dispatcher=fake_job_dispatcher
    )

    # Prepara job existente
    existing_job = Job(id="job-existing", workflow_id="faturar", variables={}, status=JobStatus.SUCCESS)
    in_memory_job_repo.save(existing_job)
    in_memory_job_repo.store_idempotency_key("duplicate-key", "job-existing")

    command = SubmitJobCommand(
        workflow_id="faturar",
        variables={},
        idempotency_key="duplicate-key"
    )

    result = use_case.execute(command)

    # Deve retornar o job existente com status SUCCESS
    assert result.job_id == "job-existing"
    assert result.status == JobStatus.SUCCESS

    # Não deve enfileirar nada novo
    assert len(fake_job_dispatcher.dispatched_jobs) == 0


def test_submit_job_validation_error(in_memory_job_repo, fake_job_dispatcher):
    # Mock do repository para lançar ValueError ao salvar
    in_memory_job_repo.save = MagicMock(side_effect=ValueError("Invalid job variables"))

    use_case = SubmitJobUseCase(
        job_repo=in_memory_job_repo,
        dispatcher=fake_job_dispatcher
    )

    command = SubmitJobCommand(
        workflow_id="faturar",
        variables={"invalido": True}
    )

    with pytest.raises(ValueError) as excinfo:
        use_case.execute(command)

    assert "Invalid job variables" in str(excinfo.value)
    assert len(fake_job_dispatcher.dispatched_jobs) == 0


def test_submit_job_infrastructure_error(in_memory_job_repo, fake_job_dispatcher):
    # Simula erro de infraestrutura na hora de despachar o job
    fake_job_dispatcher.dispatch = MagicMock(side_effect=Exception("Redis connection refused"))

    use_case = SubmitJobUseCase(
        job_repo=in_memory_job_repo,
        dispatcher=fake_job_dispatcher
    )

    command = SubmitJobCommand(
        workflow_id="faturar",
        variables={}
    )

    with pytest.raises(Exception) as excinfo:
        use_case.execute(command)

    assert "Redis connection refused" in str(excinfo.value)

    # Deve ter persistido no banco mesmo se falhou no dispatch?
    # Sim, de acordo com o submit_job_use_case, ele salva primeiro e depois faz dispatch
    # Mas a transação da fila falhou. O erro é propagado.
    # O repository deve conter o job salvo com status PENDING
    recent = in_memory_job_repo.list_recent()
    assert len(recent) == 1
    assert recent[0].status == JobStatus.PENDING
