# Reto 7 — Integración continua con Jenkins y SonarQube

## Objetivo

Esta entrega implementa la **lógica de CI** del monorepo de Recursos Humanos sin duplicar
microservicios ni administrar infraestructura. Reutiliza el código de `Reto_4` y `Reto_5`,
los tests y reportes de `Reto_6`, y agrega pipelines declarativos, análisis SonarQube,
publicación de resultados y un runner BDD que consume un entorno externo ya disponible.

La infraestructura de Jenkins, SonarQube, Docker, redes, imágenes y despliegue pertenece al
otro frente del equipo. Ningún archivo de contenedores fue creado o modificado.

## Relación entre retos

| Reto | Aporte reutilizado por CI |
|---|---|
| 4 | Empleados, Departamentos, Perfiles, persistencia, pruebas Python/Node/Go |
| 5 | Auth, Gateway, Notificaciones, Vacaciones, JWT, RBAC y pruebas Python/Java/.NET |
| 6 | Suites unitarias, integración, BDD Behave, polling y reportes base |
| 7 | Jenkinsfiles, SonarQube, Quality Gate, publicación y coordinación E2E |

## Arquitectura lógica

```text
Checkout
  -> Build nativo
  -> Test + cobertura real
  -> SonarQube Analysis
  -> Quality Gate (bloqueante)
  -> Package (job externo, omitido por defecto)
  -> E2E (job coordinado, opcional por pipeline)
  -> post/always: JUnit + Coverage + artefactos
```

La suite BDD global tiene su propio `Jenkinsfile.integration`. Los siete pipelines de servicio
pueden dispararlo, pero `TRIGGER_E2E=false` por defecto evita siete ejecuciones repetidas. En
una instalación real se debe permitir el disparo únicamente al job coordinador o al pipeline
que cierre la integración del conjunto.

## Jenkinsfiles

Los archivos están centralizados en `Reto_7/jenkins/` porque el repositorio es un monorepo:

| Pipeline | Código analizado | Tecnología |
|---|---|---|
| `Jenkinsfile.empleados` | `Reto_4/empleados` | Python / pytest |
| `Jenkinsfile.auth` | `Reto_5/auth` y `Reto_5/shared` | Python / pytest |
| `Jenkinsfile.api-gateway` | `Reto_5/api-gateway` | Python / pytest |
| `Jenkinsfile.departamentos` | `Reto_4/departamentos` | Node.js 22 / node:test |
| `Jenkinsfile.perfiles` | `Reto_4/perfiles` | Go 1.23 |
| `Jenkinsfile.notificaciones` | `Reto_5/notificaciones` | Java 21 / Maven |
| `Jenkinsfile.vacaciones` | `Reto_5/vacaciones*` | .NET 8 / xUnit |
| `Jenkinsfile.integration` | `Reto_6/e2e-tests` | Python / Behave |

Todos los pipelines de servicio usan `skipDefaultCheckout(true)` y ejecutan exactamente un
`checkout scm`. Los comandos se ejecutan desde la raíz del workspace y respetan los paths
reales del monorepo.

## Comandos de prueba y formatos

| Suite | Comando base | Resultados | Cobertura |
|---|---|---|---|
| Empleados | `pytest Reto_4/tests -m 'not integration'` | JUnit XML | Cobertura XML |
| Auth | `pytest Reto_5/tests/test_auth.py` | JUnit XML | Cobertura XML |
| Gateway | `pytest Reto_5/tests/test_gateway.py` | JUnit XML | Cobertura XML |
| Departamentos | `node --test --experimental-test-coverage` | JUnit XML nativo | LCOV nativo |
| Perfiles | `go test -json -coverprofile` | JSON convertido a JUnit | coverprofile y Cobertura XML |
| Notificaciones | `mvn verify` | Surefire JUnit | JaCoCo XML |
| Vacaciones | `dotnet test --collect:'XPlat Code Coverage'` | TRX | Cobertura y OpenCover XML |
| BDD | `python Reto_7/ci/scripts/run_e2e.py` | JUnit | Cucumber JSON y HTML |

Los conversores Go y el normalizador .NET están en `Reto_7/ci/scripts`. No escriben resultados
ficticios: transforman exclusivamente los archivos producidos por las herramientas nativas y
fallan cuando la entrada esperada no existe o es inválida.

## Publicación en Jenkins

La publicación está dentro de `post { always { ... } }` y solo se activa después de iniciar la
etapa de pruebas. Esto permite publicar el nombre y mensaje de una prueba fallida, sin exigir
un reporte imposible cuando falló la compilación antes de ejecutar tests.

| Suite | Archivo | Productor | Plugin/paso Jenkins | Vista esperada |
|---|---|---|---|---|
| Python | `reports/junit.xml` | pytest | `junit` | Test Result / tendencia |
| Python | `reports/coverage.xml` | pytest-cov | `recordCoverage(COBERTURA)` | Coverage |
| Node | `reports/junit.xml` | node:test + normalizador estructural | `junit` | Test Result |
| Node | `coverage/lcov.info` | node:test | `recordCoverage(LCOV)` | Coverage |
| Go | `reports/junit.xml` | conversor CI | `junit` | Test Result |
| Go | `reports/coverage.xml` | conversor CI | `recordCoverage(COBERTURA)` | Coverage |
| Java | `target/surefire-reports/TEST-*.xml` | Surefire | `junit` | Test Result |
| Java | `target/site/jacoco/jacoco.xml` | JaCoCo | `recordCoverage(JACOCO)` | Coverage |
| .NET | `reports/vacaciones.trx` | VSTest | `mstest` | Test Result |
| .NET | `reports/coverage.xml` | Coverlet | `recordCoverage(COBERTURA)` | Coverage |
| BDD | `reports/junit.xml` | Behave/runner | `junit` | Test Result |
| BDD | `cucumber.json` | Behave | `cucumber` | Cucumber Reports |
| BDD | `cucumber.html` | runner Reto 6 | `publishHTML` | HTML Report |

`allowEmptyResults` y `allowEmptyArchive` se mantienen en `false` para los reportes esperados.
Un archivo ausente después de iniciar las pruebas es un error visible, no un éxito silencioso.

## SonarQube y Quality Gate

Las configuraciones CLI viven en `Reto_7/ci/config/sonar`. Vacaciones usa SonarScanner for
.NET desde su Jenkinsfile. Cada componente tiene un project key único:

```text
uq-reto7-empleados
uq-reto7-auth
uq-reto7-api-gateway
uq-reto7-departamentos
uq-reto7-perfiles
uq-reto7-notificaciones
uq-reto7-vacaciones
```

`withSonarQubeEnv('sonarqube-reto7')` inyecta URL y token. Después, `waitForQualityGate` espera
el webhook y usa `abortPipeline: true`; un gate rechazado detiene Package y E2E.

El Quality Gate debe configurarse en el servidor sobre **código nuevo** con, como mínimo:

- Cobertura nueva `>= 70 %`.
- Duplicación nueva `<= 3 %`.
- Cero bugs nuevos.
- Cero vulnerabilidades nuevas.
- Mantenibilidad nueva aceptable.

No se afirma que la cobertura global de todos los servicios sea 70 %. La línea base comprobada
del Reto 6 fue 79,19 % Empleados, 86,17 % Auth, 90,91 % Gateway y 16,90 % para el ensamblado
completo de Vacaciones. El gate sobre código nuevo evita falsear esa deuda histórica.

## Package y E2E

`RUN_PACKAGE=false` omite la etapa Package. Al activarla se exige `PACKAGE_JOB`; Jenkins invoca
ese job con `COMPONENT_ID`, `SOURCE_DIR` y `SOURCE_BUILD`, espera el resultado y propaga el fallo.
Los Jenkinsfiles no contienen comandos Docker.

`TRIGGER_E2E=false` omite el disparo global. Al activarlo, se invoca `E2E_JOB` y se propaga su
resultado. El job de integración recibe una URL de Gateway, espera `/health` y devuelve:

- `0`: suite ejecutada y aprobada.
- Código Behave distinto de cero: fallo funcional.
- `20`: entorno externo ausente o configuración de infraestructura inválida.
- `21`: runner ausente o imposible de iniciar en el agente.

## Estados del build

- **SUCCESS:** build, tests, análisis y Quality Gate aprobaron; las etapas opcionales habilitadas
  también terminaron correctamente.
- **UNSTABLE:** Jenkins detecta resultados de prueba o Cucumber según la política del plugin y
  conserva sus reportes. La política recomendada del equipo es tratarlo como no promovible.
- **FAILURE:** compilación, comando de prueba, reporte requerido, SonarQube, Quality Gate, Package
  externo o E2E fallaron.
- **Skipped:** Package o E2E estaban deshabilitados por parámetro. No significa que se ejecutaron.

## Credenciales y variables

No hay secretos en el repositorio. Infraestructura debe crear:

- Configuración SonarQube Jenkins: `sonarqube-reto7` con token seguro.
- Credencial Jenkins username/password: `reto7-e2e-admin`.
- Webhook SonarQube: `<JENKINS_URL>/sonarqube-webhook/`.
- `GATEWAY_BASE_URL` apuntando al entorno ya levantado.
- Jobs externos Package y el job `reto7-integracion-e2e`.

Las variables BDD conservan `POLL_TIMEOUT_SECONDS=30`, `POLL_INTERVAL_MS=500`,
`POLL_MAX_ATTEMPTS=120` y `HTTP_TIMEOUT_SECONDS=10`.

## Compatibilidad

Los Jenkinsfiles están diseñados para agentes Linux. No dependen de PowerShell. Los scripts de
conversión y validación usan solamente la biblioteca estándar de Python 3. Los agentes deben
proporcionar Python 3, Node 22, Go 1.23, JDK 21 con Maven, .NET SDK 8, SonarScanner CLI y
SonarScanner for .NET.

## Validación local independiente de infraestructura

```text
python -m unittest discover -s Reto_7/tests -v
python Reto_7/ci/scripts/verify_ci_config.py
python Reto_7/ci/scripts/validate_reports.py --junit <archivo> --coverage <archivo> --lcov <archivo>
```

La ejecución real en Jenkins y el Quality Gate requieren los servidores externos. Los resultados
obtenidos y las limitaciones están en `docs/RESULTADOS_VERIFICACION.md`.

## Documentos

- `docs/ARQUITECTURA_CI.md`: flujo, responsabilidades y decisiones.
- `docs/MATRIZ_PIPELINES.md`: matriz técnica por servicio.
- `docs/INTEGRACION_INFRAESTRUCTURA.md`: contrato con el trabajo del compañero.
- `docs/PLAN_VERIFICACION.md`: pruebas normales y de fallo.
- `docs/RESULTADOS_VERIFICACION.md`: evidencia real y pendientes.
- `LEER_PRIMERO_IA_COMPANERO.md`: punto de entrada para el frente de infraestructura.
- `docs/GUIA_MAESTRA_IA_COMPANERO.md`: transferencia técnica autónoma y completa.
- `docs/CHECKLIST_ENTREGA_LOGICA.md`: estado verificable por requisito académico.

## Evidencias visuales pendientes

Las capturas reales deben incorporarse después de aprovisionar Jenkins y SonarQube:

1. Dashboard con los ocho jobs.
2. Test Result de una suite aprobada y otra fallida.
3. Tendencia de Coverage.
4. Cucumber Reports y HTML publicado.
5. Quality Gate aprobado y rechazado.
6. Package externo fallido con propagación al pipeline.

No se incluyen capturas simuladas.

## Auditoría técnica de segunda fase

La revisión del 27 de octubre de 2026 endureció los conversores y validadores para rechazar
archivos vacíos, XML/JSON corrupto, suites sin casos, conteos contradictorios, pruebas Go sin
resultado final y coberturas sin líneas medibles. Una cobertura real de 0 % sigue siendo válida
cuando contiene líneas instrumentadas.

`run_e2e.py` comprueba una URL HTTP(S), valida el JSON exacto de `/health` y diferencia:

- `20`: Gateway o configuración externa no disponible.
- `21`: runner ausente o imposible de iniciar.
- otro valor no cero: Behave sí se ejecutó y encontró un fallo funcional o de ejecución.

Se ejecutaron tres corridas locales consecutivas de las suites disponibles: 128/128 pruebas de
componentes y 19/19 pruebas de herramientas CI por corrida. Perfiles y Notificaciones siguen sin
ejecutarse localmente por ausencia de Go 1.23, Maven y JDK 21. Jenkins, SonarQube, Package y BDD
contra el ecosistema real continúan pendientes de infraestructura; por ello el Reto 7 no se declara
completamente validado.

## Cierre de la parte lógica y transferencia

La validación final del 27 de octubre de 2026 repitió tres veces las 128 pruebas disponibles y
amplió la suite CI a 21/21 casos. También validó LCOV y la estructura del Cucumber HTML. No quedan
bloqueos lógicos conocidos; las ejecuciones de Jenkins, SonarQube, Package y BDD integrado son la
responsabilidad pendiente de infraestructura.

La otra IA debe comenzar en `LEER_PRIMERO_IA_COMPANERO.md` y leer completamente
`docs/GUIA_MAESTRA_IA_COMPANERO.md` antes de modificar infraestructura.

