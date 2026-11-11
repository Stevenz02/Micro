<!-- Pagina 1 de 39 -->

Desarrollo Guiado por Comportamiento (BDD)

Arquitectura Basada en Microservicios Área de infraestructura

Programa de Ingeniería de Sistemas y Computación Facultad de Ingeniería

---

<!-- Pagina 2 de 39 -->

Contenido

BDD – Desarrollo Guiado por Comportamiento Gherkin – Lenguaje de escenarios Cucumber – Framework de automatización BDD en Microservicios

   - Pruebas funcionales sobre un sistema distribuido Manejo de la asincronía

- Ejemplo práctico

Creando un proyecto

- Archivo Feature con Gherkin en español

Step Definitions

Ejecución

---

<!-- Pagina 3 de 39 -->

BDD - Desarrollo Guiado por Comportamiento

---

<!-- Pagina 4 de 39 -->

¿Qué es BDD?

– Behavior Driven Development Desarrollo Guiado por Comportamiento Propuesto por Dan North (2003)

- Metodología orientada al desarrollo, cuya estrategia progresa desde afuera hacia adentro

- Se enfoca en pruebas de alto nivel (prueba funcional, de aceptación)

- Plantea el uso de un lenguaje común para combinar elementos técnicos y de negocio

No es un reemplazo de las pruebas, es un complemento

---

<!-- Pagina 5 de 39 -->

# BDD vs Pruebas Tradicionales

Aspecto Pruebas Tradicionales BDD Perspectiva Técnica (funciones, clases) Negocio (flujos, comportamiento) Lenguaje Código del lenguaje Lenguaje natural (Gherkin) Audiencia Desarrolladores Desarrolladores, QA, stakeholders Documentación Se desactualiza fácilmente Documentación viva Pregunta clave ¿Funciona esta función? ¿El sistema se comporta correctamente?

---

<!-- Pagina 6 de 39 -->

# Objetivos y Características

Objetivos:

Mejorar la comunicación (entre el equipo y con el cliente)

Identificar las verdaderas necesidades del cliente

Lenguaje común: Natural, simple y fácil de escribir, accesible para técnicos y no técnicos

Trabajo colaborativo: Cliente, Analistas, Desarrolladores y QA participan

Establecer con claridad el comportamiento basado en reglas de negocio y requisitos empresariales

- Características:

   - Comportamiento: Pensar en cómo quiero que funcione el software

---

<!-- Pagina 7 de 39 -->

Negocio (PO): ¿Qué necesitamos resolver? (problema)

Desarrollador: ¿Cómo vamos a desarrollar la solución?

QA: ¿Cómo verificar que la solución funciona correctamente?

---

<!-- Pagina 8 de 39 -->

<!-- Start of picture text -->
El Ciclo BDD<br>Fase Actividad Participantes<br>Reunión de los 3 amigos: se discuten HU y se identifican PO + Dev +<br>1. Descubrir<br>escenarios QA<br>Se escriben los escenarios en Gherkin (lenguaje natural<br>2. Formular QA + Dev<br>estructurado)<br>3. Se implementan los step definitions (código que ejecuta cada<br>Dev + QA<br>Automatizar paso)<br>4. Ejecutar Se corren las pruebas. Si fallan → se desarrolla la funcionalidad Dev<br>5. Iterar Se repite el ciclo para cada nueva funcionalidad o cambio Todos<br>Similar a TDD pero a un nivel más alto de abstracción: primero los escenarios, luego el código.<br><!-- End of picture text -->

---

<!-- Pagina 9 de 39 -->

Gherkin - Lenguaje de escenarios

---

<!-- Pagina 10 de 39 -->

# Gherkin

Es un lenguaje usado para describir el comportamiento del sistema de forma estructurada

Cuenta con una sintaxis que puede ser entendida por todos los involucrados: negocio, desarrollo y calidad

   - Elementos básicos:

      - Given / Dado — Contexto y/o precondiciones del escenario

      - When / Cuando — Condición, Evento, Acción

      - Then / Entonces — Resultado y/o comportamiento esperado

      - And / Y — Para encadenar pasos adicionales

      - But / Pero — Para agregar excepciones o condiciones negativas

- Gherkin soporta múltiples idiomas de forma nativa, incluyendo español.

---

<!-- Pagina 11 de 39 -->

# Estructura de un Feature

Feature: Funcionalidad o Historia de Usuario

Scenario: Se ejecuta una vez, está asociado a un criterio de aceptación

Scenario Outline: Escenario que se repite con diferentes conjuntos de datos

Background: Precondiciones comunes a todos los escenarios del feature

---

<!-- Pagina 12 de 39 -->

# Gherkin soporta español


<!-- Start of picture text -->
Gherkin soporta múltiples idiomas de forma nativa:<br><!-- End of picture text -->


<!-- Start of picture text -->
Inglés Español<br>Feature Característica<br>Scenario Escenario<br>Scenario Outline Esquema del escenario<br>Given Dado / Dada / Dados / Dadas<br>When Cuando<br>Then Entonces<br>And Y<br>But Pero<br><!-- End of picture text -->


<!-- Start of picture text -->
Para activar el español: # language: es en la primera línea del archivo .feature<br><!-- End of picture text -->

---

<!-- Pagina 13 de 39 -->

- `# language: es`

```
Característica: Registro de empleados
 Como administrador del sistema
 Quiero registrar nuevos empleados
 Para iniciar su proceso de onboarding
```

```
 Antecedentes:
```

```
   Dado que existe un departamento "IT" con nombre "Tecnología"
   Y que estoy autenticado como "ADMIN"
```

```
 Escenario: Registro exitoso de un empleado
   Cuando registro un empleado con los siguientes datos:
     | id    | nombre     | email              | departamentoId |
     | E001  | Juan Pérez | juan@empresa.com   | IT             |
   Entonces la respuesta debe tener código 201
   Y el cuerpo debe contener el nombre "Juan Pérez"
```

---

<!-- Pagina 14 de 39 -->

# Esquema del escenario: Múltiples datos

- `# language: es`

```
Característica: Validaciones de registro
```

```
 Esquema del escenario: Registro con diferentes datos
   Dado que estoy autenticado como "ADMIN"
   Y que existe un departamento "IT" con nombre "Tecnología"
   Cuando registro un empleado con nombre "<nombre>" email "<email>" y depto "<depto>"
   Entonces la respuesta debe tener código <codigo>
```

|`Ejemplos:`<br>`| nombre`|`| email| depto| codigo|`|
|---|---|
|`| Juan Pérez`|`| juan@empresa.com| IT| 201|`|
|`| María`|`|| IT| 400|`|
|`| Pedro`|`| pedro@empresa.com| INEXISTENTE| 400|`|


## Cada fila de la tabla `Ejemplos` genera un escenario independiente en la ejecución y en el reporte.

---

<!-- Pagina 15 de 39 -->

Cucumber - Framework de automatización

---

<!-- Pagina 16 de 39 -->

# ¿Qué es Cucumber?

Herramienta / Framework de automatización de pruebas

Basado en Gherkin

- Se enfoca en apoyar el desarrollo basado en comportamiento (BDD)

Lee los archivos `.feature` , ejecuta los step definitions asociados y genera reportes

---

<!-- Pagina 17 de 39 -->

<!-- Start of picture text -->
Cucumber: El Flujo<br>📄  .feature<br>(Gherkin)<br>🥒  Cucumber 📊  Reportes<br>(Runner) (HTML/JSON)<br>⚙  Step Definitions<br>(Código)<br><!-- End of picture text -->

- Los archivos **`.feature`** describen qué debe hacer el sistema (lenguaje natural) Los step definitions describen cómo se ejecuta cada paso (código)

- Cucumber conecta ambos mundos y ejecuta las pruebas

---

<!-- Pagina 18 de 39 -->

# Cucumber por lenguaje

Lenguaje Implementación Comando de ejecución Java Cucumber-JVM `mvn test` Python Behave / pytest-bdd `behave` / `pytest` Node.js Cucumber.js `npx cucumber-js` Go Godog `godog` Ruby Cucumber (original) `cucumber` C# SpecFlow `dotnet test`

---

<!-- Pagina 19 de 39 -->

BDD en Microservicios

---

<!-- Pagina 20 de 39 -->

¿Por qué BDD en Microservicios?

En un sistema distribuido, las pruebas unitarias no son suficientes para validar que los flujos de negocio funcionan de extremo a extremo.

Desafío Múltiples servicios involucrados en un flujo

Cómo BDD ayuda Los escenarios describen el flujo completo, no servicios aislados

Comunicación asincrónica Los pasos pueden incluir esperas con reintentos (eventos) Los escenarios validan acceso autorizado y Seguridad transversal (JWT, RBAC) denegado La suite BDD actúa como red de seguridad Regresiones entre servicios funcional

---

<!-- Pagina 21 de 39 -->

# Arquitectura de pruebas BDD


<!-- Start of picture text -->
🧪  Suite BDD<br>📄  .feature<br>(Gherkin)<br>⚙  Steps<br>(HTTP)<br><!-- End of picture text -->

#### HTTP REST


<!-- Start of picture text -->
🐳  Docker Compose<br>🚪  Gateway<br>🏢  departamentos 👥  empleados<br>📨  Broker<br>🔐  auth 📧  notificaciones<br><!-- End of picture text -->

## Las pruebas BDD se ejecutan contra el sistema real desplegado con Docker Compose.

---

<!-- Pagina 22 de 39 -->

# Ejemplo: Flujo de Onboarding

- `# language: es`

- `Característica: Onboarding de empleados Como administrador del sistema`

```
 Quiero registrar nuevos empleados
```

```
 Para que se generen automáticamente credenciales y notificaciones
```

- `Antecedentes:`

```
   Dado que el sistema está desplegado y operativo
```

- `Y que existe un departamento "IT" con nombre "Tecnología"`

- `Y que estoy autenticado como "ADMIN"`

```
 Escenario: Onboarding completo de un nuevo empleado
```

```
   Cuando registro un empleado con id "E001" nombre "Juan" y email "juan@empresa.com"
   Entonces la respuesta debe tener código 201
```

- `Y eventualmente el auth-service debe crear un usuario para "juan@empresa.com"`

- `Y eventualmente se debe registrar una notificación para "E001"`

---

<!-- Pagina 23 de 39 -->

```
# language: es
```

```
Característica: Seguridad y control de acceso
```

```
 Escenario: Acceso denegado sin token de autenticación
   Cuando consulto la lista de empleados sin token
   Entonces la respuesta debe tener código 401
```

```
 Escenario: Usuario USER puede consultar pero no eliminar
   Dado que estoy autenticado como "USER"
   Cuando consulto la lista de empleados
   Entonces la respuesta debe tener código 200
   Cuando intento eliminar el empleado "E001"
   Entonces la respuesta debe tener código 403
```

```
 Escenario: Usuario ADMIN puede realizar todas las operaciones
   Dado que estoy autenticado como "ADMIN"
   Cuando elimino el empleado "E001"
   Entonces la respuesta debe tener código 200
```

---

<!-- Pagina 24 de 39 -->

# Manejo de la Asincronía

Un desafío clave al probar sistemas basados en eventos: eventual consistencia.

```
POST /empleados → empleado.creado → auth-service procesa → usuario creado
                                 → notificaciones procesa → notificación creada
```

¿Cuándo puedo verificar que el evento se procesó? No inmediatamente.

---

<!-- Pagina 25 de 39 -->

# Polling con reintentos

Estrategia: Consultar repetidamente hasta que la condición se cumpla o expire el timeout.

```
// Pseudocódigo
voidesperarHastaQue(Condicion condicion, int maxIntentos, int intervaloMs) {
for (inti=0; i < maxIntentos; i++) {
if (condicion.evaluar()) return; // ✓ Éxito
       Thread.sleep(intervaloMs);       // ← Pausa ENTRE reintentos (válido)
   }
thrownewTimeoutException("Condición no cumplida");
}
// Uso en un step definition
@Entonces("eventualmente se debe registrar una notificación para {string}")
voidverificarNotificacion(String empleadoId) {
   esperarHastaQue(
```

```
       () -> httpGET("/notificaciones/" + empleadoId).body().size() > 0,
15,    // máximo 15 intentos
2000// cada 2 segundos
   );
}
```

No confundir: El `sleep` dentro del ciclo de polling es el intervalo entre reintentos (válido). Lo prohibido es usar un `sleep` fijo como única estrategia (ej. `Thread.sleep(5000)` y luego verificar una sola vez).

---

<!-- Pagina 26 de 39 -->

Ejemplo Práctico - Creación de un proyecto con Cucumber

---

<!-- Pagina 27 de 39 -->

# Creando un proyecto (Java + Maven)

- `mvn archetype:generate                      \ "-DarchetypeGroupId=io.cucumber"           \`

- `"-DarchetypeArtifactId=cucumber-archetype" \`

- `"-DarchetypeVersion=7.23.0"               \`

- `"-DgroupId=co.edu.uniquindio.ingesis.cucumber.ejemplo"                  \`

- `"-DartifactId=microservicios-202502-cucumber-test"               \`

- `"-Dpackage=co.edu.uniquindio.ingesis.cucumber.ejemplo.test"                  \`

- `"-Dversion=1.0"                 \`

- `"-DinteractiveMode=false"`

Referencia: https://cucumber.io/docs/guides/10-minute-tutorial/

---

<!-- Pagina 28 de 39 -->

# Estructura del proyecto

- `microservicios-202502-cucumber-test/ ├── pom.xml ├── src/ │   └── test/ │       ├── java/co/edu/.../test/ │       │   ├── RunCucumberTest.java        ← Runner │       │   └── StepDefinitions.java        ← Steps │       └── resources/ │           └── co/edu/.../test/ │               ├── onboarding.feature      ← Escenarios │               ├── seguridad.feature`

- `│               └── offboarding.feature`

Los archivos `.feature` van en resources y los step definitions en java.

---

<!-- Pagina 29 de 39 -->

Las pruebas se definen en archivos **`.feature`** usando el lenguaje Gherkin

Los archivos feature se crean en la carpeta de recursos ( `resources` ) Un feature suele estar asociado a una funcionalidad o historia de usuario

```
# language: es
```

```
Característica: El API de Login permite a los usuarios autenticarse en la aplicación
```

---

<!-- Pagina 30 de 39 -->

Cada Scenario plantea un criterio de aceptación para una funcionalidad

Un archivo `.feature` puede contener más de un escenario (todos relacionados)

```
# language: es
```

```
Característica: El API de Login permite a los usuarios autenticarse en la aplicación
```

```
 Escenario: Un usuario registrado puede autenticarse con credenciales válidas
```

---

<!-- Pagina 31 de 39 -->

- Los escenarios se dividen en steps que se asocian a métodos de prueba Dado: Establece el estado del sistema (configura y proporciona datos)

Cuando: Se asocia a una acción

- Entonces: Evalúa el resultado

Y: Permite adicionar un paso en una determinada fase

- `# language: es`

- `Característica: El API de Login permite a los usuarios autenticarse`

```
 Escenario: Un usuario registrado puede autenticarse con credenciales válidas
   Dado que soy un usuario registrado del sistema con credenciales válidas
   Cuando invoco el servicio de autenticación
   Entonces obtengo un código de estado 200
   Y un token de autenticación válido
```

---

<!-- Pagina 32 de 39 -->

# Step Definitions: El puente

### Cada línea del escenario se conecta con un método en código:

```
publicclassLoginSteps {
private Response response;
private String token;
@Dado("que soy un usuario registrado del sistema con credenciales válidas")
publicvoidprepararCredenciales() {
// Configurar usuario y contraseña de prueba
   }
@Cuando("invoco el servicio de autenticación")
publicvoidinvocarLogin() {
       response = given()
           .contentType("application/json")
           .body(Map.of("email", "admin@test.com", "password", "admin123"))
           .when()
           .post(BASE_URL + "/auth/login");
   }
@Entonces("obtengo un código de estado {int}")
publicvoidverificarCodigo(int codigo) {
       response.then().statusCode(codigo);
   }
}
```

---

<!-- Pagina 33 de 39 -->

# Herramientas Complementarias

---

<!-- Pagina 34 de 39 -->

Para que los step definitions ejecuten peticiones HTTP reales contra el sistema:

Lenguaje Librerías HTTP Java `java.net.http` (Java 11+), Rest Assured (recomendado), OkHttp, Feign Python requests, httpx Node.js axios, node-fetch Go net/http

---

<!-- Pagina 35 de 39 -->

# Rest Assured + Cucumber: Ejemplo completo

```
@Dado("que estoy autenticado como {string}")
publicvoidautenticarComo(String rol) {
```

```
Stringuser= rol.equals("ADMIN") ? "admin@test.com" : "user@test.com";
Stringpass= rol.equals("ADMIN") ? "admin123" : "user123";
```

```
   token = given()
       .contentType("application/json")
       .body(Map.of("email", user, "password", pass))
       .when().post(BASE_URL + "/auth/login")
       .then().statusCode(200)
       .extract().path("token");
}
```

```
@Cuando("consulto la lista de empleados")
publicvoidconsultarEmpleados() {
   response = given()
       .header("Authorization", "Bearer " + token)
       .when().get(BASE_URL + "/empleados");
}
```

---

<!-- Pagina 36 de 39 -->

# Ejecución de las pruebas

```
# 1. Levantar el sistema completo
docker-compose up --build -d
# 2. Esperar a que los servicios estén listos
# (verificar health checks)
# 3. Ejecutar las pruebas BDD
mvn test# Java
behave                       # Python
npx cucumber-js              # Node.js
# 4. Revisar reportes generados
# 5. Apagar el sistema
docker-compose down
```

---

<!-- Pagina 37 de 39 -->

# Salida de Cucumber

```
Característica: Onboarding de empleados
```

- `Escenario: Onboarding completo de un nuevo empleado ✓ Dado que el sistema está desplegado y operativo`

- `✓ Y que existe un departamento "IT" con nombre "Tecnología"`

- `✓ Y que estoy autenticado como "ADMIN"`

- `✓ Cuando registro un empleado con id "E001" nombre "Juan"`

- `✓ Entonces la respuesta debe tener código 201`

- `✓ Y eventualmente el auth-service debe crear un usuario`

- `3 características, 10 escenarios (10 pasaron) 45 pasos (45 pasaron)`

- `0m12.345s`

---

<!-- Pagina 38 de 39 -->

Resumen

Concepto Rol BDD Metodología: describir comportamiento antes de implementar Gherkin Lenguaje: `Dado/Cuando/Entonces` en español Cucumber Herramienta: conecta Gherkin con código ejecutable Step Definitions Código: implementa cada paso con peticiones HTTP Polling Estrategia: manejar asincronía sin `sleep` fijo Docker Compose Infraestructura: sistema real para pruebas funcionales

---

<!-- Pagina 39 de 39 -->

Arquitectura Basada en Microservicios Programa de Ingeniería de Sistemas y Computación Universidad del Quindío


2025 Christian Andrés Candela Uribe
