"""
Carrega variáveis do .env e expõe como settings tipadas.
Usado por todos os módulos do projeto.
"""

import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _resolve_path(value: str) -> str:
    if os.path.isabs(value):
        return value
    return os.path.join(BASE_DIR, value)


load_dotenv(os.path.join(BASE_DIR, ".env"))


class Settings:
    # Protheus
    PROTHEUS_URL: str = os.getenv("PROTHEUS_URL", "")
    PROTHEUS_USER: str = os.getenv("PROTHEUS_USER", "")
    PROTHEUS_PASSWORD: str = os.getenv("PROTHEUS_PASSWORD", "")
    PROTHEUS_INITIAL_PROGRAM: str = os.getenv("PROTHEUS_INITIAL_PROGRAM", "SIGAFAT")
    PROTHEUS_SERVER_ENVIRONMENT: str = os.getenv("PROTHEUS_SERVER_ENVIRONMENT", "C5UQ0X_DEV")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # Database (PostgreSQL)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/gsfat"
    )

    # Paths
    LOG_DB_PATH: str = _resolve_path(os.getenv("LOG_DB_PATH", "logs/poc_gsfat.db"))
    SCREENSHOTS_DIR: str = _resolve_path(os.getenv("SCREENSHOTS_DIR", "screenshots"))
    REPLAYS_DIR: str = _resolve_path(os.getenv("REPLAYS_DIR", "replays"))
    SPECS_DIR: str = _resolve_path(os.getenv("SPECS_DIR", "specs"))

    # Security
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    API_KEY_HEADER: str = os.getenv("API_KEY_HEADER", "X-API-Key")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "100/minute")

    # CORS
    CORS_ENABLED: bool = os.getenv("CORS_ENABLED", "true").lower() == "true"
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Observability
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development, staging, production
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    OTEL_ENABLED: bool = os.getenv("OTEL_ENABLED", "false").lower() == "true"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
    )
    OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "gsfat-api")
    JAEGER_AGENT_HOST: str = os.getenv("JAEGER_AGENT_HOST", "localhost")
    JAEGER_AGENT_PORT: int = int(os.getenv("JAEGER_AGENT_PORT", "6831"))
    
    # Sentry (Error Tracking)
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")  # URL do Sentry (opcional)
    SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

    # Circuit Breakers
    CIRCUIT_BREAKER_PROTHEUS_FAIL_MAX: int = int(
        os.getenv("CIRCUIT_BREAKER_PROTHEUS_FAIL_MAX", "5")
    )
    CIRCUIT_BREAKER_PROTHEUS_TIMEOUT: int = int(
        os.getenv("CIRCUIT_BREAKER_PROTHEUS_TIMEOUT", "60")
    )
    CIRCUIT_BREAKER_DB_FAIL_MAX: int = int(os.getenv("CIRCUIT_BREAKER_DB_FAIL_MAX", "3"))
    CIRCUIT_BREAKER_DB_TIMEOUT: int = int(os.getenv("CIRCUIT_BREAKER_DB_TIMEOUT", "30"))

    # Dead Letter Queue
    DLQ_ENABLED: bool = os.getenv("DLQ_ENABLED", "true").lower() == "true"
    DLQ_MAX_RETRIES: int = int(os.getenv("DLQ_MAX_RETRIES", "3"))


settings = Settings()
