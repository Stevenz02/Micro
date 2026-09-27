import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    departamentos_url: str
    timeout: float
    max_retries: int
    backoff: float
    cb_fail_max: int = 3
    cb_reset_timeout: float = 30
    reconciliation_interval: float = 15

    @classmethod
    def from_env(cls):
        settings = cls(
            departamentos_url=os.environ["DEPARTAMENTOS_SERVICE_URL"].rstrip("/"),
            timeout=float(os.getenv("DEPARTAMENTOS_TIMEOUT_SECONDS", "2")),
            max_retries=int(os.getenv("DEPARTAMENTOS_MAX_RETRIES", "3")),
            backoff=float(os.getenv("DEPARTAMENTOS_BACKOFF_SECONDS", "1")),
            cb_fail_max=int(os.getenv("DEPARTAMENTOS_CB_FAIL_MAX", "3")),
            cb_reset_timeout=float(os.getenv("DEPARTAMENTOS_CB_RESET_TIMEOUT_SECONDS", "30")),
            reconciliation_interval=float(os.getenv("PENDIENTES_RECONCILIATION_INTERVAL_SECONDS", "15")),
        )
        url = urlsplit(settings.departamentos_url)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("DEPARTAMENTOS_SERVICE_URL debe ser una URL HTTP válida")
        if not 0 < settings.timeout <= 60 or not 0 <= settings.max_retries <= 5:
            raise ValueError("Timeout debe estar entre 0 y 60s; reintentos entre 0 y 5")
        if not 0 < settings.backoff <= 10:
            raise ValueError("Backoff debe estar entre 0 y 10s")
        if not 1 <= settings.cb_fail_max <= 20 or not 0 < settings.cb_reset_timeout <= 300:
            raise ValueError("Circuit Breaker debe tener fail_max entre 1 y 20 y reset entre 0 y 300s")
        if not 1 <= settings.reconciliation_interval <= 300:
            raise ValueError("El intervalo de reconciliacion debe estar entre 1 y 300s")
        return settings


def database_config():
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": 5,
        "options": "-c statement_timeout=5000",
    }
