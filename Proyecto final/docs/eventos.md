# Eventos implementados

El contrato normativo es el [Catálogo de Eventos](catalogo-de-eventos.md); esta página resume
lo que el sistema implementa. **En caso de discrepancia prevalece el catálogo.**

- **Broker**: RabbitMQ, exchange `rrhh.events` (topic, durable). La *routing key* es el tipo del evento.
- **Topología**: la declara `microservicios/rabbitmq/setup.py` al arrancar (idempotente).

## Envelope

```json
{
  "id": "3f9b2c10-8e4a-4d6b-9f21-7c0a5d8e1234",
  "type": "empleado.creado",
  "version": 1,
  "occurredAt": "2026-11-12T14:32:05.000Z",
  "producer": "empleados-service",
  "data": { }
}
```

Los consumidores validan `type`, `version`, `producer` y `occurredAt` (UTC); un mensaje fuera de
contrato se rechaza sin reencolar.

## Eventos, productores y consumidores

| Evento | Publicado por | Consumido por |
|---|---|---|
| `empleado.creado` | Empleados | Autenticación, Perfiles, Notificaciones, Vacaciones¹ |
| `empleado.actualizado` | Empleados | Perfiles, Vacaciones¹ |
| `empleado.retirado` | Empleados | Autenticación, Perfiles, Notificaciones, Vacaciones¹ |
| `usuario.creado` | Autenticación | Notificaciones (correo de bienvenida con el token de activación) |
| `usuario.recuperacion` | Autenticación | Notificaciones (correo con el token de recuperación) |
| `cuenta.activada` | Autenticación | Notificaciones |
| `cuenta.desactivada` | Autenticación | Notificaciones |
| `vacaciones.programadas` | Vacaciones | Notificaciones (confirmación del período) |
| `vacaciones.iniciadas` | Vacaciones (scheduler) | Autenticación, Notificaciones, Empleados² |
| `vacaciones.finalizadas` | Vacaciones (scheduler) | Autenticación, Notificaciones, Empleados² |

¹ Vacaciones mantiene una réplica local mínima del empleado (estado y email) para validar
"empleado existente" sin llamadas síncronas.

² Consumidor adicional respecto al resumen del enunciado: Empleados refleja el estado
`EN_VACACIONES` / `ACTIVO` exigido en su modelo. No cambia ningún evento ni carga útil; solo
agrega una cola (`empleados.vacaciones`) a eventos que ya existían.

## Colas

| Cola | Servicio | Routing keys |
|---|---|---|
| `auth.events` | Autenticación | `empleado.creado`, `empleado.retirado`, `vacaciones.iniciadas`, `vacaciones.finalizadas` |
| `perfiles.events` | Perfiles | `empleado.creado`, `empleado.actualizado`, `empleado.retirado` |
| `notificaciones.events` | Notificaciones | los nueve eventos que generan notificación |
| `vacaciones.empleados` | Vacaciones | `empleado.creado`, `empleado.actualizado`, `empleado.retirado` |
| `empleados.vacaciones` | Empleados | `vacaciones.iniciadas`, `vacaciones.finalizadas` |

## Deduplicación (obligatoria)

Cada consumidor guarda el `id` del envelope en su tabla `eventos_procesados` **dentro de la misma
transacción** que aplica el efecto (`INSERT ... ON CONFLICT DO NOTHING`). Una reentrega, o la
segunda réplica de un servicio escalado, encuentra el `id` y no repite el efecto: no se crea otra
cuenta, otra notificación ni otro correo.

## Ciclo de vida de la cuenta

| Evento recibido por Autenticación | Transición | Evento publicado |
|---|---|---|
| `empleado.creado` | crea la cuenta `INACTIVA`, sin contraseña, con token de activación | `usuario.creado` |
| (el empleado usa el token) | `INACTIVA → ACTIVA` | `cuenta.activada` (`ACTIVACION_INICIAL`) |
| `vacaciones.iniciadas` | `ACTIVA → SUSPENDIDA_TEMPORAL` | `cuenta.desactivada` (`VACACIONES`, `permanente: false`) |
| `vacaciones.finalizadas` | `SUSPENDIDA_TEMPORAL → ACTIVA` | `cuenta.activada` (`FIN_VACACIONES`) |
| `empleado.retirado` | cualquier estado → `DESACTIVADA_PERMANENTE` | `cuenta.desactivada` (`RETIRO`, `permanente: true`) |

Una cuenta `DESACTIVADA_PERMANENTE` nunca se reactiva, aunque después llegue `vacaciones.finalizadas`.

## Trazabilidad

El productor inyecta `traceparent` (W3C Trace Context) en las cabeceras AMQP y cada consumidor
abre un span hijo, por lo que la cascada completa del onboarding se ve como una sola traza en Zipkin.
