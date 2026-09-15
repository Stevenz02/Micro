# Microservicios

Este repositorio contiene los diferentes retos desarrollados durante la materia
de Microservicios. Cada reto evoluciona progresivamente la arquitectura del sistema
y añade nuevos conceptos, tecnologías y patrones.

## Retos

| Reto | Tema | Estado |
|------|------|--------|
| [Reto 1](Reto_1/README.md) | Servicio inicial de empleados y contenerización | Completado según contrato documentado; 15 pruebas verificadas |
| [Reto 2](Reto_2/README.md) | Orquestación de servicios y persistencia de datos | Completado y verificado; [evidencia](Reto_2/VERIFICACION.md) |
| Reto 3 | Próximamente | Pendiente |

Se incorporarán nuevos retos durante el curso. Cada carpeta conserva su ejecución
y documentación propia; no es necesario reemplazar un reto anterior para usar el siguiente.

## Estructura general

```text
Micro/
├── README.md
├── .gitignore
├── .dockerignore
├── Reto_1/                   # Python/FastAPI, almacenamiento en memoria
│   ├── app/                  # Modelo canónico original de empleado
│   ├── tests/
│   ├── Dockerfile
│   └── README.md
└── Reto_2/                   # Dos APIs y dos bases independientes
    ├── docker-compose.yml
    ├── .env.example
    ├── empleados/            # Python/FastAPI + PostgreSQL
    ├── departamentos/        # JavaScript/Express + PostgreSQL
    ├── tests/
    ├── AUDITORIA.md
    ├── VERIFICACION.md
    └── README.md
```

Reto 2 importa el modelo de `Reto_1/app/models.py` y lo incorpora en su imagen
durante la construcción. Esto evita duplicar campos y validaciones; los servicios
se ejecutan independientemente, sin necesitar un contenedor del Reto 1.

## Prerrequisitos generales

- Git.
- Docker Engine con Docker Compose v2; en Windows, Docker Desktop iniciado con
  contenedores Linux y WSL 2.
- Para desarrollo local: Python 3.12 o 3.13; Node.js 22 y npm para departamentos.
- Puertos 8080 y 8081 disponibles. Reto 1 y empleados de Reto 2 usan 8080:
  ejecutarlos por separado o cambiar el puerto publicado.

## Entrar a cada reto

Desde PowerShell:

```powershell
Set-Location D:\Repositorios_UQ\Micro
Set-Location Reto_1
docker build -t servidor-empleados .
docker run --rm -p 8080:8080 servidor-empleados
```

Para Reto 2:

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_2
if (!(Test-Path .env)) { Copy-Item .env.example .env }
docker compose up --build
# En otra terminal ubicada en Reto_2:
docker compose ps
docker compose down
```

Los ejemplos de solicitudes, Swagger, pruebas y gestión de volúmenes están en el
README de cada reto. No hay un Compose en la raíz: cada reto tiene su propio ciclo de ejecución.

## Tecnologías utilizadas

Python, FastAPI, Pydantic, Uvicorn, HTTPX, Psycopg, JavaScript, Node.js, Express,
node-postgres, PostgreSQL 16, Docker, Compose, OpenAPI/Swagger, pytest y `node:test`.
