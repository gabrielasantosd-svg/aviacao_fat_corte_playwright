from typing import Any

from pydantic import BaseModel, Field

from domain.value_objects import JobStatus


class JobRequest(BaseModel):
    """Request para submissao de um novo job."""

    workflow_id: str = Field(
        ...,
        description="ID do workflow em specs/workflows/",
        examples=["faturar_pedido"]
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variaveis do workflow",
        examples=[{"pedido": "P-001", "cliente": "C-123"}]
    )
    idempotency_key: str | None = Field(
        None,
        description="Chave unica para garantir idempotencia (UUID recomendado)",
        max_length=255,
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workflow_id": "faturar_pedido",
                    "variables": {"pedido": "P-001"},
                    "idempotency_key": "550e8400-e29b-41d4-a716-446655440000"
                }
            ]
        }
    }


class JobResponse(BaseModel):
    """Resposta da submissao de um job."""

    job_id: str = Field(description="ID unico do job gerado", examples=["abc-123-def"])
    status: JobStatus = Field(description="Status atual do job")
    workflow_id: str = Field(description="ID do workflow", examples=["faturar_pedido"])
    message: str = Field(default="", description="Mensagem informativa")
    idempotent: bool = Field(
        default=False,
        description="True se o job foi retornado de cache por idempotencia"
    )


class JobStatusResponse(BaseModel):
    """Resposta detalhada do status de um job."""

    job_id: str = Field(description="ID unico do job", examples=["abc-123-def"])
    status: JobStatus = Field(description="Status atual do job")
    workflow_id: str = Field(description="ID do workflow", examples=["faturar_pedido"])
    worker_id: str | None = Field(None, description="ID do worker que processou o job")
    started_at: str | None = Field(None, description="Data e hora de inicio (ISO 8601)")
    finished_at: str | None = Field(None, description="Data e hora de conclusao (ISO 8601)")
    result: dict[str, Any] | None = Field(None, description="Resultado da execucao")
    error: str | None = Field(None, description="Mensagem de erro, se houver")

    model_config = {"from_attributes": True}
