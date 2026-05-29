import uuid

from actions import ACTION_REGISTRY
from application.use_cases import WorkflowRunnerUseCase
from infrastructure.browser import PlaywrightSession
from infrastructure.observability import ErrorLogger, set_trace_context
from infrastructure.persistence.postgres_job_repository import PostgresJobRepository
from infrastructure.specs import YamlWorkflowSpecRepository
from settings import settings
from workers.celery_app import celery_app

error_logger = ErrorLogger("celery_worker")


@celery_app.task(
    bind=True,
    name="workers.job_worker.run_workflow",
    max_retries=settings.DLQ_MAX_RETRIES if settings.DLQ_ENABLED else 3,
)
def run_workflow(self, job_id: str, workflow_id: str, variables: dict):
    """
    Task Celery executada no worker Windows.
    1 task = 1 processo = 1 sessão Playwright isolada.
    Toda a lógica está no WorkflowRunnerUseCase (Clean Architecture).
    
    Suporta Dead Letter Queue (DLQ) após max_retries.
    """
    # Configura contexto de trace para logs
    trace_id = str(uuid.uuid4())
    set_trace_context(trace_id=trace_id, job_id=job_id, workflow_id=workflow_id)

    session = PlaywrightSession(
        headless=False,
        timeout_ms=settings.__dict__.get("BROWSER_TIMEOUT_MS", 30_000),
    )

    repo = PostgresJobRepository()
    use_case = WorkflowRunnerUseCase(
        job_repo=repo,
        spec_repo=YamlWorkflowSpecRepository(),
        session=session,
        action_registry=ACTION_REGISTRY,
    )

    try:
        result = use_case.execute(
            job_id=job_id,
            workflow_id=workflow_id,
            variables=variables,
        )
        return result
        
    except Exception as exc:
        retry_count = self.request.retries
        
        # Log estruturado do erro com contexto completo
        error_context = error_logger.log_exception(
            exc,
            message=f"Job {job_id} failed (attempt {retry_count + 1}/{self.max_retries + 1})",
            extra_context={
                "job_id": job_id,
                "workflow_id": workflow_id,
                "variables": variables,
                "retry_count": retry_count,
                "task_id": self.request.id,
            },
        )
        
        # Se atingiu max retries e DLQ está habilitado, salva na DLQ
        if retry_count >= self.max_retries and settings.DLQ_ENABLED:
            job = repo.get(job_id)
            if job:
                repo.save_to_dead_letter(
                    job=job,
                    retry_count=retry_count,
                    original_task_id=self.request.id,
                )
                error_logger.log_error_dict(
                    {
                        "action": "moved_to_dlq",
                        "job_id": job_id,
                        "retry_count": retry_count,
                    },
                    message=f"Job {job_id} moved to Dead Letter Queue",
                )
            raise  # Não retenta mais
        
        # Retry com backoff exponencial
        if retry_count < self.max_retries:
            raise self.retry(exc=exc, countdown=5 * (retry_count + 1))
        raise
        
    finally:
        session.close()
