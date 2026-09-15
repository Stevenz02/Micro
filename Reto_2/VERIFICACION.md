# Verificación ejecutada

Fecha local: **14 de septiembre de 2026**, America/Bogota.
Entorno: Windows, Docker Desktop con motor Linux 28.4.0, Python local 3.13.7,
Node local 22.20.0. Imágenes: Python 3.12 slim, Node 22 Alpine, PostgreSQL 16 Alpine.

## Resultado

**Reto 2 implementado y verificado con contenedores reales.** Reto 1 conserva
su código, modelo, contratos y pruebas; solo se corrigió el nombre de `.dockerignore`.

| Comprobación | Resultado observado |
|--------------|---------------------|
| Auditoría inicial de Reto 1 | 15 pruebas aprobadas, antes de los cambios |
| Construcción Reto 1 | `docker build --no-cache` exitosa |
| Reto 1 dentro de su imagen Python 3.12 | 15 pruebas aprobadas |
| Reto 1 desde HTTP del host | POST 200, GET devuelve diez campos, `/docs` 200 |
| Construcción de ambas APIs de Reto 2 | `docker compose build --no-cache` exitosa |
| Configuración Compose | `docker compose config --quiet` exitosa |
| Unitarias empleados Reto 2 | 24 aprobadas |
| Unitarias departamentos | 12 aprobadas |
| Arranque desde volúmenes vacíos | Cuatro contenedores running/healthy |
| POST departamento IT | 201 y modelo íntegro |
| POST empleado E001 | 201 y diez campos íntegros, ACTIVO |
| GET por id y listado de ambas APIs | 200, valores originales conservados |
| Inexistentes | GET 404 descriptivo en ambas APIs |
| Duplicados | email, número, id de empleado e id de departamento → 400 |
| Orden de validación | email antes de número; ambos antes del departamento inexistente |
| Departamento inexistente | POST empleado → 400, sin insertar |
| Estado INACTIVO | 422, sin insertar |
| Concurrencia | 8 solicitudes por clave (email, número, id): 1 alta y 7 respuestas 400 por grupo |
| Restricciones SQL | UNIQUE de email y número, y PRIMARY KEY de id comprobados en `pg_constraint` |
| Aislamiento | Desde cada API falla la resolución DNS de la BD ajena; ambas redes de BD son independientes |
| Timeout real | Departamento pausado; 4 intentos, esperas 1/2/4 s, respuesta 503 en 15,2 s |
| Fallo cerrado | GET `/empleados/FALLO` → 404 tras el timeout; no se insertó |
| `down` y posterior `up -d` | IT, E001 y empleados concurrentes permanecieron |
| `down -v` y posterior `up -d --build` | Listas vacías; GET de IT/E001 → 404 |
| Reinicialización | Cuatro healthy y logs de arranque sin errores de conexión |
| OpenAPI | Ambos documentos accesibles y contratos/respuestas comprobados |
| Swagger en navegador real | Edge headless: 4 operaciones por API, POST 201 y GET 200 desde Try it out, sin errores JavaScript |
| Higiene Git | `.env` fuera del índice, plantilla disponible, cachés/dependencias ignoradas |

Las pruebas Python emiten un aviso de obsolescencia de Starlette/TestClient por
un alias de AnyIO; no hay fallos de prueba asociados. No se actualizaron las
dependencias originales del Reto 1 para ocultar ese aviso.

## Evidencia de la prueba integral

Comando desde la raíz:

```powershell
.\.venv\Scripts\python.exe -u Reto_2\tests\e2e.py
```

Proyecto generado: `micro-reto2-e2e-5b6ca33e`. Puertos asignados: empleados 58486,
departamentos 58487. Finalizó con código 0. Resumen emitido:

```text
OK: arranque limpio y cuatro servicios healthy
OK: Swagger, altas, consultas, diez campos, validaciones y orden
OK: 24 peticiones concurrentes; tres altas y 21 duplicados controlados
OK: timeout real, tres reintentos y 503 sin inserción (15.2s)
OK: down conserva empleados y departamentos completos
OK: down -v borra datos, reinicialización limpia y cuatro healthy
E2E COMPLETO: todas las comprobaciones pasaron
```

El script eliminó únicamente sus contenedores y volúmenes al terminar. Las pruebas
de `down -v` no se ejecutaron sobre volúmenes ajenos. El motor tenía inicialmente
otros volúmenes de proyectos distintos, que se conservaron.

## Estado final del Compose habitual

Después de la prueba aislada se ejecutó desde `Reto_2`:

```powershell
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

Resultado observado (se omiten tiempos variables):

```text
NAME                              SERVICE                  STATUS         PORTS
reto_2-database-departamentos-1    database-departamentos   Up (healthy)
reto_2-database-empleados-1        database-empleados       Up (healthy)
reto_2-departamentos-service-1     departamentos-service    Up (healthy)   127.0.0.1:8081->8081/tcp
reto_2-empleados-service-1         empleados-service        Up (healthy)   127.0.0.1:8080->8080/tcp
```

El sistema quedó ejecutándose y con IT/E001 creados desde Swagger por la prueba
de navegador. Las URLs son <http://localhost:8080/docs> y
<http://localhost:8081/docs/>. Los puertos PostgreSQL no están publicados.

Los logs de inicialización muestran el arranque y cierre esperado del servidor
temporal de PostgreSQL antes del servidor definitivo. No representan un fallo de
conexión de las APIs. Las pruebas de duplicados pueden generar errores de restricción
en logs de PostgreSQL; las APIs los convierten en respuestas 400 controladas.

## Archivos creados

```text
README.md
.dockerignore
Reto_2/.env.example
Reto_2/AUDITORIA.md
Reto_2/VERIFICACION.md
Reto_2/requirements-test.txt
Reto_2/empleados/README.md
Reto_2/empleados/requirements.txt
Reto_2/empleados/app/__init__.py
Reto_2/empleados/app/config.py
Reto_2/empleados/app/departamentos.py
Reto_2/empleados/app/main.py
Reto_2/empleados/app/models.py
Reto_2/empleados/app/repository.py
Reto_2/departamentos/.dockerignore
Reto_2/departamentos/README.md
Reto_2/departamentos/package.json
Reto_2/departamentos/package-lock.json
Reto_2/departamentos/src/config.js
Reto_2/departamentos/src/repository.js
Reto_2/departamentos/src/openapi.js
Reto_2/departamentos/src/app.js
Reto_2/departamentos/src/index.js
Reto_2/departamentos/tests/app.test.js
Reto_2/tests/test_empleados_service.py
Reto_2/tests/e2e.py
Reto_2/tests/swagger_browser.py
```

## Archivos modificados, renombrados o retirados del índice

- `.gitignore`.
- `Reto_1/dockerignore` → `Reto_1/.dockerignore` (renombrado y exclusión de `.env`).
- `Reto_2/README.md`.
- `Reto_2/docker-compose.yml`.
- `Reto_2/empleados/Dockerfile` e `init.sql`.
- `Reto_2/departamentos/Dockerfile` e `init.sql`.
- `Reto_2/.env`: retirado del índice con `git rm --cached`; archivo local conservado.

## Alcance y límites

- Se verificaron todos los flujos obligatorios de este reto; no queda una prueba
  obligatoria pendiente por ausencia de Docker u otra herramienta.
- No se realizó una migración de datos antiguos: inicialmente no había volúmenes
  de este proyecto. La estrategia para bases ya inicializadas está documentada,
  pero no se presenta como una migración implementada o probada.
- Se verificó Swagger con Edge en este equipo, no todos los navegadores ni el modo
  sin internet de los recursos CDN de FastAPI.
- No se certifican requisitos del Reto 1 que no figuren en su contrato disponible.
- No se realizaron commits ni publicaciones remotas.
