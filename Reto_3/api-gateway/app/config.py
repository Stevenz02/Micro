import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    empleados_url: str
    departamentos_url: str
    timeout: float

    @classmethod
    def from_env(cls):
        settings = cls(
            empleados_url=os.getenv("EMPLEADOS_URL", "http://empleados-service:8081").rstrip("/"),
            departamentos_url=os.getenv("DEPARTAMENTOS_URL", "http://departamentos-service:8082").rstrip("/"),
            timeout=float(os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "5")),
        )
        for name, value in {
            "EMPLEADOS_URL": settings.empleados_url,
            "DEPARTAMENTOS_URL": settings.departamentos_url,
        }.items():
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"{name} debe ser una URL HTTP valida")
        if not 0 < settings.timeout <= 60:
            raise ValueError("GATEWAY_REQUEST_TIMEOUT_SECONDS debe estar entre 0 y 60")
        return settings
