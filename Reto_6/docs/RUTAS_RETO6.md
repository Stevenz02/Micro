# Rutas reales disponibles desde el Gateway

Inventario contrastado con el código de Reto 4/5 y `GET http://localhost:8080/openapi.json` del 15 de octubre de 2026. El OpenAPI consolidado muestra **24 operaciones** de salud y negocio. Todas se invocan en `http://localhost:8080`. No se cuentan como rutas de negocio los comodines internos del proxy: una combinación sin handler en el servicio responde `404` o, si el Gateway la bloquea antes, `403`.

**Regla común de seguridad.** Salvo salud, documentación, login, recuperación y reset, se exige `Authorization: Bearer <JWT>`; su ausencia, formato inválido, firma incorrecta, expiración o claims incorrectos dan `401`. El Gateway permite lecturas GET a ADMIN y USER; las mutaciones son de ADMIN, salvo `PUT /perfiles/{empleadoId}` sobre el propio ID y `POST /auth/change-password` del titular. Un permiso insuficiente da `403`. Las operaciones proxy pueden dar `503` si el servicio no responde. Los `500` de persistencia se documentan solo donde el servicio los implementa; no son un objetivo artificial de demostración.

| Método | Ruta | Servicio | Autenticación | Rol requerido | Request | Respuesta exitosa | Errores posibles | Efectos/eventos |
|---|---|---|---|---|---|---|---|---|
| GET | `/health` | Gateway | Pública | — | Ninguno | `200` estado del Gateway | — | Ninguno |
| GET | `/health/dependencies` | Gateway → Empleados | JWT | ADMIN/USER | Ninguno | `200` dependencias | `401`, `503`, `500` | Ninguno |
| POST | `/auth/login` | Auth | Pública | — | `email`, `password` | `200` `access_token`, `token_type`, `expires_in` | `401` credenciales/cuenta no activa; `422`, `503` | Emite JWT, no evento |
| POST | `/auth/recover-password` | Auth | Pública | — | `email` | `202` mensaje genérico | `422`, `503` | `usuario.recuperacion` solo si existe cuenta no retirada; no revela existencia |
| POST | `/auth/reset-password` | Auth | Pública | — | `token`, `newPassword` | `200` detalle de contraseña establecida | `400` token o clave inválidos; `422`, `503` | Primera activación: `cuenta.activada` |
| POST | `/auth/change-password` | Auth | JWT | Titular ADMIN/USER | `currentPassword`, `newPassword` | `200` detalle | `400`, `401`, `409`, `422`, `503` | Incrementa versión de credencial; no evento |
| POST | `/empleados` | Empleados | JWT | ADMIN | Modelo `Empleado` completo | `201` empleado ACTIVO; `202` PENDIENTE si falla Departamentos | `400` duplicado/departamento; `401`, `403`, `422`, `500`, `503` | Con `201`: `empleado.creado` |
| GET | `/empleados` | Empleados | JWT | ADMIN/USER | Filtros opcionales `estado`; `desde`/`hasta` solo con `RETIRADO` | `200` lista | `400` combinación/rango inválido; `401`, `422`, `500`, `503` | Ninguno; `estado=RETIRADO` sirve para auditoría |
| GET | `/empleados/{id}` | Empleados | JWT | ADMIN/USER | ID en ruta | `200` empleado, incluso RETIRADO | `401`, `404`, `500`, `503` | Ninguno |
| PUT | `/empleados/{id}` | Empleados | JWT | ADMIN | `EmpleadoActualizacion` sin ID ni estado | `200` empleado | `400` retirado/duplicado/departamento; `401`, `403`, `404`, `422`, `500`, `503` | `empleado.actualizado` |
| DELETE | `/empleados/{id}` | Empleados | JWT | ADMIN | `motivo` en query para primer retiro | `200` empleado RETIRADO | `400` motivo ausente; `401`, `403`, `404`, `500`, `503` | Primer retiro: `empleado.retirado`; repetición idempotente |
| POST | `/departamentos` | Departamentos | JWT | ADMIN | `id`, `nombre`, `descripcion` | `201` departamento | `400` entrada o ID duplicado; `401`, `403`, `413`, `500`, `503` | Ninguno |
| GET | `/departamentos` | Departamentos | JWT | ADMIN/USER | Ninguno | `200` lista | `401`, `500`, `503` | Ninguno |
| GET | `/departamentos/{id}` | Departamentos | JWT | ADMIN/USER | ID en ruta | `200` departamento | `401`, `404`, `500`, `503` | Ninguno |
| GET | `/perfiles` | Perfiles | JWT | ADMIN/USER | Ninguno | `200` lista | `401`, `503` | Ninguno |
| GET | `/perfiles/{empleadoId}` | Perfiles | JWT | ADMIN/USER | ID en ruta | `200` perfil | `401`, `404`, `503` | Proyección creada/actualizada por eventos de Empleados |
| PUT | `/perfiles/{empleadoId}` | Perfiles | JWT | ADMIN o USER dueño | `telefono`, `direccion`, `ciudad`, `biografia` opcionales | `200` perfil | `400` entrada; `401`, `403` otro perfil; `404`, `503` | Actualiza perfil local |
| GET | `/notificaciones` | Notificaciones | JWT | ADMIN/USER | Ninguno | `200` lista | `401`, `503` | Lee historial de eventos procesados |
| GET | `/notificaciones/{empleadoId}` | Notificaciones | JWT | ADMIN/USER | ID en ruta | `200` lista del empleado | `401`, `503` | Ninguno |
| GET | `/notificaciones/seguridad/{id}/token` | Notificaciones | JWT | ADMIN | UUID de notificación de seguridad | `200` `token` simulado vigente | `401`, `403`, `404`, `503` | Permite activación/recuperación en demo; no expone contraseña |
| POST | `/vacaciones` | Vacaciones | JWT | ADMIN | `id` opcional, `empleadoId`, `fechaInicio`, `fechaFin` ISO | `201` período PROGRAMADA | `400` fecha, empleado, solapamiento o ID duplicada; `401`, `403`, `503` | `vacaciones.programadas` |
| GET | `/vacaciones` | Vacaciones | JWT | ADMIN/USER | `empleadoId` opcional | `200` lista | `401`, `503` | Ninguno |
| GET | `/vacaciones/{id}` | Vacaciones | JWT | ADMIN/USER | ID en ruta | `200` período | `401`, `404`, `503` | Ninguno |
| DELETE | `/vacaciones/{id}` | Vacaciones | JWT | ADMIN | ID en ruta | `200` período CANCELADA | `400` iniciada/ya cancelada; `401`, `403`, `404`, `503` | No hay evento de cancelación en el catálogo |

El `422` procede de la validación FastAPI en Auth/Empleados. Departamentos usa `400` para su validación propia. Vacaciones usa `400` en sus reglas de dominio; la validación del JSON por ASP.NET puede responder `400` antes del handler. El Gateway devuelve `503` para errores de transporte al upstream. El `500` no se fuerza en la sustentación; corresponde a fallos internos o de persistencia. **Solapamiento no devuelve `409` en esta implementación.**

## Documentación accesible por el Gateway

| Método | Ruta | Acceso | Contenido |
|---|---|---|---|
| GET | `/docs`, `/redoc`, `/openapi.json` | Público | Swagger, ReDoc y OpenAPI consolidado |
| GET | `/auth/docs`, `/auth/openapi.json` | Público | Contrato individual Auth |
| GET | `/empleados/docs`, `/empleados/openapi.json` | Público | Contrato individual Empleados |
| GET | `/departamentos/docs`, `/departamentos/openapi.json` | Público | Contrato individual Departamentos |
| GET | `/perfiles/docs`, `/perfiles/openapi.json` | Público | Contrato individual Perfiles |
| GET | `/notificaciones/docs`, `/notificaciones/openapi.json` | Público | Contrato individual Notificaciones |
| GET | `/vacaciones/docs`, `/vacaciones/v1/openapi.json` | Público | Contrato individual Vacaciones |

No existen rutas HTTP para consultar cuentas Auth, buscar empleado individual por email o número, actualizar/eliminar departamentos, consultar `/perfiles/me`, archivar perfil manualmente ni disparar el scheduler. El retiro de perfil ocurre por `empleado.retirado`.

## Catálogo de eventos verificado

Todos los mensajes llevan `id` UUID, `type`, `version: 1`, `occurredAt` UTC, `producer` y `data`. `id` se usa para deduplicación en consumidores con tabla de eventos procesados. No se transportan contraseñas; `usuario.creado` y `usuario.recuperacion` contienen tokens de un solo uso para la simulación de entrega.

| Evento | Productor | Consumidores | `data` principal |
|---|---|---|---|
| `empleado.creado` | Empleados | Auth, Perfiles, Vacaciones, Notificaciones | `empleadoId`, identidad, departamento, ingreso, `estado` |
| `empleado.actualizado` | Empleados | Perfiles, Vacaciones | `empleadoId`, identidad y datos de cargo/área/departamento |
| `empleado.retirado` | Empleados | Auth, Perfiles, Vacaciones, Notificaciones | `empleadoId`, `email`, `fechaRetiro`, `motivo` |
| `usuario.creado` | Auth | Notificaciones | `empleadoId`, `email`, `tokenActivacion`, `expiraEn` |
| `usuario.recuperacion` | Auth | Notificaciones | `email`, `tokenRecuperacion`, `expiraEn` |
| `cuenta.activada` | Auth | Notificaciones | `empleadoId`, `email`, `motivo` |
| `cuenta.desactivada` | Auth | Notificaciones | `empleadoId`, `email`, `motivo`, `permanente` |
| `vacaciones.programadas` | Vacaciones | Notificaciones | `vacacionesId`, `empleadoId`, `email`, fechas, `diasHabiles` |
| `vacaciones.iniciadas` | Vacaciones | Auth, Notificaciones | `vacacionesId`, `empleadoId`, `email`, fechas |
| `vacaciones.finalizadas` | Vacaciones | Auth, Notificaciones | `vacacionesId`, `empleadoId`, `email`, `fechaFin` |

No son contratos válidos `empleado.eliminado`, `cuenta.desactivada.permanente`, `crear.empleado` ni `empleado.crear`.
