# Empleados - Reto 3

Servicio FastAPI heredado de `Reto_2`, con persistencia propia y validacion HTTP
de departamentos. En `Reto_3` agrega Circuit Breaker con `pybreaker`.

## Componentes

| Archivo | Responsabilidad |
| --- | --- |
| `app/main.py` | Endpoints de empleados, health y estado de dependencias |
| `app/departamentos.py` | Cliente REST, timeout, retry, backoff y Circuit Breaker |
| `app/config.py` | Variables de entorno |
| `app/repository.py` | Acceso a PostgreSQL |
| `init.sql` | Esquema reproducible |

## Circuit Breaker

La llamada `empleados -> departamentos` conserva los reintentos de `Reto_2`.
Cuando la dependencia no responde, empleados registra la solicitud con
`estado=PENDIENTE` y responde `202 Accepted`; no inventa departamentos ni marca
el empleado como `ACTIVO` sin validar. Con el circuito abierto, las siguientes
solicitudes quedan pendientes rapidamente, sin volver a golpear la red.

Ademas, `app/main.py` arranca un reconciliador con `asyncio.create_task`. El
reconciliador busca empleados `PENDIENTE`, vuelve a validar el departamento con
el mismo cliente REST y actualiza el estado: `ACTIVO` si existe, `RECHAZADO` si
departamentos confirma 404, o conserva `PENDIENTE` si la dependencia sigue
caida.

## Estado observable

```http
GET /health/dependencies
```

Ejemplo:

```json
{
  "status": "ok",
  "dependencies": [
    {
      "dependency": "departamentos-service",
      "state": "closed"
    }
  ]
}
```

## Variables

| Variable | Valor esperado |
| --- | --- |
| `DEPARTAMENTOS_SERVICE_URL` | `http://departamentos-service:8082` cuando se dockerice |
| `DEPARTAMENTOS_TIMEOUT_SECONDS` | `2` |
| `DEPARTAMENTOS_MAX_RETRIES` | `3` |
| `DEPARTAMENTOS_BACKOFF_SECONDS` | `1` |
| `DEPARTAMENTOS_CB_FAIL_MAX` | `3` |
| `DEPARTAMENTOS_CB_RESET_TIMEOUT_SECONDS` | `30` |
| `PENDIENTES_RECONCILIATION_INTERVAL_SECONDS` | `15` |

## Pruebas

Desde la raiz:

```powershell
.\.venv\Scripts\python.exe -m pytest Reto_3/tests/test_empleados_service.py -q
```
