from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from Reto_1.app.models import EMPLEADO_EJEMPLO, Empleado as Original
from Reto_2.empleados.app.config import Settings
from Reto_2.empleados.app.departamentos import DepartamentosClient
from Reto_2.empleados.app.main import create_app
from Reto_2.empleados.app.models import Empleado


@pytest.fixture
def api():
    repo = Mock()
    repo.existe_email.return_value = False
    repo.existe_numero.return_value = False
    repo.crear.side_effect = lambda employee: employee
    repo.obtener.return_value = None
    repo.listar.return_value = []
    departments = Mock()
    with TestClient(create_app(repo, departments)) as client:
        yield client, repo, departments


def test_modelo_canonico_y_alta_completa(api):
    client, repo, departments = api
    assert Empleado is Original
    response = client.post('/empleados', json=EMPLEADO_EJEMPLO)
    assert response.status_code == 201
    assert response.json() == EMPLEADO_EJEMPLO
    departments.validar.assert_called_once_with('IT')


@pytest.mark.parametrize('email,numero,expected', [(True, True, 'email'), (False, True, 'número')])
def test_orden_unicidad_antes_de_http(api, email, numero, expected):
    client, repo, departments = api
    repo.existe_email.return_value = email
    repo.existe_numero.return_value = numero
    departments.validar.side_effect = HTTPException(400, 'Departamento inexistente')
    response = client.post('/empleados', json=EMPLEADO_EJEMPLO)
    assert response.status_code == 400
    assert expected in response.json()['detail']
    if email:
        repo.existe_numero.assert_not_called()
    departments.validar.assert_not_called()
    repo.crear.assert_not_called()


@pytest.mark.parametrize('code', [400, 503])
def test_no_persistir_sin_departamento_validado(api, code):
    client, repo, departments = api
    departments.validar.side_effect = HTTPException(code, 'No validado')
    assert client.post('/empleados', json=EMPLEADO_EJEMPLO).status_code == code
    repo.crear.assert_not_called()


@pytest.mark.parametrize('constraint,field', [
    ('empleados_email_key', 'email'), ('empleados_numero_empleado_key', 'número'), ('empleados_pkey', 'id'),
])
def test_unique_concurrente_devuelve_400(api, constraint, field):
    class Collision(psycopg.errors.UniqueViolation):
        @property
        def diag(self):
            return SimpleNamespace(constraint_name=constraint)
    client, repo, _ = api
    repo.crear.side_effect = Collision()
    response = client.post('/empleados', json=EMPLEADO_EJEMPLO)
    assert response.status_code == 400
    assert field in response.json()['detail']


@pytest.mark.parametrize('changes', [{'estado': 'INACTIVO'}, {'email': 'invalido'}, {'fechaIngreso': '2026-02-30'}, {'nombre': ' '}])
def test_validaciones_originales(api, changes):
    client, repo, _ = api
    assert client.post('/empleados', json={**EMPLEADO_EJEMPLO, **changes}).status_code == 422
    repo.crear.assert_not_called()


def test_consultas_y_documentacion(api):
    client, repo, _ = api
    assert client.get('/empleados/missing').status_code == 404
    assert client.get('/empleados').json() == []
    repo.obtener.return_value = Empleado(**EMPLEADO_EJEMPLO)
    assert client.get('/empleados/E001').json() == EMPLEADO_EJEMPLO
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert set(schema['components']['schemas']['Empleado']['properties']) == set(EMPLEADO_EJEMPLO)
    assert {'201', '400', '422', '500', '503'} <= set(schema['paths']['/empleados']['post']['responses'])


@pytest.mark.parametrize('error,status', [(psycopg.OperationalError('secret'), 503), (psycopg.ProgrammingError('secret'), 500)])
def test_error_bd_controlado(api, error, status):
    client, repo, _ = api
    repo.listar.side_effect = error
    response = client.get('/empleados')
    assert response.status_code == status
    assert 'secret' not in response.text


@pytest.mark.parametrize('failure', ['timeout', 'connection', '500', '429'])
def test_reintentos_acotados_backoff_y_timeout(failure):
    requests, sleeps = [], []
    def handler(request):
        requests.append(request)
        if failure == 'timeout':
            raise httpx.ReadTimeout('timeout', request=request)
        if failure == 'connection':
            raise httpx.ConnectError('connection', request=request)
        return httpx.Response(int(failure))
    settings = Settings('http://departamentos-service:8081', 2, 3, 1)
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        client = DepartamentosClient(settings, http, sleep=sleeps.append)
        with pytest.raises(HTTPException) as error:
            client.validar('IT')
    assert error.value.status_code == 503
    assert len(requests) == 4
    assert sleeps == [1, 2, 4]
    assert all(req.extensions['timeout']['read'] == 2 for req in requests)


def test_recuperacion_en_tercer_intento():
    replies = iter([httpx.Response(503), httpx.Response(500), httpx.Response(200, json={'id': 'IT', 'nombre': 'TI', 'descripcion': 'TI'})])
    sleeps = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: next(replies))) as http:
        DepartamentosClient(Settings('http://departamentos-service:8081', 2, 3, 1), http, sleeps.append).validar('IT')
    assert sleeps == [1, 2]


@pytest.mark.parametrize('response,code', [
    (httpx.Response(404), 400), (httpx.Response(401), 503),
    (httpx.Response(200, json={'id': 'OTRO'}), 503), (httpx.Response(200, text='invalid'), 503),
])
def test_no_reintentar_errores_definitivos(response, code):
    handler = Mock(return_value=response)
    sleep = Mock()
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(HTTPException) as error:
            DepartamentosClient(Settings('http://departamentos-service:8081', 2, 3, 1), http, sleep).validar('IT')
    assert error.value.status_code == code
    assert handler.call_count == 1
    sleep.assert_not_called()
