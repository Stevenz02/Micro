# Reto 4 - Handoff técnico

Este documento describe el estado comprobado del código al 27 de septiembre de 2026. No sustituye el README académico ni define contratos de eventos.

## 1. Estado general

**PARCIALMENTE COMPLETO.** Los servicios REST, sus bases de datos, el Gateway, Docker Compose, Swagger y las suites disponibles están implementados y verificados. RabbitMQ tiene su topología creada. La integración asíncrona queda pendiente porque no se encontró el Catálogo oficial de Eventos; no se inventaron versiones ni payloads. El E2E de eventos y la deduplicación efectiva no son ejecutables sin ese contrato.

## 2. Qué implementó Kevin

- **Gateway:** proxy HTTP para empleados, departamentos, perfiles, notificaciones y vacaciones; conserva query string, cuerpo, headers relevantes y status HTTP, y responde 503 controlado si el upstream no está disponible.
- **Empleados:** servicio Python/FastAPI con PostgreSQL; alta, consulta, actualización protegida, retiro lógico, filtros y reconciliación periódica de empleados pendientes.
- **Departamentos:** servicio Node.js/Express con PostgreSQL; alta, consulta, listado, health y OpenAPI.
- **RabbitMQ:** exchange, colas durables y bindings idempotentes inicializados mediante RabbitMQ Management API.
- **Perfiles:** servicio Go con PostgreSQL; lectura y edición de los campos propios del perfil.
- **Notificaciones:** servicio Java 21/Spring Boot con PostgreSQL; consultas del historial y por empleado; esquema con los tipos esperados.
- **Vacaciones:** servicio .NET 8 con PostgreSQL; alta, consultas, filtros, reglas de negocio y cancelación lógica.
- **Bases de datos:** una instancia PostgreSQL 16 independiente y un volumen por servicio de negocio.
- **Docker:** Compose con redes separadas, healthchecks, servicios de aplicación non-root y solo dos puertos publicados en loopback.
- **OpenAPI:** documentación para Departamentos, Perfiles, Notificaciones y Vacaciones; rutas verificadas detrás del Gateway.
- **Pruebas:** suites de Python, Node, Go, Java y .NET ejecutadas; además, prueba funcional REST con Compose levantado.
- **Reto 3:** se añadió `GET /health/dependencies` al Gateway, su prueba y el usuario non-root al contenedor de Departamentos; `.gitignore` excluye `bin/` y `obj/` de .NET.

## 3. Arquitectura actual

| Servicio | Lenguaje | Puerto interno | Base de datos | Produce | Consume |
|---|---|---:|---|---|---|
| API Gateway | Python / FastAPI | 8080 | Ninguna | Ninguno | Ninguno |
| Empleados | Python / FastAPI | 8081 | PostgreSQL `database-empleados` | Ninguno implementado | Ninguno |
| Departamentos | Node.js / Express | 8082 | PostgreSQL `database-departamentos` | Ninguno | Ninguno |
| Perfiles | Go / `net/http` | 8083 | PostgreSQL `database-perfiles` | Ninguno | Ninguno |
| Notificaciones | Java 21 / Spring Boot | 8084 | PostgreSQL `database-notificaciones` | Ninguno | Ninguno |
| Vacaciones | .NET 8 / ASP.NET minimal APIs | 8085 | PostgreSQL `database-vacaciones` | Ninguno implementado | Ninguno |
| RabbitMQ | RabbitMQ 4.1 | AMQP 5672; Management 15672 | Volumen RabbitMQ | No hay productores conectados | No hay consumidores conectados |

Las bases de datos tienen volúmenes nombrados y redes internas individuales. Los servicios se encuentran además en la red interna compartida para comunicarse con el Gateway y RabbitMQ.

## 4. RabbitMQ

- Exchange: `rrhh.events`, tipo `topic`, durable.
- Colas durables: `perfiles.events`, `notificaciones.events`, `vacaciones.empleados`.
- Bindings:
  - `perfiles.events`: `empleado.creado`, `empleado.actualizado`, `empleado.retirado`.
  - `notificaciones.events`: `empleado.creado`, `empleado.retirado`, `vacaciones.programadas`.
  - `vacaciones.empleados`: `empleado.creado`, `empleado.retirado`.
- Inicializador: `Reto_4/rabbitmq/setup.py`; declara exchange, colas y bindings de forma idempotente y reintenta si RabbitMQ aún no está disponible.
- Management UI: `http://localhost:15672` (publicada en `127.0.0.1`). AMQP `5672` solo está expuesto dentro de Docker.
- **Pendiente:** productores, consumidores, ACK/redelivery de aplicación, reconexión de clientes y deduplicación. No hay consumidores suscritos actualmente; las colas y tablas preparadas no prueban entrega ni procesamiento.

## 5. Empleados

Endpoints disponibles por Gateway:

- `POST /empleados`, `GET /empleados`, `GET /empleados/{id}`.
- `PUT /empleados/{id}`.
- `DELETE /empleados/{id}`.
- `GET /health/dependencies`.

`PUT` edita los campos de negocio, valida email, unicidad y departamento, conserva el `id` y no acepta campos adicionales como estado o `fechaRetiro`. Un empleado `RETIRADO` no se puede modificar ni reactivar.

`DELETE` es una baja lógica: asigna `RETIRADO` y una fecha UTC. Un segundo `DELETE` devuelve el estado existente y conserva la misma fecha. `GET /empleados/{id}` sigue encontrándolo. El listado acepta `estado`, `desde` y `hasta`; el rango solo se admite para `RETIRADO`, exige fechas válidas y `desde <= hasta`.

La reconciliación periódica consulta empleados `PENDIENTE` con Departamentos: activa si el departamento ya existe y rechaza si la respuesta confirma que no existe. Las fallas temporales dejan el registro pendiente. No publica eventos porque falta el contrato.

## 6. Perfiles

- Lenguaje: Go; base: PostgreSQL propia.
- Endpoints: `GET /perfiles`, `GET /perfiles/{empleadoId}`, `PUT /perfiles/{empleadoId}`, `/health`, `/perfiles/docs`, `/perfiles/openapi.json`.
- `PUT` solo permite `telefono`, `direccion`, `ciudad` y `biografia`. Rechaza campos protegidos/desconocidos. Si el perfil no existe devuelve 404.
- No hay endpoint REST para crear perfiles: el alta default corresponde al consumidor pendiente de `empleado.creado`.
- Consumidor y deduplicación persistente: **no implementados**. Existe la tabla `eventos_procesados`, pero no se usa para procesar mensajes.

## 7. Notificaciones

- Lenguaje: Java 21 con Spring Boot; base: PostgreSQL propia.
- Endpoints: `GET /notificaciones`, `GET /notificaciones/{empleadoId}`, `/health`, `/notificaciones/docs`, `/notificaciones/openapi.json`.
- Tipos permitidos en el esquema: `BIENVENIDA`, `DESVINCULACION`, `VACACIONES`.
- Consumidor de `empleado.creado`, `empleado.retirado` y `vacaciones.programadas`, generación de historial/logs de esos eventos y deduplicación: **no implementados**. La tabla `eventos_procesados` está preparada, sin lógica conectada.

## 8. Vacaciones

- Lenguaje: .NET 8; base: PostgreSQL propia.
- Endpoints: `POST /vacaciones`, `GET /vacaciones`, `GET /vacaciones/{id}`, `GET /vacaciones?empleadoId={id}`, `DELETE /vacaciones/{id}`, `/health`.
- Rechaza fin igual/anterior al inicio y fechas de inicio pasadas. El empleado debe existir en `empleados_replica` y no estar retirado. Rechaza solapamientos inclusivos (`nuevoInicio <= existenteFin && nuevoFin >= existenteInicio`).
- `DELETE` marca `CANCELADA`; no borra el registro y no deja cancelar periodos ya iniciados o ya cancelados.
- La estrategia implementada es una réplica PostgreSQL local (`empleados_replica`), no una consulta REST. Actualmente no se actualiza sola: depende del consumidor pendiente de `empleado.creado` y `empleado.retirado`. No está implementado el productor de `vacaciones.programadas`; `eventos_procesados` tampoco está conectado a un consumidor.

## 9. Docker

`docker compose -f Reto_4/docker-compose.yml up --build -d` construyó y levantó los servicios el 27-09-2026. Estado comprobado después de reiniciar: doce servicios permanentes healthy y el inicializador transitorio `rabbitmq-setup` terminó con código 0.

Hay un Gateway, cinco servicios de negocio, cinco PostgreSQL, RabbitMQ y el inicializador transitorio. Hay seis redes (una compartida y cinco internas) y seis volúmenes de datos. Los puertos publicados son `127.0.0.1:8080` y `127.0.0.1:15672`; 8081–8085 no se publican al host. Los servicios de aplicación corren como `appuser`, `node` o `app`. Bases de datos y RabbitMQ usan el usuario configurado por sus imágenes oficiales.

La configuración Compose fue validada con `docker compose -f Reto_4/docker-compose.yml config --quiet`.

## 10. Swagger

Comprobado a través de `http://localhost:8080` (siguiendo redirecciones de Swagger UI):

- `http://localhost:8080/perfiles/docs` y `/perfiles/openapi.json` — HTTP 200.
- `http://localhost:8080/notificaciones/docs` y `/notificaciones/openapi.json` — HTTP 200 final.
- `http://localhost:8080/vacaciones/docs` y `/vacaciones/v1/openapi.json` — HTTP 200 final.

## 11. Pruebas

Totales ejecutados en esta revisión; no se cuentan pruebas omitidas. Go y Java se ejecutaron dentro de contenedores de toolchain porque `go` y `mvn` no están instalados en el host.

| Suite | Comando | Aprobadas | Fallidas | Advertencias |
|---|---|---:|---:|---|
| Reto 3 Python | `.\.venv\Scripts\python.exe -m pytest Reto_3/tests -q` | 43 | 0 | 8 deprecaciones de dependencias (`starlette`, `pybreaker`) |
| Reto 3 Node | `npm --prefix Reto_3/departamentos test` | 12 | 0 | 0 |
| Reto 4 Python | `.\.venv\Scripts\python.exe -m pytest Reto_4/tests -q` | 56 | 0 | 8 deprecaciones de dependencias (`starlette`, `pybreaker`) |
| Reto 4 Node | `npm --prefix Reto_4/departamentos test` | 12 | 0 | 0 |
| Perfiles Go | `go mod tidy && go test -count=1 ./...` en `Reto_4/perfiles` | 3 | 0 | 0 |
| Notificaciones Java | `mvn -B -ntp test` en `Reto_4/notificaciones` | 2 | 0 | avisos deprecados de Mockito/agente dinámico; sin fallos |
| Vacaciones .NET | `dotnet test Reto_4/vacaciones.tests/Vacaciones.Tests.csproj --nologo` | 11 | 0 | 0 |

Además, `docker compose up --build` reconstruyó los seis servicios de aplicación sin errores. Los Dockerfiles de Go y Java ejecutan sus pruebas durante el build (`go test ./...` y `mvn package`, respectivamente).

## 12. Prueba funcional

Con Compose levantado se crearon IDs nuevos: un departamento, un empleado activo y una vacación. Se verificaron alta/consulta/actualización del empleado, conservación de identidad, creación/consulta/listado de vacaciones, fin igual al inicio (400), inicio pasado (400), empleado desconocido (400), solapamiento (400), cancelación lógica (`CANCELADA`), consulta posterior, retiro (`RETIRADO`), segundo retiro con fecha idéntica, consulta del retirado y filtros de auditoría/rango. La prueba de solapamiento cubrió el caso coincidente; los siete límites geométricos de periodos están cubiertos por la suite .NET.

Como aún no existe el consumidor de empleados, para probar la ruta REST de vacaciones se insertó manualmente el empleado de prueba en `empleados_replica`; esto **no** representa el E2E por eventos. Perfiles devolvió la lista vacía y 404 para el empleado, como corresponde mientras falte el consumidor que crea el perfil. Notificaciones devolvió listas vacías porque no hay consumidores que generen registros.

## 13. Persistencia

Después de `docker compose restart` y de esperar healthchecks, se confirmó que seguían existiendo el departamento de prueba, el empleado retirado con su `fechaRetiro` UTC, la vacación con estado `CANCELADA` y las tres colas RabbitMQ durables. No había perfil ni notificación asociados a la prueba; tampoco eventos procesados por aplicación, porque no hay consumidores activos.

## 14. Pendientes para terminar el reto

### Pendientes de código

**Bloqueo: no se encontró el Catálogo oficial de Eventos con las secciones 3.1, 3.2, 3.3 y 3.8. No se inventaron versiones ni payloads.**

La búsqueda en el repositorio, carpetas relacionadas de `D:\Repositorios_UQ` y adjuntos disponibles encontró referencias a los nombres de eventos en las instrucciones y en los bindings, pero no el contrato oficial ni sus campos `data`. Por tanto, queda bloqueado únicamente lo que depende de ese contrato:

- publicar los eventos de empleados y vacaciones, incluidos los casos de empleados pendientes, retiro idempotente y reconciliación;
- consumirlos en Perfiles, Notificaciones y Vacaciones para crear/sincronizar/archivar perfiles, generar notificaciones y mantener la réplica local;
- deduplicar por envelope `id`, confirmar ACK/redelivery y reconexión desde consumidores reales;
- ejecutar el E2E de fan-out, redelivery y efecto único.

**E2E asíncrono: NO EJECUTABLE POR FALTA DE CONTRATO OFICIAL.** La topología preparada no equivale a productores o consumidores funcionando.

### Pendientes de documentación

Para el compañero: README académico; justificación de RabbitMQ frente a Kafka/Redis Streams/NATS; tabla servicio-lenguaje; arquitectura final; evidencias de deduplicación cuando exista; guía de demostración; capturas/evidencias; explicación de la estrategia de réplica de Vacaciones; contratos/documentación de eventos oficiales y demás requisitos del profesor.

## 15. Cómo levantar el proyecto

Desde `Reto_4/`, prepara `.env` a partir de `.env.example` y configura credenciales locales. `.env` está excluido por `.gitignore`. Luego ejecuta:

```powershell
docker compose up --build -d --wait --wait-timeout 180
docker compose ps
```

El comando se validó también desde la raíz como `docker compose -f Reto_4/docker-compose.yml up --build -d --wait --wait-timeout 180`.

## 16. Flujo de demostración

Ejemplos para ejecutar desde PowerShell, cambiando los IDs y asegurando que no existan previamente:

```powershell
$base = 'http://localhost:8080'
curl.exe -i -X POST "$base/departamentos" -H 'Content-Type: application/json' -d '{"id":"DEP-DEMO","nombre":"Tecnologia","descripcion":"Departamento de prueba"}'
curl.exe -i -X POST "$base/empleados" -H 'Content-Type: application/json' -d '{"id":"E-DEMO","nombre":"Ana","apellido":"Prueba","email":"ana.demo@empresa.test","numeroEmpleado":"EMP-DEMO","cargo":"Analista","area":"Tecnologia","departamentoId":"DEP-DEMO","fechaIngreso":"2026-09-27","estado":"ACTIVO"}'
curl.exe -i "$base/empleados/E-DEMO"
curl.exe -i -X PUT "$base/empleados/E-DEMO" -H 'Content-Type: application/json' -d '{"nombre":"Ana","apellido":"Prueba","email":"ana.demo@empresa.test","numeroEmpleado":"EMP-DEMO","cargo":"Analista senior","area":"Tecnologia","departamentoId":"DEP-DEMO","fechaIngreso":"2026-09-27"}'
curl.exe -i "$base/perfiles/E-DEMO"
curl.exe -i "$base/notificaciones/E-DEMO"
curl.exe -i -X POST "$base/vacaciones" -H 'Content-Type: application/json' -d '{"id":"V-DEMO","empleadoId":"E-DEMO","fechaInicio":"2026-11-10","fechaFin":"2026-11-15"}'
curl.exe -i "$base/vacaciones?empleadoId=E-DEMO"
curl.exe -i -X DELETE "$base/empleados/E-DEMO"
curl.exe -i "$base/empleados/E-DEMO"
curl.exe -i "$base/empleados?estado=RETIRADO&desde=2026-09-27&hasta=2026-09-27"
```

Las consultas de perfil responderán 404 y las de notificaciones no mostrarán nuevos registros hasta implementar consumidores. El alta de vacaciones solo será exitosa cuando `E-DEMO` exista como activo en `empleados_replica`; hoy esa réplica no se alimenta automáticamente, así que el comando no debe presentarse como flujo E2E funcional. Los servicios de Departamentos ofrecen POST/GET; el Gateway acepta y reenvía métodos HTTP, pero la disponibilidad efectiva depende de cada endpoint de negocio.

## 17. Archivos importantes

- `Reto_4/docker-compose.yml`, `.env.example`.
- `Reto_4/api-gateway/app/`.
- `Reto_4/empleados/app/`, `Reto_4/empleados/init.sql`.
- `Reto_4/departamentos/src/`, `Reto_4/departamentos/init.sql`.
- `Reto_4/perfiles/main.go`, `main_test.go`, `init.sql`.
- `Reto_4/notificaciones/src/`, `pom.xml`, `init.sql`.
- `Reto_4/vacaciones/Program.cs`, `init.sql`; `Reto_4/vacaciones.tests/`.
- `Reto_4/rabbitmq/setup.py`.
- `Reto_4/tests/`, `Reto_4/requirements-test.txt`.

## 18. Recomendación para continuar con Claude

Prompt sugerido:

> Lee `Reto_4/HANDOFF_RETO4.md` antes de modificar el proyecto. Conserva la implementación existente y completa únicamente los pendientes allí descritos, priorizando documentación y cualquier bloqueo resuelto posteriormente. No inventes contratos: si aparece el Catálogo oficial, verifica su versión y payload antes de implementar productores, consumidores y pruebas E2E.
