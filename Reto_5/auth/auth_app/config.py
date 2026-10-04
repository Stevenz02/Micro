import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    access_ttl_seconds: int = 900
    reset_ttl_seconds: int = 1800
    admin_employee_id: str | None = None
    admin_email: str | None = None
    admin_password_hash: str | None = None

    def __post_init__(self):
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET requiere al menos 32 bytes")
        if not 60 <= self.access_ttl_seconds <= 3600:
            raise ValueError("JWT_ACCESS_TTL_SECONDS debe estar entre 60 y 3600")
        if not 900 <= self.reset_ttl_seconds <= 3600:
            raise ValueError("JWT_RESET_TTL_SECONDS debe estar entre 900 y 3600")
        seed = (self.admin_employee_id, self.admin_email, self.admin_password_hash)
        if any(seed) and not all(seed):
            raise ValueError("ADMIN_EMPLOYEE_ID, ADMIN_EMAIL y ADMIN_PASSWORD_HASH deben configurarse juntos")

    @classmethod
    def from_env(cls):
        secret = os.environ["JWT_SECRET"]
        return cls(
            jwt_secret=secret,
            access_ttl_seconds=int(os.getenv("JWT_ACCESS_TTL_SECONDS", "900")),
            reset_ttl_seconds=int(os.getenv("JWT_RESET_TTL_SECONDS", "1800")),
            admin_employee_id=os.getenv("ADMIN_EMPLOYEE_ID"),
            admin_email=os.getenv("ADMIN_EMAIL"),
            admin_password_hash=os.getenv("ADMIN_PASSWORD_HASH"),
        )


def database_config():
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.getenv("DB_PORT", "5432")),
        "dbname": os.environ["DB_NAME"],
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "connect_timeout": 5,
    }
