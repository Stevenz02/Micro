import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    empleados_url: str
    departamentos_url: str
    timeout: float
    perfiles_url: str = "http://perfiles-service:8083"
    notificaciones_url: str = "http://notificaciones-service:8084"
    vacaciones_url: str = "http://vacaciones-service:8085"
    auth_url: str = ""
    jwt_secret: str = ""

    @classmethod
    def from_env(cls):
        settings = cls(
            empleados_url=os.getenv("EMPLEADOS_URL", "http://empleados-service:8081").rstrip("/"),
            departamentos_url=os.getenv("DEPARTAMENTOS_URL", "http://departamentos-service:8082").rstrip("/"),
            timeout=float(os.getenv("GATEWAY_REQUEST_TIMEOUT_SECONDS", "20")),
            perfiles_url=os.getenv("PERFILES_URL", "http://perfiles-service:8083").rstrip("/"),
            notificaciones_url=os.getenv("NOTIFICACIONES_URL", "http://notificaciones-service:8084").rstrip("/"),
            vacaciones_url=os.getenv("VACACIONES_URL", "http://vacaciones-service:8085").rstrip("/"),
            auth_url=os.environ["AUTH_URL"].rstrip("/"),
            jwt_secret=os.environ["JWT_SECRET"],
        )
        for name, value in {
            "EMPLEADOS_URL": settings.empleados_url,
            "DEPARTAMENTOS_URL": settings.departamentos_url,
            "PERFILES_URL": settings.perfiles_url,
            "NOTIFICACIONES_URL": settings.notificaciones_url,
            "VACACIONES_URL": settings.vacaciones_url,
            "AUTH_URL": settings.auth_url,
        }.items():
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError(f"{name} debe ser una URL HTTP valida")
        if not 0 < settings.timeout <= 60:
            raise ValueError("GATEWAY_REQUEST_TIMEOUT_SECONDS debe estar entre 0 y 60")
        if len(settings.jwt_secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET requiere al menos 32 bytes")
        return settings
