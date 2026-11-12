import sys
from pathlib import Path

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "api-gateway"))

from gateway_app.config import Settings  # noqa: E402
from gateway_app.main import create_app  # noqa: E402
from shared.tokens import issue_access, issue_reset  # noqa: E402

SECRET = "test-only-secret-with-at-least-32-bytes"


def gateway(handler):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = create_app(Settings("http://empleados", "http://departamentos", 5,
                              auth_url="http://auth", jwt_secret=SECRET), client)
    return TestClient(app)


def bearer(subject="E001", role="USER"):
    return {"Authorization": "Bearer " + issue_access(SECRET, subject, role, 900)}


def test_public_routes_only_and_401_for_business():
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"ok": True})
    with gateway(handler) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/auth/login", json={}).status_code == 200
        for path in ("/empleados", "/departamentos", "/perfiles/E001", "/notificaciones", "/vacaciones"):
            assert client.get(path).status_code == 401
        assert client.post("/auth/login/", json={}).status_code == 401
        assert client.get("/auth/login/anything").status_code == 401
    # /health agrega la salud de los seis upstreams y el login sí se reenvía;
    # ninguna ruta de negocio sin JWT debe alcanzar un microservicio.
    assert len(calls) == 7
    assert all(url.endswith("/health") for url in calls[:6])
    assert calls[-1] == "http://auth/auth/login"


def test_swagger_redirect_assets_are_public_but_business_paths_remain_protected():
    with gateway(lambda request: httpx.Response(200, text="swagger")) as client:
        assert client.get("/notificaciones/swagger-ui/index.html").status_code == 200
        assert client.get("/vacaciones/docs/index.html").status_code == 200
        assert client.get("/notificaciones/EMP-1").status_code == 401


@pytest.mark.parametrize("method,path,role,subject,expected", [
    ("GET", "/empleados", "USER", "E001", 200),
    ("GET", "/departamentos/IT", "USER", "E001", 200),
    ("GET", "/perfiles/E002", "USER", "E001", 200),
    ("POST", "/departamentos", "ADMIN", "ADMIN", 200),
    ("POST", "/vacaciones", "ADMIN", "ADMIN", 200),
    ("DELETE", "/empleados/E001", "USER", "E001", 403),
    ("PUT", "/perfiles/E001", "USER", "E001", 200),
    ("PUT", "/perfiles/E002", "USER", "E001", 403),
    ("PUT", "/perfiles/E001/", "USER", "E001", 403),
    ("POST", "/auth/change-password", "USER", "E001", 200),
    ("GET", "/notificaciones/seguridad/123/token", "USER", "E001", 403),
    ("GET", "/notificaciones/seguridad/123/token", "ADMIN", "ADMIN", 200),
])
def test_roles_and_ownership(method, path, role, subject, expected):
    with gateway(lambda request: httpx.Response(200, json={"ok": True})) as client:
        result = client.request(method, path, headers=bearer(subject, role))
    assert result.status_code == expected


def test_gateway_removes_client_identity_headers_and_adds_validated_identity():
    def handler(request):
        assert request.headers["x-authenticated-employee-id"] == "E001"
        assert request.headers["x-authenticated-role"] == "USER"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"ok": True})
    headers = {**bearer(), "X-Authenticated-Employee-Id": "E002", "X-Authenticated-Role": "ADMIN"}
    with gateway(handler) as client:
        assert client.get("/empleados", headers=headers).status_code == 200


@pytest.mark.parametrize("token", [
    "garbage",
    issue_reset(SECRET, "E001", 0, 900),
    issue_access("another-test-secret-with-32-bytes", "E001", "USER", 900),
    jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "ACCESS", "role": "USER", "iat": 1, "exp": 2}, SECRET, algorithm="HS256"),
    jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "ACCESS", "role": "USER", "iat": 1, "exp": 9999999999}, SECRET, algorithm="HS384"),
    jwt.encode({"iss": "otro-emisor", "sub": "E001", "type": "ACCESS", "role": "USER", "iat": 1, "exp": 9999999999}, SECRET, algorithm="HS256"),
    jwt.encode({"iss": "rrhh-auth-service", "sub": "E001", "type": "ACCESS", "role": "GUEST", "iat": 1, "exp": 9999999999}, SECRET, algorithm="HS256"),
])
def test_invalid_tokens_get_401(token):
    with gateway(lambda request: httpx.Response(200)) as client:
        assert client.get("/empleados", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_gateway_openapi_declares_bearer_for_protected_operations():
    with gateway(lambda request: httpx.Response(200)) as client:
        schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert schema["paths"]["/empleados"]["get"]["security"] == [{"BearerAuth": []}]
    assert "security" not in schema["paths"]["/health"]["get"]
    assert "security" not in schema["paths"]["/auth/login"]["post"]
    assert schema["paths"]["/auth/change-password"]["post"]["security"] == [{"BearerAuth": []}]
    assert schema["paths"]["/auth/login"]["post"]["requestBody"]["content"]["application/json"]["schema"]["required"] == ["email", "password"]
    assert "200" in schema["paths"]["/auth/login"]["post"]["responses"]
    assert schema["paths"]["/auth/login"]["post"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == "#/components/schemas/TokenOutput"
    assert "400" in schema["paths"]["/auth/reset-password"]["post"]["responses"]


def test_gateway_openapi_includes_upstream_contracts_and_namespaced_models():
    def handler(request):
        paths = {"empleados": "/empleados", "departamentos": "/departamentos"}
        if request.url.host not in paths:
            return httpx.Response(200, json={"openapi": "3.0.3", "paths": {}})
        path = paths[request.url.host]
        return httpx.Response(200, json={
            "openapi": "3.0.3",
            "paths": {path: {"post": {
                "requestBody": {"content": {"application/json": {
                    "schema": {"$ref": "#/components/schemas/Record"}}}},
                "responses": {"201": {"description": "Creado"}},
            }}},
            "components": {"schemas": {"Record": {"type": "object"}}},
        })
    with gateway(handler) as client:
        schema = client.get("/openapi.json").json()
        assert client.get("/docs").status_code == 200
        assert client.get("/redoc").status_code == 200
    for service, path in (("Empleados", "/empleados"),
                          ("Departamentos", "/departamentos")):
        operation = schema["paths"][path]["post"]
        assert operation["requestBody"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{service}_Record"}
        assert operation["security"] == [{"BearerAuth": []}]
        assert "401" in operation["responses"]


def test_upstream_openapi_is_documented_with_bearer_at_gateway():
    def handler(request):
        assert request.url.path == "/openapi.json"
        return httpx.Response(200, json={"openapi": "3.0.3", "paths": {
            "/empleados": {"get": {"responses": {"200": {"description": "OK"}}}},
            "/health": {"get": {"responses": {"200": {"description": "OK"}}}},
        }})
    with gateway(handler) as client:
        assert client.get("/empleados/docs").status_code == 200
        schema = client.get("/empleados/openapi.json").json()
    assert schema["servers"] == [{"url": "/"}]
    assert schema["paths"]["/empleados"]["get"]["security"] == [{"BearerAuth": []}]
    assert "security" not in schema["paths"]["/health"]["get"]


def test_departamentos_docs_use_real_upstream_openapi_path():
    def handler(request):
        assert request.url.path == "/openapi.json"
        return httpx.Response(200, json={"openapi": "3.0.3", "paths": {
            "/departamentos": {"get": {"responses": {"200": {"description": "OK"}}}},
        }})
    with gateway(handler) as client:
        assert client.get("/departamentos/docs").status_code == 200
        schema = client.get("/departamentos/openapi.json").json()
    assert schema["paths"]["/departamentos"]["get"]["security"] == [{"BearerAuth": []}]


# ----------------------------------------------------------------- Proyecto final: composición
def _composicion(perfil_respuesta):
    def handler(request):
        if request.url.host == "empleados":
            if request.url.path == "/empleados/E404":
                return httpx.Response(404, json={"detail": "El empleado con id E404 no existe"})
            assert request.headers["x-authenticated-employee-id"] == "E001"
            return httpx.Response(200, json={"id": "E001", "nombre": "Ana"})
        return perfil_respuesta(request)
    return handler


def _gateway_composicion(perfil_respuesta):
    client = httpx.AsyncClient(transport=httpx.MockTransport(_composicion(perfil_respuesta)))
    app = create_app(Settings("http://empleados", "http://departamentos", 5, perfiles_url="http://perfiles",
                              auth_url="http://auth", jwt_secret=SECRET), client)
    return TestClient(app)


def test_completo_combina_empleado_y_perfil():
    with _gateway_composicion(lambda r: httpx.Response(200, json={"empleadoId": "E001", "biografia": "x"})) as client:
        response = client.get("/empleados/E001/completo", headers=bearer())
    assert response.status_code == 200
    assert response.json() == {"empleado": {"id": "E001", "nombre": "Ana"},
                               "perfil": {"empleadoId": "E001", "biografia": "x"}, "parcial": False}


def test_completo_tolera_la_caida_de_perfiles():
    def caido(request):
        raise httpx.ConnectError("perfiles caido")
    for respuesta in (caido, lambda r: httpx.Response(503, json={})):
        with _gateway_composicion(respuesta) as client:
            body = client.get("/empleados/E001/completo", headers=bearer()).json()
        assert body["empleado"]["id"] == "E001" and body["perfil"] is None and body["parcial"] is True


def test_completo_perfil_aun_no_creado_no_es_fallo():
    with _gateway_composicion(lambda r: httpx.Response(404, json={})) as client:
        body = client.get("/empleados/E001/completo", headers=bearer()).json()
    assert body == {"empleado": {"id": "E001", "nombre": "Ana"}, "perfil": None, "parcial": False}


def test_completo_propaga_404_y_exige_token():
    with _gateway_composicion(lambda r: httpx.Response(200, json={})) as client:
        assert client.get("/empleados/E404/completo", headers=bearer()).status_code == 404
        assert client.get("/empleados/E001/completo").status_code == 401


def test_completo_sin_empleados_devuelve_503():
    def handler(request):
        raise httpx.ConnectError("caido")
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = create_app(Settings("http://empleados", "http://departamentos", 5, auth_url="http://auth",
                              jwt_secret=SECRET), client)
    with TestClient(app) as test_client:
        response = test_client.get("/empleados/E001/completo", headers=bearer())
    assert response.status_code == 503 and response.json()["service"] == "empleados-service"


def test_swagger_alias_es_publico():
    with gateway(lambda request: httpx.Response(200, json={})) as client:
        assert client.get("/swagger").status_code == 200
