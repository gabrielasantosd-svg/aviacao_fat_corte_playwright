"""
PostgreSQL repository para jobs - substituindo SQLite.
"""

import json
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Generator, Optional

from pybreaker import CircuitBreaker
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, sessionmaker

from domain.entities import Job
from domain.repositories import AbstractJobRepository
from domain.value_objects import JobStatus, StepResult
from infrastructure.persistence.models import (
    Base,
    DeadLetterJobModel,
    IdempotencyKeyModel,
    JobModel,
)
from settings import settings

# Circuit breaker para PostgreSQL
db_breaker = CircuitBreaker(
    fail_max=settings.CIRCUIT_BREAKER_DB_FAIL_MAX,
    timeout_duration=settings.CIRCUIT_BREAKER_DB_TIMEOUT,
    name="postgres_connection",
)

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency para FastAPI obter sessão do banco."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PostgresJobRepository(AbstractJobRepository):
    """Implementação PostgreSQL do repositório de jobs."""

    def __init__(self, session: Optional[Session] = None):
        """
        Inicializa o repositório.
        Se session não for fornecida, cria schema automaticamente.
        """
        if session is None:
            Base.metadata.create_all(bind=engine)
        self._external_session = session

    @contextmanager
    def _get_session(self) -> Generator[Session, None, None]:
        """Context manager para sessão do banco."""
        if self._external_session:
            yield self._external_session
        else:
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

    @db_breaker
    def save(self, job: Job) -> None:
        """Salva ou atualiza um job no banco."""
        with self._get_session() as session:
            model = session.query(JobModel).filter(JobModel.id == job.id).first()

            if model:
                # Update
                model.status = job.status.value
                model.worker_id = job.worker_id
                model.started_at = job.started_at
                model.finished_at = job.finished_at
                model.result = job.result
                model.error = job.error
                model.steps = [self._step_to_dict(s) for s in job.steps]
                model.completed_step_ids = list(
                    getattr(job, "completed_step_ids", set())
                )  # Para idempotência
                model.updated_at = datetime.utcnow()
            else:
                # Insert
                model = JobModel(
                    id=job.id,
                    workflow_id=job.workflow_id,
                    variables=job.variables,
                    status=job.status.value,
                    worker_id=job.worker_id,
                    started_at=job.started_at,
                    finished_at=job.finished_at,
                    result=job.result,
                    error=job.error,
                    steps=[self._step_to_dict(s) for s in job.steps],
                    completed_step_ids=list(getattr(job, "completed_step_ids", set())),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(model)

    @db_breaker
    def get(self, job_id: str) -> Optional[Job]:
        """Busca um job por ID."""
        with self._get_session() as session:
            model = session.query(JobModel).filter(JobModel.id == job_id).first()
            if not model:
                return None
            return self._model_to_entity(model)

    @db_breaker
    def list(self, limit: int = 50, status: Optional[JobStatus] = None) -> list[Job]:
        """Lista jobs com filtros opcionais."""
        with self._get_session() as session:
            query = session.query(JobModel).order_by(desc(JobModel.created_at))

            if status:
                query = query.filter(JobModel.status == status.value)

            models = query.limit(limit).all()
            return [self._model_to_entity(m) for m in models]

    def get_job_by_idempotency_key(self, key: str) -> Optional[Job]:
        """Busca job por chave de idempotência."""
        with self._get_session() as session:
            idem = session.query(IdempotencyKeyModel).filter(IdempotencyKeyModel.key == key).first()
            if not idem:
                return None

            # Verifica expiração
            if idem.expires_at and idem.expires_at < datetime.utcnow():
                return None

            return self.get(idem.job_id)

    def store_idempotency_key(self, key: str, job_id: str, ttl_hours: int = 24) -> None:
        """Armazena chave de idempotência."""
        with self._get_session() as session:
            idem = IdempotencyKeyModel(
                key=key,
                job_id=job_id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
            )
            session.add(idem)

    def save_to_dead_letter(
        self, job: Job, retry_count: int, original_task_id: Optional[str] = None
    ) -> None:
        """Salva job na Dead Letter Queue após falhas consecutivas."""
        with self._get_session() as session:
            dlq = DeadLetterJobModel(
                id=str(uuid.uuid4()),
                job_id=job.id,
                workflow_id=job.workflow_id,
                variables=job.variables,
                error=job.error or "Unknown error",
                retry_count=retry_count,
                original_task_id=original_task_id,
                created_at=datetime.utcnow(),
            )
            session.add(dlq)

    def _model_to_entity(self, model: JobModel) -> Job:
        """Converte SQLAlchemy model para domain entity."""
        job = Job(
            id=model.id,
            workflow_id=model.workflow_id,
            variables=model.variables,
            status=JobStatus(model.status),
            worker_id=model.worker_id,
            started_at=model.started_at,
            finished_at=model.finished_at,
            result=model.result,
            error=model.error,
            steps=[self._dict_to_step(s) for s in model.steps],
        )
        # Restaura completed_step_ids para checkpointing
        job.completed_step_ids = set(model.completed_step_ids or [])
        return job

    @staticmethod
    def _step_to_dict(step: StepResult) -> dict:
        """Serializa StepResult para dict."""
        return {
            "step": step.step,
            "status": step.status,
            "duration_ms": step.duration_ms,
            "output": step.output,
            "detail": step.detail,
        }

    @staticmethod
    def _dict_to_step(data: dict) -> StepResult:
        """Desserializa dict para StepResult."""
        return StepResult(
            step=data["step"],
            status=data["status"],
            duration_ms=data["duration_ms"],
            output=data.get("output"),
            detail=data.get("detail"),
        )
