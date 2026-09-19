# API Gateway

Gateway de aplicacion para `Reto_3`, implementado con FastAPI y `httpx`.

## Ejecucion local sin Docker

Configurar upstreams locales o mockeados mediante variables:

```powershell
$env:EMPLEADOS_URL='http://127.0.0.1:8081'
$env:DEPARTAMENTOS_URL='http://127.0.0.1:8082'
$env:GATEWAY_REQUEST_TIMEOUT_SECONDS='5'
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

## Rutas

| Ruta | Destino |
| --- | --- |
| `/health` | Gateway |
| `/empleados` | `EMPLEADOS_URL` |
| `/empleados/*` | `EMPLEADOS_URL` |
| `/departamentos` | `DEPARTAMENTOS_URL` |
| `/departamentos/*` | `DEPARTAMENTOS_URL` |

El Gateway no implementa reglas de negocio. Conserva metodo, path, query, body,
headers de aplicacion, status code y body del backend. Si el upstream no responde
o supera el timeout, devuelve 503 con JSON estable.
