"""Proyecto final: Empleados refleja EN_VACACIONES a partir de los eventos del scheduler."""

import json
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "empleados"))

from app.models import EMPLEADO_EJEMPLO, Empleado  # noqa: E402
from app.vacaciones_consumer import VacacionesConsumer, procesar  # noqa: E402


class RepoEnMemoria:
    """Misma semántica que Repository.aplicar_vacaciones: dedup por id + transición condicional."""

    def __init__(self, estado="ACTIVO"):
        self.empleado = Empleado(**{**EMPLEADO_EJEMPLO, "estado": estado})
        self.vistos = set()

    def aplicar_vacaciones(self, event_id, empleado_id, iniciadas):
        if event_id in self.vistos:
            return False, None
        self.vistos.add(event_id)
        origen, destino = ("ACTIVO", "EN_VACACIONES") if iniciadas else ("EN_VACACIONES", "ACTIVO")
        if empleado_id != self.empleado.id or self.empleado.estado != origen:
            return True, None
        self.empleado = self.empleado.model_copy(update={"estado": destino})
        return True, self.empleado


def evento(tipo, event_id=None, **cambios):
    payload = {
        "id": str(event_id or uuid.uuid4()), "type": tipo, "version": 1,
        "occurredAt": "2026-11-12T05:00:00.000Z", "producer": "vacaciones-service",
        "data": {"empleadoId": EMPLEADO_EJEMPLO["id"], "email": EMPLEADO_EJEMPLO["email"],
                 "vacacionesId": "V1", "fechaInicio": "2026-11-12", "fechaFin": "2026-11-20"},
    }
    payload.update(cambios)
    return json.dumps(payload).encode()


def test_inicio_y_fin_de_vacaciones_cambian_el_estado():
    repo = RepoEnMemoria()
    assert procesar(repo, evento("vacaciones.iniciadas")) is True
    assert repo.empleado.estado == "EN_VACACIONES"
    assert procesar(repo, evento("vacaciones.finalizadas")) is True
    assert repo.empleado.estado == "ACTIVO"


def test_evento_duplicado_no_repite_el_efecto():
    repo, event_id = RepoEnMemoria(), uuid.uuid4()
    assert procesar(repo, evento("vacaciones.iniciadas", event_id)) is True
    repo.empleado = repo.empleado.model_copy(update={"estado": "ACTIVO"})
    assert procesar(repo, evento("vacaciones.iniciadas", event_id)) is False
    assert repo.empleado.estado == "ACTIVO"


def test_empleado_retirado_no_vuelve_a_activo():
    repo = RepoEnMemoria(estado="ACTIVO")
    repo.empleado = repo.empleado.model_copy(update={"estado": "RETIRADO", "fechaRetiro": "2026-11-01T00:00:00Z"})
    assert procesar(repo, evento("vacaciones.finalizadas")) is True
    assert repo.empleado.estado == "RETIRADO"


@pytest.mark.parametrize("cambios", [
    {"type": "empleado.creado"}, {"version": 2}, {"version": "1"}, {"producer": "otro-servicio"},
    {"id": "no-es-uuid"}, {"data": []}, {"data": {"empleadoId": " "}},
])
def test_envelope_invalido_se_rechaza(cambios):
    repo = RepoEnMemoria()
    with pytest.raises(ValueError):
        procesar(repo, evento("vacaciones.iniciadas", **cambios))
    assert repo.vistos == set()


def test_cuerpo_que_no_es_objeto_se_rechaza():
    with pytest.raises(ValueError):
        procesar(RepoEnMemoria(), b"[]")


def test_consumidor_se_detiene_sin_broker(monkeypatch):
    monkeypatch.setenv("RABBITMQ_HOST", "127.0.0.1")
    monkeypatch.setenv("RABBITMQ_USER", "x")
    monkeypatch.setenv("RABBITMQ_PASSWORD", "x")
    consumidor = VacacionesConsumer(RepoEnMemoria())
    consumidor.stop_event.set()   # el bucle termina de inmediato: no llega a conectarse
    consumidor.start()
    consumidor.stop()
    assert not consumidor.thread.is_alive()
