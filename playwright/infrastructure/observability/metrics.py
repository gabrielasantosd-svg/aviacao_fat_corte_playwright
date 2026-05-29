"""Configuracao de observabilidade com logs estruturados e tracing OpenTelemetry."""

import importlib
import json
import logging
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime
from typing import Any

from settings import settings

trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)
workflow_id_var: ContextVar[str | None] = ContextVar("workflow_id", default=None)


class StructuredFormatter(logging.Formatter):
    """Formatter para logs estruturados com trace_id e contexto completo."""

    def format(self, record: logging.LogRecord) -> str:
        record.trace_id = trace_id_var.get() or "-"
        record.job_id = job_id_var.get() or "-"
        record.workflow_id = workflow_id_var.get() or "-"

        if record.exc_info:
            record.exception_type = record.exc_info[0].__name__ if record.exc_info[0] else "-"
            record.exception_message = str(record.exc_info[1]) if record.exc_info[1] else "-"
        else:
            record.exception_type = "-"
            record.exception_message = "-"

        return super().format(record)


class JSONFormatter(logging.Formatter):
    """Formatter JSON para logs estruturados."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "trace_id": trace_id_var.get(),
            "job_id": job_id_var.get(),
            "workflow_id": workflow_id_var.get(),
        }

        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "stacktrace": self._get_stacktrace(record.exc_info),
            }

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data, ensure_ascii=False)

    @staticmethod
    def _get_stacktrace(exc_info: Any) -> list[str]:
        return traceback.format_exception(*exc_info)


def configure_logging(json_format: bool = False) -> None:
    """Configura logging estruturado para toda a aplicacao."""
    formatter: logging.Formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter(
            "%(asctime)s | %(levelname)-8s | trace_id=%(trace_id)s | "
            "job_id=%(job_id)s | workflow_id=%(workflow_id)s | "
            "%(name)s:%(lineno)d | %(message)s"
        )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.__dict__.get("LOG_LEVEL", "INFO")))
    root_logger.handlers = []
    root_logger.addHandler(console_handler)


def set_trace_context(trace_id: str, job_id: str = "-", workflow_id: str = "-") -> None:
    """Define contexto de trace para logging estruturado."""
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


def get_logger(name: str, **kwargs: Any) -> logging.LoggerAdapter:
    """Retorna logger com contexto extra para structured logging."""
    return logging.LoggerAdapter(logging.getLogger(name), kwargs)


class ErrorLogger:
    """Logger centralizado para erros com captura completa de contexto."""

    def __init__(self, logger_name: str = "error_logger"):
        self.logger = logging.getLogger(logger_name)

    def log_exception(
        self,
        exception: Exception,
        message: str = "Erro capturado",
        level: int = logging.ERROR,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        error_context = self._build_error_context(exception, extra_context)
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
    ) -> None:
        self.logger.log(level, f"{message}: {error_dict}", extra={"extra_fields": error_dict})

    @staticmethod
    def _build_error_context(
        exception: Exception,
        extra_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        error_context: dict[str, Any] = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "error_module": exception.__class__.__module__,
            "stacktrace": traceback.format_exception(exc_type, exc_value, exc_traceback)
            if exc_traceback
            else [],
            "stacktrace_summary": traceback.format_exc() if exc_traceback else None,
            "file": exc_traceback.tb_frame.f_code.co_filename if exc_traceback else None,
            "line": exc_traceback.tb_lineno if exc_traceback else None,
            "function": exc_traceback.tb_frame.f_code.co_name if exc_traceback else None,
            "trace_id": trace_id_var.get(),
            "job_id": job_id_var.get(),
            "workflow_id": workflow_id_var.get(),
            "timestamp": datetime.utcnow().isoformat(),
        }

        if extra_context:
            error_context["extra"] = extra_context

        if hasattr(exception, "__dict__"):
            error_context["exception_attributes"] = {
                key: value for key, value in exception.__dict__.items() if not key.startswith("_")
            }

        return error_context

    @staticmethod
    def format_error_for_api(
        exception: Exception,
        include_stacktrace: bool = False,
    ) -> dict[str, Any]:
        error_response: dict[str, Any] = {
            "error": True,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id_var.get(),
        }

        if include_stacktrace and settings.__dict__.get("DEBUG", False):
            error_response["stacktrace"] = traceback.format_exc()

        return error_response


def configure_sentry() -> None:
    """Configura Sentry para error tracking e monitoring quando estiver disponivel."""
    sentry_dsn = settings.__dict__.get("SENTRY_DSN")
    if not sentry_dsn:
        return

    try:
        sentry_sdk = importlib.import_module("sentry_sdk")
        celery_module = importlib.import_module("sentry_sdk.integrations.celery")
        logging_module = importlib.import_module("sentry_sdk.integrations.logging")
        sqlalchemy_module = importlib.import_module("sentry_sdk.integrations.sqlalchemy")

        sentry_logging = logging_module.LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.__dict__.get("ENVIRONMENT", "development"),
            traces_sample_rate=settings.__dict__.get("SENTRY_TRACES_SAMPLE_RATE", 0.1),
            integrations=[
                sentry_logging,
                celery_module.CeleryIntegration(),
                sqlalchemy_module.SqlalchemyIntegration(),
            ],
            before_send=_sentry_before_send,
        )
        logging.info("Sentry error tracking configured successfully")
    except ImportError:
        logging.warning("Sentry SDK not installed. Error tracking disabled.")


def _sentry_before_send(event: dict[str, Any], _hint: Any) -> dict[str, Any]:
    """Adiciona contexto customizado aos eventos do Sentry."""
    event.setdefault("tags", {}).update(get_trace_context())

    if job_id_var.get():
        event.setdefault("extra", {})["job_id"] = job_id_var.get()
    if workflow_id_var.get():
        event.setdefault("extra", {})["workflow_id"] = workflow_id_var.get()

    return event


def configure_tracing() -> None:
    """Configura OpenTelemetry tracing quando habilitado."""
    if not settings.OTEL_ENABLED:
        return

    try:
        trace = importlib.import_module("opentelemetry.trace")
        otlp_module = importlib.import_module(
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter"
        )
        celery_module = importlib.import_module("opentelemetry.instrumentation.celery")
        fastapi_module = importlib.import_module("opentelemetry.instrumentation.fastapi")
        resources_module = importlib.import_module("opentelemetry.sdk.resources")
        trace_sdk_module = importlib.import_module("opentelemetry.sdk.trace")
        export_module = importlib.import_module("opentelemetry.sdk.trace.export")

        resource = resources_module.Resource.create(
            {"service.name": settings.OTEL_SERVICE_NAME}
        )
        provider = trace_sdk_module.TracerProvider(resource=resource)
        processor = export_module.BatchSpanProcessor(
            otlp_module.OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        fastapi_module.FastAPIInstrumentor().instrument()
        celery_module.CeleryInstrumentor().instrument()

        logging.info("OpenTelemetry tracing configured successfully")
    except ImportError as exc:
        logging.warning("Failed to configure OpenTelemetry: %s", exc)
