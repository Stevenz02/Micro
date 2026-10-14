"""Identidades únicas por escenario; el retiro se conserva para auditoría."""

import secrets
from datetime import datetime, timezone


def unique_suffix():
    return datetime.now(timezone.utc).strftime("%y%m%d%H%M%S") + secrets.token_hex(4)


def employee(suffix: str, department_id: str):
    return {
        "id": f"E2E-{suffix}",
        "nombre": "Prueba",
        "apellido": "Automatica",
        "email": f"e2e-{suffix}@example.test",
        "numeroEmpleado": f"E2E-N-{suffix}",
        "cargo": "Analista",
        "area": "Calidad",
        "departamentoId": department_id,
        "fechaIngreso": "2026-01-01",
        "estado": "ACTIVO",
    }


def password():
    return "E2eClave" + secrets.token_hex(8) + "7"
