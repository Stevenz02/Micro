import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    departamentos_url: str
    timeout: float
    max_retries: int
    backoff: float

    @classmethod
    def from_env(cls):
        settings = cls(
            departamentos_url=os.environ["DEPARTAMENTOS_SERVICE_URL"].rstrip("/"),
            timeout=float(os.getenv("DEPARTAMENTOS_TIMEOUT_SECONDS", "2")),
            max_retries=int(os.getenv("DEPARTAMENTOS_MAX_RETRIES", "3")),
            backoff=float(os.getenv("DEPARTAMENTOS_BACKOFF_SECONDS", "1")),
        )
        url = urlsplit(settings.departamentos_url)
        if url.scheme not in {"http", "https"} or not url.hostname:
            raise ValueError("DEPARTAMENTOS_SERVICE_URL debe ser una URL HTTP válida")
        if not 0 < settings.timeout <= 60 or not 0 <= settings.max_retries <= 5:
            raise ValueError("Timeout debe estar entre 0 y 60s; reintentos entre 0 y 5")
        if not 0 < settings.backoff <= 10:
            raise ValueError("Backoff debe estar entre 0 y 10s")
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
