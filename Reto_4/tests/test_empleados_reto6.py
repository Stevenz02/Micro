"""Reglas de alta y retiro aisladas de PostgreSQL, HTTP y RabbitMQ."""

from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from Reto_4.empleados.app.main import create_app
from Reto_4.empleados.app.events import envelope
from Reto_1.app.models import EMPLEADO_EJEMPLO


class FakeRepository:
    def __init__(self):
        self.items = {}

    def existe_email(self, value, excluir_id=None):
        return any(e.email == value and key != excluir_id for key, e in self.items.items())

    def existe_numero(self, value, excluir_id=None):
        return any(e.numeroEmpleado == value and key != excluir_id for key, e in self.items.items())

    def crear(self, employee):
        self.items[employee.id] = employee
        return employee

    def obtener(self, employee_id):
        return self.items.get(employee_id)

    def retirar(self, employee_id, motivo):
        employee = self.items[employee_id]
        retired = employee.model_copy(update={"estado": "RETIRADO", "fechaRetiro": datetime.now(timezone.utc)})
        self.items[employee_id] = retired
        return retired

    def listar(self, estado=None, desde=None, hasta=None):
        return [e for e in self.items.values() if estado is None or e.estado == estado]


@pytest.fixture
def system():
    repository, departments, publisher = FakeRepository(), Mock(), Mock()
    with TestClient(create_app(repository, departments, publisher)) as client:
        yield client, repository, departments, publisher


def test_create_retire_preserves_employee_and_publishes_catalog_event(system):
    client, repository, departments, publisher = system
    response = client.post("/empleados", json=EMPLEADO_EJEMPLO)
    assert response.status_code == 201
    assert response.json()["estado"] == "ACTIVO"
    departments.validar.assert_called_once_with("IT")
    assert publisher.publish.call_args_list[0].args[0] == "empleado.creado"

    missing_reason = client.delete("/empleados/E001")
    assert missing_reason.status_code == 400
    assert repository.obtener("E001").estado == "ACTIVO"

    retired = client.delete("/empleados/E001?motivo=RENUNCIA")
    assert retired.status_code == 200
    assert retired.json()["estado"] == "RETIRADO"
    assert datetime.fromisoformat(retired.json()["fechaRetiro"]).utcoffset().total_seconds() == 0
    assert repository.obtener("E001") is not None
    assert [item["id"] for item in client.get("/empleados?estado=RETIRADO").json()] == ["E001"]
    event_type, data = publisher.publish.call_args_list[-1].args
    assert event_type == "empleado.retirado"
    assert set(data) == {"empleadoId", "email", "fechaRetiro", "motivo"}
    assert data["empleadoId"] == "E001" and data["motivo"] == "RENUNCIA"
    assert "password" not in str(data).lower()

    assert client.delete("/empleados/E001").status_code == 200
    assert publisher.publish.call_count == 2  # retiro idempotente
    update = {key: value for key, value in EMPLEADO_EJEMPLO.items() if key not in {"id", "estado"}}
    assert client.put("/empleados/E001", json=update).status_code == 400
    assert publisher.publish.call_count == 2


@pytest.mark.parametrize("field", ["email", "numeroEmpleado"])
def test_duplicate_identity_is_rejected_before_department_http(system, field):
    client, _, departments, publisher = system
    assert client.post("/empleados", json=EMPLEADO_EJEMPLO).status_code == 201
    departments.reset_mock()
    publisher.reset_mock()
    second = {**EMPLEADO_EJEMPLO, "id": "E002", "email": "otro@example.test", "numeroEmpleado": "OTRO"}
    second[field] = EMPLEADO_EJEMPLO[field]
    result = client.post("/empleados", json=second)
    assert result.status_code == 400
    departments.validar.assert_not_called()
    publisher.publish.assert_not_called()


def test_envelope_has_official_shape_and_unique_message_ids():
    one = envelope("empleado.retirado", {"empleadoId": "E001"})
    two = envelope("empleado.retirado", {"empleadoId": "E001"})
    assert one["id"] != two["id"]
    assert UUID(one["id"]) and UUID(two["id"])
    assert set(one) == {"id", "type", "version", "occurredAt", "producer", "data"}
    assert one["type"] == "empleado.retirado" and one["producer"] == "empleados-service"
    assert type(one["version"]) is int and one["version"] == 1
    assert one["occurredAt"].endswith("Z")
