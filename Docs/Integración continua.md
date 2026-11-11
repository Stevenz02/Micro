<!-- Pagina 1 de 46 -->

Integración Continua (CI)

Arquitectura Basada en Microservicios Área de infraestructura

Programa de Ingeniería de Sistemas y Computación Facultad de Ingeniería

---

<!-- Pagina 2 de 46 -->

Contenido

Integración Continua – Conceptos fundamentales Pipelines como código Jenkins – Servidor de automatización Calidad de código con SonarQube CI en microservicios

Patrones de despliegue

---

<!-- Pagina 3 de 46 -->

Integración Continua – Conceptos Fundamentales

---

<!-- Pagina 4 de 46 -->

# ¿Qué es CI?

Continuous Integration – Integración Continua

Propuesta por Martin Fowler y popularizada por el movimiento Extreme Programming (XP)

Práctica en la que los desarrolladores integran su trabajo frecuentemente en un repositorio compartido

Cada integración se verifica automáticamente mediante build y

pruebas

El objetivo es detectar errores en minutos, no en días

---

<!-- Pagina 5 de 46 -->

# El problema que resuelve CI

|Situación|SinCI|ConCI|
|---|---|---|
|Compilación|Manual, "cuando alguien se acuerda"|Automática, en cada push|
|Pruebas|Se ejecutan localmente (o no se<br>ejecutan)|Se ejecutan automáticamente|
|Detección de errores|Al intentar desplegar (tarde)|En minutos tras el commit|
|Confianza en el<br>código|"En mi máquina funciona"|Pipeline lo verifica en un entorno limpio|
|Empaquetado|`docker build` manual en la terminal|ImagenDocker generada<br>automáticamente|
|Calidad|Se revisa "a ojo" (o no se revisa)|Análisis estático y cobertura automáticos|


Principio fundamental: Si duele hacerlo manualmente, automatícelo. Si lo automatiza, hágalo frecuentemente.

---

<!-- Pagina 6 de 46 -->

# Las prácticas de CI

1. Repositorio único – Todo el código en un sistema de control de versiones 2. Build automatizado – Un solo comando para compilar todo

3. Pruebas automatizadas – Tests que corren sin intervención humana

4. Integración frecuente – Al menos una vez al día

5. Build rápido – Feedback en minutos, no horas

6. Entorno de pruebas idéntico al de producción – Contenedores Docker

7. Resultados visibles – Dashboard donde todos ven el estado del build

---

<!-- Pagina 7 de 46 -->

# CI vs CD vs CD

Práctica Qué hace Resultado CI – Continuous Compila, prueba y analiza el código Artefacto verificado (ej. `.jar` , Integration en cada cambio imagen Docker) CD – Continuous Empaqueta y prepara el artefacto Artefacto listo para publicar Delivery para despliegue manualmente CD – Continuous Despliega automáticamente a Artefacto en producción sin Deployment producción intervención humana

```
    CI                    CD (Delivery)         CD (Deployment)
```

```
┌─────┬─────┬───────┐     ┌──────┬──────────┐     ┌──────────────┐
│Build│Test │Calidad│───│ Pack │ Registry │───│ Deploy Prod  │
└─────┴─────┴───────┘     └──────┴──────────┘     └──────────────┘
   automático              automático           automático
```

En este reto nos concentramos en CI y las primeras etapas de Delivery (empaquetado Docker).

---

<!-- Pagina 8 de 46 -->

# Pipelines como Código

---

<!-- Pagina 9 de 46 -->

<!-- Start of picture text -->
¿Qué es un Pipeline?<br><!-- End of picture text -->

Un pipeline es una secuencia automatizada de etapas que transforma código fuente en un artefacto desplegable.

|📥Checkout|🔨Build<br>🧪Test<br>🔍Calidad|🐋Package|🧪E2E|
|---|---|---|---|
|Cada etapa t|iene una responsabilidad clara:|||
|Etapa|Responsabilidad|||
|Checkout|Obtener el código fuente del repositorio|||
|Build|Compilar el proyecto|||
|Test|Ejecutar pruebas unitarias + generar cobertura|||
|Calidad|Análisis estático +QualityGate|||
|Package|Construir imagenDocker|||
|E2E|Pruebas de extremo a extremo (BDD)|||

---

<!-- Pagina 10 de 46 -->

# Pipeline as Code

Tradicionalmente, los pipelines se configuraban manualmente en la interfaz web del servidor CI. Esto generaba problemas:


- No versionable: Los cambios no quedan en Git

- No reproducible: Si se pierde el servidor, se pierde la configuración

- No revisable: No hay code review del pipeline No portátil: Atado a una instancia específica

Pipeline as Code resuelve esto: el pipeline se define en un archivo de texto versionado junto al código.

Herramienta Archivo Jenkins `Jenkinsfile` GitHub Actions `.github/workflows/*.yml` GitLab CI `.gitlab-ci.yml` Azure DevOps `azure-pipelines.yml`

---

<!-- Pagina 11 de 46 -->

# Jenkins – Servidor de Automatización

---

<!-- Pagina 12 de 46 -->

<!-- Start of picture text -->
¿Qué es Jenkins?<br><!-- End of picture text -->

Servidor de automatización opensource

Creado Kohsuke por Kawaguchi (2004, como Hudson) Uno de los servidores CI/CD más utilizados en la industria Escrito en Java, extensible mediante plugins

Interfaz web para visualizar pipelines, logs y resultados

---

<!-- Pagina 13 de 46 -->

<!-- Start of picture text -->
Jenkins: Arquitectura<br><!-- End of picture text -->


<!-- Start of picture text -->
-  Desarrollador<br>git push<br>📦  Git<br>webhook<br>⚙  Jenkins Controller<br>📋  Programador de Jobs<br>🤖  Agentes de ejecución<br>Agent 1 Agent 2 Agent 3<br>Docker Maven Docker Node Docker Python<br>resultado<br>resultado resultado<br>🖥  Interfaz Web ⚙  Configuración<br>Componente Rol<br>Controller Orquesta los jobs, sirve la UI, almacena configuración<br>Agent Ejecuta las etapas del pipeline (puede ser un contenedor Docker)<br>Job/Pipeline Define qué ejecutar (definido en el Jenkinsfile )<br><!-- End of picture text -->

---

<!-- Pagina 14 de 46 -->

# Pipeline Declarativo vs Scripted

## Jenkins ofrece dos sintaxis para definir pipelines:

Aspecto Declarativo Scripted Sintaxis Estructurada con `pipeline { }` Groovy libre con `node { }` Curva de Menor, más legible Mayor, más flexible aprendizaje Jenkins valida la estructura antes de Errores se detectan en Validación ejecutar ejecución Recomendado para La mayoría de casos Escenarios muy complejos Para este curso se utiliza el pipeline declarativo por su claridad y estructura.

---

<!-- Pagina 15 de 46 -->

# Anatomía de un Jenkinsfile

```
pipeline {
   agent any                            // ← Dónde ejecutar
   environment {                        // ← Variables de entorno
       SONAR_TOKEN = credentials('sonar-token')
   }
   stages {                             // ← Etapas secuenciales
       stage('Build') {
           steps {
               sh 'mvn clean compile -DskipTests'
           }
       }
       stage('Test') {
           steps {
               sh 'mvn verify'// Tests + cobertura
           }
       }
   }
   post {                               // ← Acciones post-ejecución
       success { echo ' Pipeline exitoso' }
       failure { echo ' Pipeline fallido' }
       always  { echo ' Pipeline finalizado' }
   }
}
```

---

<!-- Pagina 16 de 46 -->

# Bloques del Jenkinsfile

|Bloque|Descripción|Ejemplo|
|---|---|---|
|`pipeline`|Bloque raíz que contiene todo|`pipeline { ... }`|
|`agent`|Dónde se ejecuta (nodo,Docker<br>image)|`agent any` ,<br>`agent { docker { image '...'`<br>`} }`|
|`environment`|Variables de entorno del pipeline|`MY_VAR = 'valor'`|
|`stages`|Contenedor de etapas secuenciales|`stages { stage('...') { } }`|
|`stage`|Etapa con nombre visible en la UI|`stage('Build') { steps { } }`|
|`steps`|Comandos a ejecutar en una etapa|`sh 'mvn test'`|
|`post`|Acciones post-ejecución|`always { }` ,<br>`success { }` ,<br>`failure { }`|
|`tools`|Herramientas auto-configuradas|`tools { maven 'Maven-3.9' }`|
|`triggers`|Disparadores automáticos|`triggers { pollSCM('H/5 * * * *') }`|

---

<!-- Pagina 17 de 46 -->

# Agentes Docker

En lugar de instalar herramientas (Maven, Node, Python) en el servidor Jenkins, se usan contenedores Docker efímeros como agentes:

```
pipeline {
   agent {
       docker {
           image 'maven:3.9-eclipse-temurin-17'
           args '-v /root/.m2:/root/.m2'// Cache de dependencias
       }
   }
   stages {
       stage('Build') {
           steps {
               sh 'mvn --version'
               sh 'mvn clean compile'
           }
       }
   }
}
```

|Ventaja|Descripción|
|---|---|
|Aislamiento|Cada build corre en un contenedor limpio|
|Reproducibilidad|La misma imagenDocker, siempre el mismo entorno|
|Multi-lenguaje|Cada servicio puede usar una imagen diferente|
|Sin contaminación|No se instala nada en el servidorJenkins|

---

<!-- Pagina 18 de 46 -->

# Jenkins en Docker Compose

Para integrar Jenkins en el ecosistema del proyecto, se ejecuta como servicio Docker:

```
FROM jenkins/jenkins:lts-jdk17
```

```
# Pre-instalar plugins (reproducibilidad)
RUN jenkins-plugin-cli --plugins \
   docker-pipeline \
   workflow-aggregator \
   git \
   configuration-as-code \
   sonar
```

- `# Instalar cliente Docker USER root`

```
RUN apt-get update && apt-get install -y docker.io
RUN groupadd -f docker && usermod -aG docker jenkins
USER jenkins
```

Los plugins se instalan en el Dockerfile, no manualmente en la interfaz. Esto garantiza que cualquier miembro del equipo obtiene el mismo Jenkins al hacer `docker-compose up` .

---

<!-- Pagina 19 de 46 -->

# Docker Socket Mount

Para que Jenkins pueda construir imágenes Docker desde dentro del contenedor:


<!-- Start of picture text -->
🖥  Host<br>🐋  Docker Daemon<br>/var/run/docker.sock<br>mount<br>/var/run/docker.sock<br>📦  Jenkins Container<br>⚙  Jenkins Docker CLI<br><!-- End of picture text -->

```
# docker-compose.yml
services:
jenkins:
volumes:
```

- `/var/run/docker.sock:/var/run/docker.sock`

El contenedor Jenkins no tiene su propio daemon Docker; usa el daemon del host a través del socket.

---

<!-- Pagina 20 de 46 -->

Aprovisionamiento Automático de Pipelines

---

<!-- Pagina 21 de 46 -->

# Configuration as Code (JCasC)

El plugin Configuration as Code permite definir la configuración de Jenkins (y los jobs) en un archivo YAML:

```
# jenkins/casc.yaml
jobs:
-script:|
     pipelineJob('empleados-service') {
       definition {
         cpsScm {
           scm {
             git {
               remote {
                 url('https://github.com/usuario/empleados-service.git')
               }
               branches('*/main')
             }
           }
           scriptPath('Jenkinsfile')
         }
       }
     }
```

```
# docker-compose.yml
services:
jenkins:
environment:
-CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs
volumes:
-./jenkins/casc.yaml:/var/jenkins_home/casc_configs/jobs.yaml
```

Al arrancar Jenkins, los jobs ya están configurados. Sin tocar la interfaz.

---

<!-- Pagina 22 de 46 -->

# Calidad de Código con SonarQube

---

<!-- Pagina 23 de 46 -->

<!-- Start of picture text -->
¿Qué es SonarQube?<br><!-- End of picture text -->

Plataforma de inspección continua de código

- Analiza código fuente sin ejecutarlo (análisis estático)

- Soporta 30+ lenguajes en una sola plataforma

Dashboard web con métricas, tendencias e historial

Quality Gates: condiciones que el código debe cumplir

---

<!-- Pagina 24 de 46 -->

# ¿Qué analiza SonarQube?

|Dimensión|Qué detecta|Ejemplo|
|---|---|---|
|Bugs|Errores potenciales|`NullPointerException` , condiciones que siempre<br>son falsas|
|Vulnerabilidades|Problemas de seguridad|InyecciónSQL, XSS, credenciales hardcodeadas|
|CodeSmells|Código difícil de mantener|Métodos demasiado largos, complejidad ciclomática<br>alta|
|Duplicación|Código repetido|Bloques copiados entre clases|
|Cobertura|% del código ejecutado por<br>tests|Importa reportes deJaCoCo, coverage.py, lcov|
|Deuda Técnica|Estimación del esfuerzo de<br>corrección|"3 horas para corregir 12 code smells"|


SonarQube no ejecuta las pruebas. Solo importa los reportes generados por la herramienta de cobertura (JaCoCo, pytest-cov, nyc).

---

<!-- Pagina 25 de 46 -->

# Análisis Estático vs Dinámico

Aspecto Análisis Estático Análisis Dinámico Cuándo Sin ejecutar el código Ejecutando el código Patrones problemáticos, estilo, Comportamiento real, errores en Qué detecta vulnerabilidades tiempo de ejecución SonarQube, Checkstyle, ESLint, Herramientas JUnit, pytest, Cucumber pylint Depende de los tests (segundos a Velocidad Rápido (segundos) minutos) Ambos son necesarios en un Complementarios pipeline CI completo

---

<!-- Pagina 26 de 46 -->

# Quality Gate

Un Quality Gate es un conjunto de condiciones booleanas que determinan si el código es aceptable para pasar a la siguiente etapa.

|Condición|Umbral típico|¿Qué mide?|
|---|---|---|
|Cobertura en código nuevo|≥ 70%|¿Las pruebas cubren el código nuevo?|
|Duplicación en código nuevo|≤ 3%|¿Hay código copiado?|
|Bugs nuevos|0|¿Se introdujeron errores potenciales?|
|Vulnerabilidades nuevas|0|¿Se introdujeron problemas de seguridad?|
|Calificación de mantenibilidad|A|¿El código es mantenible?|


Si cualquier condición no se cumple, el Quality Gate falla y el pipeline se detiene.

---

<!-- Pagina 27 de 46 -->

# SonarQube en el Pipeline

```
stage('Test') {
   steps {
       sh 'mvn verify'// Ejecuta tests + genera reporte JaCoCo (cobertura)
   }
}
stage('SonarQube') {
   steps {
       sh '''
           mvn sonar:sonar \
             -Dsonar.host.url=http://sonarqube:9000 \
             -Dsonar.token=${SONAR_TOKEN}
       '''
   }
}
stage('Quality Gate') {
   steps {
       timeout(time:5, unit:'MINUTES') {
           waitForQualityGate abortPipeline:true// ← Si falla, el pipeline se detiene
       }
   }
}
```

El flujo es: Test genera cobertura → SonarQube analiza → Quality Gate decide → o

---

<!-- Pagina 28 de 46 -->

# SonarQube: Multi-lenguaje

Lenguaje Scanner Comando Reporte de cobertura Java (Maven) Sonar Maven Plugin `mvn sonar:sonar` JaCoCo XML Java (Gradle) Sonar Gradle Plugin `gradle sonarqube` JaCoCo XML Python sonar-scanner `sonar-scanner coverage.xml` (pytest-cov) Node.js sonar-scanner `sonar-scanner lcov.info` (nyc) Go sonar-scanner `sonar-scanner coverage.out` (go test)

### Para lenguajes sin plugin nativo, se usa el Sonar Scanner con un archivo de configuración:

```
# sonar-project.properties
sonar.projectKey=mi-microservicio
sonar.projectName=Mi Microservicio
sonar.sources=src
sonar.host.url=http://sonarqube:9000
sonar.token=squ_xxxxxxxxxxxxxxxxxxxx
```

---

<!-- Pagina 29 de 46 -->

CI en Microservicios

---

<!-- Pagina 30 de 46 -->

# ¿Por qué CI es especialmente importante en Microservicios?

|Desafío del ecosistema|CómoCIlo resuelve|
|---|---|
|Múltiples servicios, múltiples<br>lenguajes|Un<br>`Jenkinsfile` por servicio, cada uno con su stack|
|Deployments independientes|Cada servicio se compila, prueba y empaqueta por<br>separado|
|Contratos entre servicios|Las pruebas detectan rupturas enAPIs y eventos|
|"En mi máquina funciona"|El pipeline ejecuta en un entorno limpio (Docker)|
|Múltiples equipos|Dashboard unificado: todos ven el estado de todos los<br>servicios|
|Flujos de negocio entre servicios|PruebasE2Evalidan el flujo completo|


Cada microservicio debe poder ser compilado, probado y empaquetado de forma independiente. Un `Jenkinsfile` por servicio garantiza esto.

---

<!-- Pagina 31 de 46 -->

<!-- Start of picture text -->
Un Pipeline por Microservicio<br>empleados-service (Java)<br>Build Test Package<br>SonarQube<br>mvn compile mvn verify docker build<br>auth-service (Python)<br>Build Test Package 🧪  E2E Tests<br>SonarQube<br>pip install pytest --cov docker build BDD<br>notificaciones-service (Node.js)<br>Build Test Package<br>SonarQube<br>npm install nyc npm test docker build<br><!-- End of picture text -->

Cada servicio tiene su propio pipeline que se ejecuta de forma independiente. Las pruebas E2E se ejecutan solo cuando todos los servicios están empaquetados.

---

<!-- Pagina 32 de 46 -->

# Pruebas E2E en el Pipeline

Las pruebas BDD del Reto 5 se incorporan al pipeline CI como etapa de verificación final:

```
stage('E2E Tests') {
   steps {
       sh 'docker-compose up -d --build'// Levantar sistema completo
       sh '''
           echo "Esperando que los servicios estén listos..."
           // Script de health check con reintentos
       '''
       sh 'mvn test -f e2e-tests/pom.xml'// Ejecutar suite BDD
   }
   post {
       always {
           sh 'docker-compose down -v'// Cleanup siempre
       }
   }
}
```

Las mismas pruebas que antes se ejecutaban manualmente ahora se ejecutan automáticamente en cada integración.

---

<!-- Pagina 33 de 46 -->

# Patrones de Despliegue

---

<!-- Pagina 34 de 46 -->

# ¿Por qué importan los Patrones de Despliegue?

Un pipeline CI genera un artefacto verificado (imagen Docker). El siguiente paso es cómo llevarlo a producción de forma segura.

|Problema|Sin patrón|Con patrón de despliegue|
|---|---|---|
|Riesgo de fallos|Todo el tráfico impacta a todos<br>los usuarios|Solo un subconjunto de usuarios<br>es afectado|
|Rollback|Manual, lento, traumático|Inmediato al redirigir el tráfico|
|Validación en<br>producción|Imposible sin afectar usuarios|Posible con un porcentaje<br>controlado|
|Experimentos|No se pueden hacer en<br>producción|A/BTesting permite comparar<br>variantes|


Los patrones de despliegue son la extensión natural de CI/CD: el pipeline entrega el artefacto; el patrón define cómo ese artefacto llega a los usuarios.

---

<!-- Pagina 35 de 46 -->

<!-- Start of picture text -->
Blue/Green Deployment<br><!-- End of picture text -->


<!-- Start of picture text -->
🔵  Blue (v1 — Producción actual)<br>100% del tráfico Instancia 1 Instancia 2<br>👥  Usuarios ⚖  Load Balancer<br>🟢  Green (v2 — Nueva versión)<br>0% → 100% (tras validación) Instancia 1 Instancia 2<br>Fase Acción<br>1. Despliegue Se levanta el entorno Green con la nueva versión<br>2. Validación Se prueban los servicios Green sin tráfico real<br>3. Cambio El Load Balancer redirige el 100% del tráfico a Green<br>4. Rollback Si hay problemas, se vuelve a Blue en segundos<br><!-- End of picture text -->

---

<!-- Pagina 36 de 46 -->

<!-- Start of picture text -->
Canary Release<br>🐦  Canary (v2) ✅  OK Incrementar %<br>📊  Métricas<br>10% 10% del tráfico<br>error rate, latencia<br>❌  Falla Rollback<br>👥  Usuarios ⚖  Load Balancer<br>🟦  Versión Estable (v1)<br>90% 90% del tráfico<br>Característica Detalle<br>Origen del nombre Como el canario en las minas: detecta el peligro primero<br>Tráfico inicial 5–10% → se incrementa gradualmente<br>Decisión Basada en métricas: tasa de error, latencia, alertas<br>Rollback Redirigir el 100% de vuelta a la versión estable<br><!-- End of picture text -->

---

<!-- Pagina 37 de 46 -->

<!-- Start of picture text -->
A/B Testing<br>🅰  Versión A (Control)<br>Algoritmo de<br>Segmento A<br>recomendación actual<br>📊  Analytics 📋  Decisión<br>👥  Usuarios 🔀  Router / Feature Flag<br>conversión, retención based on data<br>🅱  Versión B (Variante)<br>Nuevo algoritmo de<br>Segmento B<br>recomendación<br>Diferencia clave Canary A/B Testing<br>Objetivo Estabilidad técnica Validación de negocio<br>Métrica Error rate, latencia Conversión, retención, NPS<br>Selección de usuarios Aleatoria Por segmento (edad, región, perfil)<br>Decisión Automática (umbrales) Humana (análisis de datos)<br><!-- End of picture text -->

---

<!-- Pagina 38 de 46 -->

<!-- Start of picture text -->
Rolling Update<br>Rolling Update (2 a la vez)<br>Flota de réplicas (servicio) 🔄  v1→v2 🟡  v2<br>🟢  v1 🟢  v1 🟢  v1 🟢  v1 actualiza gradualmente<br>🔄  v1→v2 🟡  v2<br>Característica Detalle<br>Cómo funciona Las réplicas se reemplazan una a una (o en lotes)<br>Disponibilidad Siempre hay instancias activas: cero downtime<br>Infraestructura No requiere duplicar recursos<br>Velocidad Configurable: --update-delay , --update-parallelism<br>Rollback Automático si el health check falla en una réplica<br><!-- End of picture text -->

---

<!-- Pagina 39 de 46 -->

# Feature Flags


<!-- Start of picture text -->
💻  Código<br>🚀  Deploy mismo artefacto sí (producción) ✨  Nueva funcionalidad<br>(feature activa)<br>🔧  Feature Flag<br>¿Habilitado?<br>⚙  Configuración / Toggle  activa\/desactiva sin  🔄  Comportamiento<br>no (rollout parcial)<br>anterior<br>Service redeploy<br>Característica Detalle<br>Qué es Condición en el código que activa/desactiva una funcionalidad<br>Despliegue El código llega a producción inactivo<br>Activación A través de configuración, sin nuevo deploy<br>Combina con Canary, A/B Testing (activar sólo para ciertos usuarios)<br>Riesgo Deuda de feature flags: hay que eliminarlos cuando la feature es estable<br><!-- End of picture text -->

---

<!-- Pagina 40 de 46 -->

# Comparativa: Los Cinco Patrones

|Aspecto|Blue/Green|Canary|A/BTesting|Rolling Update|FeatureFlags|
|---|---|---|---|---|---|
|Objetivo|Cero<br>downtime|Riesgo gradual|Hipótesis negocio|Actualización<br>eficiente|Desacoplar<br>deploy/release|
|Rollback|Inmediato|Rápido|Lento|Automático|Instantáneo (sin<br>deploy)|
|Infraestructura|2×<br>(transitorio)|Incremental|Paralela<br>permanente|Sin duplicar|Sin cambios|
|Complejidad|Media|Alta|Muy alta|Baja|Media (deuda de<br>flags)|
|Automatización|Alta|Alta|Parcial|Nativa<br>(Swarm/K8s)|Alta|
|Cuándo usarlo|Releases<br>críticos|Microservicios<br>frecuentes|Experimentos de<br>producto|Entornos<br>orquestados|Trunk-based<br>development|


En equipos maduros, Feature Flags + Canary se combinan para el máximo control: el código llega inactivo y se activa progresivamente.

---

<!-- Pagina 41 de 46 -->

# Patrones de Despliegue en el Pipeline CI/CD


<!-- Start of picture text -->
🚀  CD (Deployment)<br>🔵 🟢  Blue/Green<br>🐦  Canary<br>⚙  CI (este taller)<br>Package<br>Build Test SonarQube imagen verificada Estrategia 🅰🅱 A/B<br>Docker<br>🔄  Rolling<br>🔧  Feature Flag<br><!-- End of picture text -->

El pipeline CI no cambia: siempre produce una imagen Docker verificada. La estrategia de despliegue es una decisión operativa y de negocio que se aplica después de CI.

---

<!-- Pagina 42 de 46 -->

Pipeline Completo

---

<!-- Pagina 43 de 46 -->

# Vista Integrada del Pipeline

|`┌─────────`<br>`│`<br>`├─────────`<br>|`──────────`<br> <br>`┬─────────`<br>|`───────────────────────────────────────────────────┐`<br>`Jenkinsfile                                   │`<br>`┬──────────┬──────────┬──────────┬─────────────────┤`<br>|
|---|---|---|
|`│Checkout`<br>`│`<br>`├─────────`|`│ Build`<br>`│`<br>`┼─────────`|`│  Test    │SonarQube │ Package  │   E2E Tests     │`<br>`│+ Cobert. │+ Q. Gate │Docker img│   BDD Suite     │`<br>`┼──────────┼──────────┼──────────┼─────────────────┤`|
|`│ git`<br>`│ clone`<br>`│`<br>`│`<br>`├`|`│mvn`<br>`│compile`<br>`│npm i`<br>`│go build`<br>`┴`|`│mvn verify│mvn       │docker    │docker-compose   │`<br>`│pytest    │sonar:sonar│build    │up + cucumber    │`<br>`│--cov     │sonar-    │          │+ compose down   │`<br>`│nyc test  │scanner   │          │                 │`<br>`┴┴┴┴┤`|
|`─────────`<br>`│ post { a`<br>`└─────────`|`─────────`<br>`lways { ..`<br>`──────────`|`───────────────────────────────────────────────`<br>`. } success { ... } failure { ... } }              │`<br>`───────────────────────────────────────────────────┘`|
|Si fa|lla en...|Significado|
|Build||El código no compila|
|Test||Hay pruebas unitarias que fallan|
|SonarQub|e/QualityG|ate<br>Cobertura < 70%, bugs, o vulnerabilidades|
|Package||Error en elDockerfile|
|E2E||Un flujo de negocio entre servicios está roto|

---

<!-- Pagina 44 de 46 -->

# Interpretando los Resultados

En la interfaz de Jenkins, cada etapa se muestra como una columna:

```
 Checkout    Build      Test     SonarQube   Quality    Package    E2E
                                              Gate
 ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
 │    │  │    │  │    │  │    │  │    │  │    │  │    │
 └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘
```

`┌──────┐  ┌──────┐  ┌──────┐ │ │  │ │  │ │   ← El pipeline se detuvo: una prueba falló └──────┘  └──────┘  └──────┘` Verde ( ): La etapa pasó exitosamente Rojo ( ): La etapa falló → el pipeline se detiene

Gris: La etapa no se ejecutó (porque una anterior falló)

El pipeline falla rápido y en la etapa correcta, indicando exactamente dónde está el problema.

---

<!-- Pagina 45 de 46 -->

# Resumen

|Concepto|Rol en el pipeline|
|---|---|
|CI|Práctica: verificar automáticamente cada integración|
|Pipeline asCode|Principio: el pipeline es un archivo versionado (<br>`Jenkinsfile` )|
|Jenkins|Herramienta: servidor que orquesta la ejecución del pipeline|
|AgentesDocker|Infraestructura: entornos efímeros para build y test|
|SonarQube|Calidad: análisis estático + cobertura +QualityGate|
|QualityGate|Decisión: ¿el código cumple los estándares de calidad?|
|E2E/BDD|Validación: las pruebas funcionales delReto 5, automatizadas enCI|
|DockerPackage|Entregable: imagenDocker lista para despliegue|
|Blue/Green|Despliegue atómico: cambio instantáneo entre dos entornos|
|CanaryRelease|Despliegue gradual: exposición progresiva a usuarios reales|
|A/BTesting|Experimento: validación de hipótesis de negocio con datos reales|
|Rolling Update|Actualización réplica a réplica sin duplicar infraestructura|
|FeatureFlags|Desacopla el momento de despliegue del momento de activación|

---

<!-- Pagina 46 de 46 -->

Arquitectura Basada en Microservicios Programa de Ingeniería de Sistemas y Computación Universidad del Quindío


2025 Christian Andrés Candela Uribe
