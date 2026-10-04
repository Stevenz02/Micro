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
    assert len(calls) == 1


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
