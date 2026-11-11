# Proyecto final · Ecosistema de RR. HH.

Consolidación independiente de los retos 1–8. Implementa el ciclo de vida de empleados
(onboarding, perfil, vacaciones y offboarding) con siete microservicios, RabbitMQ,
observabilidad completa, pruebas automatizadas y una base de CI/CD reproducible.

## Inicio rápido

Requisitos: Docker Desktop con Compose v2 y al menos 10 GB de memoria disponibles.

En PowerShell:

```powershell
cd "Proyecto final"
.\scripts\setup.ps1
docker compose up --build -d --wait --wait-timeout 600
```

El script genera `.env` y una contraseña administrativa aleatoria en
`secrets/admin-password.txt`. Ambos están ignorados por Git. Para rotar todas las
credenciales locales, ejecute `setup.ps1 -Force`.

En Linux/macOS use `./scripts/setup.sh`.

## Accesos

| Componente | URL local |
|---|---|
| API Gateway / Swagger | <http://localhost:8080/docs> |
| Grafana | <http://localhost:3000> |
| Prometheus | <http://localhost:9091> |
| Zipkin | <http://localhost:9411> |
| RabbitMQ Management | <http://localhost:15672> |

El Gateway es el único punto de entrada al negocio. Las bases de datos y los puertos de
los microservicios permanecen aislados en redes internas de Docker.

## CI/CD opcional

```powershell
docker compose --profile ci up --build -d
```

Esto agrega Jenkins (<http://localhost:8090>), SonarQube (<http://localhost:9000>) y un
registry local (`localhost:5001`). Jenkins se configura con JCasC y crea el job
`proyecto-final`, cuyo pipeline compila, prueba los cinco lenguajes, aplica el Quality
Gate de 70 %, construye imágenes y ejecuta las pruebas BDD.

## Pruebas BDD manuales

Con el ecosistema iniciado:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r e2e-tests\requirements.txt
$env:BASE_URL = "http://localhost:8080"
$env:ADMIN_EMAIL = "admin@proyecto.local"
$env:ADMIN_PASSWORD = Get-Content .\secrets\admin-password.txt -Raw
.\.venv\Scripts\python e2e-tests\run.py
```

Los reportes JUnit, Cucumber JSON y HTML se generan en `e2e-tests/reports/` y no se
versionan.

## Estructura

```text
Proyecto final/
├── microservicios/        # Gateway, auth y servicios de dominio (5 lenguajes)
├── e2e-tests/             # Escenarios Behave del ciclo de vida completo
├── observabilidad/        # Prometheus, Grafana, Loki/Promtail y alertas
├── infra/                 # Jenkins/JCasC y aprovisionamiento de SonarQube
├── docs/                  # Arquitectura, trazabilidad y catálogo de eventos
├── scripts/               # Generación segura de la configuración local
├── docker-compose.yml     # Despliegue integral; perfil opcional `ci`
├── Jenkinsfile            # Pipeline del proyecto consolidado
└── sonar-project.properties
```

Consulte [docs/arquitectura.md](docs/arquitectura.md) para el flujo entre servicios y
[docs/trazabilidad-requisitos.md](docs/trazabilidad-requisitos.md) para saber qué parte
del enunciado ya está cubierta y qué validaciones faltan.

## Detener

```powershell
docker compose --profile ci down
```

Agregue `-v` únicamente si también desea eliminar las bases de datos y demás volúmenes
locales.
