<!-- Pagina 1 de 5 -->

# **Reto 1 – Servidor Web para Gestión Básica de Empleados**

## **Contexto**

Este reto hace parte de una serie de ejercicios progresivos cuyo objetivo final es construir un **sistema de onboarding y offboarding de empleados** , basado en una **arquitectura orientada a microservicios** .

En este primer reto se trabajará una versión mínima del sistema, enfocada en:

- Desarrollo de servicios web

- Manejo básico de solicitudes HTTP

- Definición de una estrategia inicial de despliegue

## **Objetivo**

Iniciar el desarrollo de un sistema backend mediante la construcción de un **servicio web simple** , junto con su **estrategia de despliegue en contenedores** , que sirva como base para retos posteriores donde se incorporarán nuevos servicios, reglas de negocio y capacidades arquitectónicas.

## **Requisitos generales**

La solución desarrollada debe cumplir con los siguientes requisitos:

- Implementar un servidor web accesible desde `http://localhost` .

- Exponer endpoints HTTP para el registro y consulta de empleados.

- Manejar correctamente rutas, métodos HTTP y códigos de estado.

- Permitir la ejecución de la aplicación dentro de un contenedor Docker.

- Facilitar su prueba mediante herramientas externas de consumo de APIs.

---

<!-- Pagina 2 de 5 -->

## **1. Registro de un empleado**

#### **Ruta:**

```
 POST http://localhost/empleados
```

#### **Descripción:**

Esta operación permite registrar un empleado en el sistema.

#### **Entrada:**

El cuerpo de la solicitud debe contener la información del empleado

(por ejemplo: `id` , `nombre` , `cargo` ).

#### **Respuesta exitosa:**

Código de estado: `200 OK`

Cuerpo de la respuesta: la información del empleado registrado.

## **2. Consulta de un empleado por id**

#### **Ruta:**

```
 GET http://localhost/empleados/{id}
```

#### **Descripción:**

Esta operación permite consultar la información de un empleado a partir de su identificador.

#### **Respuesta exitosa:**

- Código de estado: `200 OK`

- Cuerpo de la respuesta: la información del empleado correspondiente al `{id}` solicitado.

#### **Si el empleado no existe:**

- Código de estado: `404 Not Found`

- Cuerpo de la respuesta:

```
El empleado con id {id} no existe
```

## **3. Rutas no soportadas**

Para cualquier otra ruta o método HTTP no definido anteriormente, el servidor debe responder:

Código de estado: `404 Not Found`

---

<!-- Pagina 3 de 5 -->

Recurso no encontrado

## **4. Pruebas del servidor**

Verifique el correcto funcionamiento de su aplicación utilizando alguna de las siguientes herramientas:

- Bruno

- curl

- Postman

- u otra herramienta similar para realizar solicitudes HTTP

## **5. Contenerización de la aplicación**

Cree un contenedor para el despliegue de la aplicación utilizando **Docker** .

La solución debe cumplir con los siguientes requisitos:

- Incluir un archivo `Dockerfile` en el proyecto.

- Exponer el puerto en el que se ejecuta el servidor.

- Permitir la ejecución de la aplicación mediante los comandos:

```
docker build -t servidor-empleados .
docker run -p8080:8080 servidor-empleados
```

El puerto puede ajustarse según la implementación del estudiante

## **6. Modelo canónico del empleado**

El empleado que se define aquí **es el mismo que acompañará todo el semestre y el proyecto final** .

---

<!-- Pagina 4 de 5 -->

Definirlo completo desde el inicio evita tener que migrarlo en cada reto.

```
{
"id":"E001",
"nombre":"Juan",
"apellido":"Pérez",
"email":"juan.perez@empresa.com",
"numeroEmpleado":"EMP-2026-001",
"cargo":"Desarrollador Senior",
"area":"Tecnología",
"departamentoId":"IT",
"fechaIngreso":"2026-02-10",
"estado":"ACTIVO"
}
```

El campo `departamentoId` queda declarado desde ya, aunque el servicio de departamentos no exista hasta el Reto 2. En este reto es simplemente un texto libre.

### **Estados del empleado**

```
ACTIVO ──────────► EN_VACACIONES ──────────► ACTIVO
   │                     │
   └─────────────────────┴──────────────────► RETIRADO   (estado final)
```

|**Estado**|**Significado**|
|---|---|
|`ACTIVO`|Empleado vinculado y con acceso al sistema|
|`EN_VACACIONES`|Vinculado, pero con el acceso suspendido temporalmente (Reto 4 y 5)|
|`RETIRADO`|Desvinculado.**Estado final**: el registro se conserva para auditoría, nunca se<br>borra|


En este reto solo se maneja `ACTIVO` . Las transiciones se implementan más adelante, pero el campo debe existir desde ahora.

### **Validaciones requeridas**

Al registrar un empleado, el servicio debe rechazar con `400 Bad Request` y un mensaje descriptivo:

Un `email` que ya esté registrado.

---

<!-- Pagina 5 de 5 -->

## **Consideraciones**

- No es obligatorio el uso de base de datos.

- Los empleados pueden almacenarse en memoria utilizando estructuras de datos simples.

- Este servicio será extendido y complementado en retos posteriores.

- Las decisiones tomadas en este reto servirán como base para la evolución hacia una

- arquitectura orientada a microservicios.

## **Criterios de Evaluación**

El reto se evalúa sobre **5 puntos** , distribuidos de la siguiente forma:

|**#**<br>**Elemento**|**Valor**|**Aspectos a evaluar**|
|---|---|---|
|1<br>**Registro de**<br>**empleados**|1.0|`POST /empleados`funcional, retorna el empleado<br>registrado con el código de estado correcto.|
|2<br>**Consulta y manejo**<br>**de rutas**|1.0|`GET /empleados/{id}`funcional.<br>`404`con el mensaje<br>exacto cuando el empleado no existe.<br>`404`con "Recurso<br>no encontrado" para cualquier otra ruta o método.|
|3<br>**Modelo canónico y**<br>**validaciones**|1.0|Todos los campos del modelo implementados, incluido<br>`estado`. Validación de unicidad de<br>`email`y<br>`numeroEmpleado`con respuesta<br>`400`descriptiva.|
|4<br>**Contenerización**|1.5|`Dockerfile`correcto, puerto expuesto, la aplicación se<br>construye y ejecuta con los comandos indicados.|
|5<br>**Pruebas y**<br>**documentación**|0.5|Evidencia de las pruebas con Bruno/curl/Postman.<br>README con instrucciones de construcción y ejecución.|
