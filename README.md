# Microservicios

Este repositorio contiene los retos desarrollados durante la materia de
Microservicios. Cada reto evoluciona progresivamente la arquitectura del sistema
y agrega nuevos conceptos sin reemplazar los retos anteriores.

## Retos

| Reto | Tema | Estado |
| --- | --- | --- |
| [Reto 1](Reto_1/README.md) | Servicio inicial de empleados y contenerizacion | Completado segun contrato documentado; 15 pruebas verificadas |
| [Reto 2](Reto_2/README.md) | Orquestacion de servicios y persistencia de datos | Completado y verificado; [evidencia](Reto_2/VERIFICACION.md) |
| [Reto 3](Reto_3/README.md) | API Gateway y resiliencia | Completado y verificado con Docker Compose: punto de entrada unico, Circuit Breaker probado en runtime (ver seccion 18 del README del reto) |
| [Reto 4](Reto_4/HANDOFF_RETO4.md) | Eventos RabbitMQ, perfiles, notificaciones y vacaciones | Logica y despliegue verificados segun el handoff tecnico del reto |
| [Reto 5](Reto_5/README.md) | JWT, eventos y control de acceso | Logica de Auth, Gateway, Notificaciones y scheduler probada localmente; Docker y flujo integrado pendientes |

## Estructura general

```text
Micro/
+-- README.md
+-- .gitignore
+-- .dockerignore
+-- Reto_1/                   # Python/FastAPI, almacenamiento en memoria
|   +-- app/
|   +-- tests/
|   +-- Dockerfile
|   +-- README.md
+-- Reto_2/                   # Dos APIs y dos bases independientes
|   +-- docker-compose.yml
|   +-- .env.example
|   +-- empleados/
|   +-- departamentos/
|   +-- tests/
|   +-- AUDITORIA.md
|   +-- VERIFICACION.md
|   +-- README.md
+-- Reto_3/                   # Gateway y Circuit Breaker, con Docker Compose
|   +-- docker-compose.yml
|   +-- .env.example
|   +-- api-gateway/
|   +-- empleados/
|   +-- departamentos/
|   +-- tests/
|   +-- docs/
|   +-- AUDITORIA.md
|   +-- VERIFICACION.md
|   +-- README.md
+-- Reto_4/                   # Eventos de RR. HH. con RabbitMQ
+-- Reto_5/                   # Codigo de seguridad y guia de integracion
```

Reto 2 importa el modelo de `Reto_1/app/models.py` y lo incorpora en su imagen
durante la construccion. Reto 3 hace lo mismo y agrega un API Gateway en
FastAPI/httpx y Circuit Breaker con `pybreaker` en la comunicacion
`empleados -> departamentos`. En ambos casos, el Dockerfile de `empleados` usa
como contexto de build la raiz del repositorio (no su propia carpeta), porque
necesita copiar ese modelo compartido durante la construccion de la imagen.

## Prerrequisitos generales

- Git.
- Docker Engine con Docker Compose v2; en Windows, Docker Desktop iniciado con
  contenedores Linux y WSL 2.
- Python 3.12 o 3.13 (para pruebas locales sin Docker).
- Node.js 22 y npm para departamentos (para pruebas locales sin Docker).
- Puertos 8080, 8081 y 8082 disponibles. Reto 1, Reto 2 y Reto 3 publican
  puertos que pueden coincidir entre si: ejecutar un reto a la vez, o ajustar
  los puertos publicados en su `.env`.

## Entrar a cada reto

Reto 1:

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_1
docker build -t servidor-empleados .
docker run --rm -p 8080:8080 servidor-empleados
```

Reto 2:

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_2
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose down
```

Reto 3:

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_3
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
# En otra terminal ubicada en Reto_3:
docker compose ps

# Verificar el punto de entrada unico: debe funcionar
curl http://localhost:8080/empleados
curl http://localhost:8080/departamentos
# Acceso directo: debe FALLAR (conexion rechazada)
curl http://localhost:8081/empleados
curl http://localhost:8082/departamentos

docker compose down
```

La prueba completa del Circuit Breaker (creacion de un departamento, caida del
servicio, salto en el tiempo de respuesta y recuperacion automatica) esta
documentada paso a paso en la seccion 18 de `Reto_3/README.md`.

Los ejemplos de solicitudes, Swagger, pruebas y gestion de volumenes estan en el
README de cada reto. No hay un Compose en la raiz; los retos 2, 3 y 4 tienen
configuraciones de ejecucion independientes.

Reto 5 todavia no tiene configuracion Docker. Su estado y pruebas locales se
describen en [Reto_5/README.md](Reto_5/README.md). Los contratos de eventos se
verificaron con el Catálogo oficial de Eventos; falta probarlos entre servicios.

## Tecnologias utilizadas

Python, FastAPI, Pydantic, Uvicorn, HTTPX, Psycopg, pybreaker, PyJWT,
bcrypt, JavaScript, Node.js, Express, node-postgres, Go, Java/Spring Boot,
.NET 8, PostgreSQL 16, RabbitMQ, Docker, Compose, OpenAPI/Swagger,
pytest y `node:test`.
