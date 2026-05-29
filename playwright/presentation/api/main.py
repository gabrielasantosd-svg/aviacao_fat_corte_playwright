import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from infrastructure.health import HealthChecker
from infrastructure.observability import (
    configure_logging,
    configure_sentry,
    configure_tracing,
    set_trace_context,
)
from infrastructure.persistence.postgres_job_repository import PostgresJobRepository
from presentation.api.exception_handlers import register_exception_handlers
from presentation.api.routes import router
from settings import settings

# ── Configurações de observabilidade ──────────────────────────────────────
# Usar JSON format em produção para melhor parsing
json_logs = settings.__dict__.get("ENVIRONMENT", "dev") == "production"
configure_logging(json_format=json_logs)
configure_tracing()
configure_sentry()  # Error tracking (se configurado)

# ── Rate Limiter ───────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events: startup e shutdown."""
    # Startup
    PostgresJobRepository()  # garante schema criado no boot
    yield
    # Shutdown (cleanup se necessário)


app = FastAPI(
    title="GSFAT Automation API",
    description="""
    # API de Automação Visual do Protheus GSFAT
    
    Esta API permite automatizar workflows no módulo GSFAT do Protheus usando Playwright.
    
    ## Autenticação
    
    Todas as requisições precisam do header:
    
    ```
    X-API-Key: sua_chave_aqui
    ```
    
    Para criar uma API key:
    
    ```bash
    python scripts/manage_api_keys.py create "Minha Key" --scopes jobs:read jobs:write
    ```
    
    ## Workflows Disponíveis
    
    - `faturar_pedido` - Workflow de faturamento de pedido
    
    ## Idempotência
    
    Use `idempotency_key` para evitar execuções duplicadas em caso de retries.
    
    ## Rate Limiting
    
    - POST /jobs: 10 requisições/min
    - GET /jobs: 30 requisições/min
    """,
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Equipe GSFAT",
        "email": "suporte@example.com",
    },
    license_info={
        "name": "Proprietário",
    },
)

# ── Exception Handlers ─────────────────────────────────────────────────────
register_exception_handlers(app)

# ── Middlewares ────────────────────────────────────────────────────────────

# CORS
if settings.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Rate Limiting
if settings.RATE_LIMIT_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Middleware para trace context
@app.middleware("http")
async def add_trace_context(request: Request, call_next):
    """Adiciona trace_id a cada request para correlação de logs."""
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    set_trace_context(trace_id)
    
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    return response


# ── Routes ─────────────────────────────────────────────────────────────────

app.include_router(router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Healthcheck básico",
    description="Verifica se a API está respondendo (fast check).",
    responses={
        200: {
            "description": "API está saudável",
            "content": {
                "application/json": {
                    "example": {"status": "ok"}
                }
            }
        }
    }
)
def health():
    return {"status": "ok"}


@app.get(
    "/health/deep",
    tags=["Health"],
    summary="Healthcheck completo",
    description="""
    Verifica conectividade com PostgreSQL e Redis.
    
    Retorna status de cada componente e tempo de resposta.
    """,
    responses={
        200: {
            "description": "Todos os componentes saudáveis",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "checks": {
                            "postgres": {"status": "up", "latency_ms": 2.5},
                            "redis": {"status": "up", "latency_ms": 1.2}
                        }
                    }
                }
            }
        },
        503: {
            "description": "Um ou mais componentes indisponíveis"
        }
    }
)
def health_deep():
    return HealthChecker.check_all()
