import logging
import uuid
from dataclasses import dataclass
from typing import Any

from application.ports import AbstractJobDispatcher
from domain.entities import Job
from domain.repositories import AbstractJobRepository
from domain.value_objects import JobStatus
from infrastructure.observability import ErrorLogger


@dataclass
class SubmitJobCommand:
    workflow_id: str
    variables: dict[str, Any]
    idempotency_key: str | None = None


@dataclass
class SubmitJobResult:
    job_id: str
    status: JobStatus


class SubmitJobUseCase:
    """
    Use case para submissão de jobs com suporte a idempotência e error logging padronizado.
    """

    def __init__(
        self,
        job_repo: AbstractJobRepository,
        dispatcher: AbstractJobDispatcher,
    ):
        self._repo = job_repo
        self._dispatcher = dispatcher
        self._error_logger = ErrorLogger("submit_job_use_case")
        self._logger = logging.getLogger(__name__)

    def execute(self, command: SubmitJobCommand) -> SubmitJobResult:
        """
        Executa submissão do job com tratamento de erros padronizado.
        
        Args:
            command: Comando com workflow_id, variables e idempotency_key opcional
            
        Returns:
            SubmitJobResult com job_id e status
            
        Raises:
            ValueError: Se dados inválidos
            Exception: Erros de infraestrutura (DB, queue, etc)
        """
        try:
            # Verifica idempotência se key fornecida
            if command.idempotency_key:
                existing = self._repo.get_job_by_idempotency_key(command.idempotency_key)
                if existing:
                    self._logger.info(
                        f"Job duplicado detectado via idempotency_key: {existing.id}",
                        extra={
                            "job_id": existing.id,
                            "idempotency_key": command.idempotency_key,
                        },
                    )
                    return SubmitJobResult(job_id=existing.id, status=existing.status)

            # Cria novo job
            job = Job(
                id=str(uuid.uuid4()),
                workflow_id=command.workflow_id,
                variables=command.variables,
            )
            self._repo.save(job)

            # Armazena idempotency key se fornecida
            if command.idempotency_key:
                self._repo.store_idempotency_key(command.idempotency_key, job.id)

            # Enfileira para processamento
            self._dispatcher.dispatch(
                job_id=job.id,
                workflow_id=job.workflow_id,
                variables=job.variables,
            )

            self._logger.info(
                f"Job {job.id} submitted successfully",
                extra={
                    "job_id": job.id,
                    "workflow_id": command.workflow_id,
                    "has_idempotency_key": bool(command.idempotency_key),
                },
            )

            return SubmitJobResult(job_id=job.id, status=job.status)

        except ValueError as exc:
            # Erros de validação (não faz retry)
            self._error_logger.log_exception(
                exc,
                message="Validation error on job submission",
                level=logging.WARNING,
                extra_context={
                    "workflow_id": command.workflow_id,
                    "variables": command.variables,
                    "idempotency_key": command.idempotency_key,
                },
            )
            raise  # Re-raise para o exception handler da API

        except Exception as exc:
            # Erros de infraestrutura (DB, queue, etc)
            self._error_logger.log_exception(
                exc,
                message="Infrastructure error on job submission",
                level=logging.ERROR,
                extra_context={
                    "workflow_id": command.workflow_id,
                    "variables": command.variables,
                    "idempotency_key": command.idempotency_key,
                },
            )
            raise  # Re-raise para o exception handler da API
