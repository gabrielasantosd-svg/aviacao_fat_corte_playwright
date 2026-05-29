"""
Configuração de observabilidade: logs estruturados e tracing OpenTelemetry.
"""

import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Optional

from settings import settings

# Context vars para trace context (correlação de logs)
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
job_id_var: ContextVar[Optional[str]] = ContextVar("job_id", default=None)
workflow_id_var: ContextVar[Optional[str]] = ContextVar("workflow_id", default=None)


# ── Structured Logging ─────────────────────────────────────────────────────


class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados com trace_id e contexto completo."""

    def format(self, record: logging.LogRecord) -> str:
        # Adiciona contexto de trace
        record.trace_id = trace_id_var.get() or "-"
        record.job_id = job_id_var.get() or "-"
        record.workflow_id = workflow_id_var.get() or "-"

        # Adiciona informações de exceção formatadas
        if record.exc_info:
            record.exception_type = record.exc_info[0].__name__ if record.exc_info[0] else "-"
            record.exception_message = str(record.exc_info[1]) if record.exc_info[1] else "-"
        else:
            record.exception_type = "-"
            record.exception_message = "-"

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Formatter JSON para logs estruturados (ideal para parsing por ferramentas)."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get() or None,
            "job_id": job_id_var.get() or None,
            "workflow_id": workflow_id_var.get() or None,
        }

        # Adiciona informações de exceção se disponível
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": self._get_stacktrace(record.exc_info),
            }

        # Adiciona campos extras customizados
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, ensure_ascii=False)

    @staticmethod
    def _get_stacktrace(exc_info) -> list[str]:
        """Extrai stack trace formatado."""
        return traceback.format_exception(*exc_info)


def configure_logging(json_format: bool = False):
    """
    Configura logging estruturado para toda a aplicação.
    
    Args:
        json_format: Se True, usa JSONFormatter (ideal para produção e parsing).
                    Se False, usa formato legível para humanos (dev).
    """
    if json_format:
        formatter = JSONFormatter()
    else:
        log_format = (
            "%(asctime)s | %(levelname)-8s | trace_id=%(trace_id)s | "
            "job_id=%(job_id)s | workflow_id=%(workflow_id)s | "
            "%(name)s:%(lineno)d | %(message)s"
        )
        formatter = StructuredFormatter(log_format)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.__dict__.get("LOG_LEVEL", "INFO")))
    root_logger.handlers = []  # Remove handlers existentes
    root_logger.addHandler(console_handler)

    job_id_var.set(job_id)
    workflow_id_var.set(workflow_id)


def get_trace_context() -> dict[str, str]:
    """Retorna o contexto de trace atual."""
    return {
        "trace_id": trace_id_var.get() or "-",
        "job_id": job_id_var.get() or "-",
        "workflow_id": workflow_id_var.get() or "-",
    }


def get_logger(name: str, **kwargs) -> logging.LoggerAdapter:
    """
    Retorna logger com contexto extra para structured logging.
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, kwargs)


# ── Error Logging ──────────────────────────────────────────────────────────


class ErrorLogger:
    """
    Logger centralizado para erros com captura completa de contexto.
    Garante que todos os erros sejam logados de forma padronizada.
    """

    def __init__(self, logger_name: str = "error_logger"):
        self.logger = logging.getLogger(logger_name)

    def log_exception(
        self,
        exception: Exception,
        message: str = "Erro capturado",
        level: int = logging.ERROR,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Loga uma exceção com contexto completo e retorna estrutura padronizada.

        Args:
            exception: Exceção capturada
            message: Mensagem descritiva do contexto do erro
            level: Nível do log (ERROR, WARNING, CRITICAL)
            extra_context: Dicionário com contexto adicional

        Returns:
            Dict com estrutura padronizada do erro
        """
        error_context = self._build_error_context(exception, extra_context)

        # Log estruturado
        self.logger.log(
            level,
            f"{message}: {error_context['error_type']} - {error_context['error_message']}",
            exc_info=True,
            extra={"extra_fields": error_context},
        )

        return error_context

    def log_error_dict(
        self,
        error_dict: dict[str, Any],
        message: str = "Erro processado",
        level: int = logging.ERROR,
    ):
        """
        Loga um erro já estruturado como dict.
        Útil quando a exceção já foi processada anteriormente.
        """
        self.logger.log(level, f"{message}: {error_dict}", extra={"extra_fields": error_dict})

    @staticmethod
    def _build_error_context(
        exception: Exception, extra_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Constrói estrutura padronizada de erro com todos os detalhes.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()

        error_context = {
            # Informações básicas da exceção
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "error_module": exception.__class__.__module__,
            # Stack trace completo
            "stacktrace": traceback.format_exception(exc_type, exc_value, exc_traceback)
            if exc_traceback
            else [],
            "stacktrace_summary": traceback.format_exc() if exc_traceback else None,
            # Localização do erro
            "file": exc_traceback.tb_frame.f_code.co_filename if exc_traceback else None,
            "line": exc_traceback.tb_lineno if exc_traceback else None,
            "function": exc_traceback.tb_frame.f_code.co_name if exc_traceback else None,
            # Contexto de trace
            "trace_id": trace_id_var.get(),
            "job_id": job_id_var.get(),
            "workflow_id": workflow_id_var.get(),
            # Timestamp
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Adiciona contexto extra se fornecido
        if extra_context:
            error_context["extra"] = extra_context

        # Captura atributos customizados da exceção
        if hasattr(exception, "__dict__"):
            error_context["exception_attributes"] = {
                k: v for k, v in exception.__dict__.items() if not k.startswith("_")
            }

        return error_context

    @staticmethod
    def format_error_for_api(exception: Exception, include_stacktrace: bool = False) -> dict:
        """
        Formata erro para resposta da API (sanitizado, sem expor internals em prod).

        Args:
            exception: Exceção a ser formatada
            include_stacktrace: Se True, inclui stacktrace (apenas para dev/debug)

        Returns:
            Dict formatado para resposta JSON da API
        """
        error_response = {
            "error": True,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id_var.get(),
        }

        # Stacktrace apenas em modo debug (não expor em produção)
        if include_stacktrace and settings.__dict__.get("DEBUG", False):
            error_response["stacktrace"] = traceback.format_exc()

        return error_response


# ── Sentry Integration (Opcional) ─────────────────────────────────────────


def configure_sentry():
    """
    Configura Sentry para error tracking e monitoring (opcional).
    Requer: pip install sentry-sdk
    """
    sentry_dsn = settings.__dict__.get("SENTRY_DSN")
    if not sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Captura logs INFO e acima
            event_level=logging.ERROR,  # Cria eventos no Sentry para ERROR e acima
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.__dict__.get("ENVIRONMENT", "development"),
            traces_sample_rate=settings.__dict__.get("SENTRY_TRACES_SAMPLE_RATE", 0.1),
            integrations=[
                sentry_logging,
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            # Adiciona contexto de trace
            before_send=_sentry_before_send,
        )

        logging.info("Sentry error tracking configured successfully")

    except ImportError:
        logging.warning("Sentry SDK not installed. Error tracking disabled.")


def _sentry_before_send(event, hint):
    """Adiciona contexto customizado aos eventos do Sentry."""
    # Adiciona trace context
    event.setdefault("tags", {}).update(get_trace_context())

    # Adiciona informações do job se disponível
    if job_id_var.get():
        event.setdefault("extra", {})["job_id"] = job_id_var.get()
    if workflow_id_var.get():
        event.setdefault("extra", {})["workflow_id"] = workflow_id_var.get()

    return event

def configure_tracing():
    """Configura OpenTelemetry tracing (se habilitado)."""
    if not settings.OTEL_ENABLED:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Resource com informações do serviço
        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})

        # Provider
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        # Instrumentação automática
        FastAPIInstrumentor().instrument()
        CeleryInstrumentor().instrument()

        logging.info("OpenTelemetry tracing configured successfully")

    except ImportError as e:
        logging.warning(f"Failed to configure OpenTelemetry: {e}")


# ── Helpers ────────────────────────────────────────────────────────────────


def set_trace_context(trace_id: str, job_id: str = "-", workflow_id: str = "-"):
    """
    Define contexto de trace para logging estruturado.
    Deve ser chamado no início de cada request/task.
    """
    trace_id_var.set(trace_id)
    job_id_var.set(job_id)
    workflow_id_var.set(workflow_id)


def get_trace_context() -> dict[str, str]:
    """Retorna o contexto de trace atual."""
    return {
        "trace_id": trace_id_var.get() or "-",
        "job_id": job_id_var.get() or "-",
        "workflow_id": workflow_id_var.get() or "-",
    }


def get_logger(name: str, **kwargs) -> logging.LoggerAdapter:
    """
    Retorna logger com contexto extra para structured logging.
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, kwargs)


# ── Error Logging ──────────────────────────────────────────────────────────


class ErrorLogger:
    """
    Logger centralizado para erros com captura completa de contexto.
    Garante que todos os erros sejam logados de forma padronizada.
    """

    def __init__(self, logger_name: str = "error_logger"):
        self.logger = logging.getLogger(logger_name)

    def log_exception(
        self,
        exception: Exception,
        message: str = "Erro capturado",
        level: int = logging.ERROR,
        extra_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Loga uma exceção com contexto completo e retorna estrutura padronizada.

        Args:
            exception: Exceção capturada
            message: Mensagem descritiva do contexto do erro
            level: Nível do log (ERROR, WARNING, CRITICAL)
            extra_context: Dicionário com contexto adicional

        Returns:
            Dict com estrutura padronizada do erro
        """
        error_context = self._build_error_context(exception, extra_context)

        # Log estruturado
        self.logger.log(
            level,
            f"{message}: {error_context['error_type']} - {error_context['error_message']}",
            exc_info=True,
            extra={"extra_fields": error_context},
        )

        return error_context

    def log_error_dict(
        self,
        error_dict: dict[str, Any],
        message: str = "Erro processado",
        level: int = logging.ERROR,
    ):
        """
        Loga um erro já estruturado como dict.
        Útil quando a exceção já foi processada anteriormente.
        """
        self.logger.log(level, f"{message}: {error_dict}", extra={"extra_fields": error_dict})

    @staticmethod
    def _build_error_context(
        exception: Exception, extra_context: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Constrói estrutura padronizada de erro com todos os detalhes.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()

        error_context = {
            # Informações básicas da exceção
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "error_module": exception.__class__.__module__,
            # Stack trace completo
            "stacktrace": traceback.format_exception(exc_type, exc_value, exc_traceback)
            if exc_traceback
            else [],
            "stacktrace_summary": traceback.format_exc() if exc_traceback else None,
            # Localização do erro
            "file": exc_traceback.tb_frame.f_code.co_filename if exc_traceback else None,
            "line": exc_traceback.tb_lineno if exc_traceback else None,
            "function": exc_traceback.tb_frame.f_code.co_name if exc_traceback else None,
            # Contexto de trace
            "trace_id": trace_id_var.get(),
            "job_id": job_id_var.get(),
            "workflow_id": workflow_id_var.get(),
            # Timestamp
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Adiciona contexto extra se fornecido
        if extra_context:
            error_context["extra"] = extra_context

        # Captura atributos customizados da exceção
        if hasattr(exception, "__dict__"):
            error_context["exception_attributes"] = {
                k: v for k, v in exception.__dict__.items() if not k.startswith("_")
            }

        return error_context

    @staticmethod
    def format_error_for_api(exception: Exception, include_stacktrace: bool = False) -> dict:
        """
        Formata erro para resposta da API (sanitizado, sem expor internals em prod).

        Args:
            exception: Exceção a ser formatada
            include_stacktrace: Se True, inclui stacktrace (apenas para dev/debug)

        Returns:
            Dict formatado para resposta JSON da API
        """
        error_response = {
            "error": True,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id_var.get(),
        }

        # Stacktrace apenas em modo debug (não expor em produção)
        if include_stacktrace and settings.__dict__.get("DEBUG", False):
            error_response["stacktrace"] = traceback.format_exc()

        return error_response


# ── Sentry Integration (Opcional) ─────────────────────────────────────────


def configure_sentry():
    """
    Configura Sentry para error tracking e monitoring (opcional).
    Requer: pip install sentry-sdk
    """
    sentry_dsn = settings.__dict__.get("SENTRY_DSN")
    if not sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Captura logs INFO e acima
            event_level=logging.ERROR,  # Cria eventos no Sentry para ERROR e acima
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.__dict__.get("ENVIRONMENT", "development"),
            traces_sample_rate=settings.__dict__.get("SENTRY_TRACES_SAMPLE_RATE", 0.1),
            integrations=[
                sentry_logging,
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            # Adiciona contexto de trace
            before_send=_sentry_before_send,
        )

        logging.info("Sentry error tracking configured successfully")

    except ImportError:
        logging.warning("Sentry SDK not installed. Error tracking disabled.")


def _sentry_before_send(event, hint):
    """Adiciona contexto customizado aos eventos do Sentry."""
    # Adiciona trace context
    event.setdefault("tags", {}).update(get_trace_context())

    # Adiciona informações do job se disponível
    if job_id_var.get():
        event.setdefault("extra", {})["job_id"] = job_id_var.get()
    if workflow_id_var.get():
        event.setdefault("extra", {})["workflow_id"] = workflow_id_var.get()

    return event
