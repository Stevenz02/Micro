# Resultados de ejecución del Reto 6

**Verificación:** 15 de octubre de 2026, 19:36–19:50 (America/Bogota). **Rama:** `features/kevin`. **Commit base revisado:** `c3c4523518f455e0d1b39ef42260210e04e4484e`. Los cambios de esta verificación están en el árbol de trabajo, sin commit. El despliegue se hizo con `Reto_6/docker-compose.yml` y `.env` local no versionado. Se usaron PostgreSQL 16 y RabbitMQ reales en Docker.

## Sistema ejecutado

`docker compose config --quiet` pasó; `docker compose up --build -d --wait --wait-timeout 300` terminó con código 0. `docker compose ps` mostró saludables Gateway, Auth, Empleados, Departamentos, Perfiles, Notificaciones, Vacaciones, RabbitMQ y las seis bases independientes (`database-auth`, `-empleados`, `-departamentos`, `-perfiles`, `-notificaciones`, `-vacaciones`). `rabbitmq-diagnostics -q ping` respondió `Ping succeeded`. `rabbitmq-setup` terminó correctamente como servicio transitorio.

El Gateway es el único puerto HTTP de negocio publicado: **`127.0.0.1:8080`**. RabbitMQ Management publica **`127.0.0.1:15672`**. Los puertos internos son Empleados 8081, Departamentos 8082, Perfiles 8083, Notificaciones 8084, Vacaciones 8085 y Auth 8086; PostgreSQL escucha 5432 dentro de cada red privada. Por el Gateway, `/health`, `/docs`, `/redoc`, `/openapi.json` y los seis Swagger individuales respondieron `200` (Notificaciones y Vacaciones tras su redirección normal). `/openapi.json` reunió **24 operaciones** y 19 modelos, con `BearerAuth` y respuesta `TokenOutput` para login. Las pruebas BDD realizaron los flujos por HTTP real al Gateway, incluidas respuestas `401` y `403`.

## Suites y cobertura

| Componente | Suite | Resultado | Pruebas | Cobertura | Reporte |
|---|---|---:|---:|---:|---|
| Reto 4 Python (Empleados y pruebas del Gateway previo) | pytest unitarias | Aprobada | 64/64 | 79.19 % de `main.py`, `models.py`, `events.py` de Empleados (175/221 líneas) | `Reto_4/empleados/reports/junit.xml`, `coverage.xml` |
| Empleados PostgreSQL | pytest integración con Testcontainers | Aprobada | 1/1 | No medida | `Reto_4/empleados/reports/junit-integration.xml` |
| Auth | pytest | Aprobada | 10/10 | 86.17 % (81/94 líneas seleccionadas) | `Reto_5/auth/reports/junit.xml`, `coverage.xml` |
| API Gateway | pytest | Aprobada | 26/26 | 90.91 % de `gateway_app/main.py` (230/253 líneas) | `Reto_5/api-gateway/reports/junit.xml`, `coverage.xml` |
| Departamentos | Node `npm test` | Aprobada | 12/12 | No medida | Salida TAP de la ejecución |
| Perfiles | Go `go test ./...` en contenedor | Aprobada | 4/4 | No medida | Salida de la ejecución; el Dockerfile también ejecuta `go test` al construir |
| Notificaciones | Maven `mvn test -q` en contenedor | Aprobada | 8/8 | No medida | `Reto_5/notificaciones/target/surefire-reports/TEST-*.xml` |
| Vacaciones | .NET xUnit | Aprobada | 16/16 | 16.90 % del ensamblado completo (58/343 líneas) | `Reto_5/vacaciones.tests/reports/vacaciones.trx`, `coverage.xml` |
| E2E | Behave en `bdd-tests` | Aprobada | 25/25 escenarios, 116/116 pasos | No aplica | `Reto_6/e2e-tests/reports/junit.xml`, `cucumber.json`, `cucumber.html` |

Los XML JUnit de pytest registran respectivamente 64, 1, 10 y 26 pruebas, con cero errores y fallos. Los dos XML Surefire suman 8 pruebas con cero fallos. El TRX de Vacaciones registra 16 aprobadas. La cobertura de Vacaciones incluye infraestructura no ejercitada por sus pruebas unitarias; no debe interpretarse como cobertura solo de reglas de fechas. Las suites Node y Go no generan JUnit en esta configuración; sus resultados se verificaron por código de salida y salida de prueba.

## Tres corridas BDD consecutivas

Cada corrida fue `docker compose run --rm bdd-tests`, conservando una copia independiente de JUnit, Cucumber JSON y HTML. El tiempo indicado procede de Behave; el arranque del contenedor añade unos segundos.

| Corrida | Características | Escenarios | Pasos | Duración Behave | Código de salida | Evidencia |
|---|---:|---:|---:|---:|---:|---|
| 1 | 5/5 | 25/25 | 116/116 | 35.926 s | 0 | `e2e-tests/reports/run-1/`, `run-1.log` |
| 2 | 5/5 | 25/25 | 116/116 | 40.299 s | 0 | `e2e-tests/reports/run-2/`, `run-2.log` |
| 3 | 5/5 | 25/25 | 116/116 | 40.629 s | 0 | `e2e-tests/reports/run-3/`, `run-3.log` |
| Final, tras reconstruir Gateway | 5/5 | 25/25 | 116/116 | 39.962 s | 0 | `e2e-tests/reports/run-final/`, `run-final.log` |

Los cuatro `junit.xml` guardados tienen `tests=25`, `failures=0`, `errors=0`. Los cuatro JSON contienen 5 características, 25 escenarios y 116 pasos con estado `passed`. Se revisó el HTML como archivo estructurado: cada copia contiene 5 secciones de característica, 25 tarjetas de escenario y 116 elementos de paso. El renderizador muestra estado y duración y, si hay fallo, su mensaje; en estas corridas aprobadas no hay errores que mostrar.

## Cambios y correcciones de esta verificación

- El Swagger principal antes exponía comodines del proxy y remitía a Swagger separados. Ahora incorpora los OpenAPI reales de los seis servicios, elimina operaciones comodín de la vista consolidada, separa nombres de modelos repetidos y declara Bearer en operaciones protegidas. Conserva el modelo de respuesta del login del Gateway.
- Las redirecciones de los Swagger individuales de Notificaciones y Vacaciones llegaban a recursos estáticos protegidos y daban `401`. Se permitieron solo los recursos de documentación y se probó que una ruta de negocio sin JWT mantiene `401`.
- Se añadieron dos pruebas significativas del Gateway: composición de contratos/modelos y acceso a recursos de Swagger sin abrir las rutas de negocio.
- El primer lanzador de tres corridas se detuvo antes de Behave porque PowerShell trató el progreso de Docker en stderr como excepción. Se corrigió **solo el lanzador de verificación** para decidir por el código de salida real de Docker. Después se ejecutaron tres corridas completas y una final; el intento abortado no se cuenta.
- Se añadieron [inventario de rutas](RUTAS_RETO6.md) y [guía de sustentación](SUSTENTACION_RETO6.md). No se cambiaron contratos de negocio ni nombres de eventos.

## Variables necesarias

Use `Reto_6/.env.example` como lista de claves, copie a `Reto_6/.env` y reemplace secretos antes de otro entorno. Grupos obligatorios: `JWT_SECRET`, `JWT_ACCESS_TTL_SECONDS`, `JWT_RESET_TTL_SECONDS`; `ADMIN_EMPLOYEE_ID`, `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH` y `E2E_ADMIN_PASSWORD` correspondiente; `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_MANAGEMENT_PORT`; `DB_{EMPLEADOS,DEPARTAMENTOS,PERFILES,NOTIFICACIONES,VACACIONES,AUTH}_{NAME,USER,PASSWORD}`; `GATEWAY_PORT` y timeout; `VACACIONES_SCHEDULER_INTERVAL_SECONDS` (5 para BDD); las variables `DEPARTAMENTOS_*` y `PENDIENTES_RECONCILIATION_INTERVAL_SECONDS`; `POLL_TIMEOUT_SECONDS`, `POLL_INTERVAL_MS`, `POLL_MAX_ATTEMPTS`, `HTTP_TIMEOUT_SECONDS`. `BASE_URL` de BDD en Compose es `http://api-gateway:8080`. No se versionó `.env`.

## Limitaciones y repetición visual

El navegador de esta sesión no expuso una ventana utilizable; por ello **no se tomaron capturas ni se verificó visualmente el renderizado** de Swagger o Cucumber HTML. Sí se verificaron sus respuestas HTTP y el contenido estructural de los reportes. Para la exposición, abra `http://localhost:8080/docs` y siga [la guía paso a paso](SUSTENTACION_RETO6.md); abra `Reto_6/e2e-tests/reports/cucumber.html` para mostrar las cinco características y sus pasos.

Auth no devuelve `role` ni datos de usuario como campos separados en login: `role` está en el JWT. No existe consulta HTTP de cuentas, actualización/borrado de Departamentos, `/perfiles/me`, búsqueda individual por email/número, ni endpoint para adelantar el scheduler. Vacaciones devuelve `400` por solapamiento, no `409`. Los retiros son lógicos y los datos BDD quedan en las bases locales. El contrato actual no sincroniza con Auth cambios posteriores del email de Empleados. El scheduler de Vacaciones está configurado con una sola réplica; el README de Reto 5 documenta el riesgo de duplicación al escalarlo.

La política actual del Gateway permite a cualquier USER autenticado las rutas GET de Empleados, Perfiles y Notificaciones; no limita esas lecturas al propio empleado. Es una decisión de acceso existente que debe revisarse antes de usar datos reales de RR. HH.
