<!-- Pagina 1 de 10 -->

# **Catálogo de Eventos del Ecosistema**

**Documento normativo.** Este catálogo es la **única fuente de verdad** sobre los nombres, productores, consumidores y estructura de los eventos del ecosistema. El enunciado del proyecto

final y los talleres (retos) lo referencian; **ninguno de ellos redefine eventos por su cuenta** . Si un reto necesita un evento nuevo, se agrega aquí primero.

## **1. Convención de nomenclatura**

```
<entidad>.<acción-en-pasado>
```

- **Minúsculas** , separadas por punto. Sin acentos, sin guiones, sin `camelCase` .

- El verbo va **siempre en pasado** : el evento describe algo que **ya ocurrió** y por lo tanto es

- un hecho inmutable. No existen eventos como `crear.empleado` o `empleado.crear` .

- La entidad es el sustantivo del dominio que cambió de estado ( `empleado` , `usuario` , `cuenta` , `vacaciones` ).

**Nota sobre el Reto 00 (DDD).** En el modelado conceptual del Event Storming los eventos se escriben en `PascalCase` ( `EmpleadoCreado` ), que es la convención de DDD para _domain events_ . Al implementarlos como mensajes en el broker se traducen a esta convención de canal: `EmpleadoCreado` → `empleado.creado` . Son el mismo evento en dos capas distintas.

## **2. Sobre técnico del mensaje (envelope)**

Todo evento publicado al broker debe ir envuelto en la siguiente estructura. Los datos propios del evento van dentro de `data` ; el resto son metadatos comunes a todos los eventos.

---

<!-- Pagina 2 de 10 -->

```
{
"id":"3f9b2c10-8e4a-4d6b-9f21-7c0a5d8e1234",
"type":"empleado.creado",
"version":1,
"occurredAt":"2026-03-01T14:32:05Z",
"producer":"empleados-service",
"data":{
"...":"carga útil específica del evento"
}
}
```

|**Campo**|**Obligatorio**|**Descripción**|
|---|---|---|
|`id`|✅|Identificador único del**mensaje**(UUID). No es el id de la entidad.|
|`type`|✅|Nombre del evento, tal como aparece en la tabla de la sección 3.|
|`version`|✅|Versión del esquema del evento. Empieza en<br>`1`.|
|`occurredAt`|✅|Instante en que ocurrió el hecho, en UTC (ISO-8601).|
|`producer`|✅|Nombre del microservicio que lo publicó.|
|`data`|✅|Carga útil. Su estructura se define por evento en la sección 3.|


### **2.1 Deduplicación**

El campo `id` existe para que **todo consumidor pueda tolerar recibir el mismo evento más de una**

**vez** . Un broker puede reentregar un mensaje si el consumidor se cae antes de confirmarlo, y el propio productor puede reintentar una publicación fallida.

Regla mínima exigida desde el **Reto 04** : antes de procesar un evento, el consumidor verifica si ya procesó ese `id` ; si es así, lo descarta y confirma el mensaje sin repetir el efecto. Una tabla `eventos_procesados(id, procesadoEn)` es suficiente en esta etapa.

El mecanismo formal (Inbox Pattern, DLQ, reintento con backoff exponencial) se estudia en el **Reto 29 – Idempotencia y Mensajería Confiable** . Lo que se pide aquí es la versión mínima que evita el bug más común del proyecto: correos de bienvenida duplicados y cuentas reactivadas indebidamente.

---

<!-- Pagina 3 de 10 -->

### **2.2 Datos sensibles**

**Ningún evento transporta contraseñas, ni en texto plano ni hasheadas.** Cuando hay que transmitir un credencial de un solo uso (activación o recuperación de contraseña), se transporta un **token con expiración** , nunca la contraseña. Ver `usuario.creado` y `usuario.recuperacion` .

## **3. Catálogo**

|**Evento**|**Productor**|**Consumidores**|**Se**<br>**introduce**<br>**en**|
|---|---|---|---|
|`empleado.creado`|`empleados-service`|`auth-service`,<br>`perfiles-service`,<br>`notificaciones-service`|Reto 04|
|`empleado.actualizado`|`empleados-service`|`perfiles-service`|Reto 04|
|`empleado.retirado`|`empleados-service`|`auth-service`,<br>`perfiles-service`,<br>`notificaciones-service`|Reto 04|
|`usuario.creado`|`auth-service`|`notificaciones-service`|Reto 05|
|`usuario.recuperacion`|`auth-service`|`notificaciones-service`|Reto 05|
|`cuenta.activada`|`auth-service`|`notificaciones-service`|Reto 05|
|`cuenta.desactivada`|`auth-service`|`notificaciones-service`|Reto 05|
|`vacaciones.programadas`|`vacaciones-service`|`notificaciones-service`|Reto 04|
|`vacaciones.iniciadas`|`vacaciones-service`|`auth-service`,<br>`notificaciones-service`|Reto 05|
|`vacaciones.finalizadas`|`vacaciones-service`|`auth-service`,<br>`notificaciones-service`|Reto 05|

---

<!-- Pagina 4 de 10 -->

### **3.1** **`empleado.creado`**

Se publica cuando RRHH registra un nuevo empleado y la operación se persistió con éxito.

```
{
```

```
"empleadoId":"E001",
"nombre":"Juan",
"apellido":"Pérez",
"email":"juan.perez@empresa.com",
"numeroEmpleado":"EMP-2026-001",
```

```
"cargo":"Desarrollador Senior",
"area":"Tecnología",
"departamentoId":"IT",
"fechaIngreso":"2026-02-10",
"estado":"ACTIVO"
}
```

#### **Reacciones esperadas:**

|**Consumidor**|**Acción**|
|---|---|
|`auth-service`|Crea la cuenta en estado**inactivo**, sin contraseña válida. Genera<br>un token de activación y publica<br>`usuario.creado`.|
|`perfiles-service`|Crea un perfil por defecto con los datos básicos del evento.|
|`notificaciones-service`|Registra la traza del alta. El correo de bienvenida**no**se dispara<br>aquí, sino con<br>`usuario.creado`(que es el que trae el token).|


### **3.2** **`empleado.actualizado`**

Se publica cuando cambia información del empleado que otros contextos replican.

---

<!-- Pagina 5 de 10 -->

```
{
```

```
"empleadoId":"E001",
"nombre":"Juan",
"apellido":"Pérez Gómez",
"email":"juan.perez@empresa.com",
"cargo":"Tech Lead",
"area":"Tecnología",
"departamentoId":"IT"
}
```

**Reacciones esperadas:** `perfiles-service` sincroniza los campos replicados en el perfil.

### **3.3** **`empleado.retirado`**

Se publica cuando RRHH marca al empleado como `RETIRADO` . **El empleado no se borra físicamente** : cambia de estado y se conserva para auditoría.

```
{
```

```
"empleadoId":"E001",
"email":"juan.perez@empresa.com",
```

```
"fechaRetiro":"2026-11-30T16:45:00Z",
```

```
"motivo":"RENUNCIA"
```

```
}
```

#### **Reacciones esperadas:**

|**Consumidor**|**Acción**|
|---|---|
|`auth-service`|Desactiva la cuenta de forma**permanente**y publica<br>`cuenta.desactivada`con<br>`motivo: "RETIRO"`.|
|`perfiles-service`|Archiva el perfil (no lo borra).|
|`notificaciones-service`|Registra la traza. El correo de despedida se dispara con<br>`cuenta.desactivada`.|


**Nota:** este evento sustituye al `empleado.eliminado` que aparecía en versiones anteriores del material. El nombre anterior sugería borrado físico, que contradice la regla de dominio establecida en el Reto 00 ( _"Eliminar = marcar como RETIRADO, no se borra físicamente"_ ).

---

<!-- Pagina 6 de 10 -->

### **3.4** **`usuario.creado`**

Se publica cuando el `auth-service` termina de crear la cuenta a raíz de `empleado.creado` . Es el evento que dispara el correo de bienvenida.

```
{
```

```
"empleadoId":"E001",
"email":"juan.perez@empresa.com",
"tokenActivacion":"a3f8b2c9-1e4d-07f6-50a1-823bc79e14d5",
"expiraEn":"2026-02-10T15:30:00Z"
}
```

⚠ **Nunca** se incluye una contraseña, ni temporal ni generada. El empleado establece su propia contraseña usando el token. Ver `POST /auth/reset-password` en el Reto 05.

**Reacciones esperadas:** `notificaciones-service` envía el correo de bienvenida con el enlace o token de activación.

### **3.5** **`usuario.recuperacion`**

Se publica cuando un usuario solicita recuperar su contraseña vía

`POST /auth/recover-password` .

```
{
```

```
"email":"juan.perez@empresa.com",
```

- `"tokenRecuperacion": "9c1d4e7a-2b8f-4a30-b6e5-1f207d9a4c88",`

```
"expiraEn":"2026-05-14T11:00:00Z"
}
```

**Reacciones esperadas:** `notificaciones-service` envía el correo de recuperación.

### **3.6** **`cuenta.activada`**

Se publica cada vez que una cuenta pasa a estado habilitado: al establecer la contraseña por primera vez, o al regresar de vacaciones.

---

<!-- Pagina 7 de 10 -->

```
{
"empleadoId":"E001",
"email":"juan.perez@empresa.com",
"motivo":"ACTIVACION_INICIAL"
}
```

|**`motivo`**|**Cuándo**|
|---|---|
|`ACTIVACION_INICIAL`|El empleado estableció su contraseña con el token de activación.|
|`FIN_VACACIONES`|Reactivación automática al consumir<br>`vacaciones.finalizadas`.|


### **3.7** **`cuenta.desactivada`**

Se publica cada vez que una cuenta deja de poder autenticarse. El campo `motivo` distingue si la desactivación es temporal o permanente; **no existe un evento separado para el caso permanente** .

```
{
```

```
"empleadoId":"E001",
"email":"juan.perez@empresa.com",
```

```
"motivo":"VACACIONES",
```

```
"permanente":false
}
```

|**`motivo`**|**`permanente`**|**Cuándo**|
|---|---|---|
|`VACACIONES`|`false`|Al consumir<br>`vacaciones.iniciadas`.|
|`RETIRO`|`true`|Al consumir<br>`empleado.retirado`.|


### **3.8** **`vacaciones.programadas`**

Se publica cuando RRHH registra un período de vacaciones que aún **no ha comenzado** .

---

<!-- Pagina 8 de 10 -->

```
{
```

```
"vacacionesId":"V-2026-0042",
```

- `"empleadoId": "E001",`

```
"email":"juan.perez@empresa.com",
```

- `"fechaInicio": "2026-03-15",`

```
"fechaFin":"2026-03-30",
```

- `"diasHabiles": 12`

```
}
```

**Reacciones esperadas:** `notificaciones-service` envía la confirmación del período al empleado.

- Este evento **no** desactiva la cuenta. La desactivación ocurre en `fechaInicio` , con

- `vacaciones.iniciadas` .

### **3.9** **`vacaciones.iniciadas`**

Lo publica el **scheduler** del `vacaciones-service` al llegar la `fechaInicio` del período.

```
{
```

- `"vacacionesId": "V-2026-0042",`

- `"empleadoId": "E001",`

- `"email": "juan.perez@empresa.com",`

- `"fechaInicio": "2026-03-15",`

- `"fechaFin": "2026-03-30"`

- `}`

#### **Reacciones esperadas:**

|**Consumidor**|**Acción**|
|---|---|
|`auth-service`|Desactiva la cuenta temporalmente y publica<br>`cuenta.desactivada`con<br>`motivo: "VACACIONES"`.|
|`notificaciones-service`|Notifica al empleado el inicio de su período.|

---

<!-- Pagina 9 de 10 -->

### **3.10** **`vacaciones.finalizadas`**

Lo publica el **scheduler** del `vacaciones-service` al llegar la `fechaFin` del período.

```
{
```

- `"vacacionesId": "V-2026-0042",`

- `"empleadoId": "E001", "email": "juan.perez@empresa.com", "fechaFin": "2026-03-30"`

- `}`

#### **Reacciones esperadas:**

|**Consumidor**|**Acción**|
|---|---|
||Reactiva la cuenta**solo si el empleado sigue en estado**<br>**`ACTIVO`**|
|`auth-service`|y publica<br>`cuenta.activada`con<br>`motivo: "FIN_VACACIONES"`. Si<br>el empleado fue retirado durante sus vacaciones, la cuenta**no**se|
||reactiva.|
|`notificaciones-service`|Envía la bienvenida de regreso.|


## **4. Diagrama de flujo de eventos**


<!-- Start of picture text -->
Productores<br>empleado.creado<br>empleado.creado empleado.retirado<br>POST /empleados 👥  empleados-service empleado.actualizado vacaciones.iniciadas<br>👤  RRHH empleado.retirado vacaciones.finalizadas<br>🔐  auth-service<br>POST /vacaciones usuario.creado<br>usuario.recuperacion<br>vacaciones.programadas<br>cuenta.activada<br>🏖  vacaciones-service vacaciones.iniciadas<br>⏰  Scheduler cuenta.desactivada<br>al llegar la fecha vacaciones.finalizadas<br>(vacaciones-service)<br>Consumidores<br>empleado.creado<br>📨  Message Broker empleado.actualizado 📋  perfiles-service<br>empleado.retirado<br>todos los eventos 📧  notificaciones-service<br><!-- End of picture text -->

---

<!-- Pagina 10 de 10 -->

## **5. Trazabilidad: reto ↔ eventos**

|**Reto**|**Eventos que debe implementar**|
|---|---|
|**03 – Comunicación**|`empleado.creado`,<br>`empleado.actualizado`,<br>`empleado.retirado`,|
|**Asincrónica**|`vacaciones.programadas`|
||`usuario.creado`,<br>`usuario.recuperacion`,<br>`cuenta.activada`,|
|**04 – Seguridad JWT**|`cuenta.desactivada`,<br>`vacaciones.iniciadas`,<br>`vacaciones.finalizadas`|
|**07 – Observabilidad**|Todos: cada consumo de evento debe generar un log estructurado<br>con<br>`traceId`y el<br>`id`del mensaje.|
|**11 – Saga Pattern**|Todos, más las transacciones compensatorias de cada uno.|
|**21 – AsyncAPI**|Especificación formal en YAML de al menos cuatro de estos canales.|
|**28 – Idempotencia**|Inbox Pattern y DLQ para todos los consumidores de esta tabla.|


## **6. Historial de cambios del catálogo**

|**Versión**|**Fecha**|**Cambio**|
|---|---|---|
|||Versión inicial. Unifica la convención de nomenclatura, incorpora los|
|1.0|2026-<br>08-01|eventos de vacaciones y los del<br>`auth-service`, y sustituye<br>`empleado.eliminado`por<br>`empleado.retirado`y<br>`cuenta.desactivada.permanente`por<br>`cuenta.desactivada`con|
|||`motivo`/<br>`permanente`.|
