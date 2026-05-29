"""
SQLiteJobRepository — implementação concreta de AbstractJobRepository.
Toda a infra de banco fica aqui; o domínio não sabe de SQLite.
"""

import json
import os
import sqlite3
from datetime import datetime

from domain.entities import Job
from domain.repositories import AbstractJobRepository
from domain.value_objects import JobStatus
from settings import settings


class SQLiteJobRepository(AbstractJobRepository):
    def __init__(self, db_path: str = settings.LOG_DB_PATH):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_schema()

    # ── schema ────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id          TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    variables   TEXT NOT NULL DEFAULT '{}',
                    status      TEXT NOT NULL DEFAULT 'pending',
                    worker_id   TEXT,
                    started_at  TEXT,
                    finished_at TEXT,
                    result      TEXT,
                    error       TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_logs (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id      TEXT NOT NULL,
                    timestamp   TEXT NOT NULL,
                    step        TEXT NOT NULL,
                    status      TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    detail      TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                )
            """)

    # ── AbstractJobRepository ─────────────────────────────────────────

    def save(self, job: Job) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, workflow_id, variables, status, worker_id,
                                  started_at, finished_at, result, error)
                VALUES (:id, :workflow_id, :variables, :status, :worker_id,
                        :started_at, :finished_at, :result, :error)
                ON CONFLICT(id) DO UPDATE SET
                    status      = excluded.status,
                    worker_id   = excluded.worker_id,
                    started_at  = excluded.started_at,
                    finished_at = excluded.finished_at,
                    result      = excluded.result,
                    error       = excluded.error
            """,
                {
                    "id": job.id,
                    "workflow_id": job.workflow_id,
                    "variables": json.dumps(job.variables),
                    "status": job.status.value,
                    "worker_id": job.worker_id,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                    "result": json.dumps(job.result) if job.result else None,
                    "error": job.error,
                },
            )

    def get(self, job_id: str) -> Job | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_recent(self, limit: int = 50) -> list[Job]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs ORDER BY rowid DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def log_step(
        self, job_id: str, step: str, status: str, duration_ms: int, detail: str = ""
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO step_logs (job_id, timestamp, step, status, duration_ms, detail)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (job_id, datetime.utcnow().isoformat(), step, status, duration_ms, detail),
            )

    # ── helpers ───────────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            id=row["id"],
            workflow_id=row["workflow_id"],
            variables=json.loads(row["variables"]),
            status=JobStatus(row["status"]),
            worker_id=row["worker_id"],
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            result=json.loads(row["result"]) if row["result"] else None,
            error=row["error"],
        )
