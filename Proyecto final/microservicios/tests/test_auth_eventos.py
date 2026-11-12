"""Proyecto final: validación del envelope entrante de Auth según el Catálogo de Eventos."""

import json
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "auth"))

from auth_app.events import IncomingEvent, utc_datetime  # noqa: E402

CREADO = {
    "empleadoId": "E001", "email": "ana@example.test", "nombre": "Ana", "apellido": "Ríos",
    "numeroEmpleado": "N001", "cargo": "Dev", "area": "TI", "departamentoId": "IT",
    "fechaIngreso": "2026-11-01", "estado": "ACTIVO",
}
PRODUCTORES = {"empleado": "empleados-service", "vacaciones": "vacaciones-service"}


def envelope(tipo, data, **cambios):
    payload = {"id": str(uuid.uuid4()), "type": tipo, "version": 1,
               "occurredAt": "2026-11-12T05:00:00.000Z",
               "producer": PRODUCTORES[tipo.split(".")[0]], "data": data}
    payload.update(cambios)
    return json.dumps(payload).encode()


@pytest.mark.parametrize("tipo,data", [
    ("empleado.creado", CREADO),
    ("empleado.retirado", {"empleadoId": "E001", "email": "ana@example.test",
                           "fechaRetiro": "2026-11-12T05:00:00Z", "motivo": "RENUNCIA"}),
    ("vacaciones.iniciadas", {"empleadoId": "E001", "email": "ana@example.test", "vacacionesId": "V1",
                              "fechaInicio": "2026-11-12", "fechaFin": "2026-11-20"}),
    ("vacaciones.finalizadas", {"empleadoId": "E001", "email": "ana@example.test", "vacacionesId": "V1",
                                "fechaFin": "2026-11-20"}),
])
def test_eventos_validos_del_catalogo_se_aceptan(tipo, data):
    evento = IncomingEvent.from_bytes(envelope(tipo, data))
    assert evento.type == tipo and evento.data["empleadoId"] == "E001"


@pytest.mark.parametrize("cuerpo", [
    b"[]",
    envelope("empleado.creado", CREADO, type="empleado.desconocido"),
    envelope("empleado.creado", CREADO, version=2),
    envelope("empleado.creado", CREADO, version="1"),
    envelope("empleado.creado", CREADO, producer="otro-servicio"),
    envelope("empleado.creado", CREADO, occurredAt="2026-11-12T05:00:00-05:00"),
    envelope("empleado.creado", []),
    envelope("empleado.creado", {**CREADO, "estado": "RETIRADO"}),
    envelope("empleado.creado", {**CREADO, "nombre": " "}),
    envelope("empleado.creado", {k: v for k, v in CREADO.items() if k != "email"}),
    envelope("empleado.retirado", {"empleadoId": "E001", "email": "ana@example.test",
                                   "fechaRetiro": "2026-11-12T05:00:00", "motivo": "X"}),
    envelope("vacaciones.iniciadas", {"empleadoId": "E001", "email": "ana@example.test",
                                      "vacacionesId": "V1", "fechaFin": "2026-11-20"}),
])
def test_envelope_fuera_de_contrato_se_rechaza(cuerpo):
    with pytest.raises(ValueError):
        IncomingEvent.from_bytes(cuerpo)


def test_fecha_utc_exige_zona_explicita():
    assert utc_datetime("2026-11-12T05:00:00Z").utcoffset().total_seconds() == 0
    with pytest.raises(ValueError):
        utc_datetime("2026-11-12T05:00:00")
