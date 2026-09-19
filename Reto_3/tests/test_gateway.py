import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

GATEWAY_ROOT = Path(__file__).resolve().parents[1] / "api-gateway"
sys.path.insert(0, str(GATEWAY_ROOT))

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


def gateway(handler, timeout=5):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport, follow_redirects=False)
    app = create_app(
        Settings("http://empleados-upstream", "http://departamentos-upstream", timeout),
        client,
    )
    return TestClient(app), client


def test_health_responde_desde_gateway():
    test_client, http = gateway(lambda request: httpx.Response(500))
    with test_client as client:
        assert client.get("/health").json() == {"status": "ok", "service": "api-gateway"}
    assert not http.is_closed


@pytest.mark.parametrize(
    "method,path,body,expected_host",
    [
        ("GET", "/empleados?area=TI", None, "empleados-upstream"),
        ("POST", "/empleados", {"id": "E001"}, "empleados-upstream"),
        ("GET", "/departamentos/IT?verbose=true", None, "departamentos-upstream"),
        ("POST", "/departamentos", {"id": "IT"}, "departamentos-upstream"),
        ("PUT", "/empleados/E001", {"cargo": "Lead"}, "empleados-upstream"),
        ("PATCH", "/departamentos/IT", {"nombre": "Tecnologia"}, "departamentos-upstream"),
        ("DELETE", "/empleados/E001", None, "empleados-upstream"),
        ("OPTIONS", "/departamentos", None, "departamentos-upstream"),
    ],
)
def test_proxy_preserva_metodo_path_query_body_headers_y_status(method, path, body, expected_host):
    seen = []

    def handler(request):
        seen.append(request)
        assert request.url.host == expected_host
        assert request.headers.get("x-request-id") == "abc-123"
        assert "host" not in request.headers or request.headers["host"] == expected_host
        if body is not None:
            assert request.headers["content-type"].startswith("application/json")
        return httpx.Response(
            207,
            json={"proxied": str(request.url), "method": request.method},
            headers={"X-Upstream": "ok", "Connection": "close"},
        )

    test_client, _ = gateway(handler)
    with test_client as client:
        response = client.request(method, path, json=body, headers={"X-Request-Id": "abc-123"})
    assert response.status_code == 207
    assert response.headers["x-upstream"] == "ok"
    assert "connection" not in response.headers
    assert response.json()["method"] == method
    assert seen[0].url.query == path.partition("?")[2].encode()


@pytest.mark.parametrize("status", [400, 404, 500])
def test_propaga_status_y_body_del_backend(status):
    test_client, _ = gateway(lambda request: httpx.Response(status, json={"detail": f"backend {status}"}))
    with test_client as client:
        response = client.get("/departamentos/missing")
    assert response.status_code == status
    assert response.json() == {"detail": f"backend {status}"}


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timeout"),
    ],
)
def test_upstream_caido_o_timeout_devuelve_503_json_estable(error):
    def handler(request):
        raise error

    test_client, _ = gateway(handler, timeout=0.01)
    with test_client as client:
        response = client.get("/departamentos")
    assert response.status_code == 503
    assert response.json() == {
        "error": "upstream_unavailable",
        "service": "departamentos-service",
        "message": "El servicio solicitado no esta disponible temporalmente",
    }
    assert "Traceback" not in response.text
    assert "httpx" not in response.text
