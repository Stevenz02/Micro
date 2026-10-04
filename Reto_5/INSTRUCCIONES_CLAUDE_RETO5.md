# Integración Docker del Reto 5: instrucciones para el compañero

Este archivo es una guía de despliegue. La lógica de aplicación está en el repositorio; los archivos Docker y la topología RabbitMQ **no fueron editados ni ejecutados por Codex**. El Catálogo oficial de Eventos versión 1.0 apareció en `C:\Users\Usuario\Desktop\catalogo-de-eventos.pdf` y se verificaron sus secciones 2 y 3.1–3.10. No hace falta redefinir eventos en Docker.

## Código que debes integrar

| Servicio | Código de aplicación | Dependencia de despliegue |
|---|---|---|
| Auth nuevo | `Reto_5/auth/auth_app`, `Reto_5/auth/requirements.txt` | PostgreSQL exclusivo, RabbitMQ y paquete `Reto_5/shared`. |
| Gateway nuevo | `Reto_5/api-gateway/gateway_app`, `Reto_5/api-gateway/requirements.txt` | Paquete `Reto_5/shared`, secreto JWT igual al de Auth y URL interna de Auth. |
| Notificaciones ampliado | `Reto_5/notificaciones` | Reemplaza su código del Reto 4; misma base, nuevas columnas y bindings. |
| Vacaciones con scheduler | `Reto_5/vacaciones` | Reemplaza su código del Reto 4; misma base, scheduler y bindings. |
| Empleados, Departamentos, Perfiles | `Reto_4/empleados`, `Reto_4/departamentos`, `Reto_4/perfiles` | Reutilizar sin cambios de lógica. |

El Gateway usa `gateway_app.main:app` y Auth `auth_app.main:app`. Ambos importan `shared.tokens`, por lo que cada imagen debe incluir `Reto_5/shared` en el `PYTHONPATH`. No supongas que copiar solo la subcarpeta de cada aplicación basta. `Reto_5/notificaciones` no contiene `application.properties`: es configuración de puertos y conexiones que queda bajo tu responsabilidad. Puedes incorporar el archivo existente `Reto_4/notificaciones/src/main/resources/application.properties` al empaquetado o definir propiedades Spring equivalentes en tu despliegue. Conserva el puerto interno 8084, las rutas `/notificaciones/docs`, `/notificaciones/openapi.json` y `/health`, JDBC, AMQP con ACK manual y prefetch 1.

## Topología y puertos confirmados

En `Reto_4/docker-compose.yml` constan Gateway 8080, Empleados 8081, Departamentos 8082, Perfiles 8083, Notificaciones 8084 y **Vacaciones 8085**. El dibujo de `reto5.pdf` asigna también 8085 a Auth. El código nuevo de Auth no fija puerto: **elige uno libre para su proceso y configura `AUTH_URL=http://auth-service:<puerto_elegido>` en el Gateway**. Mantén coherente ese puerto en la escucha Uvicorn, red interna y healthcheck. No publiques directamente al host Auth ni los cinco servicios de negocio; solo el Gateway debe ser la entrada HTTP de negocio. La UI de RabbitMQ puede conservar su acceso local de administración según el Reto 4.

El Reto 4 tiene cinco PostgreSQL propios, un exchange topic durable `rrhh.events`, colas `perfiles.events`, `notificaciones.events` y `vacaciones.empleados`, y un servicio transitorio `rabbitmq-setup` que declara la topología. Agrega una **sexta base exclusiva de Auth** y una cola durable `auth.events` con bindings:

```text
auth.events ← empleado.creado, empleado.retirado,
              vacaciones.iniciadas, vacaciones.finalizadas
```

Conserva los bindings anteriores de `notificaciones.events` y añade `usuario.creado`, `usuario.recuperacion`, `cuenta.activada`, `cuenta.desactivada`, `vacaciones.iniciadas` y `vacaciones.finalizadas`. Esa cola recibirá los tres tipos anteriores y seis adicionales. El archivo `Reto_4/rabbitmq/setup.py` define actualmente la topología; actualizarlo o crear su equivalente del Reto 5 es **tu tarea de orquestación**. Auth, Notificaciones y Vacaciones deben iniciar después de que RabbitMQ esté saludable y la configuración de colas haya terminado. Perfiles y Empleados conservan su dependencia de broker.

## Variables de entorno exactas

| Servicio | Variable | Propósito y valor de aplicación |
|---|---|---|
| Auth y Gateway | `JWT_SECRET` | Requerida, **mismo valor** en ambos, mínimo 32 bytes UTF-8. Mantener en configuración local no versionada; no escribir el valor real en README ni en esta guía. |
| Auth | `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Requeridas para su PostgreSQL exclusivo. |
| Auth | `DB_PORT` | Opcional; predeterminado 5432. |
| Auth | `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | Requeridas para `auth.events` y publicación en `rrhh.events`. |
| Auth | `JWT_ACCESS_TTL_SECONDS` | Opcional; predeterminado 900, rango 60–3600. |
| Auth | `JWT_RESET_TTL_SECONDS` | Opcional; predeterminado 1800, rango 900–3600. |
| Auth | `ADMIN_EMPLOYEE_ID`, `ADMIN_EMAIL`, `ADMIN_PASSWORD_HASH` | Grupo opcional, necesario para la demo inicial. Generar el hash bcrypt con `python Reto_5/auth/hash_admin.py`; no fijar contraseña por defecto. |
| Gateway | `AUTH_URL` | Requerida, URL interna HTTP con el puerto elegido para Auth. |
| Gateway | `EMPLEADOS_URL`, `DEPARTAMENTOS_URL`, `PERFILES_URL`, `NOTIFICACIONES_URL`, `VACACIONES_URL` | Opcionales con defaults de nombres y puertos del Reto 4; confirmar coincidencia con Compose. |
| Gateway | `GATEWAY_REQUEST_TIMEOUT_SECONDS` | Opcional, predeterminado 20, rango mayor que 0 y hasta 60. |
| Vacaciones | `VACACIONES_SCHEDULER_INTERVAL_SECONDS` | Opcional, predeterminado 60, rango 1–3600. |
| Notificaciones y Vacaciones | `DB_*`, `RABBITMQ_HOST`, `RABBITMQ_USER`, `RABBITMQ_PASSWORD` | Conservan las variables de conexión del Reto 4 y sus bases independientes. |

Auth crea las tablas `cuentas` y `eventos_procesados` al iniciar. Los `init.sql` de `Reto_5/notificaciones` y `Reto_5/vacaciones` reflejan el esquema nuevo para volúmenes vacíos; los servicios también ejecutan migraciones al iniciar para volúmenes existentes. Usa esos archivos en la configuración nueva y conserva los volúmenes existentes durante la demo. Vacaciones actualiza su CHECK para admitir un período de un día; Notificaciones agrega `token_entrega`, `token_expira_en`, permite `empleado_id` nulo y amplía los tipos admitidos.

Las rutas de salud verificadas en código son `GET /health` para Auth, Gateway y Vacaciones; Notificaciones expone `/health` de Actuator cuando se reutiliza la configuración del Reto 4 indicada arriba. El `/health` de Auth toca PostgreSQL; el del Gateway solo verifica su proceso. Definir healthchecks y condiciones de arranque en Compose es tu responsabilidad. Los healthchecks HTTP no garantizan por sí solos que haya consumidores AMQP conectados; revisar la UI de RabbitMQ y el flujo real.

## Pruebas locales ejecutadas por Codex

```powershell
.venv\Scripts\python.exe -m pytest Reto_5\tests -q
dotnet test Reto_5\vacaciones.tests\Vacaciones.Tests.csproj --nologo
```

Python: **31 aprobadas**. .NET: **16 aprobadas**. Notificaciones: **8 aprobadas** con Maven 3.9.11, JDK 25 y `mvn test -q -DargLine=-Dnet.bytebuddy.experimental=true`. Con JDK 21, ejecutar `mvn test` desde `Reto_5/notificaciones`. Se probaron contratos de eventos por servicio, estados, el caso borde de retiro durante vacaciones, scheduler de un día, deduplicación, seguridad del token de entrega y RBAC del Gateway. **No se hizo una ejecución integrada con PostgreSQL/RabbitMQ ni se lanzó Docker.**

## Flujo de comprobación integrado que te corresponde

1. Crear la configuración Compose del Reto 5, los Dockerfiles necesarios y la topología de RabbitMQ. Verificar con `docker compose config --quiet`; construir y levantar con `docker compose up --build -d --wait`; revisar `docker compose ps`. Esos comandos están documentados para tu trabajo y no fueron ejecutados por Codex.
2. Confirmar que el Gateway tiene acceso a Auth y a los cinco servicios, que Auth usa su propia base, que el `JWT_SECRET` coincide, y que solo el Gateway ofrece las APIs de negocio al host. En RabbitMQ deben verse los nuevos bindings y un consumidor en `auth.events`.
3. Generar y configurar el hash del ADMIN, iniciar sesión por `POST /auth/login`, verificar `GET /empleados` sin token → `401`, con Bearer válido → `200`, `USER` que borra un empleado → `403`, y propiedad de `PUT /perfiles/E001` frente a `E002`.
4. Como ADMIN, crear departamento y empleado. Verificar `empleado.creado` → cuenta `INACTIVA` → `usuario.creado` → notificación `SEGURIDAD`. El UUID de la notificación es el ID del evento; obtener su token vigente con `GET /notificaciones/seguridad/{id}/token` usando Bearer ADMIN. Restablecer contraseña en `POST /auth/reset-password` e iniciar sesión como USER. El token no aparece en listados normales.
5. Probar recuperación y cambio de contraseña. `POST /auth/recover-password` debe responder igual para emails existentes e inexistentes; para la cuenta real debe crear `usuario.recuperacion`. Obtener su token con el endpoint ADMIN de notificaciones, restablecer, y comprobar que la contraseña anterior ya no sirve. Probar `/auth/change-password` como USER con su contraseña actual.
6. Programar vacaciones de un día (`fechaInicio=fechaFin=hoy`) con ADMIN. En un ciclo el scheduler las inicia y Auth suspende la cuenta; el login falla. En el ciclo siguiente se finalizan y Auth reactiva la cuenta; el login vuelve a funcionar. Verificar `vacaciones.programadas`, `vacaciones.iniciadas`, `vacaciones.finalizadas` y las notificaciones respectivas.
7. Para el caso borde, iniciar vacaciones de E002, retirarlo como ADMIN mientras están `EN_CURSO` y esperar el fin. `vacaciones.finalizadas` debe llegar a Auth sin reactivar la cuenta; el login sigue fallando. Consultar `GET /empleados?estado=RETIRADO` y confirmar `fechaRetiro`.
8. Repetir un mismo evento UUID para verificar marcadores de deduplicación; reiniciar RabbitMQ y luego los servicios para comprobar reconexión y persistencia. Guardar los resultados y capturas reales exigidos por el curso.

## Límites conocidos para la entrega

Auth y Vacaciones publican después del commit de sus bases. Si RabbitMQ falla en ese instante, un cambio confirmado puede quedarse sin evento; no se implementó outbox/replay automático. Los access tokens existentes pueden seguir pasando el Gateway hasta expirar aun después de una suspensión o retiro; Auth sí bloquea nuevos logins. El endpoint ADMIN de token de entrega es solo para la simulación académica y depende de que Notificaciones no sea accesible directamente desde el host. No hay coordinación distribuida del scheduler entre réplicas; la actualización SQL condicional limita transiciones repetidas, pero el job corre en cada instancia. Estas limitaciones deben mencionarse al presentar la evidencia.

El catálogo v1 no incluye Auth entre los consumidores de `empleado.actualizado`. Si cambia el email del empleado, Auth seguirá reconociendo el email anterior para login/recuperación hasta que se acuerde una extensión del contrato o un identificador de login diferente. Es una decisión de contrato pendiente, no una variable de Docker.
