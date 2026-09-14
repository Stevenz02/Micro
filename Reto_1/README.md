# Reto 1: servidor de empleados

API REST sencilla para registrar y consultar empleados. Está construida con Python,
FastAPI, Uvicorn y Pydantic; sus pruebas usan pytest y FastAPI TestClient.

## Estructura

```text
app/
  __init__.py
  main.py          # Endpoints y manejo de errores HTTP
  models.py        # Modelo y validación del empleado
  repository.py    # Almacenamiento en memoria
tests/
  test_empleados.py
requirements.txt
Dockerfile
pruebas.ps1
```

## Modelo de empleado

Todos los campos son obligatorios:

```json
{
  "id": "E001",
  "nombre": "Juan",
  "apellido": "Pérez",
  "email": "juan.perez@empresa.com",
  "numeroEmpleado": "EMP-2026-001",
  "cargo": "Desarrollador Senior",
  "area": "Tecnología",
  "departamentoId": "IT",
  "fechaIngreso": "2026-02-10",
  "estado": "ACTIVO"
}
```

`fechaIngreso` debe ser una fecha válida, el email debe tener formato válido y
`estado` solo admite `ACTIVO`. `departamentoId` es texto libre.

## Endpoints y validaciones

- `POST /empleados`: registra y devuelve el empleado (`200`). Rechaza con `400`
  un `id`, `email` o `numeroEmpleado` ya registrado.
- `GET /empleados/{id}`: devuelve el empleado (`200`) o un error descriptivo
  (`404`).
- Las rutas y métodos no soportados responden `404` con
  `{"detail":"Recurso no encontrado"}`.

Los datos se guardan en un diccionario de Python y se pierden al reiniciar la
aplicación. No se utiliza base de datos.

## Instalación y ejecución local

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

La API quedará disponible en `http://localhost:8080`. En otra terminal se puede
ejecutar la evidencia manual (se recomienda iniciar con almacenamiento vacío):

```powershell
.\pruebas.ps1
```

## Documentación interactiva con Swagger

Después de iniciar la aplicación:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

abre `http://localhost:8080/docs`. Desde Swagger UI se pueden probar directamente
los endpoints mediante el botón **Try it out**. El formulario de
`POST /empleados` incluye automáticamente un empleado completo de ejemplo.

- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`
- OpenAPI JSON: `http://localhost:8080/openapi.json`

## Pruebas automatizadas

```powershell
pytest -v
```

Cada prueba limpia el almacenamiento para ser independiente.

## Docker

```powershell
docker build -t servidor-empleados .
docker run --rm -p 8080:8080 servidor-empleados
```
