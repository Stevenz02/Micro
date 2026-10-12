# Reto 6: automatización de pruebas

Este reto añade pruebas repetibles sobre el sistema de `Reto_5`. Mantiene tres niveles: pruebas unitarias de reglas aisladas, una integración con PostgreSQL real y escenarios BDD por HTTP contra el sistema desplegado. Los reportes quedan en rutas fijas para Jenkins y SonarQube en el Reto 7. No se modifica Docker Compose: otro integrante puede empaquetar la suite BDD y conectar los reportes como volumen.

## Arquitectura de pruebas

| Nivel | Alcance | Dependencias |
|---|---|---|
| Unitarias | Unicidad, alta y retiro de Empleados; contraseñas y ciclo de Auth; fechas, solapamiento, días hábiles y scheduler de Vacaciones; validación JWT del Gateway | Fakes/mocks, sin Docker, PostgreSQL, HTTP real ni RabbitMQ |
| Integración | Repositorio de Empleados, esquema real, restricciones UNIQUE, lectura y retiro lógico | PostgreSQL 16 efímero con Testcontainers; ningún otro microservicio |
| BDD | Salud, RBAC, onboarding, vacaciones y offboarding | Gateway y ecosistema completos levantados con Docker Compose |

Se eligió **Behave** porque ya hay Python en el Gateway, Auth y Empleados. Behave ejecuta Gherkin en español; `httpx` hace peticiones reales al Gateway. Cada escenario recibe un `ScenarioState` nuevo, con su cliente HTTP, tokens, última respuesta, empleado, departamento y contraseña generados. Las carpetas `features`, `step_definitions` y `support` separan lenguaje de negocio, pasos y utilidades.

## Contratos reales y diferencias con el enunciado

- `POST /empleados` responde **201** para un alta confirmada; 202 si Departamentos no está disponible y el empleado queda `PENDIENTE`. La suite exige 201 porque las proyecciones de Auth dependen de `empleado.creado`.
- La cuenta de Auth no tiene endpoint público de consulta. La prueba observa `usuario.creado` por la notificación `SEGURIDAD`, obtiene el token con `GET /notificaciones/seguridad/{id}/token` como ADMIN y verifica el login tras activarla.
- No hay servicio independiente de auditoría. El retiro se comprueba mediante `GET /empleados/{id}` y `GET /empleados?estado=RETIRADO`.
- `POST /auth/recover-password` siempre responde **202** con un mensaje genérico, incluso para cuentas retiradas. Para una cuenta retirada la suite verifica además que no se emite una nueva notificación de seguridad durante una ventana acotada.
- Vacaciones admite `fechaInicio == fechaFin`. `fechaFin < fechaInicio` y comienzo pasado producen **400**. Los períodos son inclusivos: compartir una fecha límite cuenta como solapamiento. Los días hábiles excluyen sábado y domingo.
- Los mensajes usan el sobre `id`, `type`, `version`, `occurredAt`, `producer`, `data` y los diez nombres del catálogo oficial. Las pruebas unitarias inspeccionan los payloads y las BDD observan los efectos públicos. Ningún evento transporta contraseñas.

## Aislamiento y asincronía

Cada escenario crea IDs, correos y números de empleado únicos con fecha UTC y bytes aleatorios. Como el dominio exige conservar empleados retirados para auditoría, la suite no los borra físicamente. Los escenarios no leen datos creados por otros escenarios. La integración usa un contenedor PostgreSQL nuevo y lo destruye al finalizar.

`support/polling.py` usa reloj monotónico, timeout total, intervalo y máximo de intentos. Reintenta únicamente errores transitorios de HTTP y de decodificación; muestra la condición incumplida y el último error al agotar el plazo. Los pasos de eventos esperan una notificación que demuestre que el consumidor procesó el hecho **antes** de comprobar un login rechazado. Valores iniciales: 30 segundos, 500 ms y 120 intentos. Se pueden ajustar por entorno.

Para el ciclo de vacaciones, el servicio ya admite `VACACIONES_SCHEDULER_INTERVAL_SECONDS`. Configure **5** al levantar `Reto_5` para las pruebas: unas vacaciones con inicio y fin en el día UTC actual empiezan en un ciclo y terminan en el siguiente. El mecanismo es el mismo scheduler de producción y no requiere endpoint especial. Si se usa el valor de producción de 60 segundos, suba `POLL_TIMEOUT_SECONDS` por encima de 130. La zona usada por el scheduler es UTC.

## Prerrequisitos y ejecución en PowerShell

- Python 3.13 con `venv`, .NET SDK 8 y Docker Desktop con motor activo.
- Dependencias Python: `python -m pip install -r Reto_4/requirements-test.txt -r Reto_5/requirements-test.txt -r Reto_6/e2e-tests/requirements.txt`.
- Para BDD, copie `Reto_6/e2e-tests/.env.example` a `.env` en esa carpeta y establezca `ADMIN_EMAIL` y `ADMIN_PASSWORD`. `USER_EMAIL` y `USER_PASSWORD` están previstos para datos semilla opcionales; los escenarios actuales crean su propio USER.
- En `Reto_5/.env`, configure los valores del sistema y `VACACIONES_SCHEDULER_INTERVAL_SECONDS=5`. Este archivo está ignorado por Git. Desde `Reto_5`: `docker compose up --build -d --wait --wait-timeout 300`.

Desde la raíz del repositorio:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_empleados.ps1 -Suite Unit
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_empleados.ps1 -Suite Integration
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_auth.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_gateway.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_vacaciones.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File Reto_6/run_e2e.ps1
```

Cada comando retorna un código diferente de cero si falla. `run_empleados.ps1` sin parámetro ejecuta unitarias e integración. En Linux o dentro de Docker, la BDD se ejecuta con `python Reto_6/e2e-tests/run.py`; `BASE_URL` puede ser `http://api-gateway:8080` en la red de Compose.

| Suite | Comando | Reporte JUnit/resultados | Reporte cobertura | Reporte BDD |
|---|---|---|---|---|
| empleados-service, unitarias | `run_empleados.ps1 -Suite Unit` | `Reto_4/empleados/reports/junit.xml` | `Reto_4/empleados/reports/coverage.xml` | — |
| empleados-service, integración | `run_empleados.ps1 -Suite Integration` | `Reto_4/empleados/reports/junit-integration.xml` | — | — |
| auth-service | `run_auth.ps1` | `Reto_5/auth/reports/junit.xml` | `Reto_5/auth/reports/coverage.xml` | — |
| api-gateway | `run_gateway.ps1` | `Reto_5/api-gateway/reports/junit.xml` | `Reto_5/api-gateway/reports/coverage.xml` | — |
| vacaciones-service | `run_vacaciones.ps1` | `Reto_5/vacaciones.tests/reports/vacaciones.trx` | `Reto_5/vacaciones.tests/reports/coverage.xml` (Cobertura) | — |
| e2e-tests | `run_e2e.ps1` o `python Reto_6/e2e-tests/run.py` | `Reto_6/e2e-tests/reports/junit.xml` | — | `Reto_6/e2e-tests/reports/cucumber.json` y `cucumber.html` |

El runner BDD genera también XML crudo de Behave en `reports/junit_raw/`. La cobertura de Empleados mide `main.py`, `models.py` y `events.py`, que contienen las reglas, decisiones HTTP y publicación del catálogo. Se excluyen el adaptador SQL, la configuración, el Dockerfile y los archivos generados. La cobertura de Vacaciones mide toda la imagen de código, por lo que su porcentaje global incluye infraestructura no ejercitada por la suite unitaria; `VacationRules` sí se cubre íntegramente.

## Escenarios y prueba manual

Los 25 escenarios describen disponibilidad, tokens ausentes/alterados, RBAC ADMIN/USER, propiedad del perfil, headers falsificados, registro válido e inválido, activación, programación y solapamiento de vacaciones, suspensión/reactivación y retiro definitivo. Los 116 pasos usan HTTP real o aserciones sobre sus respuestas y proyecciones.

Swagger se abre en `http://localhost:8080/docs`. El Gateway también ofrece `/auth/docs`, `/empleados/docs`, `/perfiles/docs`, `/notificaciones/docs` y `/vacaciones/docs`, con `Authorize` Bearer para llamadas protegidas. El login devuelve `access_token`; se copia en `Authorize` sin el prefijo `Bearer`. Los códigos más relevantes son 200 lectura/cambio, 201 creación, 202 recuperación anónima o alta pendiente, 400 regla de dominio, 401 token/credenciales, 403 permiso, 404 recurso ausente y 422 cuerpo inválido.

## Evidencia de ejecución

Se ejecutó el 12 de octubre de 2026 en Windows con Docker Compose y PostgreSQL/RabbitMQ reales. Las tres ejecuciones BDD consecutivas pasaron **25/25 escenarios y 116/116 pasos** en 1:27.744, 1:27.627 y 1:26.703. Una ejecución final, después de restaurar la prueba deliberada y actualizar Swagger, también pasó 25/25 en 1:31.718. Los reportes finales corresponden a esa ejecución correcta.

| Suite | Resultado | Cobertura medida |
|---|---|---|
| Empleados unitarias | 64 pasaron | 79.19 % de `main.py`, `models.py` y `events.py` |
| Empleados integración | 1 pasó con PostgreSQL 16 efímero | No se mide cobertura separada |
| Auth | 10 pasaron | 86.17 % de contraseñas, ciclo de cuenta y tokens |
| Gateway | 24 pasaron | 91.76 % de `gateway_app/main.py` |
| Vacaciones | 16 pasaron | 16.9 % del ensamblado completo; `VacationRules` 100 % |
| BDD | 25 escenarios y 116 pasos pasaron | No aplica |

Prueba deliberada de fallo: se cambió temporalmente la expectativa de salud de 200 a 201. Behave salió con código **1**; JUnit registró un fallo, el HTML marcó el escenario como fallido y ambos reportaron “Esperaba HTTP 201, obtuvo 200”. En Vacaciones se cambió temporalmente el límite inclusivo de solapamiento; xUnit salió con código **1** e indicó `Expected: True, Actual: False` para dos períodos que comparten la fecha límite. Ambos cambios se revirtieron, se ejecutaron otra vez las suites y los reportes finales quedaron sin fallos.

## Variables necesarias para Dockerizar la suite

`BASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `POLL_TIMEOUT_SECONDS`, `POLL_INTERVAL_MS`, `POLL_MAX_ATTEMPTS` y `HTTP_TIMEOUT_SECONDS`; `USER_EMAIL` y `USER_PASSWORD` se reservan para un USER precargado si el equipo decide añadirlo. El contenedor de pruebas debe estar en `microservices-network`, usar `BASE_URL=http://api-gateway:8080` y montar `e2e-tests/reports` para conservar los reportes. No incluya `.env` ni credenciales en la imagen.
