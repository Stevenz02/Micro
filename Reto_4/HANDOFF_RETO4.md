# Reto 4 — entrega técnica y guía para el compañero

Estado revisado el 29-09-2026 (America/Bogota). Fuente del contrato: `catalogo-de-eventos.pdf`, “Catálogo de Eventos del Ecosistema”, versión 1.0, entregado por el usuario. Este documento describe el código y las verificaciones reales; el PDF es la autoridad para los eventos. Los ejemplos de datos son solo para la demo.

## Estado general

**La parte técnica del Reto 4 está implementada y verificada en Docker.** Los servicios REST, bases independientes, Gateway, topología RabbitMQ, productores, consumidores, deduplicación persistente, Swagger y flujo de extremo a extremo funcionan. Se probaron 145 tests sin fallos. No se hizo commit ni push; los cambios están en la rama local `features/kevin`.

Quedan dos decisiones de negocio por confirmar, sin impedir el funcionamiento actual: de dónde debe venir el `motivo` del retiro y qué calendario define `diasHabiles`. La implementación usa `DELETE /empleados/{id}?motivo=...` y cuenta lunes a viernes, inclusive, sin festivos. El catálogo exige los campos pero no especifica esas dos reglas. Su ejemplo de 15–30 de marzo de 2026 indica 12 días, mientras ese intervalo tiene 11 días de lunes a viernes; por eso no se copió el número del ejemplo como una regla.

## Contrato oficial implementado

Todos los mensajes usan el sobre `{"id":"UUID","type":"...","version":1,"occurredAt":"UTC ISO-8601","producer":"...","data":{...}}`. El identificador `id` del **mensaje** permite la deduplicación; no es el `empleadoId` ni el ID de la vacación. Se publican como JSON persistente en el exchange topic durable `rrhh.events` con routing key igual a `type`.

| Evento | Productor | Campos `data` del catálogo | Efecto actual |
|---|---|---|---|
| `empleado.creado` | empleados-service | `empleadoId,nombre,apellido,email,numeroEmpleado,cargo,area,departamentoId,fechaIngreso,estado` (ACTIVO) | Perfiles crea/sincroniza; Notificaciones registra traza `ALTA`; Vacaciones crea su réplica local |
| `empleado.actualizado` | empleados-service | `empleadoId,nombre,apellido,email,cargo,area,departamentoId` | Perfiles sincroniza solo campos del empleado; Vacaciones actualiza el email de su réplica |
| `empleado.retirado` | empleados-service | `empleadoId,email,fechaRetiro,motivo` | Perfiles archiva; Notificaciones registra traza `RETIRO`; Vacaciones marca la réplica RETIRADO |
| `vacaciones.programadas` | vacaciones-service | `vacacionesId,empleadoId,email,fechaInicio,fechaFin,diasHabiles` | Notificaciones registra confirmación `VACACIONES` |

`auth-service` aparece en el catálogo, pero **no existe en este proyecto hasta el Reto 5**. No se implementó ni se espera como consumidor. El catálogo indica que el correo de bienvenida espera `usuario.creado` y el de despedida `cuenta.desactivada` del Reto 5; los registros `ALTA` y `RETIRO` actuales son trazas, no correos enviados. `vacaciones.empleados` es una proyección interna necesaria para validar vacaciones sin consultar Empleados por REST; no añade un consumidor de negocio del catálogo.

## Implementación por servicio

- **Empleados (Python/FastAPI):** publica `empleado.creado` al confirmar un alta ACTIVO o al activar un PENDIENTE mediante reconciliación; `empleado.actualizado` después de un PUT exitoso; `empleado.retirado` solo en el primer retiro. No publica alta de PENDIENTE/RECHAZADO ni repite retiro en el segundo DELETE. Guarda `motivo_retiro` y conserva la fecha UTC del primer retiro. El primer DELETE requiere `?motivo=...`; las repeticiones idempotentes no lo requieren. Publica después del commit de PostgreSQL, con confirmación del broker y mensaje persistente.
- **Perfiles (Go):** consume `perfiles.events` con ACK manual posterior al commit. Crea el perfil, sincroniza nombre/apellido/email/cargo/área/departamento y archiva al retirar. Respeta los campos propios editables (`telefono,direccion,ciudad,biografia`). El cambio del empleado no los sobrescribe. Migración de columnas para volúmenes preexistentes.
- **Notificaciones (Java/Spring Boot):** consume `notificaciones.events` con ACK manual; guarda una notificación de traza o confirmación por evento y el marcador de `eventos_procesados` en una misma transacción. Los tipos actuales son `ALTA`, `RETIRO` y `VACACIONES`. Hay migración del CHECK del tipo para volúmenes existentes. OpenAPI publica `servers: [{url: "/"}]` para que “Try it out” use el Gateway.
- **Vacaciones (.NET 8):** consume `vacaciones.empleados` con ACK manual para mantener `empleados_replica`, incluido email actualizado y retiro. Una vacación programada se guarda primero y luego publica `vacaciones.programadas` con email de la réplica y días hábiles. La API conserva las validaciones de fechas, solapamiento, empleado activo y cancelación lógica.
- **RabbitMQ:** `rabbitmq/setup.py` declara de forma idempotente exchange, tres colas durables y bindings. `perfiles.events` recibe creado/actualizado/retirado; `notificaciones.events` recibe creado/retirado/vacaciones.programadas; `vacaciones.empleados` recibe creado/actualizado/retirado. El binding de actualizado en Vacaciones mantiene vigente el destinatario de la confirmación.

Los tres consumidores persisten `eventos_procesados(id)` dentro de la misma transacción que el efecto en su BD y hacen ACK después. Una entrega repetida con el mismo `id` no repite el efecto; errores temporales se reencolan y los mensajes inválidos se rechazan. Hay bucles de reconexión para los consumidores. El productor de Empleados registra en logs el fallo de publicación después del commit; el de Vacaciones también publica después del commit. **Aún no hay outbox/replay automático:** si la BD confirma y el broker falla en ese instante, el dato queda guardado pero el evento puede faltar. Esta es la principal limitación de fiabilidad pendiente para endurecimiento posterior, no un fallo del flujo comprobado con RabbitMQ disponible.

## Docker: qué quedó hecho y qué falta

Desde `Reto_4/`, copiar `.env.example` a `.env` y ajustar las credenciales locales antes de levantar. `.env` no se versiona. Comandos:

```powershell
Copy-Item .env.example .env
docker compose config --quiet
docker compose up --build -d --wait --wait-timeout 240
docker compose ps
```

Si ya existe `.env`, conservarlo y ejecutar desde `Reto_4/` solo los comandos `docker compose`. Desde la raíz del repositorio se puede usar `docker compose -f Reto_4/docker-compose.yml ...`.

**Hecho y verificado:** Compose pasa `RABBITMQ_HOST/USER/PASSWORD` a los cuatro servicios que usan eventos; espera a `rabbitmq-setup` antes de iniciarlos. Los Dockerfiles compilan los seis servicios, y los archivos `.dockerignore` reducen los contextos. Se ejecutó `up --build -d --wait --wait-timeout 240`: doce contenedores permanentes healthy; `rabbitmq-setup` finalizó con código 0, como corresponde a su trabajo transitorio. Cinco PostgreSQL y RabbitMQ tienen volúmenes; hay una red compartida y redes de BD internas. Solo están publicados al host `127.0.0.1:8080` (Gateway) y `127.0.0.1:15672` (Management); los puertos de negocio no se publican. Las colas durables mostraron un consumidor cada una, ACK manual y prefetch 1. Reiniciar RabbitMQ mostró reconexión y procesamiento de un alta posterior. Un reinicio completo de Compose conservó empleado, perfil, vacación, notificaciones, colas y marcadores de deduplicación.

**Pendiente de Docker para la entrega:** ninguno que impida levantar o demostrar Reto 4. El compañero debe preparar su propio `.env`, levantar `up --build` en su equipo y capturar las evidencias que pida el profesor. Para una entrega con garantías superiores harían falta outbox/replay, política de mensajes inválidos (DLQ) y monitoreo de consumidores/conexión AMQP; son mejoras futuras. Los healthchecks actuales comprueban la API y/o BD, no demuestran por sí solos que la suscripción AMQP esté activa: en la demo mirar la UI de RabbitMQ o ejecutar el flujo real. No usar `docker compose down -v` si se quieren conservar los datos de prueba.

Los `init.sql` se aplican automáticamente solo cuando se crea un volumen de BD. Para volúmenes ya existentes, las nuevas columnas y el CHECK de Notificaciones se migran al iniciar los servicios; **no hace falta borrar volúmenes**. Empleados antiguos creados antes de esta integración no generan eventos retroactivos y los retiros históricos no tienen `motivo` recuperable. Si se necesita reconstruir ese histórico, requiere una migración/backfill de datos acordada aparte.

## Pruebas y evidencia funcional

| Suite ejecutada | Aprobadas | Fallidas |
|---|---:|---:|
| Reto 3 Python | 43 | 0 |
| Reto 3 Node | 12 | 0 |
| Reto 4 Python | 60 | 0 |
| Reto 4 Node | 12 | 0 |
| Perfiles Go | 4 | 0 |
| Notificaciones Java (build Maven en Docker) | 2 | 0 |
| Vacaciones .NET | 12 | 0 |
| **Total** | **145** | **0** |

Se comprobó además `docker compose config --quiet` y el build de las seis aplicaciones. El E2E real por Gateway creó el departamento `DEP-CAT-1790730785` y el empleado `E-CAT-1790730785`: aparecieron perfil, traza `ALTA` y réplica de Vacaciones sin insertar datos a mano. Una actualización cambió email/apellido/cargo en Perfiles y el email de la réplica, mientras el perfil conservó teléfono y ciudad propios. La vacación `V-CAT-1790730785` produjo una notificación `VACACIONES` al email actualizado. El primer retiro con `motivo=RENUNCIA` archivó perfil, marcó réplica RETIRADO y creó una traza `RETIRO`. El segundo retiro mantuvo la misma `fechaRetiro` y no creó otro efecto.

La deduplicación se comprobó de dos maneras. Primero, dos publicaciones iguales por la API Management de RabbitMQ produjeron un perfil, una traza ALTA y un marcador por BD para `E-DEDUP-1790730952`. Después se abrió la **interfaz web** de RabbitMQ en Edge mediante Playwright y se pulsó dos veces “Publish message” con el mismo payload: `id=85a5a1da-d41b-47aa-8e30-02415a710672`, `empleadoId=E-UI-DEDUP-1790731828`. El resultado verificado por Gateway fue **un perfil y una sola notificación ALTA**; la consulta SQL de `eventos_procesados` para ese `id` devolvió **1 en Perfiles, 1 en Notificaciones y 1 en Vacaciones**. La repetición presencial queda preparada con los pasos de abajo. Después de reiniciar RabbitMQ se creó `E-REC-1790731362` y las tres colas volvieron a procesarlo. Después de reiniciar todo Compose, los datos y marcadores previos persistieron.

Swagger de Notificaciones: `http://localhost:8080/notificaciones/docs` devolvió 200, `/notificaciones/openapi.json` declaró servidor `/` y `/notificaciones/openapi.json/swagger-config` devolvió 200 con URL del contrato bajo el Gateway. En Edge, “Try it out” → “Execute” para `GET /notificaciones` llamó a `http://localhost:8080/notificaciones` y recibió **200 JSON**.

## Demo en vivo desde RabbitMQ Management UI

1. Levantar Compose y abrir `http://localhost:15672`. Entrar con `RABBITMQ_USER` y `RABBITMQ_PASSWORD` de `Reto_4/.env`. En “Queues and Streams” deben verse `perfiles.events`, `notificaciones.events` y `vacaciones.empleados` con un consumidor cada una.
2. Abrir “Exchanges” → `rrhh.events` → “Publish message”. En “Routing key” escribir `empleado.creado`. En “Payload” pegar el JSON siguiente. Si ya se hizo esta prueba antes, cambiar **una vez** tanto `id` como `empleadoId`, email y `numeroEmpleado`, y luego reutilizar exactamente ese mismo JSON en ambos envíos. Elegir payload como texto/JSON; las propiedades opcionales pueden quedar vacías.
3. Pulsar “Publish message” **dos veces sin modificar ni un carácter del JSON**. La UI debe indicar que el exchange lo enrutó a las colas correspondientes.
4. Consultar `http://localhost:8080/perfiles/E-DEMO-DUP-01` y `http://localhost:8080/notificaciones/E-DEMO-DUP-01`. Debe existir **un perfil** y **una sola notificación ALTA**. Consultar otra vez tras unos segundos; los conteos no aumentan. En la base de Perfiles, Notificaciones y Vacaciones, `SELECT COUNT(*) FROM eventos_procesados WHERE id='9f6d58b2-e26d-4c3b-a8ee-8808026f68aa';` debe dar 1 en cada una. Si se cambiaron los IDs del JSON, usar el nuevo `id` en la consulta.
5. Esta publicación sintética prueba los consumidores; no inserta un registro en Empleados. Para mostrar el flujo productor real, crear primero un departamento y luego un empleado por el Gateway, consultar perfil/notificaciones, actualizarlo, programar vacaciones y retirarlo con `?motivo=RENUNCIA`.

```json
{
  "id": "9f6d58b2-e26d-4c3b-a8ee-8808026f68aa",
  "type": "empleado.creado",
  "version": 1,
  "occurredAt": "2026-09-29T18:00:00.000Z",
  "producer": "empleados-service",
  "data": {
    "empleadoId": "E-DEMO-DUP-01",
    "nombre": "Ana",
    "apellido": "Demo",
    "email": "ana.demo.duplicado@empresa.test",
    "numeroEmpleado": "EMP-DEMO-DUP-01",
    "cargo": "Analista",
    "area": "Tecnologia",
    "departamentoId": "DEP-DEMO-DUP-01",
    "fechaIngreso": "2026-09-29",
    "estado": "ACTIVO"
  }
}
```

Para una prueba completa con APIs, usar IDs nuevos y este orden: `POST /departamentos` → `POST /empleados` (ACTIVO) → `GET /perfiles/{id}` y `GET /notificaciones/{id}` → `PUT /perfiles/{id}` con teléfono/ciudad → `PUT /empleados/{id}` con cambios de email/cargo → `POST /vacaciones` con fechas futuras → `DELETE /empleados/{id}?motivo=RENUNCIA`. Esperar unos segundos entre escritura y lectura porque los consumidores son asíncronos. Antes de retirar, verificar que la confirmación de Vacaciones llegó al email actualizado; después, que Perfiles quedó archivado. Repetir el DELETE para comprobar idempotencia.

## Tareas del compañero y límites del alcance

Al compañero le queda preparar el README/entrega académica: arquitectura y tabla de lenguajes, justificación de RabbitMQ frente a las alternativas, diagrama de flujo, referencia al catálogo, evidencia de Docker healthy y de la demo de duplicado desde la **UI**, capturas solicitadas por el profesor y explicación de la réplica local de Vacaciones. Debe mencionar las dos decisiones de negocio pendientes de confirmar (`motivo` y `diasHabiles`) y la limitación de publicación post-commit sin outbox. Si el profesor pide demostrar “Try it out”, abrir `/notificaciones/docs` por el Gateway y ejecutar un GET desde el navegador.

No implementar `auth-service`, `usuario.creado` ni `cuenta.desactivada` en Reto 4; corresponden a Reto 5. No presentar `ALTA` o `RETIRO` como correos enviados. El código y esta documentación quedan locales en `features/kevin` hasta que Kevin decida versionarlos/subirlos.
