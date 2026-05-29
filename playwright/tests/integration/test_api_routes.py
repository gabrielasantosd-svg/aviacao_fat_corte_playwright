from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from domain.entities import Job
from domain.value_objects import JobStatus
from infrastructure.security import verify_api_key
from presentation.api.main import app


@pytest.fixture
def auth_override():
    # Setup: define a autenticação mockada padrão
    app.dependency_overrides[verify_api_key] = lambda: {
        "id": "test-key-id",
        "name": "Test Key",
        "scopes": ["jobs:read", "jobs:write"]
    }
    yield
    # Teardown: limpa overrides
    app.dependency_overrides.clear()


@pytest.fixture
def api_client(auth_override, in_memory_job_repo, fake_job_dispatcher):
    with (
        patch("presentation.api.main.PostgresJobRepository"),
        patch("presentation.api.routes._repo", return_value=in_memory_job_repo),
        patch("presentation.api.routes.CeleryJobDispatcher", return_value=fake_job_dispatcher),
        TestClient(app) as client,
    ):
        yield client


def test_health_endpoint():
    # Endpoint público, não precisa de autenticação
    with patch("presentation.api.main.PostgresJobRepository"), TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_deep_health_endpoint_healthy():
    # Mock do HealthChecker para não bater em banco/redis real
    with patch("infrastructure.health.healthcheck.HealthChecker.check_database") as mock_db, \
         patch("infrastructure.health.healthcheck.HealthChecker.check_redis") as mock_redis, \
         patch("presentation.api.main.PostgresJobRepository"):

        mock_db.return_value = {"status": "healthy", "type": "postgresql"}
        mock_redis.return_value = {"status": "healthy", "type": "redis"}

        with TestClient(app) as client:
            response = client.get("/health/deep")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["checks"]["database"]["status"] == "healthy"
            assert data["checks"]["redis"]["status"] == "healthy"


def test_deep_health_endpoint_degraded():
    with patch("infrastructure.health.healthcheck.HealthChecker.check_database") as mock_db, \
         patch("infrastructure.health.healthcheck.HealthChecker.check_redis") as mock_redis, \
         patch("presentation.api.main.PostgresJobRepository"):

        mock_db.return_value = {"status": "unhealthy", "error": "Connection refused", "type": "postgresql"}
        mock_redis.return_value = {"status": "healthy", "type": "redis"}

        with TestClient(app) as client:
            response = client.get("/health/deep")
            # A rota health_deep retorna o dicionário, mesmo que degraded o status HTTP pode ser 200
            # ou 503 dependendo de como o healthcheck está configurado. Na rota principal ele só retorna o JSON.
            # O status HTTP na rota principal é apenas return HealthChecker.check_all() (200 OK)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["checks"]["database"]["status"] == "unhealthy"


def test_auth_protection_missing_header():
    # Remove dependência de mock de auth para testar a validação real da falta de token
    with patch("presentation.api.main.PostgresJobRepository"), TestClient(app) as client:
        # Se fizermos requisição sem o header X-API-Key, a rota deve levantar 401
        response = client.post("/jobs/", json={"workflow_id": "faturar", "variables": {}})
        assert response.status_code == 401
        assert "Missing API Key" in response.json()["message"]


def test_submit_job_api_success(api_client, in_memory_job_repo, fake_job_dispatcher):
    payload = {
        "workflow_id": "faturar_pedido",
        "variables": {"pedido": "P-100"},
        "idempotency_key": "key-api-test"
    }

    response = api_client.post("/jobs/", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    assert data["workflow_id"] == "faturar_pedido"
    assert data["idempotent"] is False

    # Verifica se foi persistido
    job_id = data["job_id"]
    job = in_memory_job_repo.get(job_id)
    assert job is not None
    assert job.variables == {"pedido": "P-100"}

    # Verifica se foi enfileirado
    assert len(fake_job_dispatcher.dispatched_jobs) == 1
    assert fake_job_dispatcher.dispatched_jobs[0]["job_id"] == job_id


def test_submit_job_api_idempotent(api_client, in_memory_job_repo, fake_job_dispatcher):
    # Insere um job prévio
    existing_job = Job(id="job-previo", workflow_id="faturar_pedido", variables={"pedido": "P-100"}, status=JobStatus.SUCCESS)
    in_memory_job_repo.save(existing_job)
    in_memory_job_repo.store_idempotency_key("key-repetida", "job-previo")

    payload = {
        "workflow_id": "faturar_pedido",
        "variables": {"pedido": "P-100"},
        "idempotency_key": "key-repetida"
    }

    response = api_client.post("/jobs/", json=payload)

    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == "job-previo"
    assert data["status"] == "success"
    assert data["idempotent"] is True

    # Não deve enfileirar nada novo
    assert len(fake_job_dispatcher.dispatched_jobs) == 0


def test_get_job_api_found(api_client, in_memory_job_repo):
    job = Job(id="job-busca", workflow_id="faturar", variables={}, status=JobStatus.RUNNING, worker_id="worker-api")
    in_memory_job_repo.save(job)

    response = api_client.get("/jobs/job-busca")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "job-busca"
    assert data["status"] == "running"
    assert data["worker_id"] == "worker-api"


def test_get_job_api_not_found(api_client):
    response = api_client.get("/jobs/job-inexistente")
    assert response.status_code == 404
    assert "Job nao encontrado" in response.json()["message"]


def test_list_jobs_api(api_client, in_memory_job_repo):
    job1 = Job(id="job-list-1", workflow_id="faturar", variables={})
    job2 = Job(id="job-list-2", workflow_id="faturar", variables={})
    in_memory_job_repo.save(job1)
    in_memory_job_repo.save(job2)

    response = api_client.get("/jobs/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["job_id"] in ["job-list-1", "job-list-2"]
