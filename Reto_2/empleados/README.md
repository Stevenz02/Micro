# Empleados — Reto 2

Python 3.12/FastAPI, HTTPX y Psycopg 3; PostgreSQL 16 propio.
Conserva el modelo de `Reto_1/app/models.py` mediante importación, sin duplicarlo.

| Método | Ruta | Resultado |
|--------|------|-----------|
| POST | `/empleados` | 201; 400 por duplicado o departamento inexistente; 422 por cuerpo inválido; 503 por dependencia no disponible |
| GET | `/empleados` | 200, lista completa |
| GET | `/empleados/{id}` | 200 o 404 |
| GET | `/health` | 200 si la BD y tabla responden |

Swagger: <http://localhost:8080/docs>. OpenAPI: <http://localhost:8080/openapi.json>.
Errores SQL no previstos: 500 con mensaje controlado.

La configuración requiere `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`DEPARTAMENTOS_SERVICE_URL`; `DB_PORT` vale 5432 por defecto. Las variables de
timeout, reintentos y backoff se detallan en el [README del reto](../README.md).

## Ejecución

El flujo recomendado es Compose desde `Reto_2`. Para construir la imagen por separado,
ejecutar desde la raíz del repositorio:

```powershell
docker build -f Reto_2/empleados/Dockerfile -t empleados-service .
```

El contexto raíz permite incorporar el modelo canónico. Para desarrollo fuera de
Docker, preparar una BD con `init.sql`, definir las variables anteriores y ejecutar
también desde la raíz:

```powershell
python -m pip install -r Reto_2/empleados/requirements.txt
python -m uvicorn Reto_2.empleados.app.main:app --host 127.0.0.1 --port 8080
```

Las bases del Compose no publican puertos; este modo local requiere una instancia
PostgreSQL accesible al proceso. `.env` lo lee Compose, no la aplicación Python.

## Organización

- `app/models.py`: contrato canónico.
- `app/config.py`: variables y límites de reintentos.
- `app/repository.py`: consultas parametrizadas; commit/rollback por operación.
- `app/departamentos.py`: validación remota, timeout y backoff.
- `app/main.py`: endpoints, OpenAPI y errores.
- `init.sql`: esquema de una base vacía.

Pruebas desde la raíz: `python -m pytest Reto_2/tests -q` con
`Reto_2/requirements-test.txt` instalado.
