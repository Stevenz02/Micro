import time
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pybreaker
import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as Original
from Reto_3.empleados.app.config import Settings
from Reto_3.empleados.app.departamentos import DepartamentosClient
from Reto_3.empleados.app.main import create_app
from Reto_3.empleados.app.models import Empleado


def settings(max_retries=0, backoff=0.01, cb_fail_max=3, cb_reset_timeout=0.05):
    return Settings(
        "http://departamentos-service:8082",
        2,
        max_retries,
        backoff,
        cb_fail_max,
        cb_reset_timeout,
    )


@pytest.fixture
def api():
    repo = Mock()
    repo.existe_email.return_value = False
    repo.existe_numero.return_value = False
    repo.crear.side_effect = lambda employee: employee
    repo.obtener.return_value = None
    repo.listar.return_value = []
    departments = Mock()
    departments.estado.return_value = {"dependency": "departamentos-service", "state": "closed"}
    with TestClient(create_app(repo, departments)) as client:
        yield client, repo, departments


def test_modelo_canonico_y_alta_completa(api):
    client, repo, departments = api
    assert issubclass(Empleado, Original)
    assert set(Empleado.model_fields) == set(Original.model_fields)
    response = client.post("/empleados", json=EMPLEADO_EJEMPLO)
    assert response.status_code == 201
    assert response.json() == EMPLEADO_EJEMPLO
    departments.validar.assert_called_once_with("IT")


def test_estado_observable_del_breaker(api):
    client, _, departments = api
    response = client.get("/health/dependencies")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "dependencies": [{"dependency": "departamentos-service", "state": "closed"}],
    }
    departments.estado.assert_called_once()


@pytest.mark.parametrize("email,numero,expected", [(True, True, "email"), (False, True, "numero")])
def test_orden_unicidad_antes_de_http(api, email, numero, expected):
    client, repo, departments = api
    repo.existe_email.return_value = email
    repo.existe_numero.return_value = numero
    response = client.post("/empleados", json={key: value for key, value in EMPLEADO_EJEMPLO.items() if key != "estado"})
    assert response.status_code == 400
    assert expected in response.json()["detail"]
    departments.validar.assert_not_called()
    repo.crear.assert_not_called()


@pytest.mark.parametrize("code", [400, 503])
def test_no_persistir_sin_departamento_validado(api, code):
    client, repo, departments = api
    departments.validar.side_effect = HTTPException(code, "No validado")
    assert client.post("/empleados", json=EMPLEADO_EJEMPLO).status_code == code
    repo.crear.assert_not_called()


@pytest.mark.parametrize(
    "constraint,field",
    [
        ("empleados_email_key", "email"),
        ("empleados_numero_empleado_key", "numero"),
        ("empleados_pkey", "id"),
    ],
)
def test_unique_concurrente_devuelve_400(api, constraint, field):
    class Collision(psycopg.errors.UniqueViolation):
        @property
        def diag(self):
            return SimpleNamespace(constraint_name=constraint)

    client, repo, _ = api
    repo.crear.side_effect = Collision()
    response = client.post("/empleados", json=EMPLEADO_EJEMPLO)
    assert response.status_code == 400
    assert field in response.json()["detail"]


@pytest.mark.parametrize(
    "changes",
    [{"estado": "INACTIVO"}, {"email": "invalido"}, {"fechaIngreso": "2026-02-30"}, {"nombre": " "}],
)
def test_validaciones_originales(api, changes):
    client, repo, _ = api
    assert client.post("/empleados", json={**EMPLEADO_EJEMPLO, **changes}).status_code == 422
    repo.crear.assert_not_called()


@pytest.mark.parametrize("failure", ["timeout", "connection", "500", "429"])
def test_reintentos_acotados_backoff_y_timeout(failure):
    requests, sleeps = [], []

    def handler(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if failure == "connection":
            raise httpx.ConnectError("connection", request=request)
        return httpx.Response(int(failure))

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings(max_retries=3), http, sleep=sleeps.append)
        with pytest.raises(HTTPException) as error:
            client.validar("IT")
    assert error.value.status_code == 503
    assert len(requests) == 4
    assert sleeps == [0.01, 0.02, 0.04]
    assert all(req.extensions["timeout"]["read"] == 2 for req in requests)


def test_circuito_inicia_closed_y_respuesta_correcta_funciona():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "IT", "nombre": "TI", "descripcion": "TI"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings(), http)
        assert client.estado()["state"] == "closed"
        client.validar("IT")
    assert len(calls) == 1
    assert client.estado()["state"] == "closed"


def test_departamento_inexistente_no_abre_circuito():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(404))) as http:
        client = DepartamentosClient(settings(), http)
        with pytest.raises(HTTPException) as error:
            client.validar("IT")
        assert error.value.status_code == 400
        assert client.estado()["state"] == "closed"


def test_despues_de_tres_fallos_open_y_no_hace_llamada_http():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings(), http)
        for _ in range(3):
            with pytest.raises(HTTPException) as error:
                client.validar("IT")
            assert error.value.status_code == 503
        assert client.estado()["state"] == "open"
        before = len(calls)
        start = time.perf_counter()
        with pytest.raises(HTTPException) as error:
            client.validar("IT")
        elapsed = time.perf_counter() - start
    assert error.value.status_code == 503
    assert len(calls) == before
    assert elapsed < 0.02


def test_half_open_exitoso_vuelve_a_closed():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) <= 3:
            return httpx.Response(503)
        return httpx.Response(200, json={"id": "IT", "nombre": "TI", "descripcion": "TI"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings(cb_reset_timeout=0.01), http)
        for _ in range(3):
            with pytest.raises(HTTPException):
                client.validar("IT")
        assert client.estado()["state"] == "open"
        time.sleep(0.02)
        client.validar("IT")
        assert client.estado()["state"] == "closed"
    assert len(calls) == 4


def test_half_open_fallido_regresa_a_open():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings(cb_reset_timeout=0.01), http)
        for _ in range(3):
            with pytest.raises(HTTPException):
                client.validar("IT")
        time.sleep(0.02)
        with pytest.raises(HTTPException) as error:
            client.validar("IT")
        assert error.value.status_code == 503
        assert client.estado()["state"] == "open"
    assert len(calls) == 4


def test_consultas_y_documentacion(api):
    client, repo, _ = api
    assert client.get("/empleados/missing").status_code == 404
    assert client.get("/empleados").json() == []
    repo.obtener.return_value = Empleado(**EMPLEADO_EJEMPLO)
    assert client.get("/empleados/E001").json() == EMPLEADO_EJEMPLO
    schema = client.get("/openapi.json").json()
    assert "/health/dependencies" in schema["paths"]
    assert set(schema["components"]["schemas"]["Empleado"]["properties"]) == set(EMPLEADO_EJEMPLO)


@pytest.mark.parametrize("error,status", [(psycopg.OperationalError("secret"), 503), (psycopg.ProgrammingError("secret"), 500)])
def test_error_bd_controlado(api, error, status):
    client, repo, _ = api
    repo.listar.side_effect = error
    response = client.get("/empleados")
    assert response.status_code == status
    assert "secret" not in response.text
