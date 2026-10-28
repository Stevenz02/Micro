# Contrato de integración con infraestructura

Este documento define lo que debe proporcionar el integrante responsable de Jenkins, SonarQube,
Docker y despliegue. La lógica de CI no administra esos recursos.

## 1. Jenkins

### Plugins requeridos

- Pipeline y Pipeline: Declarative.
- Git y Credentials Binding.
- JUnit.
- Coverage (`recordCoverage`).
- SonarQube Scanner for Jenkins.
- MSTest (`mstest`) para TRX de .NET.
- Cucumber Reports (`cucumber`).
- HTML Publisher (`publishHTML`).
- Timestamper.

### Toolchains de agentes Linux

| Herramienta | Requisito del código |
|---|---|
| Python | Python 3 con `venv`; validado con 3.13 |
| Node.js | 22 o superior |
| Go | 1.23 |
| Java | JDK 21 |
| Maven | Compatible con Spring Boot 3.4.3 |
| .NET | SDK 8 |
| SonarScanner CLI | En `PATH` como `sonar-scanner` |
| SonarScanner for .NET | En `PATH` como `dotnet sonarscanner` |

Los agentes deben tener salida a los repositorios de dependencias de Python, npm, Go, Maven y
NuGet. No se exige PowerShell.

### Jobs esperados

| Job sugerido | Script Path |
|---|---|
| `reto7-empleados` | `Reto_7/jenkins/Jenkinsfile.empleados` |
| `reto7-auth` | `Reto_7/jenkins/Jenkinsfile.auth` |
| `reto7-api-gateway` | `Reto_7/jenkins/Jenkinsfile.api-gateway` |
| `reto7-departamentos` | `Reto_7/jenkins/Jenkinsfile.departamentos` |
| `reto7-perfiles` | `Reto_7/jenkins/Jenkinsfile.perfiles` |
| `reto7-notificaciones` | `Reto_7/jenkins/Jenkinsfile.notificaciones` |
| `reto7-vacaciones` | `Reto_7/jenkins/Jenkinsfile.vacaciones` |
| `reto7-integracion-e2e` | `Reto_7/jenkins/Jenkinsfile.integration` |

Todos apuntan al mismo SCM y usan la raíz del monorepo como workspace. El job debe permitir
checkout del commit o rama seleccionada. Los pipelines realizan su propio `checkout scm`.

### Estrategia de disparo

- Los siete jobs de servicio pueden usar cambios por path o ejecutarse en paralelo desde un
  orquestador de infraestructura.
- Package debe habilitarse únicamente cuando exista el job externo correspondiente.
- E2E debe ejecutarse una vez cuando todos los servicios que forman el release hayan aprobado.
- No habilitar `TRIGGER_E2E` indiscriminadamente en los siete jobs.
- Para reproducibilidad académica, ejecutar tres builds consecutivos por pipeline y conservar URLs.

### Credenciales y configuración

| ID/nombre | Tipo | Uso |
|---|---|---|
| `sonarqube-reto7` | Configuración global SonarQube con token seguro | `withSonarQubeEnv` |
| `reto7-e2e-admin` | Username/Password | `ADMIN_EMAIL` y `ADMIN_PASSWORD` BDD |
| Credencial SCM definida por infraestructura | Según proveedor | Checkout privado, si aplica |

No registrar los valores en parámetros de texto, archivos o logs.

## 2. SonarQube

### Proyectos

Crear o permitir aprovisionamiento de los siete project keys enumerados en
`MATRIZ_PIPELINES.md`. Asociarles el Quality Gate de Reto 7.

### Quality Gate mínimo sobre código nuevo

- Coverage >= 70 %.
- Duplicated Lines Density <= 3 %.
- New Bugs = 0.
- New Vulnerabilities = 0.
- Maintainability Rating aceptable según la rúbrica.

La cobertura histórica no debe confundirse con la cobertura de código nuevo. Vacaciones tiene una
línea base global de 16,90 % y puede rechazar un gate global de 70 %; esto debe registrarse como
deuda real, no corregirse mediante exclusiones artificiales.

### Webhook obligatorio

Configurar en SonarQube:

```text
<JENKINS_URL>/sonarqube-webhook/
```

Sin este webhook, `waitForQualityGate` agotará el timeout. El pipeline no debe continuar por una
respuesta inventada.

### Formatos consumidos

| Lenguaje | Formato Sonar |
|---|---|
| Python | Cobertura XML |
| JavaScript | LCOV |
| Go | coverprofile nativo |
| Java | JaCoCo XML |
| C# | OpenCover XML mediante SonarScanner for .NET |

## 3. Contrato Package

La implementación de imágenes queda fuera de esta entrega. Cada Jenkinsfile llama un job externo
solo cuando `RUN_PACKAGE=true`.

### Entrada obligatoria del job externo

| Parámetro | Significado |
|---|---|
| `COMPONENT_ID` | `empleados`, `auth`, `api-gateway`, `departamentos`, `perfiles`, `notificaciones` o `vacaciones` |
| `SOURCE_DIR` | Directorio real del componente dentro del workspace |
| `SOURCE_BUILD` | Número del build de servicio que solicitó el paquete |

Infraestructura puede añadir `IMAGE_REGISTRY`, `IMAGE_REPOSITORY`, `IMAGE_TAG` o credenciales sin
modificar la lógica de tests.

### Salida y errores

- Resultado SUCCESS únicamente después de producir y, si aplica, publicar el artefacto acordado.
- El tag recomendado debe incluir commit y/o `SOURCE_BUILD`.
- Un fallo de compilación, autenticación o publicación devuelve FAILURE.
- El pipeline padre usa `wait: true, propagate: true`, por lo que el error se propaga.
- Si `RUN_PACKAGE=true` y `PACKAGE_JOB` está vacío o no existe, el pipeline falla explícitamente.

No devolver SUCCESS para un paquete que no fue creado.

## 4. Contrato E2E

### Responsabilidad de infraestructura

- Levantar y mantener saludable el ecosistema completo.
- Proporcionar una URL alcanzable por el agente Jenkins.
- Configurar scheduler compatible con el timeout BDD.
- Garantizar credenciales ADMIN y aislamiento de datos.
- Apagar o limpiar infraestructura según su propia política; el runner no borra bases ni volúmenes.

### Entrada

| Variable/parámetro | Valor esperado |
|---|---|
| `GATEWAY_BASE_URL` / `BASE_URL` | URL del Gateway, sin ruta final |
| `E2E_READY_PATH` | `/health` por defecto |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Inyectadas desde `reto7-e2e-admin` |
| `POLL_TIMEOUT_SECONDS` | `30` |
| `POLL_INTERVAL_MS` | `500` |
| `POLL_MAX_ATTEMPTS` | `120` |
| `HTTP_TIMEOUT_SECONDS` | `10` |

### Comando

```text
python Reto_7/ci/scripts/run_e2e.py
```

El runner espera disponibilidad y luego reutiliza `Reto_6/e2e-tests/run.py`. No ejecuta comandos
de contenedores.

### Reportes

```text
Reto_6/e2e-tests/reports/junit.xml
Reto_6/e2e-tests/reports/cucumber.json
Reto_6/e2e-tests/reports/cucumber.html
Reto_6/e2e-tests/reports/junit_raw/*.xml
```

### Tratamiento de errores

- Código `20`: Gateway ausente/configuración externa inválida. Clasificar como fallo de
  infraestructura; no intentar publicar reportes BDD que nunca se generaron.
- Código `21`: el runner no existe o no pudo iniciarse. Clasificar como fallo del checkout o del
  agente; no intentar publicar reportes BDD inexistentes.
- Código diferente de `0`, `20` y `21`: Behave fue ejecutado y falló. Publicar todos los reportes y
  marcar el job como fallido.
- Código `0`: publicar JUnit, Cucumber y HTML.

El `200` de disponibilidad debe contener exactamente `{"status":"ok","service":"api-gateway"}`.
Así se evita ejecutar la suite contra otro proceso que responda por accidente en el mismo puerto.

## 5. Trabajo pendiente de infraestructura

1. Aprovisionar Jenkins y agentes con las herramientas indicadas.
2. Instalar los plugins.
3. Crear los ocho jobs con sus Script Paths.
4. Configurar SCM y credenciales.
5. Aprovisionar SonarQube, proyectos, gate y webhook.
6. Crear los jobs Package con el contrato anterior.
7. Proporcionar el entorno E2E y su URL.
8. Ejecutar linter declarativo de los Jenkinsfiles.
9. Ejecutar tres builds consecutivos por pipeline.
10. Conservar capturas y URLs reales de resultados, cobertura, Cucumber y fallos.

## 6. Procedimiento de aceptación conjunta

1. Confirmar que Jenkins responde y que los ocho jobs anteriores apuntan a la raíz del mismo SCM.
2. Ejecutar el Declarative Linter del servidor sobre cada Script Path antes del primer build.
3. Confirmar en cada agente `python3`, Node 22, Go 1.23, JDK 21, Maven, .NET 8 y ambos scanners.
4. Crear la configuración `sonarqube-reto7`, los siete proyectos y el webhook de Quality Gate.
5. Ejecutar los siete jobs con `RUN_PACKAGE=false` y `TRIGGER_E2E=false`; comprobar JUnit/TRX,
   cobertura, análisis Sonar y bloqueo del gate.
6. Probar un fallo controlado de test y uno de Quality Gate; Package y E2E no deben ejecutarse.
7. Conectar el job externo de Package, habilitar `RUN_PACKAGE=true` y comprobar los tres parámetros,
   el etiquetado por build y la propagación de un error real.
8. Levantar el ecosistema desde la infraestructura del compañero y comprobar el health exacto del
   Gateway desde el agente Jenkins.
9. Ejecutar una sola vez `reto7-integracion-e2e`; publicar JUnit, Cucumber JSON y HTML navegable.
10. Repetir cada job tres veces sobre el mismo commit y conservar número, resultado, URL y duración.
11. Ejecutar una prueba con Gateway ausente y verificar el código 20 sin reportes históricos.

Los pipelines individuales conservan `TRIGGER_E2E=false` por defecto. En la integración final se
habilita en un único job de cierre o se invoca directamente el job de integración desde el
orquestador. `disableConcurrentBuilds()` impide dos ejecuciones E2E simultáneas en ese job.

