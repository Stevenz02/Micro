# Microservicios

Este repositorio contiene los retos desarrollados durante la materia de
Microservicios. Cada reto evoluciona progresivamente la arquitectura del sistema
y agrega nuevos conceptos sin reemplazar los retos anteriores.

## Retos

| Reto | Tema | Estado |
| --- | --- | --- |
| [Reto 1](Reto_1/README.md) | Servicio inicial de empleados y contenerizacion | Completado segun contrato documentado; 15 pruebas verificadas |
| [Reto 2](Reto_2/README.md) | Orquestacion de servicios y persistencia de datos | Completado y verificado; [evidencia](Reto_2/VERIFICACION.md) |
| [Reto 3](Reto_3/README.md) | API Gateway y resiliencia | Implementacion funcional pre-Docker completada. Pendiente: dockerizacion, aislamiento de puertos y evidencias runtime |

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
+-- Reto_3/                   # Gateway y Circuit Breaker pre-Docker
    +-- .env.example
    +-- api-gateway/
    +-- empleados/
    +-- departamentos/
    +-- tests/
    +-- docs/
    +-- AUDITORIA.md
    +-- VERIFICACION.md
    +-- README.md
```

Reto 2 importa el modelo de `Reto_1/app/models.py` y lo incorpora en su imagen
durante la construccion. Reto 3 copia esa base funcional y agrega un API Gateway
en FastAPI/httpx y Circuit Breaker con `pybreaker` en la comunicacion
`empleados -> departamentos`.

## Prerrequisitos generales

- Git.
- Docker Engine con Docker Compose v2 para los retos que ya tienen Compose.
- Python 3.12 o 3.13.
- Node.js 22 y npm para departamentos.

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
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose down
```

Reto 3, fase pre-Docker:

```powershell
Set-Location D:\Repositorios_UQ\Micro
.\.venv\Scripts\python.exe -m pip install -r Reto_3/requirements-test.txt
.\.venv\Scripts\python.exe -m pytest Reto_3/tests -q
npm --prefix Reto_3/departamentos ci
npm --prefix Reto_3/departamentos test
```

Reto 3 todavia no debe declararse cerrado como entrega Docker. Queda pendiente
crear Compose, publicar solo el Gateway, dejar empleados/departamentos sin acceso
directo desde el host y capturar evidencias runtime.

## Tecnologias utilizadas

Python, FastAPI, Pydantic, Uvicorn, HTTPX, Psycopg, pybreaker, JavaScript,
Node.js, Express, node-postgres, PostgreSQL 16, Docker, Compose,
OpenAPI/Swagger, pytest y `node:test`.
