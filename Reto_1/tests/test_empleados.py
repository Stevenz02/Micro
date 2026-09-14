import pytest
from fastapi.testclient import TestClient

from app import repository
from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def almacenamiento_limpio():
    repository.limpiar()
    yield
    repository.limpiar()


@pytest.fixture
def empleado():
    return {
        "id": "E001",
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan.perez@empresa.com",
        "numeroEmpleado": "EMP-2026-001",
        "cargo": "Desarrollador Senior",
        "area": "Tecnología",
        "departamentoId": "IT",
        "fechaIngreso": "2026-02-10",
        "estado": "ACTIVO",
    }


def test_post_empleado_exitoso(empleado):
    respuesta = client.post("/empleados", json=empleado)
    assert respuesta.status_code == 200


def test_post_devuelve_todos_los_campos(empleado):
    respuesta = client.post("/empleados", json=empleado)
    assert respuesta.json() == empleado


def test_get_empleado_existente(empleado):
    client.post("/empleados", json=empleado)
    respuesta = client.get("/empleados/E001")
    assert respuesta.status_code == 200
    assert respuesta.json() == empleado


def test_get_empleado_inexistente():
    respuesta = client.get("/empleados/E999")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "El empleado con id E999 no existe"}


def test_email_duplicado(empleado):
    client.post("/empleados", json=empleado)
    duplicado = {**empleado, "id": "E002", "numeroEmpleado": "EMP-2026-002"}
    respuesta = client.post("/empleados", json=duplicado)
    assert respuesta.status_code == 400
    assert "email" in respuesta.json()["detail"]
    assert "ya está registrado" in respuesta.json()["detail"]


def test_numero_empleado_duplicado(empleado):
    client.post("/empleados", json=empleado)
    duplicado = {**empleado, "id": "E002", "email": "otro@empresa.com"}
    respuesta = client.post("/empleados", json=duplicado)
    assert respuesta.status_code == 400
    assert "número de empleado" in respuesta.json()["detail"]
    assert "ya está registrado" in respuesta.json()["detail"]


def test_id_duplicado_no_sobrescribe(empleado):
    client.post("/empleados", json=empleado)
    duplicado = {
        **empleado,
        "nombre": "Ana",
        "email": "ana@empresa.com",
        "numeroEmpleado": "EMP-2026-099",
    }
    respuesta = client.post("/empleados", json=duplicado)
    assert respuesta.status_code == 400
    assert "id E001" in respuesta.json()["detail"]
    assert client.get("/empleados/E001").json()["nombre"] == "Juan"


def test_ruta_inexistente():
    respuesta = client.get("/ruta-inexistente")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Recurso no encontrado"}


@pytest.mark.parametrize("metodo", ["delete", "put", "patch"])
def test_metodo_no_soportado_devuelve_404(metodo):
    respuesta = getattr(client, metodo)("/empleados/E001")
    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Recurso no encontrado"}


def test_swagger_disponible():
    respuesta = client.get("/docs")
    assert respuesta.status_code == 200
    assert "Swagger UI" in respuesta.text


def test_redoc_disponible():
    respuesta = client.get("/redoc")
    assert respuesta.status_code == 200


def test_openapi_documenta_endpoints_y_respuestas():
    respuesta = client.get("/openapi.json")
    assert respuesta.status_code == 200

    esquema = respuesta.json()
    assert "/empleados" in esquema["paths"]
    assert "/empleados/{id}" in esquema["paths"]
    assert set(esquema["paths"]["/empleados"]["post"]["responses"]) >= {
        "200",
        "400",
        "422",
    }
    assert set(esquema["paths"]["/empleados/{id}"]["get"]["responses"]) >= {
        "200",
        "404",
    }


def test_openapi_incluye_ejemplo_y_descripciones():
    esquema = client.get("/openapi.json").json()
    modelo = esquema["components"]["schemas"]["Empleado"]

    assert modelo["examples"][0] == empleado_ejemplo()
    assert all(
        propiedad.get("description")
        for propiedad in modelo["properties"].values()
    )

    operacion_get = esquema["paths"]["/empleados/{id}"]["get"]
    parametro_id = operacion_get["parameters"][0]
    assert parametro_id["name"] == "id"
    assert parametro_id["description"] == "Identificador único del empleado"


def empleado_ejemplo():
    return {
        "id": "E001",
        "nombre": "Juan",
        "apellido": "Pérez",
        "email": "juan.perez@empresa.com",
        "numeroEmpleado": "EMP-2026-001",
        "cargo": "Desarrollador Senior",
        "area": "Tecnología",
        "departamentoId": "IT",
        "fechaIngreso": "2026-02-10",
        "estado": "ACTIVO",
    }
