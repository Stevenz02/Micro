# Resultados de verificación del Reto 7

Este documento se completa con resultados reales. La línea base del Reto 6 no se presenta como
una ejecución nueva de Jenkins.

## Entorno local auditado

- Repositorio: monorepo en rama `features/kevin`.
- Estado inicial: limpio según `git status --short`.
- Python: 3.13.7.
- Node.js: 22.20.0; npm 10.9.3.
- .NET SDK: 8.0.426.
- Go: no disponible localmente.
- Maven: no disponible localmente.
- Java local: 8; el servicio requiere Java 21.
- Jenkins, Jenkinsfile Runner y SonarScanner: no disponibles localmente.
- Docker/Compose: no utilizados por esta implementación.

## Verificaciones ejecutadas el 27 de octubre de 2026

| Verificación | Estado | Resultado/evidencia |
|---|---|---|
| Tests de utilidades CI | Aprobada | 5/5: conversión Go JUnit/Cobertura, normalización Node/.NET y detección de fallos JUnit |
| Auditor estático Jenkins/Sonar | Aprobada | 7 pipelines de servicio, 1 E2E, 6 propiedades CLI + .NET; etapas y llaves verificadas |
| Empleados | Aprobada tres veces localmente | 64/64 por corrida; 175/221 líneas, 79,19 % |
| Auth | Aprobada tres veces localmente | 10/10 por corrida; 81/94 líneas, 86,17 % |
| Gateway | Aprobada tres veces localmente | 26/26 por corrida; 230/253 líneas, 90,91 % |
| Departamentos | Aprobada tres veces localmente | 12/12 por corrida; 83/85 líneas, 97,65 % LCOV |
| Perfiles | No ejecutable localmente | Falta Go 1.23 |
| Notificaciones | No ejecutable localmente | Faltan JDK 21 y Maven |
| Vacaciones | Aprobada tres veces localmente | 16/16 por corrida; 51/310 líneas, 16,45 % en Release |
| Validación de reportes | Aprobada | 4 JUnit, 4 coberturas, OpenCover y Cucumber JSON válidos |
| Runner E2E sin infraestructura | Aprobada | Gateway inalcanzable produjo exactamente código 20 y diagnóstico explícito |
| BDD actual | No ejecutada | `localhost:8080/health` no estuvo disponible; no se administró Docker |
| Jenkins declarativo | Implementado, no ejecutado | Requiere servidor/linter Jenkins real |
| Sonar/Quality Gate | Implementado, no ejecutado | Requiere servidor, token y webhook |
| Package | Dependiente de infraestructura | Contrato documentado; `RUN_PACKAGE=false` por defecto |

Las cinco suites ejecutables en la estación suman **128 pruebas de componentes por corrida** y
todas aprobaron en las tres repeticiones locales. Las cinco pruebas propias de utilidades CI
también aprobaron. Estas repeticiones no se presentan como builds Jenkins.

### Comandos principales ejecutados

- `pytest` con JUnit y `pytest-cov` para Empleados, Auth y Gateway.
- `node --test --experimental-test-coverage` con JUnit normalizado y LCOV.
- `dotnet test` con TRX, Cobertura y OpenCover.
- `python -m unittest discover -s Reto_7/tests -v`.
- `python Reto_7/ci/scripts/verify_ci_config.py`.
- `python Reto_7/ci/scripts/validate_reports.py ...`.
- `python Reto_7/ci/scripts/run_e2e.py` contra un puerto deliberadamente inalcanzable para
  comprobar la clasificación de infraestructura.

### Hallazgos

- Node 22 produce un XML con `testcase` directamente bajo `testsuites`. Se añadió un normalizador
  probado que crea el `testsuite` requerido por Jenkins sin alterar nombres ni fallos.
- `npm ci` informó 3 vulnerabilidades de dependencias (una moderada, una alta y una crítica). No se
  ejecutó `npm audit fix` porque actualizar dependencias automáticamente puede cambiar el servicio;
  debe analizarse y corregirse como trabajo de seguridad separado.
- .NET emitió un warning nullable `CS8604` en `Program.cs:139`; las 16 pruebas aprobaron.
- La cobertura de Vacaciones actual fue 16,45 %, consistente con la deuda histórica de 16,90 %.
  No se excluyó producción ni se alteró la lógica para elevar la cifra.

## Línea base histórica del Reto 6

- Unitarias: 140/140.
- Integración PostgreSQL: 1/1.
- BDD: 25/25 escenarios y 116/116 pasos.
- Cobertura: Empleados 79,19 %, Auth 86,17 %, Gateway 90,91 %, Vacaciones 16,90 %.

La sección anterior sirve para detectar regresiones, pero no sustituye los builds Jenkins del
Reto 7. La ejecución local actual confirmó 128 de las 140 pruebas de componentes históricas; las
12 restantes corresponden a Perfiles (4) y Notificaciones (8), cuyos toolchains no están presentes.

## Validaciones pendientes con infraestructura

- Sintaxis mediante Jenkins Declarative Linter.
- Tres builds consecutivos de cada job.
- Importación real a SonarQube.
- Quality Gate y webhook.
- Tendencia `recordCoverage`.
- Publicación Cucumber/HTML dentro de Jenkins.
- Package externo y propagación de fallo.
- E2E contra el sistema completo proporcionado por infraestructura.

## Auditoría y regresión de segunda fase — 27 de octubre de 2026

Esta sección conserva la evidencia de la primera fase y registra la verificación posterior a las
correcciones. Los resultados siguientes son ejecuciones locales, no builds Jenkins.

### Correcciones verificadas

- Los conversores Go rechazan entradas vacías o inválidas, conservan fallos y omisiones y marcan
  como error una prueba que termina sin evento `pass`, `fail` o `skip`.
- Los normalizadores Node y .NET rechazan suites o coberturas incompletas.
- El validador comprueba casos JUnit contra sus atributos, métricas Cobertura/JaCoCo/OpenCover y
  estructura y estados de cada paso Cucumber.
- `junit_status.py` distingue aprobado (`0`), fallo funcional (`1`), reporte ausente (`2`) y reporte
  corrupto o inconsistente (`3`).
- El runner E2E valida el health exacto del Gateway y separa infraestructura (`20`) de runner (`21`).
- `Program.cs` valida el ID antes de persistir Vacaciones; el build Release pasó con 0 warnings y
  eliminó el anterior `CS8604`.
- El lockfile de Departamentos actualizó tres dependencias transitivas dentro de los rangos de
  Express: `body-parser` 2.4.0, `proxy-addr` 2.0.8 y `qs` 6.17.0. `npm audit` pasó de 3 a 0.

### Tres corridas consecutivas posteriores a las correcciones

| Suite | Corrida 1 | Corrida 2 | Corrida 3 | Cobertura en las tres |
|---|---:|---:|---:|---:|
| Empleados | 64/64 | 64/64 | 64/64 | 175/221, 79,19 % |
| Auth | 10/10 | 10/10 | 10/10 | 81/94, 86,17 % |
| API Gateway | 26/26 | 26/26 | 26/26 | 230/253, 90,91 % |
| Departamentos | 12/12 | 12/12 | 12/12 | LCOV generado y validado por Node |
| Vacaciones | 16/16 | 16/16 | 16/16 | 51/311, 16,39 % OpenCover |
| Herramientas CI | 19/19 | 19/19 | 19/19 | No aplica |

Cada corrida ejecutó **128/128 pruebas de componentes disponibles**. No se afirma 140/140:
Perfiles (4) y Notificaciones (8) no se ejecutaron porque el equipo sigue sin Go 1.23, Maven y
JDK 21. Tampoco se ejecutó la integración PostgreSQL porque depende de Testcontainers.

Los reportes JUnit, Cobertura y OpenCover recién generados se validaron en cada corrida. El
Cucumber JSON histórico se revalidó con 25 escenarios y 116 pasos, pero la suite BDD no se volvió
a ejecutar: el Gateway no estaba disponible. La prueba negativa del wrapper devolvió exactamente
código 20 contra `127.0.0.1:1`.

### Estado externo después de la auditoría

- Jenkins Declarative Linter y builds: pendientes de un servidor real.
- SonarQube y Quality Gate: siete configuraciones verificadas estáticamente; ejecución pendiente.
- Package: contrato preparado, implementación de imágenes a cargo de infraestructura.
- E2E funcional: preparado y no duplicado; pendiente del ecosistema completo y credencial ADMIN.

## VALIDACIÓN FINAL DE LA PARTE LÓGICA — RETO 7

**Fecha:** 27 de octubre de 2026.

Esta sección registra ejecuciones nuevas de la fase final. Mantiene intactas las evidencias de las
fases anteriores. Los resultados son locales y no se presentan como builds Jenkins ni análisis
SonarQube.

### Archivos revisados

- Los 33 archivos existentes de `Reto_7` al iniciar la fase: ocho Jenkinsfiles, nueve scripts CI,
  siete configuraciones Sonar/README, `vacaciones.runsettings`, pruebas y documentación.
- `Reto_4/departamentos/package-lock.json`.
- `Reto_5/notificaciones/pom.xml`.
- `Reto_5/vacaciones/Program.cs`.
- Rutas físicas de fuentes, tests y reportes de los siete servicios y la suite BDD.
- Infraestructura existente se leyó únicamente para confirmar puertos y dependencias; no se ejecutó
  ni modificó.

### Comandos realmente ejecutados

- Tres corridas de pytest para Empleados, Auth y Gateway con JUnit y Cobertura XML nuevos.
- Tres corridas de `node --test --experimental-test-coverage` con JUnit y LCOV nuevos.
- Tres corridas de `dotnet test` con TRX, Cobertura y OpenCover nuevos.
- Tres corridas de `python -m unittest discover -s Reto_7/tests -q`.
- `validate_reports.py` sobre JUnit, Cobertura, OpenCover y LCOV de cada corrida.
- Validación del Cucumber JSON/HTML histórico mediante `validate_reports.py`.
- `verify_ci_config.py` y `python -m compileall -q Reto_7`.
- `npm ci`, `npm test` y `npm audit --json`.
- `dotnet build ... --configuration Release --no-restore` y una prueba adicional de Vacaciones.
- `run_e2e.py` contra `127.0.0.1:1` con timeout corto para verificar código 20.
- Inventario de `python`, Node, npm, .NET, Go, Maven, Java, Jenkinsfile Runner y SonarScanner.

### Resultados exactos de las tres corridas

| Suite | Corrida 1 | Corrida 2 | Corrida 3 | Cobertura en las tres |
|---|---:|---:|---:|---:|
| Empleados | 64/64 | 64/64 | 64/64 | 175/221, 79,19 % |
| Auth | 10/10 | 10/10 | 10/10 | 81/94, 86,17 % |
| API Gateway | 26/26 | 26/26 | 26/26 | 230/253, 90,91 % |
| Departamentos | 12/12 | 12/12 | 12/12 | 83/85, 97,65 % LCOV |
| Vacaciones | 16/16 | 16/16 | 16/16 | 51/311, 16,39 % OpenCover |
| Herramientas CI | 21/21 | 21/21 | 21/21 | No aplica |

Total de componentes disponible por corrida: **128/128**. Pruebas fallidas reales: **0**.
Las salidas deliberadas de JUnit ausente, fallido y corrupto forman parte de los casos negativos de
la suite CI y terminaron con los códigos esperados.

### Reportes y validaciones estáticas

- Cada corrida generó y validó cuatro JUnit, tres Cobertura Python, Cobertura y OpenCover .NET y un
  LCOV Node. LCOV midió dos archivos, 85 líneas y 83 cubiertas.
- El reporte histórico Cucumber conserva 25 escenarios, 116 pasos y 25 tarjetas HTML. Fue validado,
  pero Behave no se volvió a ejecutar porque el Gateway no estaba disponible.
- JaCoCo no se generó localmente: faltan Maven y JDK 21. Su configuración se verificó estáticamente.
- `verify_ci_config.py` aprobó siete pipelines, un E2E, siete project keys, rutas físicas, orden de
  etapas y contratos de publicación. No sustituye el Declarative Linter.
- `npm audit` informó 0 vulnerabilidades sobre 85 dependencias de producción.
- Vacaciones compiló con 0 errores y 0 advertencias.
- El wrapper E2E devolvió exactamente 20 ante infraestructura ausente.

### Pruebas no ejecutadas

| Prueba | Motivo exacto |
|---|---|
| Perfiles, 4 unitarias | Go no está instalado |
| Notificaciones, 8 unitarias | Maven no está instalado y Java disponible es 8, no 21 |
| Integración PostgreSQL | Utiliza Testcontainers; administrar contenedores está prohibido en esta fase |
| BDD funcional | Gateway/ecosistema no disponible |
| Jenkins Declarative Linter/builds | Jenkins/Jenkinsfile Runner no disponibles |
| SonarQube/Quality Gate | SonarScanner y servidor no disponibles |
| Package externo | Responsabilidad de infraestructura |

No se afirma 140/140 ni un Quality Gate aprobado.

### Correcciones exclusivas de esta fase

- `validate_reports.py` ahora valida LCOV y la estructura del Cucumber HTML, además de los formatos
  XML/JSON ya cubiertos.
- `test_ci_tools.py` aumentó de 19 a 21 casos para comprobar LCOV inconsistente y HTML sin
  escenarios.
- El README ahora documenta también el código E2E 21.
- Se crearon la guía maestra, el punto de entrada y el checklist de entrega para infraestructura.

### Riesgos pendientes y congelamiento lógico

- Continúan pendientes Jenkins, SonarQube, Go, Java, PostgreSQL integrado, Package y BDD real.
- La cobertura global de Vacaciones sigue en 16,39 %; el gate debe evaluar código nuevo.
- Los cambios están locales y sin commit por instrucción expresa.
- No se creó, modificó ni ejecutó ningún Dockerfile, Compose, contenedor, red o volumen.
- La parte lógica queda congelada para integración; cambios posteriores en pipelines, scripts o
  contratos deben coordinarse y volver a probarse.

