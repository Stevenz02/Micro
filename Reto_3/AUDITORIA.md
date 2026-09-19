# Auditoria Reto 3

Estado: implementacion funcional pre-Docker completada. Docker Compose,
aislamiento real de puertos y evidencias runtime quedan pendientes.

## Implementado pre-Docker

| Requisito | Estado | Implementacion | Archivo | Prueba | Observaciones |
| --- | --- | --- | --- | --- | --- |
| Crear `Reto_3` independiente | CUMPLE | Carpeta nueva basada en Reto 2 | `Reto_3/` | `git status --short` | No modifica funcionalmente Reto 1 ni Reto 2 |
| API Gateway de aplicacion | CUMPLE | FastAPI + httpx | `api-gateway/app/main.py` | `pytest Reto_3/tests` | No usa Nginx/Traefik/Kong |
| Punto unico conceptual | CUMPLE PRE-DOCKER | Rutas externas por Gateway | `api-gateway/app/main.py` | `test_gateway.py` | Aislamiento real queda para Docker |
| `/health` del Gateway | CUMPLE | Respuesta propia | `api-gateway/app/main.py` | `test_health_responde_desde_gateway` | No redirige a upstream |
| Proxy `/empleados` y `/empleados/*` | CUMPLE | Proxy centralizado | `api-gateway/app/main.py` | `test_proxy_preserva...` | Conserva metodo/path/query/body |
| Proxy `/departamentos` y `/departamentos/*` | CUMPLE | Proxy centralizado | `api-gateway/app/main.py` | `test_proxy_preserva...` | Conserva metodo/path/query/body |
| GET/POST/PUT/PATCH/DELETE/OPTIONS | CUMPLE | `api_route` con lista de metodos | `api-gateway/app/main.py` | Parametrizado en `test_gateway.py` | Sin reglas de negocio |
| Headers hop-by-hop filtrados | CUMPLE | Lista centralizada | `api-gateway/app/main.py` | `test_proxy_preserva...` | No propaga `host` ni `content-length` |
| Upstream caido -> 503 JSON | CUMPLE | Captura timeout/transporte | `api-gateway/app/main.py` | `test_upstream_caido...` | Sin stack trace |
| Configuracion Gateway | CUMPLE | Variables de entorno | `api-gateway/app/config.py` | Tests con `Settings` inyectado | URLs no hardcodeadas en logica |
| Circuit Breaker en empleados | CUMPLE | `pybreaker` | `empleados/app/departamentos.py` | `test_despues_de_tres_fallos...` | No esta en Gateway ni departamentos |
| Retry + Circuit Breaker en orden correcto | CUMPLE | Breaker envuelve validacion completa | `empleados/app/departamentos.py` | `test_reintentos...` | Los retries de una solicitud no abren solos el circuito |
| Parametros configurables | CUMPLE | `DEPARTAMENTOS_CB_*` | `empleados/app/config.py` | Import/config en tests | Fail max 3, reset 30 por defecto |
| CLOSED | CUMPLE | Estado inicial `closed` | `empleados/app/departamentos.py` | `test_circuito_inicia...` | Sale del breaker real |
| OPEN | CUMPLE | Tres fallos abren circuito | `empleados/app/departamentos.py` | `test_despues_de_tres_fallos...` | No hace nueva llamada HTTP |
| HALF_OPEN | CUMPLE | Prueba tras reset timeout | `empleados/app/departamentos.py` | `test_half_open_*` | Timeout reducido solo en test |
| 404 no abre circuito | CUMPLE | `HTTPException(400)` excluido | `empleados/app/departamentos.py` | `test_departamento_inexistente...` | Mantiene semantica de negocio |
| Fallback 503 | CUMPLE | No registra empleado | `empleados/app/departamentos.py` | `test_no_persistir...` | Consistencia sobre disponibilidad |
| Estado observable | CUMPLE | `/health/dependencies` | `empleados/app/main.py` | `test_estado_observable...` | Proviene de `current_state` |
| Pruebas Gateway sin Docker | CUMPLE | MockTransport | `tests/test_gateway.py` | `39 passed` | Cubre errores y headers |
| Pruebas empleados sin Docker | CUMPLE | TestClient + MockTransport | `tests/test_empleados_service.py` | `39 passed` | Cubre breaker/retry/fallback |
| Departamentos heredado | CUMPLE | Copia funcional | `departamentos/` | `npm test` | 12 pruebas pasan |
| Documentacion principal | CUMPLE | README completo | `README.md` | Revision documental | Docker marcado pendiente |
| README por servicio | CUMPLE | Gateway, empleados, departamentos | `*/README.md` | Revision documental | Coherente con Reto 3 |
| Evidencias futuras | CUMPLE | Lista sin inventar capturas | `docs/evidencias/README.md` | Revision documental | Para fase Docker |

## Pendiente de Docker

| Requisito | Estado | Implementacion requerida | Archivo futuro | Observaciones |
| --- | --- | --- | --- | --- |
| Compose de Reto 3 | PENDIENTE | Crear `docker-compose.yml` | `Reto_3/docker-compose.yml` | No creado en esta fase |
| Gateway publicado en host 8080 | PENDIENTE | `ports: 127.0.0.1:8080:8080` | Compose futuro | Requiere contenedor Gateway |
| Empleados sin acceso directo | PENDIENTE | `expose: 8081`, sin `ports` | Compose futuro | Requiere cambiar puerto interno |
| Departamentos sin acceso directo | PENDIENTE | `expose: 8082`, sin `ports` | Compose futuro | Requiere cambiar puerto interno |
| Network wiring final | PENDIENTE | Redes de APIs/BD | Compose futuro | Debe preservar DB independientes |
| Healthchecks Docker | PENDIENTE | `depends_on.condition: service_healthy` | Compose futuro | Similar a Reto 2 |

## Pendiente de evidencia runtime

| Evidencia | Estado | Como obtenerla despues de Docker |
| --- | --- | --- |
| Gateway por `localhost:8080` | PENDIENTE | `Invoke-RestMethod http://localhost:8080/health` |
| Directo a empleados rechazado | PENDIENTE | Intentar puerto host de empleados y fallar |
| Directo a departamentos rechazado | PENDIENTE | Intentar puerto host de departamentos y fallar |
| Apertura por diferencia de tiempos | PENDIENTE | Pausar departamentos y medir respuestas |
| Estado OPEN observable | PENDIENTE | Consultar `/health/dependencies` |
| Recuperacion HALF_OPEN/CLOSED | PENDIENTE | Restaurar departamentos, esperar reset, probar alta |
