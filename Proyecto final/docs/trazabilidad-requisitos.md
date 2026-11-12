# Trazabilidad del enunciado

Dónde se cumple cada requisito del proyecto final.

## Funcionalidad

| Requisito | Implementación |
|---|---|
| CRUD de empleados; estados `ACTIVO`, `EN_VACACIONES`, `RETIRADO`; retiro como transición con `fechaRetiro` | `microservicios/empleados` |
| Auditoría de retirados por rango de fechas | `GET /empleados?estado=RETIRADO&desde=&hasta=` |
| Unicidad de `email` y `numeroEmpleado` | `microservicios/empleados/app/main.py` + restricciones SQL |
| Departamentos como fuente de verdad; `400` si el `departamentoId` no existe | `microservicios/departamentos`, `empleados/app/departamentos.py` |
| Cuenta creada por `empleado.creado`, inactiva, sin contraseña, con token de activación | `microservicios/auth/auth_app/events.py`, `lifecycle.py` |
| Login, establecer contraseña con token, recuperación, cambio de contraseña | `microservicios/auth/auth_app/main.py` |
| Suspensión temporal (vacaciones) distinta de baja permanente (retiro) | `auth_app/repository.py`, `lifecycle.py` |
| Sin endpoint público de registro | No existe `/register`; rutas públicas en `api-gateway/gateway_app/main.py` (`PUBLIC_ROUTES`) |
| Perfil propio; modificar el de otro responde `403` | Gateway (autorización por propiedad) + `microservicios/perfiles` |
| Archivado del perfil al retirar | `microservicios/perfiles/consumer.go` |
| Vacaciones: validaciones y scheduler de inicio/fin | `microservicios/vacaciones` (`VacationScheduler.cs`) |
| Notificaciones por correo con plantillas configurables | `microservicios/notificaciones` (`EmailSender.java`, `plantillas/`) + Mailpit |
| Eventos según el catálogo; consumidores idempotentes | [eventos.md](eventos.md); tabla `eventos_procesados` en cada consumidor |
| Gateway: punto único, enrutamiento, validación de token | `microservicios/api-gateway` |
| Composición `GET /empleados/{id}/completo` con fallo parcial (puntaje adicional) | `api-gateway/gateway_app/main.py` |

## Requisitos técnicos por microservicio

| Requisito | Implementación |
|---|---|
| OpenAPI + Swagger UI | `microservicios/<servicio>/openapi.yaml`; <http://localhost:8080/swagger> |
| Pruebas unitarias, de integración y funcionales | `microservicios/tests`, pruebas por lenguaje, `e2e-tests/` |
| Cobertura mínima 70 % | Umbral en las pruebas y Quality Gate de SonarQube |
| `GET /health` con `status`, `service`, `checks`; 200 / 503 | Todos los servicios |
| Pipeline Jenkins: build, test, calidad, package | `microservicios/<servicio>/Jenkinsfile`, `Jenkinsfile` |
| Dockerfile multi-stage y configuración por entorno | `microservicios/<servicio>/Dockerfile` |
| Compose con un solo comando, incluido Jenkins | `docker-compose.yml` |

## Observabilidad

| Requisito | Implementación |
|---|---|
| Logs centralizados y estructurados con `traceId` | Loki + Promtail; `observabilidad/promtail` |
| Métricas de salud y de negocio; dashboards | Prometheus + Grafana; `observabilidad/grafana/provisioning/dashboards` |
| Trazabilidad distribuida W3C entre lenguajes y por RabbitMQ | OpenTelemetry + Zipkin |
| Alertas hacia un canal externo | Grafana → Discord; `observabilidad/grafana/provisioning/alerting` |

## Seguridad y configuración

| Requisito | Implementación |
|---|---|
| Ningún secreto en el repositorio | `.gitignore` (`.env`, `secrets/`); `.env.example` solo con valores no sensibles |
| Docker Compose Secrets | Sección `secrets:` de `docker-compose.yml`; `docker-entrypoint.sh` |
| Script de generación de secretos | `scripts/setup-secrets.sh` / `.ps1`; plantillas en `secrets.example/` |
| Contraseñas hasheadas; nunca por correo ni por eventos | bcrypt en `auth_app/passwords.py`; los correos llevan solo tokens |
| RBAC por rol y autorización por propiedad | Middleware del Gateway |
| Identity Provider OAuth2/OIDC (puntaje adicional) | **No implementado**: se usa la opción (a), servicio propio con JWT |

## Escalabilidad y resiliencia

| Requisito | Implementación |
|---|---|
| Servicios stateless escalables horizontalmente | Empleados y Departamentos con 2 réplicas |
| Balanceador con health checks | Traefik (`load-balancer` en `docker-compose.yml`) |
| Circuit Breaker con fallback, timeouts y reintentos | `empleados/app/departamentos.py` (estado `PENDIENTE` + reconciliación) |
| El sistema atiende cuando cae una instancia | [guias/escalabilidad-y-resiliencia.md](guias/escalabilidad-y-resiliencia.md) |

## Restricciones

| Restricción | Cumplimiento |
|---|---|
| Comunicación asíncrona por broker | RabbitMQ; la única llamada REST entre servicios es la validación de departamento que el enunciado define como punto síncrono |
| Al menos 4 lenguajes | 5: Python, Node.js, Go, Java y C# |
| Despliegue unificado | `docker compose up --build` |
| Cero secretos | Ver sección anterior |

## Limitaciones conocidas

- No hay Identity Provider (Keycloak); la autenticación es propia con JWT HS256.
- El perfil gestiona teléfono, dirección, ciudad y biografía; no incluye foto, redes sociales ni
  código postal.
- Vacaciones permite crear, consultar y cancelar períodos, pero no editarlos.
- Las redes Docker separan datos (una red interna por base) y CI/CD; negocio, mensajería y
  observabilidad comparten `microservices-network`.
