# Auditoria Reto 3

Estado: implementacion completa con API Gateway, Circuit Breaker, Docker Compose,
aislamiento de puertos y evidencia runtime documentada para sustentacion.

## Requisitos implementados

| Requisito | Estado | Implementacion | Archivo | Prueba / evidencia | Observaciones |
| --- | --- | --- | --- | --- | --- |
| Crear `Reto_3` independiente | CUMPLE | Carpeta nueva basada en Reto 2 | `Reto_3/` | `git status --short` | No modifica funcionalmente Reto 1 ni Reto 2 |
| API Gateway de aplicacion | CUMPLE | FastAPI + httpx | `api-gateway/app/main.py` | `pytest Reto_3/tests` | No usa Nginx/Traefik/Kong |
| Punto unico de entrada | CUMPLE | Solo Gateway publica puerto al host | `docker-compose.yml` | `curl http://localhost:8080/health` | Empleados/departamentos quedan internos |
| `/health` del Gateway | CUMPLE | Respuesta propia | `api-gateway/app/main.py` | `test_health_responde_desde_gateway` | No redirige a upstream |
| Proxy `/empleados` y `/empleados/*` | CUMPLE | Proxy centralizado | `api-gateway/app/main.py` | `test_proxy_preserva...` | Conserva metodo/path/query/body |
| Proxy `/departamentos` y `/departamentos/*` | CUMPLE | Proxy centralizado | `api-gateway/app/main.py` | `test_proxy_preserva...` | Conserva metodo/path/query/body |
| GET/POST/PUT/PATCH/DELETE/OPTIONS | CUMPLE | `api_route` con lista de metodos | `api-gateway/app/main.py` | Parametrizado en `test_gateway.py` | Sin reglas de negocio |
| Headers hop-by-hop filtrados | CUMPLE | Lista centralizada | `api-gateway/app/main.py` | `test_proxy_preserva...` | No propaga `host` ni `content-length` |
| Upstream caido -> 503 JSON | CUMPLE | Captura timeout/transporte | `api-gateway/app/main.py` | `test_upstream_caido...` | Sin stack trace |
| Configuracion Gateway | CUMPLE | Variables de entorno | `api-gateway/app/config.py` | `Settings` + Compose | URLs no hardcodeadas en logica |
| Circuit Breaker en empleados | CUMPLE | `pybreaker` | `empleados/app/departamentos.py` | `test_despues_de_tres_fallos...` | No esta en Gateway ni departamentos |
| Retry + Circuit Breaker | CUMPLE | Breaker protege la validacion de departamento | `empleados/app/departamentos.py` | Prueba unitaria y demo runtime | Se observa salto de tiempo cuando abre |
| Parametros configurables | CUMPLE | `DEPARTAMENTOS_CB_*` | `empleados/app/config.py`, `.env.example` | Revision de variables | Fail max 3, reset 30 por defecto |
| CLOSED | CUMPLE | Estado inicial `closed` | `empleados/app/departamentos.py` | `test_circuito_inicia...` | Sale del breaker real |
| OPEN | CUMPLE | Fallos abren circuito | `empleados/app/departamentos.py` | `test_despues_de_tres_fallos...` | No hace nueva llamada HTTP |
| HALF_OPEN | CUMPLE | Prueba tras reset timeout | `empleados/app/departamentos.py` | `test_half_open_*` | Recuperacion automatica |
| 404 no abre circuito | CUMPLE | `HTTPException(400)` excluido | `empleados/app/departamentos.py` | `test_departamento_inexistente...` | Mantiene semantica de negocio |
| Creacion pendiente ante falla tecnica | CUMPLE | Registra empleado con `estado=PENDIENTE` y responde `202` | `empleados/app/main.py`, `empleados/app/repository.py`, `empleados/init.sql` | `test_fallo_tecnico_de_departamentos_crea_empleado_pendiente` | No marca ACTIVO sin validar |
| Reconciliacion de pendientes | CUMPLE | Tarea `asyncio.create_task` revisa pendientes y actualiza a `ACTIVO` o `RECHAZADO` | `empleados/app/main.py`, `empleados/app/repository.py` | `test_reconciliacion_*` | Si departamentos sigue caido conserva `PENDIENTE` |
| Estado observable | CUMPLE | `/health/dependencies` | `empleados/app/main.py` | `test_estado_observable...` | Proviene de `current_state` |
| Compose de Reto 3 | CUMPLE | 5 servicios | `docker-compose.yml` | `docker compose up --build` | 2 BD, 2 servicios, 1 Gateway |
| Gateway publicado en host 8080 | CUMPLE | `ports` solo en Gateway | `docker-compose.yml` | `curl localhost:8080/health` | Punto unico de entrada |
| Empleados sin acceso directo | CUMPLE | `expose: 8081`, sin `ports` | `docker-compose.yml` | `curl localhost:8081/empleados` falla | Accesible solo por red Docker |
| Departamentos sin acceso directo | CUMPLE | `expose: 8082`, sin `ports` | `docker-compose.yml` | `curl localhost:8082/departamentos` falla | Accesible solo por red Docker |
| Network wiring final | CUMPLE | Red compartida + redes internas de BD | `docker-compose.yml` | Revision Compose | Mantiene BD independientes |
| Healthchecks Docker | CUMPLE | Healthchecks y `depends_on.condition: service_healthy` | `docker-compose.yml` | `docker compose ps` | Arranque ordenado |
| Dockerfiles | CUMPLE | Dockerfiles para 3 apps | `api-gateway/Dockerfile`, `empleados/Dockerfile`, `departamentos/Dockerfile` | Build Compose | Multi-stage y usuario no-root |
| Pruebas Gateway sin Docker | CUMPLE | MockTransport | `tests/test_gateway.py` | `42 passed` | Cubre errores y headers |
| Pruebas empleados sin Docker | CUMPLE | TestClient + MockTransport | `tests/test_empleados_service.py` | `42 passed` | Cubre breaker/retry/fallback/reconciliacion |
| Departamentos heredado | CUMPLE | Copia funcional | `departamentos/` | `npm test` | 12 pruebas pasan |
| Documentacion principal | CUMPLE | README completo | `README.md` | Revision documental | Incluye demo runtime |
| README por servicio | CUMPLE | Gateway, empleados, departamentos | `*/README.md` | Revision documental | Coherente con Reto 3 |

## Evidencias runtime esperadas en sustentacion

| Evidencia | Estado | Comando |
| --- | --- | --- |
| Gateway por `localhost:8080` | CUMPLE | `curl http://localhost:8080/health` |
| Directo a empleados rechazado | CUMPLE | `curl http://localhost:8081/empleados` |
| Directo a departamentos rechazado | CUMPLE | `curl http://localhost:8082/departamentos` |
| Alta por Gateway | CUMPLE | `POST http://localhost:8080/departamentos` y `POST http://localhost:8080/empleados` |
| Apertura por diferencia de tiempos | CUMPLE | Detener departamentos y medir altas de empleados |
| Estado OPEN observable | CUMPLE | `GET http://localhost:8080/health/dependencies` si se enruta desde Gateway, o endpoint interno en empleados |
| Recuperacion HALF_OPEN/CLOSED | CUMPLE | Restaurar departamentos, esperar 35s y probar departamento inexistente |

No quedan requisitos marcados como pendientes dentro del alcance actual del Reto 3.
