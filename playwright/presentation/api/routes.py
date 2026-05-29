from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from application.use_cases import (
    GetJobStatusUseCase,
    ListJobsUseCase,
    SubmitJobCommand,
    SubmitJobUseCase,
)
from infrastructure.messaging import CeleryJobDispatcher
from infrastructure.persistence.postgres_job_repository import PostgresJobRepository
from infrastructure.security import verify_api_key
from presentation.api.schemas import JobRequest, JobResponse, JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])
limiter = Limiter(key_func=get_remote_address)


# Composicao de dependencias, simples e sem framework de DI.
def _repo():
    return PostgresJobRepository()


def _submit_uc():
    return SubmitJobUseCase(job_repo=_repo(), dispatcher=CeleryJobDispatcher())


def _status_uc():
    return GetJobStatusUseCase(job_repo=_repo())


def _list_uc():
    return ListJobsUseCase(job_repo=_repo())


@router.post(
    "/",
    response_model=JobResponse,
    status_code=202,
    summary="Submeter novo job",
    description="""
    Submete um novo job para execucao assincrona.

    **Autenticacao:** Requer API Key no header `X-API-Key`.

    **Idempotencia:** Use `idempotency_key` para evitar execucao duplicada.
    Se um job com a mesma key ja existir, retorna o job existente.

    **Rate Limit:** 10 requisicoes por minuto por IP.
    """,
    responses={
        202: {
            "description": "Job aceito e enfileirado com sucesso",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "abc-123-def",
                        "status": "PENDING",
                        "workflow_id": "faturar_pedido",
                        "message": "Job enfileirado com sucesso.",
                        "idempotent": False
                    }
                }
            }
        },
        401: {"description": "API Key invalida ou ausente"},
        429: {"description": "Rate limit excedido"}
    }
)
@limiter.limit("10/minute")
async def submit_job(
    request: Request,
    job_request: JobRequest,
    _api_key_info: Annotated[dict, Depends(verify_api_key)],
):
    _ = request
    repo = _repo()

    # Verifica idempotencia.
    if job_request.idempotency_key:
        existing_job = repo.get_job_by_idempotency_key(job_request.idempotency_key)
        if existing_job:
            return JobResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                workflow_id=existing_job.workflow_id,
                message="Job ja existe (requisicao idempotente).",
                idempotent=True,
            )

    # Cria novo job
    result = _submit_uc().execute(
        SubmitJobCommand(
            workflow_id=job_request.workflow_id,
            variables=job_request.variables,
            idempotency_key=job_request.idempotency_key,
        )
    )

    return JobResponse(
        job_id=result.job_id,
        status=result.status,
        workflow_id=job_request.workflow_id,
        message="Job enfileirado com sucesso.",
        idempotent=False,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Consultar status de um job",
    description="""
    Retorna informacoes detalhadas sobre um job especifico.

    **Autenticacao:** Requer API Key no header `X-API-Key`.

    Inclui status, timestamps, resultado e possiveis erros.
    """,
    responses={
        200: {
            "description": "Job encontrado",
            "content": {
                "application/json": {
                    "example": {
                        "job_id": "abc-123-def",
                        "status": "SUCCESS",
                        "workflow_id": "faturar_pedido",
                        "worker_id": "worker-1",
                        "started_at": "2026-05-29T10:00:00",
                        "finished_at": "2026-05-29T10:02:30",
                        "result": {"pedidos_processados": 1},
                        "error": None
                    }
                }
            }
        },
        404: {"description": "Job nao encontrado"},
        401: {"description": "API Key invalida ou ausente"}
    }
)
async def get_job(
    job_id: str,
    _api_key_info: Annotated[dict, Depends(verify_api_key)],
):
    job = _status_uc().execute(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado.")
    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        workflow_id=job.workflow_id,
        worker_id=job.worker_id,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        result=job.result,
        error=job.error,
    )


@router.get(
    "/",
    response_model=list[JobStatusResponse],
    summary="Listar jobs recentes",
    description="""
    Retorna lista de jobs recentes ordenados por data de criacao, mais recentes primeiro.

    **Autenticacao:** Requer API Key no header `X-API-Key`.

    **Rate Limit:** 30 requisicoes por minuto por IP.
    """,
    responses={
        200: {"description": "Lista de jobs retornada com sucesso"},
        401: {"description": "API Key invalida ou ausente"},
        429: {"description": "Rate limit excedido"}
    }
)
@limiter.limit("30/minute")
async def list_jobs(
    request: Request,
    _api_key_info: Annotated[dict, Depends(verify_api_key)],
    limit: int = 50,
):
    _ = request
    jobs = _list_uc().execute(limit=limit)
    return [
        JobStatusResponse(
            job_id=j.id,
            status=j.status,
            workflow_id=j.workflow_id,
            worker_id=j.worker_id,
            started_at=j.started_at.isoformat() if j.started_at else None,
            finished_at=j.finished_at.isoformat() if j.finished_at else None,
            result=j.result,
            error=j.error,
        )
        for j in jobs
    ]
