# Guía maestra para la IA responsable de infraestructura — Reto 7

## Propósito y reglas de transferencia

Este documento permite continuar el Reto 7 sin acceso al historial de conversación que produjo la
parte lógica. La entrega fue revisada el **27 de octubre de 2026**. Los pipelines, scripts de CI,
configuraciones Sonar y contratos descritos aquí existen en el repositorio local. Jenkins,
SonarQube, Package y el ecosistema desplegado todavía deben ser conectados y ejecutados por
infraestructura.

Antes de cambiar cualquier contrato, leer también:

1. `Reto_7/LEER_PRIMERO_IA_COMPANERO.md`.
2. `Reto_7/docs/INTEGRACION_INFRAESTRUCTURA.md`.
3. `Reto_7/docs/RESULTADOS_VERIFICACION.md`.

No sobrescribir Jenkinsfiles, scripts CI ni lógica funcional para adaptar una configuración de
infraestructura. Si aparece una incompatibilidad real, conservar la evidencia y coordinar el cambio.

## 1. Presentación del proyecto

El sistema académico administra recursos humanos mediante microservicios.

- **Reto 4:** introdujo Empleados, Departamentos, Perfiles, sus bases PostgreSQL, comunicación REST,
  eventos y pruebas en Python, Node.js y Go.
- **Reto 5:** agregó Auth, JWT, RBAC, API Gateway, Notificaciones, Vacaciones, onboarding,
  offboarding y eventos de ciclo de vida mediante RabbitMQ.
- **Reto 6:** consolidó 140 pruebas unitarias históricas, una integración PostgreSQL, 25 escenarios
  Behave, 116 pasos, polling de consistencia eventual y reportes reutilizables.
- **Reto 7:** agrega ocho pipelines Jenkins declarativos, siete análisis SonarQube, Quality Gate
  bloqueante, publicación de evidencia, contrato de Package y coordinación E2E.

La responsabilidad se divide así:

- **Parte lógica entregada:** Jenkinsfiles, comandos de build/test, formatos, conversores,
  validadores, configuración de scanners y contratos externos.
- **Parte de infraestructura:** servidores Jenkins/SonarQube, agentes, plugins, credenciales,
  despliegue, conectividad, jobs Package, ejecución real y capturas académicas.

## 2. Arquitectura real

| Componente | Tecnología | Ruta de código | Puerto del ecosistema | Persistencia/comunicación |
|---|---|---|---:|---|
| API Gateway | Python, FastAPI | `Reto_5/api-gateway` | 8080 | Entrada HTTP; valida JWT/RBAC y enruta |
| Empleados | Python, FastAPI | `Reto_4/empleados` | 8081 | PostgreSQL; REST a Departamentos; eventos RabbitMQ |
| Departamentos | Node.js, Express | `Reto_4/departamentos` | 8082 | PostgreSQL; catálogo consultado por Empleados |
| Perfiles | Go | `Reto_4/perfiles` | 8083 | PostgreSQL; consume eventos de empleados |
| Notificaciones | Java 21, Spring Boot | `Reto_5/notificaciones` | 8084 | PostgreSQL; consume eventos y registra notificaciones |
| Vacaciones | .NET 8 | `Reto_5/vacaciones` | 8085 | PostgreSQL; scheduler y eventos de vacaciones |
| Auth | Python, FastAPI | `Reto_5/auth` | 8086 | PostgreSQL; emite JWT y consume eventos de cuenta |
| BDD | Python, Behave | `Reto_6/e2e-tests` | No aplica | Consume el Gateway por HTTP |
| RabbitMQ | Servicio externo | Configuración de infraestructura | 5672 | Eventos entre servicios |
| PostgreSQL | Servicio externo por dominio | Configuración de infraestructura | 5432 interno | Base separada para cada servicio persistente |

Flujo HTTP principal:

```text
Cliente/BDD -> API Gateway -> Auth o servicio de negocio -> PostgreSQL
```

Flujo eventual principal:

```text
Empleados/Vacaciones -> RabbitMQ -> Auth, Perfiles y Notificaciones
```

El Gateway utiliza las URL lógicas `AUTH_URL`, `EMPLEADOS_URL`, `DEPARTAMENTOS_URL`,
`PERFILES_URL`, `NOTIFICACIONES_URL` y `VACACIONES_URL`. Infraestructura debe preservar la
conectividad; los Jenkinsfiles no crean redes ni servicios.

## 3. Inventario de archivos del Reto 7

### 3.1 Pipelines

| Ruta | Archivo | Propósito/tecnología | Dependencias y relación CI | Responsable |
|---|---|---|---|---|
| `Reto_7/jenkins` | `Jenkinsfile.empleados` | Pipeline Python | pytest, Cobertura, Sonar CLI, Package/E2E externos | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.auth` | Pipeline Python | pytest, código `Reto_5/shared`, Sonar CLI | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.api-gateway` | Pipeline Python | pytest/MockTransport, Sonar CLI | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.departamentos` | Pipeline Node.js | npm, node:test, LCOV, normalizador JUnit | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.perfiles` | Pipeline Go | Go JSON/coverprofile, dos conversores, detector JUnit | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.notificaciones` | Pipeline Java | Maven, Surefire, JaCoCo, detector JUnit | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.vacaciones` | Pipeline .NET | VSTest, TRX, Coverlet, Scanner for .NET | Lógica protegida |
| `Reto_7/jenkins` | `Jenkinsfile.integration` | Pipeline Behave | Gateway externo, credencial ADMIN, Cucumber/HTML | Lógica protegida |

### 3.2 Scripts CI

| Ruta | Archivo | Propósito | Dependencias/relación | Responsable |
|---|---|---|---|---|
| `Reto_7/ci/scripts` | `go_test_json_to_junit.py` | Convierte `go test -json` a JUnit sin ocultar fallos | Perfiles; biblioteca estándar Python | Lógica protegida |
| `Reto_7/ci/scripts` | `go_cover_to_cobertura.py` | Convierte coverprofile Go a Cobertura | Perfiles; conserva coverprofile para Sonar | Lógica protegida |
| `Reto_7/ci/scripts` | `normalize_node_junit.py` | Inserta `testsuite` requerido por Jenkins | Departamentos | Lógica protegida |
| `Reto_7/ci/scripts` | `normalize_dotnet_coverage.py` | Estabiliza rutas UUID de Cobertura/OpenCover | Vacaciones | Lógica protegida |
| `Reto_7/ci/scripts` | `junit_status.py` | Detecta fallos, ausencia o corrupción JUnit | Perfiles y Notificaciones | Lógica protegida |
| `Reto_7/ci/scripts` | `validate_reports.py` | Valida JUnit, cobertura XML, LCOV y Cucumber | Verificación local y diagnóstico CI | Lógica protegida |
| `Reto_7/ci/scripts` | `verify_ci_config.py` | Audita contratos y rutas sin interpretar Groovy | Todos los pipelines/Sonar | Lógica protegida |
| `Reto_7/ci/scripts` | `run_e2e.py` | Espera Gateway y ejecuta Behave existente | Pipeline integration y `Reto_6/e2e-tests/run.py` | Lógica protegida |
| `Reto_7/ci/scripts` | `__init__.py` | Paquete Python de utilidades | Pruebas CI | Lógica protegida |

### 3.3 Configuración

| Ruta | Archivo | Propósito | Relación Jenkins/Sonar | Responsable |
|---|---|---|---|---|
| `Reto_7/ci/config/sonar` | `empleados.properties` | Fuentes, tests y Cobertura Python | `uq-reto7-empleados` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `auth.properties` | Auth, shared, tests y Cobertura | `uq-reto7-auth` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `api-gateway.properties` | Gateway, tests y Cobertura | `uq-reto7-api-gateway` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `departamentos.properties` | JavaScript, tests y LCOV | `uq-reto7-departamentos` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `perfiles.properties` | Go, tests y coverprofile | `uq-reto7-perfiles` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `notificaciones.properties` | Java, bytecode, Surefire y JaCoCo | `uq-reto7-notificaciones` | Lógica protegida |
| `Reto_7/ci/config/sonar` | `README.md` | Explica CLI frente a Scanner for .NET | Referencia operativa | Lógica protegida |
| `Reto_7/ci/config` | `vacaciones.runsettings` | Activa Cobertura y OpenCover | VSTest y `uq-reto7-vacaciones` | Lógica protegida |

### 3.4 Pruebas y documentación

| Ruta/archivo | Propósito | Dependencias | Responsable |
|---|---|---|---|
| `Reto_7/tests/test_ci_tools.py` | 21 pruebas de casos normales y defectuosos | Scripts CI y estructura real | Lógica protegida |
| `Reto_7/tests/__init__.py` | Marca el paquete de pruebas CI | `unittest` | Lógica protegida |
| `Reto_7/README.md` | Entrada humana de la entrega lógica | Todos los contratos | Parte lógica |
| `Reto_7/LEER_PRIMERO_IA_COMPANERO.md` | Entrada para otra IA | Esta guía | Transferencia compartida |
| `Reto_7/docs/ARQUITECTURA_CI.md` | Decisiones de arquitectura | Jenkinsfiles | Parte lógica |
| `Reto_7/docs/MATRIZ_PIPELINES.md` | Matriz por componente | Código y reportes | Parte lógica |
| `Reto_7/docs/INTEGRACION_INFRAESTRUCTURA.md` | Contrato operativo resumido | Jenkins/Sonar/Package/E2E | Infraestructura lo ejecuta |
| `Reto_7/docs/PLAN_VERIFICACION.md` | Casos normales y controlados | Jenkins real pendiente | Compartido |
| `Reto_7/docs/RESULTADOS_VERIFICACION.md` | Evidencia y limitaciones | Resultados locales/reales | Compartido |
| `Reto_7/docs/CHECKLIST_ENTREGA_LOGICA.md` | Estado contra requisitos | Toda la entrega | Compartido |
| `Reto_7/docs/GUIA_MAESTRA_IA_COMPANERO.md` | Transferencia autónoma | Todo el monorepo relevante | Infraestructura debe leerla |

## 4. Explicación de los ocho Jenkinsfiles

### 4.1 Empleados

- **Job/Script Path:** `reto7-empleados` / `Reto_7/jenkins/Jenkinsfile.empleados`.
- **Código:** `Reto_4/empleados`; tests `Reto_4/tests`, excluyendo marca `integration`.
- **Build:** crea `.ci/venv-empleados`, instala `Reto_4/requirements-test.txt` y usa `compileall`.
- **Test:** pytest con cobertura de `main`, `models` y `events`.
- **Reportes:** `Reto_4/empleados/reports/junit.xml` y `coverage.xml`.
- **Sonar:** CLI con `empleados.properties`; gate bloqueante.
- **Externos:** Package recibe `empleados`, `Reto_4/empleados`, `BUILD_NUMBER`.
- **Fallo:** pytest no cero detiene Sonar; `post/always` publica evidencia si inició tests.

### 4.2 Auth

- **Job/Script Path:** `reto7-auth` / `Reto_7/jenkins/Jenkinsfile.auth`.
- **Código:** `Reto_5/auth` y `Reto_5/shared`; tests `Reto_5/tests/test_auth.py`.
- **Build:** `.ci/venv-auth`, `Reto_5/requirements-test.txt`, `compileall`.
- **Cobertura:** `auth_app.passwords`, `auth_app.lifecycle` y `shared.tokens`.
- **Reportes:** `Reto_5/auth/reports/junit.xml` y `coverage.xml`.
- **Sonar/externos:** `uq-reto7-auth`; Package usa `auth`, `Reto_5/auth`, build actual.
- **Fallo:** ausencia o error del reporte impide un resultado exitoso.

### 4.3 API Gateway

- **Job/Script Path:** `reto7-api-gateway` / `Reto_7/jenkins/Jenkinsfile.api-gateway`.
- **Código/tests:** `Reto_5/api-gateway/gateway_app`, `Reto_5/tests/test_gateway.py`.
- **Build:** `.ci/venv-gateway`, dependencias Reto 5 y `compileall`.
- **Cobertura/reportes:** `gateway_app.main`, JUnit y Cobertura bajo `api-gateway/reports`.
- **Sonar/externos:** `uq-reto7-api-gateway`; Package usa `api-gateway` y su directorio.
- **Pruebas:** usan transportes simulados; no requieren upstream desplegado.

### 4.4 Departamentos

- **Job/Script Path:** `reto7-departamentos` / `Reto_7/jenkins/Jenkinsfile.departamentos`.
- **Directorio:** `Reto_4/departamentos`.
- **Build:** `npm ci --no-audit --no-fund` y `node --check` sobre `src/*.js`.
- **Test:** Node 22 `node --test --experimental-test-coverage`.
- **Reportes:** `reports/junit.xml`, normalizado después de capturar el código nativo, y
  `coverage/lcov.info`.
- **Sonar:** `uq-reto7-departamentos`, LCOV.
- **Package:** `departamentos`, `Reto_4/departamentos`, build actual.
- **Fallo:** el código de Node se conserva y se vuelve a lanzar después de normalizar el reporte.

### 4.5 Perfiles

- **Job/Script Path:** `reto7-perfiles` / `Reto_7/jenkins/Jenkinsfile.perfiles`.
- **Directorio/toolchain:** `Reto_4/perfiles`, Go 1.23.
- **Build:** `go mod download && go build ./...`.
- **Test:** `go test -json -covermode=atomic -coverprofile=reports/coverage.out ./...`.
- **Reportes:** JSON nativo, JUnit convertido, coverprofile nativo y Cobertura convertido.
- **Sonar:** usa el coverprofile original con `uq-reto7-perfiles`.
- **Protección:** `junit_status.py` comprueba el XML antes de Sonar; una prueba interrumpida es error.
- **Package:** `perfiles`, `Reto_4/perfiles`, build actual.

### 4.6 Notificaciones

- **Job/Script Path:** `reto7-notificaciones` / `Reto_7/jenkins/Jenkinsfile.notificaciones`.
- **Directorio/toolchain:** `Reto_5/notificaciones`, JDK 21 y Maven.
- **Build:** `mvn -B -ntp -DskipTests compile`.
- **Test:** `mvn ... -Dmaven.test.failure.ignore=true verify` permite generar JaCoCo/Surefire;
  después `junit_status.py` recupera el estado real. Los fallos siguen terminando en FAILURE.
- **Reportes:** `target/surefire-reports/TEST-*.xml` y `target/site/jacoco/jacoco.xml`.
- **Sonar:** CLI sobre bytecode compilado, `uq-reto7-notificaciones`.
- **Package:** `notificaciones`, `Reto_5/notificaciones`, build actual.

### 4.7 Vacaciones

- **Job/Script Path:** `reto7-vacaciones` / `Reto_7/jenkins/Jenkinsfile.vacaciones`.
- **Proyectos:** `Reto_5/vacaciones` y `Reto_5/vacaciones.tests` con .NET 8.
- **Build:** restore y build Release de `Vacaciones.Tests.csproj`.
- **Test:** VSTest/xUnit con `vacaciones.runsettings` y XPlat Code Coverage.
- **Reportes:** `vacaciones.trx`, `coverage.xml`, `coverage.opencover.xml` bajo `reports`.
- **Sonar:** Scanner for .NET, project key `uq-reto7-vacaciones`, OpenCover y TRX.
- **Publicación:** paso `mstest`, `recordCoverage(COBERTURA)` y archivo de OpenCover.
- **Package:** `vacaciones`, `Reto_5/vacaciones`, build actual.

### 4.8 Integración E2E

- **Job/Script Path:** `reto7-integracion-e2e` / `Reto_7/jenkins/Jenkinsfile.integration`.
- **Parámetros:** `GATEWAY_BASE_URL`, `UPSTREAM_COMPONENT`, `UPSTREAM_BUILD`.
- **Build:** `.ci/venv-e2e`, requisitos Behave y `compileall`.
- **Credencial:** username/password `reto7-e2e-admin`, inyectada como `ADMIN_EMAIL` y
  `ADMIN_PASSWORD`.
- **Ejecución:** `run_e2e.py` espera `/health` y reutiliza `Reto_6/e2e-tests/run.py`.
- **Reportes:** JUnit, Cucumber JSON, Cucumber HTML y JUnit crudo.
- **Publicación:** `junit`, `cucumber`, `publishHTML`, `archiveArtifacts`.
- **Concurrencia:** `disableConcurrentBuilds()`; ejecutar una vez por ciclo integrado.
- **Códigos:** `0` éxito; `20` infraestructura; `21` runner; otros no cero son fallo de Behave o
  ejecución, con publicación de reportes cuando Behave alcanzó a ejecutarse.

## 5. Contrato de Jenkins

### Jobs y Script Paths

| Job esperado | Script Path |
|---|---|
| `reto7-empleados` | `Reto_7/jenkins/Jenkinsfile.empleados` |
| `reto7-auth` | `Reto_7/jenkins/Jenkinsfile.auth` |
| `reto7-api-gateway` | `Reto_7/jenkins/Jenkinsfile.api-gateway` |
| `reto7-departamentos` | `Reto_7/jenkins/Jenkinsfile.departamentos` |
| `reto7-perfiles` | `Reto_7/jenkins/Jenkinsfile.perfiles` |
| `reto7-notificaciones` | `Reto_7/jenkins/Jenkinsfile.notificaciones` |
| `reto7-vacaciones` | `Reto_7/jenkins/Jenkinsfile.vacaciones` |
| `reto7-integracion-e2e` | `Reto_7/jenkins/Jenkinsfile.integration` |

Todos usan la raíz del monorepo como workspace y hacen `checkout scm` una vez.

### Plugins realmente utilizados

- Pipeline, Pipeline: Declarative, Git y Credentials Binding.
- JUnit, Coverage, SonarQube Scanner for Jenkins.
- MSTest, Cucumber Reports, HTML Publisher y Timestamper.

### Agentes y herramientas

Agente Linux con Python 3 y `venv`, Node.js 22+, Go 1.23, JDK 21, Maven compatible con Spring
Boot 3.4.3, .NET SDK 8, `sonar-scanner` y `dotnet sonarscanner`. Debe tener salida hacia los
repositorios de paquetes y conectividad con Jenkins, SonarQube y el Gateway E2E.

### Parámetros y variables

- Servicios: `RUN_PACKAGE=false`, `PACKAGE_JOB=''`, `TRIGGER_E2E=false`,
  `E2E_JOB='reto7-integracion-e2e'`.
- Comunes: `TESTS_STARTED`, `SONARQUBE_ENV='sonarqube-reto7'`.
- Integración: `GATEWAY_BASE_URL`, `UPSTREAM_COMPONENT`, `UPSTREAM_BUILD` y límites de polling.
- Credenciales: configuración Sonar `sonarqube-reto7`; username/password `reto7-e2e-admin`.

Infraestructura decide labels de agentes, triggers SCM, retención de builds, URL real del Gateway,
nombre del job Package y almacenamiento de credenciales. No debe cambiar nombres de parámetros que
ya forman parte del contrato.

## 6. Contrato SonarQube

| Servicio | Project key | Scanner | Cobertura |
|---|---|---|---|
| Empleados | `uq-reto7-empleados` | SonarScanner CLI | Cobertura XML |
| Auth | `uq-reto7-auth` | SonarScanner CLI | Cobertura XML |
| API Gateway | `uq-reto7-api-gateway` | SonarScanner CLI | Cobertura XML |
| Departamentos | `uq-reto7-departamentos` | SonarScanner CLI | LCOV |
| Perfiles | `uq-reto7-perfiles` | SonarScanner CLI | coverprofile Go |
| Notificaciones | `uq-reto7-notificaciones` | SonarScanner CLI | JaCoCo XML |
| Vacaciones | `uq-reto7-vacaciones` | SonarScanner for .NET | OpenCover XML |

Jenkins debe registrar una instalación llamada `sonarqube-reto7`. SonarQube debe enviar el webhook
a `<JENKINS_URL>/sonarqube-webhook/`. El token se guarda en Jenkins/SonarQube, nunca en SCM.

Quality Gate recomendado sobre código nuevo: cobertura >=70 %, duplicación <=3 %, cero bugs y
vulnerabilidades nuevas, mantenibilidad aceptable. `waitForQualityGate abortPipeline: true` bloquea
Package y E2E. La cobertura global de Vacaciones es 16,39 %; no debe maquillarse con exclusiones.

## 7. Contrato Package

Package está deshabilitado por defecto. Cuando `RUN_PACKAGE=true`, `PACKAGE_JOB` debe contener el
nombre del job externo. Jenkins lo invoca con `wait: true` y `propagate: true`.

| Parámetro | Contenido |
|---|---|
| `COMPONENT_ID` | Uno de los siete IDs exactos del servicio |
| `SOURCE_DIR` | Directorio del componente en el workspace |
| `SOURCE_BUILD` | `BUILD_NUMBER` del pipeline solicitante |

El job externo debe devolver SUCCESS solo después de producir el artefacto acordado. Un error de
compilación, credencial, publicación o etiquetado debe devolver FAILURE. Se recomienda etiquetar con
commit y/o `SOURCE_BUILD`. La lógica actual no construye imágenes ni define registry.

## 8. Contrato E2E

- **Suite original:** `Reto_6/e2e-tests/features` y `step_definitions`.
- **Runner original:** `Reto_6/e2e-tests/run.py`.
- **Wrapper CI:** `Reto_7/ci/scripts/run_e2e.py`.
- **URL:** `BASE_URL`, tomada de `GATEWAY_BASE_URL` del job.
- **Health:** `GET /health` debe devolver 200 y exactamente
  `{"status":"ok","service":"api-gateway"}`.
- **Disponibilidad:** 60 s por defecto, intervalo 2 s, request timeout 10 s.
- **Consistencia eventual:** `POLL_TIMEOUT_SECONDS=30`, `POLL_INTERVAL_MS=500`,
  `POLL_MAX_ATTEMPTS=120`.
- **Credenciales:** `ADMIN_EMAIL` y `ADMIN_PASSWORD` desde `reto7-e2e-admin`.
- **Códigos:** 0 aprobado; 20 infraestructura; 21 runner; otros no cero indican ejecución fallida.
- **Aislamiento:** la suite genera datos únicos; infraestructura debe ofrecer un entorno coherente y
  aplicar su propia política de limpieza.
- **Concurrencia:** ejecutar un único job E2E; `disableConcurrentBuilds()` evita solapamiento.

## 9. Tabla técnica de reportes

| Suite/servicio | Formato | Ruta | Productor | Publicación Jenkins |
|---|---|---|---|---|
| Empleados | JUnit | `Reto_4/empleados/reports/junit.xml` | pytest | `junit` |
| Empleados | Cobertura XML | `Reto_4/empleados/reports/coverage.xml` | pytest-cov | `recordCoverage` |
| Auth | JUnit/Cobertura | `Reto_5/auth/reports/{junit,coverage}.xml` | pytest | `junit`/Coverage |
| Gateway | JUnit/Cobertura | `Reto_5/api-gateway/reports/{junit,coverage}.xml` | pytest | `junit`/Coverage |
| Departamentos | JUnit | `Reto_4/departamentos/reports/junit.xml` | node:test + normalizador | `junit` |
| Departamentos | LCOV | `Reto_4/departamentos/coverage/lcov.info` | node:test | `recordCoverage(LCOV)` |
| Perfiles | Go JSON/JUnit | `Reto_4/perfiles/reports/{test-results.json,junit.xml}` | Go + conversor | `junit` |
| Perfiles | Go/Cobertura | `Reto_4/perfiles/reports/{coverage.out,coverage.xml}` | Go + conversor | Sonar/Coverage |
| Notificaciones | Surefire XML | `Reto_5/notificaciones/target/surefire-reports/TEST-*.xml` | Maven | `junit` |
| Notificaciones | JaCoCo XML | `Reto_5/notificaciones/target/site/jacoco/jacoco.xml` | JaCoCo | `recordCoverage` |
| Vacaciones | TRX | `Reto_5/vacaciones.tests/reports/vacaciones.trx` | VSTest | `mstest` |
| Vacaciones | Cobertura | `Reto_5/vacaciones.tests/reports/coverage.xml` | Coverlet | `recordCoverage` |
| Vacaciones | OpenCover | `Reto_5/vacaciones.tests/reports/coverage.opencover.xml` | Coverlet | Sonar/artefacto |
| BDD | JUnit | `Reto_6/e2e-tests/reports/junit.xml` | Behave/runner | `junit` |
| BDD | Cucumber JSON | `Reto_6/e2e-tests/reports/cucumber.json` | Behave | `cucumber` |
| BDD | HTML | `Reto_6/e2e-tests/reports/cucumber.html` | runner | `publishHTML` |

## 10. Estado de pruebas

Línea base histórica Reto 6: 140 unitarias, una integración PostgreSQL, 25 escenarios y 116 pasos.

Validación lógica final local, tres corridas consecutivas:

| Servicio | Resultado por corrida | Cobertura final |
|---|---:|---:|
| Empleados | 64/64 | 175/221, 79,19 % |
| Auth | 10/10 | 81/94, 86,17 % |
| API Gateway | 26/26 | 230/253, 90,91 % |
| Departamentos | 12/12 | 83/85, 97,65 % LCOV |
| Vacaciones | 16/16 | 51/311, 16,39 % |
| Herramientas CI | 21/21 | No aplica |

Total actual ejecutado: 128/128 por corrida. Perfiles (4) no se ejecutó por ausencia de Go 1.23;
Notificaciones (8) no se ejecutó por falta de Maven/JDK 21. La integración PostgreSQL no se ejecutó
porque usa Testcontainers. El Cucumber histórico fue validado con 25/116 y 25 tarjetas HTML, pero
no constituye una nueva ejecución BDD.

## 11. Cambios realizados fuera de Reto 7

- `Reto_4/departamentos/package-lock.json`: actualiza transitivamente `body-parser` 2.4.0,
  `proxy-addr` 2.0.8 y `qs` 6.17.0. `npm audit` actual: cero vulnerabilidades; 12 pruebas aprobadas.
- `Reto_5/notificaciones/pom.xml`: agrega JaCoCo 0.8.12 en `prepare-agent` y `verify` para producir
  XML consumible por Jenkins y SonarQube.
- `Reto_5/vacaciones/Program.cs`: valida que el ID exista antes de persistir; elimina `CS8604` sin
  cambiar el contrato HTTP. Build Release: cero warnings; 16 pruebas aprobadas.

## 12. Archivos que no deben sobrescribirse

No modificar unilateralmente:

- `Reto_7/jenkins/*`.
- `Reto_7/ci/scripts/*`.
- `Reto_7/ci/config/*`.
- `Reto_7/tests/*`.
- Los tres archivos externos enumerados en la sección anterior.
- Endpoints, JWT/RBAC, catálogo de eventos, persistencia, scheduler o suite Behave.

Los archivos de infraestructura existentes pueden evolucionar bajo responsabilidad del compañero,
pero no deben exigir que los pipelines administren contenedores. Cualquier cambio de nombre de job,
parámetro, credencial o ruta se coordina antes de modificar la lógica protegida.

## 13. Trabajo exclusivo de infraestructura

- Aprovisionar Jenkins, agentes, SCM y plugins.
- Aprovisionar SonarQube Server y su base de datos.
- Crear proyectos, Quality Gate, token y webhook.
- Instalar y versionar toolchains/scanners en agentes.
- Gestionar credenciales secretas y permisos.
- Implementar jobs Package, registry, imágenes y etiquetas.
- Desplegar PostgreSQL, RabbitMQ y microservicios.
- Proporcionar conectividad del agente E2E al Gateway.
- Ejecutar el linter Jenkins y todos los pipelines.
- Producir capturas, URLs y artefactos académicos reales.

## 14. Plan recomendado de integración

1. **Comprender contratos:** leer los tres documentos iniciales. Termina cuando puede enumerar ocho
   jobs, siete project keys y parámetros Package sin consultar código adicional.
2. **Preparar Jenkins/agentes:** instalar plugins y toolchains. Termina cuando cada comando de
   versión funciona desde el agente asignado.
3. **Conectar Jenkinsfiles:** crear los ocho jobs con Script Paths exactos. Termina cuando el
   Declarative Linter acepta los ocho archivos.
4. **Verificar Build/Test/reportes:** ejecutar con Package/E2E deshabilitados. Termina cuando los
   siete jobs publican sus resultados nativos y ninguna suite fallida continúa.
5. **Conectar SonarQube:** crear siete proyectos, gate y webhook. Termina cuando cada análisis llega
   al proyecto correcto y `waitForQualityGate` recibe respuesta real.
6. **Conectar Package:** implementar el job externo y los tres parámetros. Termina cuando un éxito
   y un fallo controlado se propagan correctamente.
7. **Conectar E2E:** desplegar ecosistema, credencial y URL. Termina cuando `/health` cumple el JSON
   exacto desde el agente Jenkins.
8. **Ejecutar pruebas completas:** correr Perfiles, Notificaciones, integración PostgreSQL y BDD.
   Termina con reportes navegables y conteos reales, sin reutilizar históricos.
9. **Tres ejecuciones:** repetir sobre el mismo commit. Termina con tres builds consecutivos por job.
10. **Evidencias académicas:** guardar dashboard, Test Result, Coverage, Sonar, gates, Package,
    Cucumber/HTML y fallos controlados con URL y número de build.

## 15. Riesgos conocidos

| Riesgo | Estado/mitigación |
|---|---|
| Cobertura global Vacaciones 16,39 % | Abierto; usar gate sobre código nuevo, sin exclusiones artificiales |
| Parser real Jenkins no ejecutado | Abierto; ejecutar Declarative Linter |
| Go y Java no ejecutados localmente | Abierto; agentes con Go 1.23 y JDK 21/Maven |
| Integración PostgreSQL pendiente | Abierto; ejecutar en infraestructura autorizada |
| BDD funcional pendiente | Abierto; requiere ecosistema y ADMIN |
| Webhook/Quality Gate pendientes | Abierto; configurar y probar bloqueo |
| Workspaces/rutas | Mitigado con raíz de monorepo; mantener Script Paths exactos |
| E2E duplicado | Mitigado por defaults falsos y `disableConcurrentBuilds`; usar un único cierre |
| Reportes defectuosos | Corregido con conversores y validadores probados |
| Vulnerabilidades npm | Corregido; audit actual cero |
| Cambios locales sin commits | Abierto por instrucción; coordinar cómo transferirlos sin perderlos |

## 16. Matriz de responsabilidades

| Actividad | Parte lógica | Infraestructura | Estado |
|---|---|---|---|
| Jenkinsfiles y comandos | Implementada y protegida | Cargar/ejecutar | Verificada estáticamente |
| Plugins y agentes | Define requisitos | Instalar/configurar | Pendiente |
| Pruebas/reportes | Define comandos y rutas | Ejecutar/publicar | Parcial local |
| Sonar projects/gate | Define keys y formatos | Aprovisionar/validar | Pendiente servidor |
| Package | Define contrato | Implementar | Pendiente |
| E2E wrapper | Implementado | Proveer entorno/credencial | Pendiente funcional |
| Docker/despliegue | No interviene | Responsable exclusivo | Pendiente externo |
| Evidencias | Documenta lo local | Capturar Jenkins/Sonar | Pendiente externo |

## 17. Checklist académico para infraestructura

### Criterio 1 — Pipelines declarativos por componente

- [x] Ocho Script Paths definidos.
- [ ] Ocho archivos aceptados por Declarative Linter.
- [ ] Jobs visibles y vinculados al mismo SCM.

### Criterio 2 — Build, tests, cobertura y reportes

- [x] Comandos y formatos implementados.
- [x] Cinco suites y herramientas CI verificadas localmente.
- [ ] Perfiles y Notificaciones ejecutados en Jenkins.
- [ ] JUnit/TRX y tendencias Coverage visibles.

### Criterio 3 — SonarQube y Quality Gate

- [x] Siete keys y rutas configuradas.
- [ ] Siete análisis reales.
- [ ] Webhook y gate bloqueante demostrados con éxito y rechazo.

### Criterio 4 — Package e integración de entrega

- [x] Contrato externo y propagación definidos.
- [ ] Job Package implementado por infraestructura.
- [ ] Artefacto/imagen etiquetado y fallo controlado evidenciados.

### Criterio 5 — Integración E2E y evidencias

- [x] Wrapper, polling y publicación configurados.
- [ ] 25 escenarios ejecutados contra el sistema integrado.
- [ ] Cucumber JSON/HTML publicados en Jenkins.
- [ ] Tres ejecuciones consecutivas y capturas finales conservadas.

La parte lógica se considera lista para integración. El Reto 7 completo solo se considera validado
después de cerrar todas las casillas dependientes de infraestructura con resultados reales.
