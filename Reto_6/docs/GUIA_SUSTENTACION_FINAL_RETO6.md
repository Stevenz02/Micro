# Guía final de sustentación — Reto 6

Esta guía es para **dos estudiantes**. Estudiante A opera Swagger; Estudiante B explica arquitectura, eventos y resultados. La demostración funcional se hace desde **<http://localhost:8080/docs>**. Los reportes se muestran como evidencia al final. No se necesitan PowerShell, `curl` ni Postman durante la exposición.

## 1. Apertura: qué construimos

**Estudiante B dice:**

> En el Reto 6 implementamos y verificamos una estrategia completa de pruebas automatizadas para un ecosistema de microservicios de Recursos Humanos. Validamos pruebas unitarias, integración con PostgreSQL y pruebas funcionales BDD contra el sistema completo desplegado. Además, documentamos y centralizamos los contratos de los servicios mediante Swagger.

## 2. Arquitectura en una frase

**Estudiante B explica:** El cliente entra por el **API Gateway**. Detrás están **Auth, Empleados, Departamentos, Perfiles, Notificaciones y Vacaciones**, cada uno con su base PostgreSQL independiente. Los servicios se consultan por REST y propagan cambios mediante eventos asincrónicos en RabbitMQ. La entrada pública para esta demostración es el Gateway en `http://localhost:8080`; los puertos internos no se usan en la exposición.

**Estudiante A muestra:** la pantalla principal de Swagger, sus seis grupos de servicios, modelos de entrada y salida, respuestas HTTP y el botón **Authorize**. El OpenAPI consolidado contiene **24 operaciones reales**.

> Swagger permite ejecutar solicitudes en una interfaz gráfica y ver el cuerpo enviado, la respuesta y el código HTTP, junto con el contrato de cada operación.

## 3. Regla de la demostración

**No hay que crear departamento, empleado, cuenta ni vacaciones antes de empezar.** Se crean en los pasos siguientes y cada respuesta aporta el dato que usa el paso posterior. Solo se usan las credenciales del administrador semilla que ya forman parte de la configuración del sistema. Estudiante A opera Swagger; Estudiante B explica el resultado. En cada ruta, pulsar **Try it out → Execute** y señalar el código y cuerpo de respuesta.

Cuando un paso diga **anotar**, basta con mantener el valor visible o copiarlo temporalmente para pegarlo en el siguiente formulario de Swagger. No se guarda en el repositorio. En **Authorize** se pega solo `access_token`: Swagger construye el encabezado `Authorization: Bearer <token>`. El rol se valida por los permisos observados; la respuesta de login no tiene un campo separado `role`.

## 4. Demostración completa, un paso detrás de otro

1. **Abrir Swagger.** Ir a `http://localhost:8080/docs`. Mostrar los seis grupos de servicios, modelos y **Authorize**. Ejecutar `GET /health`: `200`. Decir: «El Gateway es nuestra única entrada de demostración».

2. **Mostrar `401` sin token.** Sin pulsar **Authorize**, ejecutar `GET /empleados`: `401 Unauthorized`. Decir: «El Gateway exige una identidad válida».

3. **Iniciar sesión como ADMIN.** Ejecutar `POST /auth/login` con el correo y contraseña del administrador semilla definidos en el proyecto. Copiar `access_token` de la respuesta `200` y pegarlo en **Authorize**. Decir: «Auth emite el JWT; el Gateway lo valida». La capacidad de crear el departamento en el siguiente paso demuestra el permiso ADMIN.

4. **Crear el identificador durante la exposición.** En ese momento, formar el sufijo **S** con fecha y hora `AAMMDDHHMMSS`; por ejemplo, el 15 de octubre de 2026 a las 15:48:30, **S = `261015154830`**. En `POST /departamentos`, enviar `{"id":"D-261015154830","nombre":"Calidad","descripcion":"Sustentación"}`, sustituyendo `261015154830` por **S**. Mostrar `201` y anotar **D**, el `id` devuelto. Este paso crea el departamento; no se presupone uno existente.

5. **Consultar ese departamento.** Ejecutar `GET /departamentos/{id}` con **D**. Mostrar `200` y el mismo identificador. Decir: «El empleado se asociará a este departamento válido».

6. **Crear el empleado ahora.** En `POST /empleados`, enviar el siguiente cuerpo sustituyendo **S** y **D** por los valores recién obtenidos. Usar la fecha de ingreso del ejemplo si es anterior al día de la exposición. Mostrar `201`, `estado=ACTIVO`, correo y número. Anotar **E** (ID) y **C** (correo) de la respuesta. Decir: «El alta publica `empleado.creado`; sus efectos aparecen de forma asincrónica».

   ```json
   {
     "id": "EMP-261015154830",
     "nombre": "Ana",
     "apellido": "Prueba",
     "email": "ana-261015154830@example.test",
     "numeroEmpleado": "N-261015154830",
     "cargo": "Analista",
     "area": "Calidad",
     "departamentoId": "D-261015154830",
     "fechaIngreso": "2026-01-01",
     "estado": "ACTIVO"
   }
   ```

7. **Confirmar el registro.** Ejecutar `GET /empleados/{id}` con **E**. Mostrar `200`, el mismo correo **C** y `numeroEmpleado`.

8. **Esperar el perfil.** Ejecutar `GET /perfiles/{empleadoId}` con **E**. Si aún no aparece, repetir la consulta hasta recibir `200`; no crear otro empleado. Decir: «Perfiles recibe el evento y construye su proyección».

9. **Encontrar la notificación de activación.** Ejecutar `GET /notificaciones/{empleadoId}` con **E** y repetir hasta ver una notificación `SEGURIDAD` de cuenta creada. Anotar **N**, su `id`. Decir: «Esta notificación representa la entrega simulada del token; no contiene contraseña».

10. **Obtener el token de esa notificación.** Con ADMIN todavía autorizado, ejecutar `GET /notificaciones/seguridad/{id}/token` con **N**. Mostrar `200` y anotar temporalmente el valor **T** de `token` para el siguiente paso. No guardarlo en el proyecto.

11. **Activar la cuenta recién creada.** En `POST /auth/reset-password`, enviar `{"token":"<T>","newPassword":"DemoClave2026A7"}` sustituyendo `<T>` por el token del paso 10. Esa clave de demostración cumple la política de longitud, mayúsculas, minúsculas y números. Mostrar `200`. Decir: «El empleado establece su clave con un token; la clave no viajó en RabbitMQ. La activación publica `cuenta.activada`».

12. **Iniciar sesión como USER.** Ejecutar `POST /auth/login` con **C** y `DemoClave2026A7`. Mostrar `200`, copiar el nuevo `access_token` y reemplazar el anterior en **Authorize**. Este token corresponde al empleado **E** que acabamos de activar.

13. **Mostrar permisos permitidos.** Con USER, ejecutar `GET /empleados` y `GET /perfiles/{empleadoId}` con **E**: ambos `200`. Después ejecutar `PUT /perfiles/{empleadoId}` con **E** y `{"telefono":"3001234567","ciudad":"Armenia"}`: `200`. Decir: «USER puede consultar y editar su propio perfil».

14. **Mostrar `403` con el mismo USER.** Ejecutar `PUT /perfiles/{empleadoId}` con `OTRO-ID` y el mismo cuerpo: `403`. Ejecutar `POST /empleados` con el cuerpo del paso 6: `403` antes de crear nada. Ejecutar `DELETE /empleados/{id}?motivo=RENUNCIA` con **E**: `403`, por lo que **E continúa activo**. Decir: «El token es válido, pero no autoriza cambios ajenos ni administración».

15. **Volver a ADMIN.** Ejecutar otra vez `POST /auth/login` con las credenciales del administrador semilla. Sustituir el JWT USER por el nuevo `access_token` ADMIN en **Authorize**. No se crea ninguna cuenta adicional.

16. **Programar vacaciones futuras para el mismo empleado E.** Elegir ahora dos fechas ISO `AAAA-MM-DD` futuras, por ejemplo dos días del próximo mes, con fin posterior al inicio. En `POST /vacaciones`, enviar `{"empleadoId":"<E>","fechaInicio":"<inicio futuro>","fechaFin":"<fin futuro>"}`. Mostrar `201` y anotar el ID **V** del período. Decir: «Se publica `vacaciones.programadas`».

17. **Confirmar el período y su efecto.** Ejecutar `GET /vacaciones/{id}` con **V**: `200`. Ejecutar `GET /notificaciones/{empleadoId}` con **E** y repetir hasta ver la confirmación de vacaciones. No se requiere otra persona ni otro departamento.

18. **Probar tres errores de fechas, uno por uno.** En `POST /vacaciones`, siempre con **E**: primero enviar fin anterior al inicio; luego inicio y fin en el pasado; finalmente repetir el rango futuro del paso 16 para provocar solapamiento. Mostrar el cuerpo y `400` de cada regla. Una fecha con formato mal escrito puede ser rechazada antes de llegar a la regla de negocio: si se enseña, leer el código real de Swagger.

19. **Mostrar el scheduler con el mismo empleado E.** La vacación del paso 16 es futura y no se solapa con hoy. En `POST /vacaciones`, usar **E** y poner `fechaInicio` y `fechaFin` iguales a la **fecha UTC de hoy** (en Colombia, UTC va cinco horas adelante). Mostrar `201`. Repetir `GET /notificaciones/{empleadoId}` hasta observar inicio/suspensión y después fin/reactivación. Intentar `POST /auth/login` con **C** y la clave USER durante la suspensión (`401`) y al finalizar (`200`). Como el intervalo configurado es de 5 segundos, la ventana manual puede pasar muy rápido: si ocurre, abrir el escenario **«El inicio suspende el login y el fin lo restablece»** en `e2e-tests/reports/cucumber.html`, donde la BDD ya verificó ambos estados. Explicar `vacaciones.iniciadas`, `cuenta.desactivada`, `vacaciones.finalizadas` y `cuenta.activada`.

20. **Retirar al mismo empleado E.** Una vez visto el fin del período de hoy, volver a comprobar que **Authorize** contiene ADMIN. Ejecutar `DELETE /empleados/{id}?motivo=RENUNCIA` con **E**. Mostrar `200`, `estado=RETIRADO` y `fechaRetiro`. Luego ejecutar `GET /empleados/{id}` y `GET /empleados?estado=RETIRADO`; el registro aparece en ambas lecturas. Decir: «Es un retiro lógico para conservar la auditoría».

21. **Comprobar el bloqueo definitivo.** Con **C** y la clave USER, `POST /auth/login` debe dar `401` después de que se procese el retiro. Consultar `GET /notificaciones/{empleadoId}` con ADMIN y anotar cuántas notificaciones `SEGURIDAD` hay. Ejecutar `POST /auth/recover-password` con **C**: devuelve **`202` genérico**, incluso para retirados. Consultar de nuevo las notificaciones: no debe aparecer un nuevo token de recuperación. Decir: «La respuesta no revela si existe la cuenta y el retiro impide reactivarla». El caso de fin de vacaciones posterior a un retiro está probado por un escenario BDD; no existe una ruta HTTP de reactivación manual.

22. **Cerrar con evidencia.** Abrir `e2e-tests/reports/cucumber.html` y señalar 5 características, 25 escenarios y 116 pasos aprobados. Después indicar dónde están JUnit, cobertura y el documento de resultados. Decir: «Todo lo mostrado se creó durante esta misma secuencia; la BDD repitió los flujos contra el Gateway real».

**Códigos que no debemos confundir:** `401` es ausencia o invalidez de autenticación; `403` es falta de permiso con identidad válida. Empleados podría devolver `202 PENDIENTE` si Departamentos no está disponible; en esta secuencia debe devolver `201` para continuar la activación. Vacaciones devuelve `400` por solapamiento o ID duplicado, no `409`. La recuperación de una cuenta retirada devuelve `202` genérico, no una confirmación de reactivación.

## 5. Cómo explicar las pruebas

| Nivel | Texto breve para decir | Resultado verificado |
|---|---|---:|
| Unitarias | «Validan reglas aisladas: unicidad y retiro, contraseñas y JWT, fechas, solapamiento y scheduler, sin necesitar el ecosistema desplegado». | **140/140** |
| Integración | «Ejecutamos el repositorio de Empleados contra PostgreSQL real y verificamos persistencia y restricciones». | **1/1** |
| BDD | «Gherkin describe seguridad, onboarding, vacaciones y offboarding desde el punto de vista del usuario. Behave llama al Gateway real y observa los efectos entre servicios». | **25/25 escenarios; 116/116 pasos** |

**Polling:**

> Los eventos son asincrónicos. En vez de dormir un tiempo fijo, las pruebas consultan repetidamente hasta observar la condición esperada o agotar un límite. Así se verifica el efecto real de Auth, Perfiles y Notificaciones.

Se realizaron **tres corridas BDD consecutivas** y una corrida final después del ajuste de Swagger; todas pasaron. El JUnit consolidado registra 25 pruebas y cero fallos en cada una.

## 6. Cobertura: decir el alcance de cada cifra

| Componente | Cobertura medida |
|---|---:|
| Empleados | **79,19 %** de los módulos Python seleccionados |
| Auth | **86,17 %** de los módulos seleccionados |
| Gateway | **90,91 %** de `gateway_app/main.py` |
| Vacaciones | **16,90 %** del ensamblado completo |

> Empleados, Auth y Gateway superan el 70 % en las mediciones indicadas. Vacaciones registra 16,90 % porque la medición incluye infraestructura del ensamblado que la suite unitaria no ejercita. Lo mostramos de forma explícita; no afirmamos que todos los servicios superan el 70 %.

Si se pregunta por cobertura de Departamentos, Perfiles o Notificaciones, indiquen que **no se midió cobertura en esta verificación**, aunque sus pruebas pasaron. No conviertan la cifra de un componente en cobertura global del sistema.

## 7. Reportes para mostrar al terminar

**Estudiante A abre primero** [`../e2e-tests/reports/cucumber.html`](../e2e-tests/reports/cucumber.html): 5 características, 25 escenarios y 116 pasos aprobados. Señale nombres, estados y duraciones. El HTML puede mostrar mensajes de error cuando una corrida falla; **esta corrida aprobada no contiene errores**. También existen `../e2e-tests/reports/cucumber.json` y `../e2e-tests/reports/junit.xml`. Las copias de cada corrida están en `../e2e-tests/reports/run-1/`, `run-2/`, `run-3/` y `run-final/`.

**Estudiante B explica:**

> El JSON conserva el detalle Cucumber; el HTML facilita revisar escenarios y pasos; JUnit deja los resultados listos para que Jenkins los consuma en el Reto 7. Los XML de cobertura registran las líneas medidas por componente.

Los reportes JUnit/cobertura de Empleados están en `Reto_4/empleados/reports/`; los de Auth en `Reto_5/auth/reports/`; los del Gateway en `Reto_5/api-gateway/reports/`; y los de Vacaciones en `Reto_5/vacaciones.tests/reports/` (`vacaciones.trx` y `coverage.xml`). El detalle de todas las suites se encuentra en [RESULTADOS_EJECUCION_RETO6.md](RESULTADOS_EJECUCION_RETO6.md).

## 8. Documentos de respaldo

- [SUSTENTACION_RETO6.md](SUSTENTACION_RETO6.md): pasos técnicos y límites del contrato.
- [RUTAS_RETO6.md](RUTAS_RETO6.md): métodos, rutas reales, autenticación, roles, respuestas y eventos.
- [RESULTADOS_EJECUCION_RETO6.md](RESULTADOS_EJECUCION_RETO6.md): fecha, servicios, pruebas, cobertura, reportes, variables y limitaciones.
- [cucumber.html](../e2e-tests/reports/cucumber.html): evidencia navegable de la BDD final.

## 9. Preguntas probables del profesor

**¿Por qué Swagger?** Permite mostrar y ejecutar contratos reales, modelos y códigos HTTP en una interfaz gráfica desde el Gateway.

**¿Qué diferencia hay entre `401` y `403`?** `401` significa que no hay autenticación válida; `403` significa que sí hay identidad, pero el rol o la propiedad del recurso no permite la operación.

**¿Qué diferencia hay entre unitarias y BDD?** Las unitarias prueban reglas aisladas; BDD recorre el sistema desplegado por el Gateway y observa el comportamiento de varios servicios.

**¿Cómo verificaron eventos asincrónicos?** Mediante polling con límite de tiempo hasta observar perfiles, notificaciones, estados de cuenta o respuestas de login esperadas.

**¿Por qué no borrar al empleado?** El retiro es lógico para conservar auditoría, fecha de retiro y trazabilidad.

**¿Qué pasa si termina la vacación después del retiro?** `vacaciones.finalizadas` no reactiva una cuenta `DESACTIVADA_PERMANENTE`; existe un escenario BDD que lo comprueba.

**¿Qué demuestra Cucumber HTML?** Las características, escenarios, pasos, estados y duraciones de la ejecución. Mostraría el error si un paso fallara.

**¿Qué quedó pendiente de la verificación visual?** En esta sesión no hubo un navegador disponible para tomar capturas ni revisar visualmente el renderizado. Sí respondieron Swagger y OpenAPI por HTTP, los flujos BDD pasaron contra el Gateway real y el HTML fue generado y revisado estructuralmente. Esta limitación de evidencia no equivale a un fallo del sistema.

## 10. Cierre

**Estudiante B dice:**

> El Reto 6 quedó demostrado en tres niveles: 140 pruebas unitarias aprobadas, una integración real con PostgreSQL y 25 escenarios BDD con 116 pasos aprobados en tres corridas consecutivas y una final. Swagger reúne las 24 operaciones reales del Gateway, y los reportes permiten repetir y auditar la verificación.
