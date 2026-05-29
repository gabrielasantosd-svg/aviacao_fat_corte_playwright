"""
Exception handlers customizados para FastAPI.
Garante respostas de erro padronizadas e logging completo.
"""

import logging
from typing import Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pybreaker import CircuitBreakerError
from slowapi.errors import RateLimitExceeded

from infrastructure.observability.metrics import ErrorLogger

error_logger = ErrorLogger("api_error_handler")
log = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler para HTTPException (erros esperados da API)."""
    # Log apenas erros 5xx (erros de servidor)
    if exc.status_code >= 500:
        error_logger.log_exception(
            exc,
            message=f"HTTP {exc.status_code} Error",
            level=logging.ERROR,
            extra_context={
                "url": str(request.url),
                "method": request.method,
                "client": request.client.host if request.client else None,
            },
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "error_type": "HTTPException",
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handler para erros de validação de request (Pydantic)."""
    log.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={"errors": exc.errors(), "body": exc.body},
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "error_type": "ValidationError",
            "status_code": 422,
            "message": "Erro de validação nos dados da requisição",
            "details": exc.errors(),
            "path": str(request.url.path),
        },
    )


async def circuit_breaker_exception_handler(
    request: Request, exc: CircuitBreakerError
) -> JSONResponse:
    """Handler para circuit breaker aberto."""
    error_logger.log_exception(
        exc,
        message="Circuit breaker open",
        level=logging.WARNING,
        extra_context={
            "url": str(request.url),
            "method": request.method,
            "circuit_breaker": str(exc),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": True,
            "error_type": "CircuitBreakerOpen",
            "status_code": 503,
            "message": "Serviço temporariamente indisponível devido a falhas recentes. Tente novamente em breve.",
            "path": str(request.url.path),
        },
    )


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handler para rate limit excedido."""
    log.warning(
        f"Rate limit exceeded: {request.client.host if request.client else 'unknown'} - {request.url.path}"
    )

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": True,
            "error_type": "RateLimitExceeded",
            "status_code": 429,
            "message": "Limite de requisições excedido. Tente novamente mais tarde.",
            "path": str(request.url.path),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handler genérico para exceções não tratadas.
    Captura e loga qualquer erro inesperado.
    """
    # Log completo do erro
    error_context = error_logger.log_exception(
        exc,
        message=f"Unhandled exception on {request.method} {request.url.path}",
        level=logging.CRITICAL,
        extra_context={
            "url": str(request.url),
            "method": request.method,
            "client": request.client.host if request.client else None,
            "headers": dict(request.headers),
        },
    )

    # Em produção, não expor detalhes internos
    from settings import settings

    if settings.__dict__.get("DEBUG", False):
        error_message = f"{error_context['error_type']}: {error_context['error_message']}"
        include_trace = True
    else:
        error_message = "Erro interno do servidor. Contate o suporte."
        include_trace = False

    response_content = {
        "error": True,
        "error_type": "InternalServerError",
        "status_code": 500,
        "message": error_message,
        "path": str(request.url.path),
        "trace_id": error_context["trace_id"],
    }

    # Adiciona stacktrace apenas em modo debug
    if include_trace and error_context.get("stacktrace_summary"):
        response_content["stacktrace"] = error_context["stacktrace_summary"]

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=response_content)


def register_exception_handlers(app):
    """
    Registra todos os exception handlers na aplicação FastAPI.
    
    Deve ser chamado durante a inicialização da app.
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(CircuitBreakerError, circuit_breaker_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    log.info("Exception handlers registered successfully")
