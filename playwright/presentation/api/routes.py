from fastapi import APIRouter, Depends, HTTPException
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
from settings import settings

router = APIRouter(prefix="/jobs", tags=["jobs"])
limiter = Limiter(key_func=get_remote_address)


# ── Dependency composition (simples; sem DI framework) ───────────────────────
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
    Submete um novo job para execução assíncrona.
    
    **Autenticação:** Requer API Key no header `X-API-Key`.
    
    **Idempotência:** Use `idempotency_key` para evitar execução duplicada.
    Se um job com a mesma key já existir, retorna o job existente.
    
    **Rate Limit:** 10 requisições por minuto por IP.
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
        401: {"description": "API Key inválida ou ausente"},
        429: {"description": "Rate limit excedido"}
    }
)
@limiter.limit("10/minute")
async def submit_job(
    request: JobRequest,
    api_key_info: dict = Depends(verify_api_key),
):
    repo = _repo()
    
    # Verifica idempotência
    if request.idempotency_key:
        existing_job = repo.get_job_by_idempotency_key(request.idempotency_key)
        if existing_job:
            return JobResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                workflow_id=existing_job.workflow_id,
                message="Job já existe (requisição idempotente).",
                idempotent=True,
            )
    
    # Cria novo job
    result = _submit_uc().execute(
        SubmitJobCommand(
            workflow_id=request.workflow_id,
            variables=request.variables,
            idempotency_key=request.idempotency_key,
        )
    )
    
    return JobResponse(
        job_id=result.job_id,
        status=result.status,
        workflow_id=request.workflow_id,
        message="Job enfileirado com sucesso.",
        idempotent=False,
    )


@router.get(
    "/{job_id}",
    response_model=JobStatusResponse,
    summary="Consultar status de um job",
    description="""
    Retorna informações detalhadas sobre um job específico.
    
    **Autenticação:** Requer API Key no header `X-API-Key`.
    
    Inclui status, timestamps, resultado e possíveis erros.
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
        404: {"description": "Job não encontrado"},
        401: {"description": "API Key inválida ou ausente"}
    }
)
async def get_job(
    job_id: str,
    api_key_info: dict = Depends(verify_api_key),
):
    job = _status_uc().execute(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
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
    Retorna lista de jobs recentes ordenados por data de criação (mais recentes primeiro).
    
    **Autenticação:** Requer API Key no header `X-API-Key`.
    
    **Rate Limit:** 30 requisições por minuto por IP.
    """,
    responses={
        200: {"description": "Lista de jobs retornada com sucesso"},
        401: {"description": "API Key inválida ou ausente"},
        429: {"description": "Rate limit excedido"}
    }
)
@limiter.limit("30/minute")
async def list_jobs(
    limit: int = 50,
    api_key_info: dict = Depends(verify_api_key),
):
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
