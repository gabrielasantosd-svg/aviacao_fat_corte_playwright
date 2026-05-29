"""Healthcheck robusto que verifica todas as dependencias."""

import logging
from typing import Any

import redis
from sqlalchemy import text

from infrastructure.persistence.postgres_job_repository import SessionLocal
from settings import settings

log = logging.getLogger(__name__)


class HealthChecker:
    """Verifica a saude de todas as dependencias do sistema."""

    @staticmethod
    def check_database() -> dict[str, Any]:
        """Verifica conexao com PostgreSQL."""
        try:
            session = SessionLocal()
            session.execute(text("SELECT 1"))
            session.close()
            return {"status": "healthy", "type": "postgresql"}
        except Exception as e:
            log.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e), "type": "postgresql"}

    @staticmethod
    def check_redis() -> dict[str, Any]:
        """Verifica conexao com Redis."""
        try:
            r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
            r.ping()
            return {"status": "healthy", "type": "redis"}
        except Exception as e:
            log.error(f"Redis health check failed: {e}")
            return {"status": "unhealthy", "error": str(e), "type": "redis"}

    @staticmethod
    def check_all() -> dict[str, Any]:
        """
        Executa todos os healthchecks.
        Retorna status agregado e detalhes de cada componente.
        """
        checks = {
            "database": HealthChecker.check_database(),
            "redis": HealthChecker.check_redis(),
        }

        # Status agregado: so fica healthy se todos estiverem healthy.
        overall_healthy = all(check["status"] == "healthy" for check in checks.values())

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "checks": checks,
        }
