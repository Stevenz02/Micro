"""Identidades en base propia; el ID estable de Empleados es la clave primaria."""

from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row


INACTIVE = "INACTIVA"
ACTIVE = "ACTIVA"
SUSPENDED = "SUSPENDIDA_TEMPORAL"
RETIRED = "DESACTIVADA_PERMANENTE"


def next_status(status: str, password_hash: str | None, event_type: str) -> str | None:
    if event_type == "empleado.retirado" and status != RETIRED:
        return RETIRED
    if event_type == "vacaciones.iniciadas" and status in {INACTIVE, ACTIVE}:
        return SUSPENDED
    if event_type == "vacaciones.finalizadas" and status == SUSPENDED:
        return ACTIVE if password_hash else INACTIVE
    return None


@dataclass(frozen=True)
class Account:
    employee_id: str
    email: str
    role: str
    status: str
    password_hash: str | None
    credential_version: int


class Repository:
    def __init__(self, connection_config: dict):
        self.connection_config = connection_config

    def _connection(self):
        return psycopg.connect(**self.connection_config, row_factory=dict_row)

    @staticmethod
    def _account(row):
        return Account(**row) if row else None

    def ensure_schema(self):
        with self._connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS cuentas (
                employee_id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL CHECK (role IN ('ADMIN','USER')),
                status TEXT NOT NULL CHECK (status IN ('INACTIVA','ACTIVA','SUSPENDIDA_TEMPORAL','DESACTIVADA_PERMANENTE')),
                password_hash TEXT NULL,
                credential_version INTEGER NOT NULL DEFAULT 0 CHECK (credential_version >= 0),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS eventos_procesados (
                id UUID PRIMARY KEY, procesado_en TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    def seed_admin(self, employee_id: str, email: str, password_hash: str):
        if not password_hash.startswith("$2"):
            raise ValueError("ADMIN_PASSWORD_HASH debe ser un hash bcrypt")
        with self._connection() as conn:
            conn.execute("""INSERT INTO cuentas(employee_id,email,role,status,password_hash)
                VALUES(%s,%s,'ADMIN','ACTIVA',%s) ON CONFLICT(employee_id) DO NOTHING""",
                (employee_id, email.lower(), password_hash))

    def get_by_email(self, email: str):
        with self._connection() as conn:
            row = conn.execute("""SELECT employee_id,email,role,status,password_hash,credential_version
                FROM cuentas WHERE email=%s""", (email.lower(),)).fetchone()
            return self._account(row)

    def get_by_id(self, employee_id: str):
        with self._connection() as conn:
            row = conn.execute("""SELECT employee_id,email,role,status,password_hash,credential_version
                FROM cuentas WHERE employee_id=%s""", (employee_id,)).fetchone()
            return self._account(row)

    def set_password(self, employee_id: str, expected_version: int, password_hash: str):
        with self._connection() as conn:
            row = conn.execute("""UPDATE cuentas SET password_hash=%s,
                credential_version=credential_version+1,
                status=CASE WHEN status='INACTIVA' THEN 'ACTIVA' ELSE status END,
                updated_at=CURRENT_TIMESTAMP
                WHERE employee_id=%s AND credential_version=%s
                  AND status <> 'DESACTIVADA_PERMANENTE'
                RETURNING employee_id,email,role,status,password_hash,credential_version""",
                (password_hash, employee_id, expected_version)).fetchone()
            return self._account(row)

    def create_employee(self, employee_id: str, email: str):
        with self._connection() as conn:
            row = conn.execute("""INSERT INTO cuentas(employee_id,email,role,status)
                VALUES(%s,%s,'USER','INACTIVA') ON CONFLICT(employee_id) DO NOTHING
                RETURNING employee_id,email,role,status,password_hash,credential_version""",
                (employee_id, email.lower())).fetchone()
            return self._account(row)

    def transition(self, employee_id: str, from_status: tuple[str, ...], to_status: str):
        with self._connection() as conn:
            row = conn.execute("""UPDATE cuentas SET status=%s,updated_at=CURRENT_TIMESTAMP
                WHERE employee_id=%s AND status=ANY(%s)
                RETURNING employee_id,email,role,status,password_hash,credential_version""",
                (to_status, employee_id, list(from_status))).fetchone()
            return self._account(row)

    def apply_event(self, event):
        """Guarda el marcador de deduplicación y la transición en una transacción."""
        with self._connection() as conn:
            inserted = conn.execute(
                "INSERT INTO eventos_procesados(id) VALUES(%s) ON CONFLICT DO NOTHING RETURNING id",
                (event.id,),
            ).fetchone()
            if inserted is None:
                return False, None
            employee_id = event.data["empleadoId"]
            if event.type == "empleado.creado":
                row = conn.execute("""INSERT INTO cuentas(employee_id,email,role,status)
                    VALUES(%s,%s,'USER','INACTIVA') ON CONFLICT(employee_id) DO NOTHING
                    RETURNING employee_id,email,role,status,password_hash,credential_version""",
                    (employee_id, event.data["email"].lower())).fetchone()
                return row is not None, self._account(row)
            row = conn.execute("""SELECT employee_id,email,role,status,password_hash,credential_version
                FROM cuentas WHERE employee_id=%s FOR UPDATE""", (employee_id,)).fetchone()
            if row is None:
                raise RuntimeError("La cuenta aún no existe; reintentar evento")
            status = next_status(row["status"], row["password_hash"], event.type)
            if status is None:
                return False, self._account(row)
            updated = conn.execute("""UPDATE cuentas SET status=%s,updated_at=CURRENT_TIMESTAMP
                WHERE employee_id=%s
                RETURNING employee_id,email,role,status,password_hash,credential_version""",
                (status, employee_id)).fetchone()
            return True, self._account(updated)
