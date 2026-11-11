<!-- Pagina 1 de 58 -->

Comunicación en Microservicios

Arquitectura Basada en Microservicios Área de infraestructura Programa de Ingeniería de Sistemas y Computación Facultad de Ingeniería

---

<!-- Pagina 2 de 58 -->

Consideraciones de comunicación

Remote Procedure Invocation (REST)

API Gateway Pattern

- Backend for Frontend (BFF)

- Patrones de resiliencia

- Messaging (Comunicación asincrónica)

- Domain-specific Protocol

- Idempotent Consumer

- Mejores prácticas y Antipatrones

---

<!-- Pagina 3 de 58 -->

# Consideraciones de Comunicación

---

<!-- Pagina 4 de 58 -->

# ¿Cómo se comunican los microservicios?

Problema: ¿Cómo se comunican los servicios entre sí de manera eficiente y confiable? Dimensiones de la comunicación:

- Uno a uno vs Uno a muchos

- Sincrónica vs Asincrónica

- Formatos de texto legible vs Formatos binarios

---

<!-- Pagina 5 de 58 -->

# Uno a Uno vs Uno a Muchos

La interacción entre microservicios puede ser de uno a uno o de uno a muchos.

---

<!-- Pagina 6 de 58 -->

# Sincrónica vs Asincrónica

## La interacción entre microservicios puede ser sincrónica o asincrónica.

---

<!-- Pagina 7 de 58 -->

# Comunicación Sincrónica vs Asincrónica

Aspecto Sincrónica Asincrónica Tiempo El cliente espera la respuesta El cliente no espera Acoplamiento Temporal alto Temporal bajo Complejidad Menor Mayor (colas, eventos) Ejemplo REST, gRPC RabbitMQ, Kafka

---

<!-- Pagina 8 de 58 -->

# Formatos de Intercambio

La interacción entre microservicios puede ser mediante formatos de texto legible o formatos binarios.

---

<!-- Pagina 9 de 58 -->

Matriz de Interacción


Uno a Uno

Sincrono Solicitud/Respuesta Solicitud Asíncrona/Respuesta Asíncrono Notificación de una via

Uno a Muchos


Publicación/Suscripción Publicación/Respuesta asíncrona

---

<!-- Pagina 10 de 58 -->

# Identificación de Colaboradores

Identifique para cada microservicio los colaboradores (otros microservicios) que intervienen en el manejo de cada operación disponible.

Determine el estilo de comunicación a ser usado entre el microservicio y sus colaboradores.

---

<!-- Pagina 11 de 58 -->

# ¿Cuándo usar comunicación sincrónica?

Cuando la respuesta es necesaria inmediatamente Para consultas y operaciones CRUD básicas Cuando la latencia baja es crítica

En validaciones que bloquean flujos de negocio

Ejemplo: Validar que un departamento existe antes de registrar un empleado.

---

<!-- Pagina 12 de 58 -->

# Remote Procedure Invocation (REST)

---

<!-- Pagina 13 de 58 -->

# REST - Representational State Transfer

Problema: ¿Cómo se comunican los microservicios en una arquitectura de microservicios?

Posible solución: Se hace uso de un protocolo tipo solicitud/respuesta para realizar solicitudes a los servicios (REST).

Características:

- Basado en recursos identificados por URIs

- Métodos HTTP semánticos (GET, POST, PUT, DELETE)

- Sin estado (stateless)

- Formato de intercambio: JSON/XML

---

<!-- Pagina 14 de 58 -->

## Beneficios

   - Simple y ampliamente adoptado

   - Fácil de entender y depurar

   - No requiere intermediario

   - Compatible con cualquier lenguaje

- Dificultades

   - Acoplamiento temporal entre servicios (disponibilidad reducida)

   - Se requiere conocer la ubicación del servicio

   - Latencia acumulativa en cadenas de llamadas

   - Vulnerabilidad a fallos en cascada

   - No admite otros patrones de interacción

---

<!-- Pagina 15 de 58 -->

# Ejemplo: Servicio de Empleados → Departamentos

```
POST/empleadosHTTP/1.1
Content-Type: application/json
{
"nombre": "Juan Pérez",
"departamentoId": "IT"
}
```

El servicio de empleados debe validar que el departamento existe:

```
GET/departamentos/ITHTTP/1.1
HTTP/1.1200 OK
{"id": "IT", "nombre": "Tecnología"}
```

---

<!-- Pagina 16 de 58 -->

Comunicación Cliente → Microservicios (API Gateway Pattern)

---

<!-- Pagina 17 de 58 -->

# API Gateway

Hemos visto cómo los microservicios se comunican entre sí. Pero, ¿cómo acceden los clientes externos a estos servicios?

- Problema: Un cliente necesitaría conocer la ubicación de cada microservicio y manejar múltiples endpoints. ¿Cómo acceden los clientes de una aplicación basada en microservicios a los servicios individuales?

Solución: Implementar un punto de entrada único que enruta las peticiones a los servicios internos apropiados.

- Se direcciona la solicitud del cliente a través de un proxy.

- Se extiende en llamadas a múltiples servicios.

---

<!-- Pagina 18 de 58 -->

<!-- Start of picture text -->
API Gateway - Diagrama<br><!-- End of picture text -->


<!-- Start of picture text -->
🌐  Cliente<br>🚪  API Gateway (Traefik /<br>Kong)<br>Empleados Deps Perfiles<br><!-- End of picture text -->

---

<!-- Pagina 19 de 58 -->

# API Gateway - Rol en la comunicación

Función Descripción Enrutamiento Dirigir peticiones al servicio correcto Composición Agregar respuestas de múltiples servicios Load Balancing Distribuir carga entre instancias Traducción de protocolos Adaptar protocolos entre cliente y servicios

Nota: El API Gateway también puede asumir responsabilidades transversales como autenticación, rate limiting y CORS, pero estos aspectos se abordan en el contexto de seguridad e infraestructura.

---

<!-- Pagina 20 de 58 -->

## Beneficios

   - Desacopla a los clientes de la topología interna de servicios

   - Permite evolucionar y reorganizar servicios sin afectar clientes

   - Aísla a los clientes de problemas de ubicación de servicios.

   - Simplifica la comunicación desde el cliente (un solo endpoint)

   - Reduce el número de solicitudes del cliente.

   - Permite ocultar los mecanismos internos de comunicación.

- Dificultades

   - Punto único de fallo (requiere alta disponibilidad)

   - Puede convertirse en cuello de botella de comunicación

   - Introduce latencia adicional en cada petición

   - Mayor complejidad

---

<!-- Pagina 21 de 58 -->

# Traefik como API Gateway

```
services:
traefik:
image:traefik:v3.0
command:
-"--providers.docker=true"
-"--entrypoints.web.address=:80"
ports:
-"80:80"
volumes:
-/var/run/docker.sock:/var/run/docker.sock
empleados-service:
labels:
-"traefik.http.routers.emp.rule=PathPrefix(`/api/empleados`)"
```

---

<!-- Pagina 22 de 58 -->

# Backend for Frontend

Problema: Un único API Gateway debe servir a clientes con necesidades muy diferentes (web, móvil, IoT). Esto genera respuestas genéricas que no son óptimas para ninguno. ¿Cómo acceden los clientes de una aplicación basada en microservicios a los servicios individuales?

Solución: Crear un Gateway especializado por tipo de cliente, que adapte la comunicación a las necesidades específicas de cada uno.

- Se direcciona la solicitud del cliente a través de un proxy.

- Se extiende en llamadas a múltiples servicios.

- Se puede exponer un api diferente a cada “cliente”

---

<!-- Pagina 23 de 58 -->

<!-- Start of picture text -->
BFF - Diagrama<br>📱  Móvil 🌐  Web 🤖  IoT<br>BFF Móvil BFF Web BFF IoT<br>Deps Empleados Perfiles<br><!-- End of picture text -->

---

<!-- Pagina 24 de 58 -->

BFF - ¿Qué adapta cada Backend?

Aspecto BFF Web BFF Móvil Datos Respuestas completas y detalladas Payloads compactos y optimizados Agregación Múltiples recursos en una vista Solo datos esenciales por pantalla Formato JSON extenso con metadatos JSON mínimo, sin campos opcionales Ejemplo: Para listar empleados, el BFF Web retorna nombre, departamento, historial y foto. El BFF Móvil retorna solo nombre y departamento.

---

<!-- Pagina 25 de 58 -->

### Beneficios

   - Comunicación optimizada para cada tipo de cliente

   - Equipos frontend pueden evolucionar su BFF independientemente

   - Evita un Gateway genérico que no satisface a nadie

   - Oculta a los clientes la estructura interna del sistema.

   - Aísla a los clientes de problemas de ubicación de servicios.

   - Reduce el número de solicitudes del cliente.

   - Permite ocultar los mecanismos internos de comunicación.

- Dificultades

   - Duplicación de lógica entre BFFs (requiere disciplina)

   - Mayor cantidad de servicios a mantener y desplegar

   - Riesgo de que el BFF acumule lógica de negocio

   - Mayor complejidad

   - Aumento en los tiempos de respuesta

---

<!-- Pagina 26 de 58 -->

# Patrones de Resiliencia

---

<!-- Pagina 27 de 58 -->

# El problema de los fallos en cascada

## Cuando un servicio falla o está lento:

```
Cliente → Gateway → Empleados → Departamentos
                        ↑
                   (esperando...)
                        ↓
 Timeout
                        ↓
 Recursos agotados
```

Un servicio lento puede agotar recursos de todos los servicios upstream.

---

<!-- Pagina 28 de 58 -->

# Patrones de Resiliencia

Patrón Propósito Circuit Breaker Detener llamadas a servicios fallidos Timeout Limitar tiempo de espera Retry Reintentar operaciones fallidas Fallback Proporcionar respuesta alternativa Bulkhead Aislar recursos por servicio

---

<!-- Pagina 29 de 58 -->

# Circuit Breaker

---

<!-- Pagina 30 de 58 -->

Circuit Breaker

Problema: ¿Cómo prevenir que un servicio siga llamando a otro que está fallando? Solución: Implementar un "interruptor" que detecta fallos y evita llamadas innecesarias.

---

<!-- Pagina 31 de 58 -->

<!-- Start of picture text -->
CLOSED<br>N fallos<br>OPEN 1 éxito<br>timeout 1 fallo<br>HALF_OPEN<br><!-- End of picture text -->

---

<!-- Pagina 32 de 58 -->

Comportamientoomportamientoamientomientoientonto

Estado Comportamientoomportamientoamientomientoientonto CLOSED Llamadas fluyen normalmente. Se cuentan fallos. OPEN Llamadas bloqueadas inmediatamente. Retorna fallback. HALF-OPEN Permite una llamada de prueba. Si falla → OPEN. Si éxito → CLOSED.

---

<!-- Pagina 33 de 58 -->

Parámetro Valor típico Descripción `failureThreshold` 5 Fallos para abrir el circuito `successThreshold` 2 Éxitos para cerrar el circuito `timeout` 30s Tiempo en estado OPEN `requestTimeout` 5s Timeout por llamada individual

---

<!-- Pagina 34 de 58 -->

# Circuit Breaker - Ejemplo conceptual

```
defregistrar_empleado(empleado):
if circuit_breaker.is_open():
return fallback_response()
try:
       response = http.get(f"/departamentos/{empleado.dept_id}",
                          timeout=5)
       circuit_breaker.record_success()
return crear_empleado(empleado, response)
except Exception:
       circuit_breaker.record_failure()
if circuit_breaker.should_open():
           circuit_breaker.open()
return fallback_response()
```

---

<!-- Pagina 35 de 58 -->

# Timeout y Retry

---

<!-- Pagina 36 de 58 -->

# Timeout

Problema: Un servicio lento puede bloquear recursos indefinidamente. Solución: Establecer un tiempo máximo de espera para cada llamada.

Recomendación: El timeout debe ser menor que el tiempo que el usuario está dispuesto a esperar.

```
response = http.get("/departamentos/IT", timeout=5)  # 5 segundos max
```

---

<!-- Pagina 37 de 58 -->

# Retry con Backoff Exponencial

Problema: Un fallo momentáneo no debería causar error permanente. Solución: Reintentar con espera incremental entre intentos.

```
Intento 1: fallo → espera 1s
Intento 2: fallo → espera 2s
Intento 3: fallo → espera 4s
Intento 4: éxito ✓
```

Importante: Agregar jitter (variación aleatoria) para evitar que todos los clientes reintenten al mismo tiempo.

---

<!-- Pagina 38 de 58 -->

<!-- Start of picture text -->
Retry - Cuándo reintentar<br><!-- End of picture text -->

Reintentar ✓ No reintentar ✗ Timeout de red Error 400 Bad Request Error 503 Service Unavailable Error 401 Unauthorized Error de conexión Error 404 Not Found Error de validación

Regla: Solo reintentar errores transitorios (que podrían solucionarse espontáneamente).

---

<!-- Pagina 39 de 58 -->

# Fallback y Bulkhead

---

<!-- Pagina 40 de 58 -->

# Fallback

Problema: ¿Qué respuesta dar cuando un servicio no está disponible?

Solución: Proporcionar una respuesta alternativa que permita continuar.

Estrategias de Fallback:

- Retornar valor por defecto

- Usar datos en caché

- Degradar funcionalidad (registrar sin validar)

Retornar mensaje explicativo

---

<!-- Pagina 41 de 58 -->

# Fallback - Ejemplo

```
defvalidar_departamento(dept_id):
try:
       response = http.get(f"/departamentos/{dept_id}", timeout=5)
return {"valido": True, "departamento": response}
except ServiceUnavailable:
# Fallback: permitir registro con validación pendiente
return {
"valido": None,
"mensaje": "Validación pendiente. Se verificará posteriormente."
       }
```

---

<!-- Pagina 42 de 58 -->

# Bulkhead (Mamparo)

Problema: Un servicio lento consume todos los recursos disponibles.

Solución: Aislar recursos para diferentes dependencias.

Analogía: Los mamparos en un barco evitan que una fuga inunde todo el navío.

- `┌────────────────────────────┐ │     Thread Pool Total      │`

- `│  ┌─────────┐  ┌─────────┐  │`

- `│  │ Deps: 5 │  │Auth: 10 │  │ │  │ threads │  │ threads │  │ │  └─────────┘  └─────────┘  │ └────────────────────────────┘`

---

<!-- Pagina 43 de 58 -->

# Resumen: Defensa en profundidad

- `┌─────────────────┐ │    Timeout      │  ← Limita espera individual`

- `├─────────────────┤`

- `│     Retry       │  ← Recupera de fallos transitorios ├─────────────────┤`

- `│ Circuit Breaker │  ← Detiene avalancha de fallos`

- `├─────────────────┤`

- `│    Fallback     │  ← Respuesta alternativa`

- `├─────────────────┤`

- `│    Bulkhead     │  ← Aísla impacto └─────────────────┘`

---

<!-- Pagina 44 de 58 -->

# Bibliotecas de Resiliencia

Lenguaje Biblioteca Características Java Resilience4j Circuit Breaker, Retry, Bulkhead, Rate Limiter Python pybreaker, tenacity Circuit Breaker, Retry Go go-resiliency Circuit Breaker, Retry, Deadline Circuit Breaker con métricas Node.js opossum .NET Polly Retry, Circuit Breaker, Fallback

---

<!-- Pagina 45 de 58 -->

```
@CircuitBreaker(name = "departamentos", fallbackMethod = "fallback")
@Retry(name = "departamentos")
```

```
@TimeLimiter(name = "departamentos")
public CompletableFuture<Departamento> getDepartamento(String id) {
return CompletableFuture.supplyAsync(() ->
```

```
       restTemplate.getForObject("/departamentos/" + id,
                                  Departamento.class));
```

```
}
```

```
public CompletableFuture<Departamento> fallback(String id, Exception e) {
return CompletableFuture.completedFuture(
newDepartamento(id, "Pendiente validación", "UNKNOWN"));
```

```
}
```

---

<!-- Pagina 46 de 58 -->

# Messaging (Comunicación Asincrónica)

---

<!-- Pagina 47 de 58 -->

# Messaging

Problema: ¿Cómo se comunican los servicios en una arquitectura de microservicio? Posible Solución: Usar mensajería asincrónica para la comunicación entre servicios. Servicios que se comunican mediante el intercambio de mensajes a través de canales de mensajería. Se tiene estilos como:

- `Solicitud / respuesta`

- `Notificaciones`

- `Solicitud / respuesta asincrónica`

- `Publicar / suscribirse`

- `Publicar / respuestas asincrónica`

-

---

<!-- Pagina 48 de 58 -->

# Messaging - Beneficios y Dificultades

- Beneficios

   - Bajo acoplamiento

   - Disponibilidad mejorada

   - Admite una variedad de patrones de comunicación

- Dificultades

   - Complejidad adicional del agente de mensajería

   - Comunicación solicitud / respuesta es más compleja

---

<!-- Pagina 49 de 58 -->

Domain-specific Protocol

---

<!-- Pagina 50 de 58 -->

# Domain-specific Protocol

Problema: ¿Cómo se comunican los microservicios en una arquitectura de microservicios?

Posible Solución: Se hace uso de un protocolo específico del dominio para la comunicación entre microservicios.

SMPT, IMAP

Media Streaming (RTMP, HLS)

---

<!-- Pagina 51 de 58 -->

# Domain-specific Protocol - Beneficios y Dificultades

Beneficios Conocido y probado.

Dificultades

Puede llegar a ser poco flexible.

---

<!-- Pagina 52 de 58 -->

Idempotent Consumer

---

<!-- Pagina 53 de 58 -->

# Idempotent Consumer

Problema: ¿Cómo pueden manejar un consumidor los mensajes duplicados? Posible Solución: Implementar consumidores idempotentes, bien sea que de forma natural lo sean, o mediante el registro de los mensajes ya procesados.

---

<!-- Pagina 54 de 58 -->

# Idempotent Consumer - Beneficios y Dificultades

Beneficios

Evita el procesamiento repetido de mensajes. Dificultades

Requiere la implementación de estructuras adicionales de almacenamiento para el registro de los mensajes procesados.

---

<!-- Pagina 55 de 58 -->

Mejores Prácticas

---

<!-- Pagina 56 de 58 -->

1. Definir timeouts explícitos en todas las llamadas HTTP 2. Implementar circuit breakers para dependencias externas

3. Diseñar fallbacks significativos para el negocio

4. Monitorear estados de circuit breakers

5. Documentar comportamiento degradado

6. Probar escenarios de fallo regularmente

---

<!-- Pagina 57 de 58 -->

Antipatrones a evitar

Antipatrón Problema Sin timeout Bloqueo indefinido de recursos Retry infinito Amplificación de carga Fallback que falla Cascada de errores Circuit Breaker muy sensible Cortes frecuentes innecesarios Ignorar métricas No detectar problemas a tiempo

---

<!-- Pagina 58 de 58 -->

Arquitectura Basada en Microservicios Programa de Ingeniería de Sistemas y Computación Universidad del Quindío


2025 Christian Andrés Candela Uribe
