from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient

from Reto_1.app.models import EMPLEADO_EJEMPLO
from Reto_4.empleados.app.events import envelope
from Reto_4.empleados.app.main import create_app, reconciliar_pendientes
from Reto_4.empleados.app.models import Empleado


def test_envelope_oficial_version_1():
    event = envelope("empleado.creado", {"empleadoId": "E001"})
    assert set(event) == {"id", "type", "version", "occurredAt", "producer", "data"}
    assert UUID(event["id"])
    assert event["version"] == 1
    assert event["producer"] == "empleados-service"
    assert datetime.fromisoformat(event["occurredAt"].replace("Z", "+00:00")).utcoffset().total_seconds() == 0


def test_publicacion_exacta_tras_alta_actualizacion_y_retiro_idempotente():
    repo, departamentos, publisher = Mock(), Mock(), Mock()
    repo.existe_email.return_value = False
    repo.existe_numero.return_value = False
    repo.crear.side_effect = lambda empleado: empleado
    activo = Empleado(**EMPLEADO_EJEMPLO)
    actualizado = activo.model_copy(update={"cargo": "Tech Lead", "apellido": "Gomez"})
    retirado = actualizado.model_copy(update={"estado": "RETIRADO", "fechaRetiro": datetime(2026, 9, 29, tzinfo=timezone.utc)})
    repo.obtener.side_effect = [activo, actualizado, retirado]
    repo.actualizar.return_value = actualizado
    repo.retirar.return_value = retirado
    with TestClient(create_app(repo, departamentos, publisher)) as client:
        assert client.post("/empleados", json=EMPLEADO_EJEMPLO).status_code == 201
        body = {key: value for key, value in EMPLEADO_EJEMPLO.items() if key not in {"id", "estado"}}
        body.update(cargo="Tech Lead", apellido="Gomez")
        assert client.put("/empleados/E001", json=body).status_code == 200
        assert client.delete("/empleados/E001?motivo=RENUNCIA").status_code == 200
        assert client.delete("/empleados/E001").status_code == 200
    calls = publisher.publish.call_args_list
    assert [call.args[0] for call in calls] == ["empleado.creado", "empleado.actualizado", "empleado.retirado"]
    assert set(calls[0].args[1]) == {"empleadoId", "nombre", "apellido", "email", "numeroEmpleado", "cargo", "area", "departamentoId", "fechaIngreso", "estado"}
    assert set(calls[1].args[1]) == {"empleadoId", "nombre", "apellido", "email", "cargo", "area", "departamentoId"}
    assert calls[2].args[1] == {"empleadoId": "E001", "email": activo.email, "fechaRetiro": "2026-09-29T00:00:00.000Z", "motivo": "RENUNCIA"}
    repo.retirar.assert_called_once_with("E001", "RENUNCIA")


def test_pendiente_solo_publica_al_activarse_una_vez():
    repo, departamentos, publisher = Mock(), Mock(), Mock()
    repo.existe_email.return_value = False
    repo.existe_numero.return_value = False
    repo.crear.side_effect = lambda empleado: empleado
    departamentos.validar.side_effect = HTTPException(503, "temporal")
    with TestClient(create_app(repo, departamentos, publisher)) as client:
        assert client.post("/empleados", json=EMPLEADO_EJEMPLO).status_code == 202
    publisher.publish.assert_not_called()
    pendiente = Empleado(**{**EMPLEADO_EJEMPLO, "estado": "PENDIENTE"})
    activo = Empleado(**EMPLEADO_EJEMPLO)
    repo.listar_pendientes.return_value = [pendiente]
    repo.actualizar_estado.side_effect = [activo, None]
    departamentos.validar.side_effect = None
    reconciliar_pendientes(repo, departamentos, publisher=publisher)
    reconciliar_pendientes(repo, departamentos, publisher=publisher)
    publisher.publish.assert_called_once()
    assert publisher.publish.call_args.args[0] == "empleado.creado"


def test_primer_retiro_exige_motivo_del_catalogo():
    repo, departamentos, publisher = Mock(), Mock(), Mock()
    repo.obtener.return_value = Empleado(**EMPLEADO_EJEMPLO)
    with TestClient(create_app(repo, departamentos, publisher)) as client:
        response = client.delete("/empleados/E001")
    assert response.status_code == 400
    repo.retirar.assert_not_called()
    publisher.publish.assert_not_called()
