# Guía: correo y plantillas de notificación

Notificaciones envía correo real por SMTP. En el Compose el servidor es **Mailpit**, que recibe
todo y lo muestra en <http://localhost:8025> sin entregarlo fuera.

## Qué correos se envían

| Evento | Plantilla | Contenido |
|---|---|---|
| `usuario.creado` | `usuario.creado.txt` | Bienvenida con el **token de activación** (nunca una contraseña) |
| `usuario.recuperacion` | `usuario.recuperacion.txt` | Token de recuperación |
| `vacaciones.programadas` | `vacaciones.programadas.txt` | Confirmación del período |
| `cuenta.desactivada` | `cuenta.desactivada.VACACIONES.txt` / `.RETIRO.txt` | Suspensión temporal o baja permanente |
| `cuenta.activada` | `cuenta.activada.ACTIVACION_INICIAL.txt` / `.FIN_VACACIONES.txt` | Activación o regreso |

Todos los eventos quedan además en el historial (`GET /notificaciones/{empleadoId}`).

## Plantillas configurables

Están en `microservicios/notificaciones/plantillas/` y se montan como volumen: se editan sin
recompilar ni reiniciar. Formato y marcadores disponibles en el
[README de la carpeta](../../microservicios/notificaciones/plantillas/README.md).

## Usar un servidor SMTP real

Cambie `SMTP_HOST` y `SMTP_PORT` del servicio `notificaciones-service` en `docker-compose.yml`
(y agregue las credenciales como un secreto más). El remitente es `NOTIFICACIONES_REMITENTE` en `.env`.

Si el servidor SMTP no responde, el evento se procesa igual: la notificación queda registrada y
la métrica `notificaciones_enviadas_total{correo="solo_registro"}` lo refleja.
