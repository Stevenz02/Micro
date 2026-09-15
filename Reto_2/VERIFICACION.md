# Verificación ejecutada

## Auditoría final contra el documento del docente

Fuente de verdad: `reto2.pdf`, 19 páginas, proporcionado por el usuario desde
`C:\Users\Usuario\Desktop\reto2.pdf`. SHA-256:
`c3ea5516e2ecc53e8bf60775d7cbd03b8a01544e4832dd82f988887684d90c6d`.
Auditoría final realizada el **14 de septiembre de 2026**, America/Bogota.
Se revisaron los requisitos, entregables (pp. 14–15) y criterios de evaluación
(pp. 18–19), además de los 40 puntos solicitados por el usuario.

### Incumplimientos encontrados y corregidos

1. **Arranque sin pasos manuales (pp. 1 y 10).** Antes era obligatorio copiar
   `.env.example` a `.env`. Compose ahora usa valores públicos de demostración
   por defecto, sobrescribibles por variables de entorno o `.env` local. Las APIs
   siguen leyendo credenciales exclusivamente de su entorno. La prueba E2E
   desactiva la carga del `.env` y elimina credenciales heredadas del host.
2. **Ejemplos de registro del docente (pp. 12–13).** Omiten `estado`; antes eso
   producía 422. Reto 2 ahora hereda el modelo de Reto 1 y asigna ACTIVO cuando se
   omite. Los diez campos se mantienen y persisten. Reto 1 no cambia; otros estados
   siguen siendo inválidos. El E2E verifica el alta y los tres rechazos sin enviar estado.

Se ajustaron las instrucciones de arranque, el contrato documentado y la tabla
servicio/lenguaje/motor/puerto. No se incorporaron funcionalidades adicionales.
Los healthchecks propios existentes se conservaron: el docente permite cualquier
ruta que responda 200 (pp. 5–6); no se añadieron métricas, trazas ni observabilidad.
Ambas bases pueden usar 5432 internamente porque son contenedores y redes separados;
el 5433 del diagrama ilustrativo no es un requisito de publicación de puertos.

### Tabla final de cumplimiento

Las rutas de esta tabla son relativas a `Reto_2/`, excepto las indicadas explícitamente.
`E2E` significa `python Reto_2/tests/e2e.py` desde la raíz, ejecutado nuevamente
después de las correcciones, con salida 0.

| Requisito docente / comprobación de entrega | Estado | Evidencia |
|-------------------------------------------|--------|-----------|
| 1. Compose y arranque ordenado | CUMPLE | `docker-compose.yml`; E2E sin .env y logs sin errores de conexión |
| 2. Healthchecks de ambas bases | CUMPLE | `pg_isready` TCP + consulta SQL; cuatro healthy |
| 3. depends_on con service_healthy | CUMPLE | Dependencias declaradas en `docker-compose.yml` |
| 4. Red Docker | CUMPLE | Red de APIs y dos redes internas de BD en Compose |
| 5. Volúmenes independientes | CUMPLE | `vol-empleados`, `vol-departamentos`; E2E |
| 6. Variables de entorno | CUMPLE | Compose y configuración propia de cada aplicación |
| 7. Puertos publicados | CUMPLE | `docker compose ps`: solo 8080 y 8081 en host |
| 8. Departamentos en otro lenguaje | CUMPLE | JavaScript/Express frente a Python/FastAPI |
| 9. POST /departamentos | CUMPLE | `departamentos/src/app.js`; E2E: 201 y objeto completo |
| 10. GET /departamentos/{id} | CUMPLE | E2E: 200 existente, 404 descriptivo inexistente |
| 11. GET /departamentos | CUMPLE | E2E: lista 200 |
| 12. BD propia de departamentos | CUMPLE | `database-departamentos`, repositorio y configuración propios |
| 13. Swagger de departamentos | CUMPLE | `/docs/`, `src/openapi.js`; Edge: GET 200 desde UI |
| 14. Empleados persisten en BD | CUMPLE | `empleados/app/repository.py`; E2E tras destruir contenedores |
| 15. Diez campos originales | CUMPLE | Subclase del modelo original y comparación íntegra en E2E |
| 16. estado = ACTIVO | CUMPLE | Modelo, INSERT y CHECK SQL; estado omitido → ACTIVO |
| 17. Email único | CUMPLE | Consulta SQL previa; pruebas unitarias y E2E |
| 18. numeroEmpleado único | CUMPLE | Consulta SQL previa; pruebas unitarias y E2E |
| 19. UNIQUE reales en BD | CUMPLE | `pg_constraint` consultado; 24 solicitudes concurrentes |
| 20. Validación HTTP del departamento | CUMPLE | `empleados/app/departamentos.py`; E2E |
| 21. Sin acceso cruzado entre BD | CUMPLE | Redes separadas; DNS de BD ajena falla desde ambas APIs |
| 22. URL interna por nombre Docker | CUMPLE | `http://departamentos-service:8081` en Compose |
| 23. Timeout HTTP explícito | CUMPLE | HTTPX: 2 s por fase; departamento pausado en E2E |
| 24. Reintentos | CUMPLE | Máximo 3 adicionales; cuatro intentos verificados |
| 25. Backoff creciente | CUMPLE | Esperas 1, 2 y 4 s verificadas en pruebas y logs |
| 26. Respuesta controlada al agotarse | CUMPLE | 503 en 15,3 s; GET del empleado rechazado → 404 |
| 27. Swagger de empleados | CUMPLE | `/docs`, OpenAPI; Edge: GET 200 desde UI |
| 28. Esquemas reproducibles | CUMPLE | Ambos `init.sql` montados; E2E con volúmenes vacíos |
| 29. Persistencia tras down | CUMPLE | E2E: IT y E001 íntegros después de down/up |
| 30. Eliminación tras down -v | CUMPLE | E2E: listas vacías y consultas IT/E001 → 404 |
| 31. Email duplicado → 400 | CUMPLE | E2E y pruebas de orden, también sin estado en el request |
| 32. Número duplicado → 400 | CUMPLE | E2E y pruebas de orden, también sin estado en el request |
| 33. Departamento inexistente → 400 | CUMPLE | E2E, también sin estado en el request |
| 34. README raíz | CUMPLE | `../README.md`: materia, retos, tecnologías y ejecución |
| 35. README Reto 2 | CUMPLE | `README.md`: arquitectura, ejecución, contrato, configuración y pruebas |
| 36. README por servicio | CUMPLE | `empleados/README.md`, `departamentos/README.md` |
| 37. Tres decisiones justificadas | CUMPLE | README: motor, esquema/evolución y consulta previa + UNIQUE |
| 38. Evidencia ps healthy | CUMPLE | Salida real resumida abajo y verificada por E2E |
| 39. Evidencia de persistencia | CUMPLE | Contraste down/down -v comprobado abajo y en E2E |
| 40. .env excluido; plantilla incluida | CUMPLE | `git ls-files`: solo `.env.example`; `git check-ignore` para `.env` |

### Criterios de evaluación del PDF

| Criterio (pp. 18–19) | Peso docente | Estado técnico | Evidencia |
|---------------------|--------------|----------------|-----------|
| Docker Compose y arranque ordenado | 1,0 | CUMPLE | Puntos 1–7; E2E sin .env y desde volúmenes vacíos |
| Servicio de Departamentos | 1,0 | CUMPLE | Puntos 8–13; Dockerfile propio y 12 pruebas |
| Servicio de Empleados | 1,0 | CUMPLE | Puntos 14–22 y 27; 25 pruebas y E2E |
| Persistencia y esquema | 1,0 | CUMPLE | Puntos 21, 28–30 y 39; init.sql y volúmenes independientes |
| Tolerancia a fallos y pruebas | 1,0 | CUMPLE | Puntos 23–26 y 31–33; Swagger y timeout real |

Esta evaluación técnica no asigna una calificación: corresponde al docente.
Los Dockerfiles de ambos servicios están presentes y construyen correctamente.
Se verificó por `git ls-remote origin refs/heads/features/kevin` que GitHub contiene
la base `b0ca6c8`. Las correcciones de esta auditoría quedan locales, pendientes
de commit y publicación por petición expresa del usuario. No se hizo commit ni push.

### Resultados repetidos tras revisar el PDF

- Reto 1: **15 pruebas aprobadas**; `git diff 31de26b -- Reto_1/app Reto_1/tests
  Reto_1/Dockerfile Reto_1/requirements.txt` vacío.
- Empleados Reto 2: **25 pruebas aprobadas**, incluida asignación de estado omitido.
- Departamentos: **12 pruebas aprobadas**; su implementación no requirió cambios.
- E2E final: proyecto `micro-reto2-e2e-d3eb1bdd`, puertos 50656/50657,
  configuración sin `.env`, volúmenes vacíos, salida **0**.
- Swagger: ambas interfaces renderizadas en Edge headless, cuatro operaciones
  por servicio y GET 200 desde Try it out; sin errores JavaScript.
- UNIQUE de email/número y PRIMARY KEY consultados directamente en PostgreSQL.
- Aislamiento: cada API no resuelve por DNS la base del otro servicio.

Salida resumida del E2E final:

```text
OK: arranque limpio y cuatro servicios healthy
OK: Swagger, altas, consultas, diez campos, validaciones y orden
OK: 24 peticiones concurrentes; tres altas y 21 duplicados controlados
OK: timeout real, tres reintentos y 503 sin inserción (15.3s)
OK: down conserva empleados y departamentos completos
OK: down -v borra datos, reinicialización limpia y cuatro healthy
E2E COMPLETO: todas las comprobaciones pasaron
```

`docker compose ps` del proyecto habitual tras reconstruir (tiempos omitidos):

```text
SERVICE                  STATUS         PORTS
database-departamentos   Up (healthy)
database-empleados       Up (healthy)
departamentos-service    Up (healthy)   127.0.0.1:8081->8081/tcp
empleados-service        Up (healthy)   127.0.0.1:8080->8080/tcp
```

**Reto 2 listo para entrega: SÍ**, con las correcciones locales listas para
versionar y publicar. No se añadieron Circuit Breaker, Gateway, mensajería,
Kubernetes, PUT/DELETE ni observabilidad de retos posteriores.

## Registro histórico: verificación anterior al PDF

El siguiente registro corresponde a la implementación inicial. La auditoría final
anterior actualiza sus resultados, el valor predeterminado de estado y el arranque
sin `.env`; conserva esta evidencia histórica sin presentarla como una nueva ejecución.

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
