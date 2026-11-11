<!-- Pagina 1 de 32 -->

# **Reto 7 – Integración Continua con Jenkins**

## **Contexto**

Este reto continúa el desarrollo del **sistema de onboarding y offboarding de empleados** . Hasta ahora, se ha construido un sistema distribuido con:

Servicios de negocio con persistencia y comunicación REST (Retos 1 y 2)

Comunicación asincrónica basada en eventos (Reto 4)

Seguridad centralizada con JWT y RBAC (Reto 5)

Pruebas automatizadas en los tres niveles de la pirámide —unitarias, de integración y BDD— **con generación de reportes en formato estándar** (Reto 6)

A lo largo de los retos anteriores, cada equipo ha compilado, probado y desplegado sus microservicios de forma **manual** : ejecutando comandos de build localmente, corriendo pruebas en la terminal, y construyendo imágenes Docker a mano. Cuando un miembro del equipo introduce un cambio que rompe el build o las pruebas de otro servicio, el problema se descubre tarde — a veces solo cuando alguien ejecuta `docker compose up` y el sistema falla.

Además, los reportes generados en el Reto 6 hoy **no los ve nadie** : son archivos XML y HTML que quedan en el disco de quien ejecutó las pruebas. Nadie sabe si la cobertura sube o baja entre commits, ni qué escenario de negocio se rompió en el último cambio.

En este reto se implementará un **pipeline de Integración Continua (CI)** utilizando **Jenkins** , de modo que cada cambio en el código sea automáticamente compilado, probado y empaquetado, **con todos los reportes de pruebas publicados y visibles en la interfaz de Jenkins** , detectando problemas **en minutos** , no en días.

## **Objetivo**

Configurar un entorno de **Integración Continua** con **Jenkins** dentro del ecosistema Docker del proyecto. Cada microservicio debe contar con un **Jenkinsfile** que defina un pipeline automatizado con las etapas de **build** , **test** , **calidad** y **empaquetado Docker** , **publicando en Jenkins todos los reportes**

**de pruebas generados en el Reto de automatización de pruebas** , y preparando al equipo para los requisitos CI/CD del proyecto final.

---

<!-- Pagina 2 de 32 -->

## **Introducción**

### **¿Qué es la Integración Continua?**

La **Integración Continua (CI – Continuous Integration)** es una práctica de desarrollo de software en la que los desarrolladores integran su código en un repositorio compartido de forma frecuente, y cada integración se **verifica automáticamente** mediante compilación y pruebas.

|**Aspecto**|**Sin CI**|**Con CI**|
|---|---|---|
|**Compilación**|Manual, cuando alguien se<br>acuerda|Automática, en cada push|
|**Pruebas**|Se ejecutan localmente (o no se<br>ejecutan)|Se ejecutan automáticamente en cada<br>cambio|
|**Detección de**<br>**errores**|Al intentar desplegar (tarde)|En minutos tras el commit (temprano)|
|**Confianza en el**<br>**código**|"En mi máquina funciona"|El pipeline lo verifica en un entorno<br>limpio|
|**Empaquetado**|Manual:<br>`docker build`en la<br>terminal|Automático: imagen Docker generada<br>por el pipeline|


**Principio fundamental:** Si duele hacerlo manualmente, automatícelo. Si lo automatiza, hágalo frecuentemente.

### **CI en el contexto de Microservicios**

En una arquitectura de microservicios, la CI es especialmente valiosa porque:

1. **Múltiples servicios, múltiples lenguajes** : Cada servicio puede tener su propio stack tecnológico. Sin CI automatizada, es fácil que un servicio quede sin compilar o sin pruebas durante días.

2. **Deployments independientes** : Cada servicio debería poder compilarse, probarse y empaquetarse **de forma independiente** . Un `Jenkinsfile` por servicio garantiza esto.

3. **Contratos entre servicios** : Un cambio en un evento o en un endpoint puede romper otro servicio. Las pruebas automatizadas (unitarias e integración) en el pipeline detectan estas rupturas.

---

<!-- Pagina 3 de 32 -->

### **Jenkins**

**Jenkins** es un servidor de automatización open-source, ampliamente utilizado para implementar pipelines de CI/CD.

|**Característica**|**Descripción**|
|---|---|
|**Open Source**|Gratuito, con una gran comunidad y ecosistema de plugins|
|**Pipeline as Code**|Los pipelines se definen en un archivo<br>`Jenkinsfile`versionado junto al<br>código|
|**Extensible**|Miles de plugins: Docker, Git, reportes, notificaciones, etc.|
|**Integración**|Puede construir imágenes Docker, ejecutar contenedores, y publicar en|
|**Docker**|registries|
|**Multi-lenguaje**|No está atado a ningún lenguaje; ejecuta lo que usted configure|


#### **Pipeline Declarativo vs Scripted**

Jenkins ofrece dos sintaxis para definir pipelines:

|**Aspecto**|**Declarativo**|**Scripted**|
|---|---|---|
|**Sintaxis**|Estructurada con bloques<br>`pipeline { }`|Groovy libre con<br>`node { }`|
|**Curva de aprendizaje**|Menor, más legible|Mayor, más flexible|
|**Recomendado para**|La mayoría de casos|Escenarios muy complejos|


Para este reto se utilizará el **pipeline declarativo** por su claridad y estructura:

---

<!-- Pagina 4 de 32 -->

```
pipeline {
    agent any
    stages {
stage('Build'){
            steps {
// Compilar el proyecto
}
}
stage('Test'){
            steps {
// Ejecutar pruebas
}
}
stage('Package'){
            steps {
// Construir imagen Docker
}
}
}
    post {
        always {
// Acciones de limpieza o notificación
}
}
}
```

#### **Conceptos clave del Jenkinsfile**

|**Concepto**|**Descripción**|
|---|---|
|`pipeline`|Bloque raíz que define todo el pipeline|
|`agent`|Dónde se ejecuta el pipeline (nodo, contenedor Docker, etc.)|
|`stages`|Conjunto de etapas secuenciales|
|`stage`|Una etapa con nombre (Build, Test, Package...)|
|`steps`|Los comandos a ejecutar dentro de una etapa|
|`post`|Acciones que se ejecutan después del pipeline (siempre, solo si falla, etc.)|
|`environment`|Variables de entorno disponibles en todo el pipeline|

---

<!-- Pagina 5 de 32 -->

|**Concepto**|**Descripción**|
|---|---|
|`tools`|Herramientas a configurar (Maven, JDK, Node, etc.)|


### **Jenkins en Docker**

Para que Jenkins funcione dentro del ecosistema Docker del proyecto, se necesita resolver un

problema: **Jenkins necesita construir imágenes Docker desde dentro de un contenedor** .

Hay dos estrategias principales:

|**Estrategia**|**Cómo funciona**|**Ventajas**|**Desventajas**|
|---|---|---|---|
|**Docker**<br>**Socket**<br>**Mount**|Se monta<br>`/var/run/docker.sock`del<br>host en el contenedor Jenkins|Sencillo, usa<br>el Docker del<br>host|Compartir el socket es un<br>riesgo de seguridad<br>(aceptable en entorno<br>académico)|
|**Docker-in-**<br>**Docker**<br>**(DinD)**|Se ejecuta un daemon Docker<br>dentro del contenedor Jenkins|Más aislado|Más complejo, posibles<br>problemas con capas de<br>almacenamiento|


**Recomendación para este reto** : Docker Socket Mount, por simplicidad.

## **Requisitos Generales**

- Utilizar **Jenkins** como servidor de integración continua.

- Definir los pipelines en archivos **`Jenkinsfile`** versionados junto al código de cada microservicio. Usar la sintaxis de **pipeline declarativo** .

- Jenkins debe ejecutarse como un **servicio en Docker Compose** , accesible desde el navegador. Los pipelines deben poder ejecutarse **sin intervención manual** una vez configurados.

- **Todos los reportes de pruebas del Reto 6 deben publicarse en Jenkins** : resultados unitarios y de integración, cobertura, y el reporte navegable de los escenarios BDD.

- Un fallo de pruebas debe verse **en la interfaz de Jenkins** , indicando qué prueba o escenario falló, no solo en el log de consola.

---

<!-- Pagina 6 de 32 -->

## **Retos**

Los siguientes cinco puntos están organizados en orden de complejidad creciente. Se recomienda abordarlos en secuencia, ya que cada punto construye sobre las habilidades y la configuración del anterior.

### **Punto 1: Configuración de Jenkins en Docker Compose (1.0 pt)**

#### **Lo que se entrega**

Un enfoque basado en un **`Dockerfile` personalizado** que pre-instala los plugins necesarios y el cliente Docker, de modo que la configuración sea **reproducible** y no dependa de pasos manuales en la interfaz de Jenkins.

**`jenkins/Dockerfile` :**

---

<!-- Pagina 7 de 32 -->

```
# Instalar plugins necesarios de forma automatizada
# Referencia: https://github.com/jenkinsci/docker#preinstalling-plugins
RUN jenkins-plugin-cli --plugins \
    docker-pipeline \
    docker-workflow \
    pipeline-stage-view \
    workflow-aggregator \
    git \
    configuration-as-code \
    job-dsl \
    sonar \
# --- Publicación de reportes de pruebas (Reto 6) ---
    junit \
    coverage \
    cucumber-reports \
    htmlpublisher
# Instalar cliente Docker dentro del contenedor Jenkins
USER root
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*
# Agregar usuario jenkins al grupo docker para acceder al socket
RUN groupadd -f docker && usermod -aG docker jenkins
USER jenkins
```

**`docker-compose.yml` (fragmento):**

---

<!-- Pagina 8 de 32 -->

```
services:
jenkins:
build:
context: ./jenkins
dockerfile: Dockerfile
container_name: jenkins
ports:
-"9090:8080"# Interfaz web
-"50000:50000"# Comunicación con agentes
volumes:
- jenkins_data:/var/jenkins_home
- /var/run/docker.sock:/var/run/docker.sock  # Acceso al Docker del host
environment:
- JAVA_OPTS=-Djenkins.install.runSetupWizard=false
networks:
- microservices-network
```

```
volumes:
jenkins_data:
```

**Nota:** `jenkins-plugin-cli` es la herramienta oficial para instalar plugins desde la línea de comandos. Al incluirla en el Dockerfile, cada vez que se reconstruya la imagen, Jenkins tendrá los mismos plugins instalados sin intervención manual.

**Nota:** `runSetupWizard=false` desactiva el asistente de configuración inicial, ya que los plugins se pre-instalan en el Dockerfile.

#### **Lo que debe hacer**

1. **Crear un directorio** **`jenkins/`** en la raíz del proyecto con un `Dockerfile` personalizado basado en la imagen oficial de Jenkins ( `jenkins/jenkins:lts-jdk17` o `lts-jdk21` ).

2. **Pre-instalar los plugins necesarios** en el Dockerfile usando `jenkins-plugin-cli` . Como mínimo: `workflow-aggregator` (Pipeline)

   - `docker-pipeline` (Docker Pipeline)

   - `git` (integración Git)

   - **Plugins de reportes** (Puntos 2 y 4): `junit` para resultados de pruebas, `coverage` para cobertura (sustituye al antiguo plugin `jacoco` y soporta JaCoCo, Cobertura y lcov), `cucumber-reports` para los escenarios BDD y `htmlpublisher` como alternativa genérica

**Nota sobre los plugins de reportes.** No los deje para después: son la diferencia entre un pipeline que dice _"FAILED"_ y uno que dice _"falló el escenario «El empleado retirado no puede iniciar sesión»"_ . Instálelos desde el inicio.

---

<!-- Pagina 9 de 32 -->

3. **Instalar el cliente Docker** dentro del contenedor Jenkins para permitir la construcción de

imágenes. Montar el socket Docker del host en el `docker-compose.yml` .

4. **Agregar Jenkins al** **`docker-compose.yml`** usando `build:` en lugar de `image:` , apuntando al Dockerfile personalizado. Asegúrese de que Jenkins esté en la misma red que los demás servicios.

5. **Levantar el sistema** y verificar que Jenkins es accesible desde `http://localhost:9090` . No debería requerir instalar plugins manualmente.

6. **Verificar la configuración** creando un pipeline de prueba que confirme que Docker funciona desde Jenkins:

`pipeline { agent any stages { stage('Verificación') { steps { echo '` ✅ `Jenkins está correctamente configurado' sh 'docker --version' sh 'docker ps' } } } }`

Si ambos comandos Docker se ejecutan correctamente, la configuración está completa.

#### **Decisión técnica requerida**

Usted debe decidir:

- ¿Qué plugins adicionales pre-instala en el Dockerfile según las herramientas que usará en los puntos posteriores (cobertura, análisis estático, reportes HTML)?

- ¿Monta el socket de Docker o utiliza DinD? ¿Cómo resuelve los permisos del socket Docker dentro del contenedor?

- ¿Desactiva el Setup Wizard ( `runSetupWizard=false` ) o lo mantiene para crear el usuario administrador manualmente?

---

<!-- Pagina 10 de 32 -->

#### **Lo que se entrega**

Ejemplo de un `Jenkinsfile` declarativo para un microservicio Java con Maven, **publicando los reportes generados en el Reto 6** :

---

<!-- Pagina 11 de 32 -->

```
pipeline {
    agent any
    stages {
stage('Checkout'){
            steps {
// Si el Jenkinsfile está en el mismo repo, Jenkins hace checkout automáti
// Si necesita clonar un repo diferente:
// git url: 'https://github.com/usuario/mi-servicio.git', branch: 'main'
                echo 'Código fuente obtenido'
}
}
stage('Build'){
            steps {
                sh 'mvn clean compile -DskipTests'
}
}
stage('Test'){
            steps {
// Ejecuta unitarias + integración y genera los reportes del Reto 6.
// El flag -Dmaven.test.failure.ignore permite que el pipeline llegue al
// bloque post y publique el reporte ANTES de marcar el build como fallido
                sh 'mvn verify -Dmaven.test.failure.ignore=true'
}
            post {
                always {
// Publica los resultados: Jenkins marca el build UNSTABLE si hay fall
                    junit 'target/surefire-reports/*.xml, target/failsafe-reports/*.xml'
// Publica la cobertura y su tendencia entre builds
recordCoverage(
                        tools:[[parser:'JACOCO', pattern:'target/site/jacoco/jacoco.xml
                        sourceCodeRetention:'EVERY_BUILD'
)
}
}
}
}
    post {
        always {
            echo 'Pipeline finalizado'
```

---

<!-- Pagina 12 de 32 -->

`} success { echo '` ✅ `Build y tests exitosos' } unstable { echo '` ⚠ `El build compiló pero hay pruebas fallando' } failure { echo '` ❌ `El pipeline ha fallado' } } }`

##### **Los tres pasos de publicación que debe conocer**

|**Paso**|**Qué hace**|**Qué aparece en Jenkins**|
|---|---|---|
|`junit '<patrón>'`|Lee los XML de<br>resultados|Pestaña**Test Result**con el detalle de cada<br>prueba fallida, y una**gráfica de tendencia**<br>de pruebas por build|
|`recordCoverage(...)`|Lee el reporte<br>de cobertura|Pestaña**Coverage**con el porcentaje por<br>paquete/archivo y su**variación respecto al**<br>**build anterior**|
|`archiveArtifacts '<patrón>'`|Guarda<br>archivos del<br>build|Enlaces de descarga en la página del build|


**Por qué** **`-Dmaven.test.failure.ignore=true` (o su equivalente).** Si el comando de pruebas aborta el pipeline inmediatamente, la etapa nunca llega a publicar el reporte y usted pierde justo la información que necesita para diagnosticar. El patrón correcto es: **dejar que las pruebas**

**terminen, publicar el reporte, y que sea el paso** **`junit` quien marque el build como fallido o inestable.** El equivalente en otros stacks es `|| true` en el comando seguido de la publicación del reporte.

##### **Publicación por lenguaje**

Todos los stacks producen JUnit XML (configurado en el Reto 6), así que el paso `junit` es el mismo. Solo cambia el parser de cobertura:

---

<!-- Pagina 13 de 32 -->

|**Lenguaje**|**Patrón de resultados**|**Parser de cobertura**|
|---|---|---|
|**Java**<br>**(Maven)**|`target/surefire-reports/*.xml`|`JACOCO`sobre<br>`target/site/jacoco/jacoco.xml`|
|**Python**|`reports/junit.xml`|`COBERTURA`sobre<br>`coverage.xml`|
|**Node.js**|`reports/junit.xml`|`COBERTURA`(tras convertir lcov) o el<br>parser de lcov|
|**Go**|`reports/junit.xml`(vía<br>`go-junit-report`)|`COBERTURA`(tras convertir con<br>`gocover-cobertura`)|
|**.NET**|`**/*.trx`(con el plugin<br>`mstest`)|`COBERTURA`sobre<br>`coverage.cobertura.xml`|


La siguiente tabla muestra los comandos de build, test y generación de cobertura según el lenguaje:

|**Lenguaje**|**Comando Build**|**Comando Test + Cobertura**|
|---|---|---|
|**Java**<br>**(Maven)**|`mvn clean compile -DskipTests`|`mvn verify`(con JaCoCo configurado en<br>`pom.xml`)|
|**Java**<br>**(Gradle)**|`gradle build -x test`|`gradle test jacocoTestReport`|
|**Python**|`pip install -r requirements.txt`|`pytest --cov --cov-report=xml`|
|**Node.js**|`npm install`|`nyc --reporter=lcov npm test`|
|**Go**|`go build ./...`|`go test -coverprofile=coverage.out ./...`|


**Importante:** La generación de reportes de cobertura en la etapa de Test es esencial para que SonarQube (Punto 3) pueda importarlos y evaluar el Quality Gate. SonarQube **no ejecuta las pruebas** ; solo lee los reportes generados aquí.

#### **Lo que debe hacer**

1. **Crear un** **`Jenkinsfile`** en la raíz del directorio de **uno** de sus microservicios. Elija el servicio que tenga pruebas unitarias implementadas.

2. **Definir las etapas** del pipeline:

   - **Checkout** : Obtener el código fuente

   - **Build** : Compilar el proyecto

---

<!-- Pagina 14 de 32 -->

**Test** : Ejecutar las pruebas unitarias y de integración del Reto 6, **generar los reportes**

- y **publicarlos en Jenkins** con `junit` y `recordCoverage` en un bloque `post { always { } }`

- 3. **Aprovisionar el pipeline como código** (sin configuración manual en la interfaz). El objetivo es que al levantar Jenkins con `docker compose up` , los pipelines ya estén configurados. Hay varias estrategias:

**Opción A — Jenkins Configuration as Code (JCasC):** Crear un archivo YAML que defina los jobs automáticamente. Este archivo se monta como volumen en el contenedor Jenkins:

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

Y en el `docker-compose.yml` :

```
services:
jenkins:
# ...
volumes:
- ./jenkins/casc.yaml:/var/jenkins_home/casc_configs/jobs.yaml
environment:
```

```
- CASC_JENKINS_CONFIG=/var/jenkins_home/casc_configs
```

**Opción B — Script** **`init.groovy.d` :** Colocar scripts Groovy en el directorio `init.groovy.d/` que se ejecutan al arrancar Jenkins. Estos scripts pueden crear los jobs programáticamente:

---

<!-- Pagina 15 de 32 -->

```
// jenkins/init.groovy.d/create-jobs.groovy
import jenkins.model.*
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import hudson.plugins.git.GitSCM
```

```
def jenkins = Jenkins.instance
// ... crear el job programáticamente
```

**Opción C — Jenkinsfile local:** Si el código de los microservicios está accesible desde el contenedor (por ejemplo, montado como volumen), configurar el pipeline para que lea el `Jenkinsfile` directamente del sistema de archivos local.

**Importante:** El plugin `configuration-as-code` debe estar pre-instalado en el Dockerfile de Jenkins (Punto 1) para que la Opción A funcione. El plugin `job-dsl` es necesario para definir jobs en JCasC.

4. **Configurar las herramientas necesarias** dentro del pipeline. Dado que Jenkins se ejecuta en un contenedor, puede necesitar:

Usar una imagen Docker como agente del pipeline

   - ( `agent { docker { image 'maven:3.9-eclipse-temurin-17' } }` ) O instalar las herramientas directamente en el contenedor Jenkins

5. **Verificar los reportes en la interfaz de Jenkins** . Tras ejecutar el pipeline debe poder ver:

   - La pestaña **Test Result** con el número de pruebas ejecutadas y el detalle de cada una. La pestaña **Coverage** con el porcentaje alcanzado.

Tras un segundo build, las **gráficas de tendencia** de ambas métricas.

6. **Comprobar que un fallo se ve en la interfaz.** Rompa deliberadamente una prueba unitaria y verifique que Jenkins muestra el nombre de la prueba fallida y su mensaje de error **en la pestaña Test Result** , sin tener que abrir el log de consola.

#### **Decisión técnica requerida**

- **Aprovisionamiento de jobs** : ¿Qué estrategia usa para que los pipelines se configuren automáticamente al levantar Jenkins? ¿JCasC, init.groovy.d, o volúmenes locales? Justifique su elección.

- **Fallido vs. inestable** : por convención, un build con **pruebas fallidas** se marca `UNSTABLE` (amarillo) y uno que **no compila** se marca `FAILURE` (rojo). ¿Adoptó esa convención o prefiere que cualquier prueba fallida sea `FAILURE` ? Justifique: ¿debería un servicio con pruebas fallidas poder llegar a la etapa de empaquetado?

- **Agente del pipeline** : ¿Ejecuta los pasos directamente en el contenedor Jenkins o utiliza

- contenedores Docker efímeros como agentes? La opción de contenedores efímeros es más limpia

---

<!-- Pagina 16 de 32 -->

pero requiere la configuración Docker del Punto 1.

```
// Opción A: Ejecutar en Jenkins directamente
agent any
// Opción B: Usar contenedor Docker como agente
agent {
    docker {
        image 'maven:3.9-eclipse-temurin-17'
        args '-v /root/.m2:/root/.m2'// Cache de dependencias
}
}
```

**Gestión de dependencias** : ¿Cómo evita que cada ejecución descargue todas las dependencias desde cero? (hint: volúmenes para cachés)

### **Punto 3: Calidad de Código con SonarQube (1.0 pt)**

#### **Lo que se entrega**

**SonarQube** es una plataforma de inspección continua de código que permite evaluar la calidad del software de forma automatizada. A diferencia de herramientas individuales (Checkstyle, ESLint, flake8...) que solo cubren un lenguaje y un tipo de análisis, SonarQube ofrece una **solución unificada** :

|**Dimensión**|**Qué analiza**|
|---|---|
|**Bugs**|Errores potenciales que pueden causar comportamiento inesperado|
|**Vulnerabilidades**|Problemas de seguridad (inyecciones SQL, XSS, etc.)|
|**Code Smells**|Código que funciona pero es difícil de mantener|
|**Duplicación**|Porcentaje de código duplicado|
|**Cobertura**|Porcentaje de código ejecutado por las pruebas|
|**Deuda Técnica**|Estimación del esfuerzo para corregir los problemas|


##### **¿Por qué SonarQube en este proyecto?**

El proyecto final requiere **al menos 4 lenguajes de programación** . Con herramientas individuales, cada microservicio necesitaría su propia herramienta de análisis (Checkstyle para Java, ESLint para Node.js,

---

<!-- Pagina 17 de 32 -->

flake8 para Python, golangci-lint para Go). SonarQube analiza **todos los lenguajes en una sola plataforma** , con un dashboard unificado y Quality Gates consistentes.

##### **Quality Gate**

Un **Quality Gate** es un conjunto de condiciones que el código debe cumplir para ser considerado aceptable. SonarQube incluye un Quality Gate por defecto ("Sonar way") que se puede personalizar:

|**Condición**|**Umbral por defecto**|
|---|---|
|Cobertura en código nuevo|≥ 80%|
|Líneas duplicadas en código nuevo|≤ 3%|
|Bugs nuevos|0|
|Vulnerabilidades nuevas|0|
|Calificación de mantenibilidad|A|


Para este reto, se recomienda configurar un Quality Gate personalizado con **cobertura ≥ 70%** (alineado con el requisito del proyecto final).

##### **SonarQube en Docker**

SonarQube se dockeriza fácilmente, agregando dos servicios al Docker Compose:

---

<!-- Pagina 18 de 32 -->

```
services:
```

```
sonarqube:
image: sonarqube:lts-community
container_name: sonarqube
ports:
```

- `"9000:9000"`

- `environment:`

- `SONAR_JDBC_URL=jdbc:postgresql://sonar-db:5432/sonar`

- `SONAR_JDBC_USERNAME=sonar`

- `SONAR_JDBC_PASSWORD=sonar`

```
volumes:
```

- `sonarqube_data:/opt/sonarqube/data`

- `sonarqube_logs:/opt/sonarqube/logs`

- `sonarqube_extensions:/opt/sonarqube/extensions`

- `depends_on: - sonar-db`

- `networks:`

- `microservices-network`

```
sonar-db:
```

```
image: postgres:16-alpine
container_name: sonar-db
environment:
```

- `POSTGRES_DB=sonar`

- `POSTGRES_USER=sonar`

- `POSTGRES_PASSWORD=sonar`

```
volumes:
```

- `sonar_db_data:/var/lib/postgresql/data`

- `networks:`

- `microservices-network`

```
volumes:
sonarqube_data:
sonarqube_logs:
sonarqube_extensions:
sonar_db_data:
```

##### **Integración con el Pipeline**

Cada lenguaje tiene su propia forma de enviar el análisis a SonarQube:

|**Lenguaje**|**Herramienta**|**Comando**|
|---|---|---|
|**Java (Maven)**|Sonar Maven Plugin|`mvn sonar:sonar`|

---

<!-- Pagina 19 de 32 -->

|**Lenguaje**|**Herramienta**|**Comando**|
|---|---|---|
|**Java (Gradle)**|Sonar Gradle Plugin|`gradle sonarqube`|
|**Python**|sonar-scanner|`sonar-scanner`|
|**Node.js**|sonar-scanner|`sonar-scanner`|
|**Go**|sonar-scanner|`sonar-scanner`|


Para los lenguajes que no usan Maven/Gradle, se utiliza el **Sonar Scanner** , un cliente genérico que se configura con un archivo `sonar-project.properties` en la raíz del proyecto:

```
# sonar-project.properties
sonar.projectKey=mi-microservicio
sonar.projectName=Mi Microservicio
sonar.sources=src
sonar.host.url=http://sonarqube:9000
sonar.token=squ_xxxxxxxxxxxxxxxxxxxx
```

Ejemplo de la etapa SonarQube en el Jenkinsfile (Java/Maven):

```
stage('SonarQube'){
    steps {
        sh '''
            mvn sonar:sonar \
              -Dsonar.host.url=http://sonarqube:9000 \
              -Dsonar.token=${SONAR_TOKEN}
        '''
}
}
stage('Quality Gate'){
    steps {
timeout(time:5, unit:'MINUTES'){
            waitForQualityGate abortPipeline:true
}
}
}
```

**Nota:** La etapa `waitForQualityGate` requiere el plugin **SonarQube Scanner for Jenkins** y un webhook configurado en SonarQube que notifique a Jenkins del resultado del análisis.

---

<!-- Pagina 20 de 32 -->

**Importante:** Para que la cobertura aparezca en SonarQube, el microservicio debe generar un reporte de cobertura en un formato compatible (ej. JaCoCo XML para Java, `coverage.xml` para Python, `lcov.info` para Node.js). SonarQube **no ejecuta las pruebas** , solo **importa los reportes** generados en la etapa de Test.

#### **Lo que debe hacer**

1. **Agregar SonarQube y su base de datos PostgreSQL** al `docker-compose.yml` . Verificar que SonarQube es accesible desde `http://localhost:9000` .

2. **Configurar SonarQube** :

   - Acceder con las credenciales por defecto ( `admin` / `admin` ), cambiar la contraseña Crear un **proyecto** para el microservicio del Punto 2

   - Generar un **token de autenticación** para el análisis desde Jenkins Configurar un **Quality Gate** personalizado con cobertura ≥ 70%

3. **Configurar la generación de reportes de cobertura** en el microservicio. El reporte debe generarse durante la etapa de Test (Punto 2). Por ejemplo:

   - **Java** : JaCoCo genera `target/site/jacoco/jacoco.xml` automáticamente con `mvn test` **Python** : `pytest --cov --cov-report=xml` genera `coverage.xml`

   - **Node.js** : `nyc --reporter=lcov npm test` genera `coverage/lcov.info`

   - **Go** : `go test -coverprofile=coverage.out ./...`

4. **Agregar la etapa de SonarQube** al Jenkinsfile:

   - Ejecutar el scanner/plugin que envía el código y los reportes de cobertura a SonarQube Esperar el resultado del **Quality Gate**

Si el Quality Gate **no pasa** , el pipeline debe **fallar**

5. **Verificar en SonarQube** que el dashboard del proyecto muestra:

   - Métricas de bugs, vulnerabilidades y code smells

   - Porcentaje de cobertura

   - Porcentaje de duplicación

   - Estado del Quality Gate (Passed/Failed)

##### 6. **Probar el Quality Gate** :

Temporalmente reduzca las pruebas para que la cobertura caiga por debajo del 70% O introduzca un bug intencional que SonarQube detecte

- Verifique que el Quality Gate falla y el pipeline se detiene

#### **Decisión técnica requerida**

- ¿Cómo gestiona el token de SonarQube en el pipeline? ¿Lo almacena en Jenkins Credentials, en variables de entorno del Docker Compose, o en un archivo?

- ¿Configura el Quality Gate por defecto ("Sonar way") o crea uno personalizado? ¿Con qué umbrales?

---

<!-- Pagina 21 de 32 -->

¿Cómo configura el webhook de SonarQube a Jenkins para que `waitForQualityGate` funcione? Para servicios en lenguajes diferentes a Java, ¿cómo instala y ejecuta `sonar-scanner` ? ¿Lo incluye en el `Dockerfile` del servicio, lo descarga en el pipeline, o usa una imagen Docker con el scanner pre-instalado?

### **Punto 4: Empaquetado Docker y Pruebas E2E (1.0 pt)**

#### **Lo que se entrega**

Este punto cierra el ciclo del pipeline integrando dos etapas finales: el **empaquetado** del microservicio como imagen Docker y la ejecución de **pruebas de extremo a extremo (E2E)** contra el sistema completo desplegado.

##### **Empaquetado Docker**

Ejemplo de la etapa de empaquetado Docker en el Jenkinsfile:

```
stage('Package'){
    steps {
        script {
def imageName ="mi-microservicio"
def imageTag ="${env.BUILD_NUMBER}"
```

`sh "docker build -t ${imageName}:${imageTag} -t ${imageName}:latest ." echo "` ✅ `Imagen construida: ${imageName}:${imageTag}" } } }`

Y cómo configurar un **Docker Registry local** en el Docker Compose:

---

<!-- Pagina 22 de 32 -->

```
services:
registry:
image: registry:2
container_name: docker-registry
ports:
-"5000:5000"
volumes:
- registry_data:/var/lib/registry
networks:
- microservices-network
volumes:
registry_data:
```

##### **Pruebas E2E con BDD y publicación de sus reportes**

En el **Reto 6** se construyó una suite de pruebas funcionales automatizadas con BDD (Cucumber/Behave) que **genera reportes en JUnit XML, Cucumber JSON y HTML** . Esa suite se ejecutó manualmente después de levantar el sistema. Ahora se incorpora al pipeline CI para que se ejecute **automáticamente** como última etapa de verificación, **y sus reportes se publiquen en Jenkins** . El flujo es:

`Package → Deploy (docker compose up) → E2E Tests (BDD) → Publicar reportes → Cleanup` Ejemplo de la etapa E2E en el Jenkinsfile:

---

<!-- Pagina 23 de 32 -->

```
stage('E2E Tests'){
    steps {
// Levantar el sistema completo con las imágenes recién construidas
        sh 'docker compose -f docker-compose.yml up -d --build'
```

```
// Esperar a que los servicios estén listos (health checks del Reto 8)
        sh './scripts/wait-for-healthy.sh'
// Ejecutar la suite BDD. El '|| true' deja que el pipeline llegue al bloque post
// y publique el reporte; es el paso 'junit' quien decide el estado del build.
        sh '''
            cd e2e-tests
            npx cucumber-js \
              --format junit:reports/junit.xml \
              --format json:reports/cucumber.json \
              --format html:reports/cucumber.html || true
        '''
}
    post {
        always {
// 1. Resultados máquina-legibles: marca el build y alimenta la tendencia
            junit 'e2e-tests/reports/junit.xml'
// 2. Reporte navegable de escenarios BDD (plugin cucumber-reports)
cucumber(
                jsonReportDirectory:'e2e-tests/reports',
                fileIncludePattern:'**/cucumber.json',
                buildStatus:'UNSTABLE'// escenario fallido → build inestable
)
// 3. Alternativa genérica si no usa Cucumber JSON (plugin htmlpublisher)
publishHTML(target:[
                reportDir  :'e2e-tests/reports',
                reportFiles:'cucumber.html',
                reportName :'Reporte BDD',
                keepAll    :true,
                alwaysLinkToLastBuild:true
])
// 4. Diagnóstico: si el E2E falla, los logs son lo primero que se necesita
            sh 'docker compose logs --no-color > docker-logs.txt || true'
            archiveArtifacts artifacts:'docker-logs.txt', allowEmptyArchive:true
```

```
// 5. Limpiar: apagar el sistema y borrar volúmenes para no contaminar el próx
```

---

<!-- Pagina 24 de 32 -->

```
            sh 'docker compose -f docker-compose.yml down -v'
}
}
}
```

##### **Qué aporta cada publicación**

|**Paso**|**Resultado en Jenkins**|
|---|---|
|`junit`|Conteo de escenarios y**tendencia entre builds**. Es lo que hace que el build<br>cambie de estado.|
|`cucumber(...)`|Pestaña**Cucumber Reports**con cada<br>`Característica`y<br>`Escenario`en<br>lenguaje de negocio, con el paso exacto donde falló.|
|`publishHTML(...)`|Enlace al reporte HTML navegable, útil si su framework no produce<br>Cucumber JSON.|
|`archiveArtifacts`|Los logs del sistema quedan descargables. Sin esto, diagnosticar un E2E<br>fallido es adivinar.|


**El reporte de Cucumber es el que se le muestra a alguien que no programa.** Un escenario en rojo llamado _"El empleado retirado no puede iniciar sesión"_ comunica el problema mucho mejor que un stack trace. Es la promesa de la _documentación viva_ del Reto 6, cumplida.

**Nota:** La etapa E2E puede ser costosa en tiempo. En un pipeline real, se puede configurar para ejecutarse solo en ciertos eventos (ej. merge a `main` ), no en cada commit. Para este reto, se ejecutará siempre.

#### **Lo que debe hacer**

1. **Agregar la etapa** **`Package`** al Jenkinsfile del microservicio del Punto 2: Construir la imagen Docker del microservicio

   - Etiquetar la imagen con el número de build y con `latest` Verificar que la imagen se construyó correctamente

2. **(Opcional pero recomendado)** Agregar un **Docker Registry local** al Docker Compose: Publicar la imagen construida al registry local

   - Verificar que la imagen es accesible desde el registry

---

<!-- Pagina 25 de 32 -->

```
stage('Publish'){
    steps {
        script {
def imageName ="localhost:5000/mi-microservicio"
def imageTag ="${env.BUILD_NUMBER}"
```

```
            sh "docker tag mi-microservicio:${imageTag}${imageName}:${imageTag}"
            sh "docker push ${imageName}:${imageTag}"
```

`echo "` 📤 `Imagen publicada en registry: ${imageName}:${imageTag}" } } }`

##### 3. **Agregar la etapa de pruebas E2E** al pipeline:

Levantar el sistema completo con Docker Compose

   - Esperar a que todos los servicios estén operativos (health checks o espera con reintentos) Ejecutar la **suite BDD del Reto 6** contra el sistema desplegado

   - **Publicar los reportes BDD** : `junit` para los resultados y `cucumber(...)` (o `publishHTML(...)` ) para el reporte navegable de escenarios

   - **Archivar los logs** del sistema como artefacto, para poder diagnosticar los fallos Apagar el sistema al finalizar (en el bloque `post { always { } }` )

4. **Verificar la visibilidad de los reportes BDD.** Ejecute el pipeline y confirme que puede navegar el resultado de los escenarios desde la página del build, **viendo los nombres en español de las características y escenarios** , sin abrir el log de consola.

5. **Extender a un segundo microservicio** : Crear un `Jenkinsfile` para otro microservicio del sistema, **en un lenguaje de programación diferente** , con su propia publicación de resultados y cobertura. Esto demuestra que el pipeline CI es adaptable a cualquier stack tecnológico.

6. **Verificar el pipeline completo** : Ejecutar ambos pipelines y confirmar que todas las etapas (Checkout → Build → Test → SonarQube → Quality Gate → Package → E2E) pasan exitosamente y que **cada etapa que ejecuta pruebas deja su reporte publicado** .

#### **Decisión técnica requerida**

- **Naming convention** : ¿Qué convención de nombres usa para las imágenes Docker? ¿Incluye prefijo de proyecto, versionado semántico, hash del commit?

- **Multi-stage builds** : ¿Sus Dockerfiles utilizan multi-stage builds para optimizar el tamaño de las imágenes? ¿Cómo se integra esto con el pipeline?

- **Registry** : ¿Local o DockerHub? ¿Cómo configura la autenticación si usa un registry externo?

---

<!-- Pagina 26 de 32 -->

- **Health check antes de E2E** : ¿Cómo verifica que todos los servicios están listos antes de ejecutar las pruebas BDD? ¿Usa un script de espera, polling a los endpoints de health check, o `depends_on` con condiciones?

- **Aislamiento de datos** : ¿Cómo garantiza que las pruebas E2E no interfieran con datos de ejecuciones anteriores? ¿Usa `docker compose down -v` para limpiar volúmenes?

- **Rescate de los reportes** : si la suite BDD corre **dentro de un contenedor** (la opción del Punto 6 del Reto 6), sus reportes quedan en el sistema de archivos del contenedor y Jenkins no los ve. ¿Cómo los extrae? ¿Volumen montado, `docker cp` , o ejecuta la suite fuera del contenedor?

- **Reportes cuando el build muere temprano** : si el sistema nunca llega a levantar, no hay reporte que publicar y `junit` fallará por no encontrar el archivo. ¿Usa `allowEmptyResults` , o prefiere que ese caso también rompa el build? Justifique.

### **Punto 5: Reproducibilidad y Documentación (1.0 pt)**

#### **Lo que debe hacer**

1. **Ejecución consistente del pipeline** : Ejecute cada pipeline al menos **3 veces** consecutivas y confirme que todos los builds pasan de forma consistente. Si hay builds intermitentes ( _flaky builds_ ), identifique y corrija la causa.

2. **Simular un fallo** : Modifique intencionalmente el código para que:

   - Una prueba unitaria falle → el pipeline debe detenerse en la etapa **Test** con mensaje descriptivo

   - La cobertura caiga por debajo del 70% → el Quality Gate de SonarQube debe fallar y el pipeline detenerse en la etapa **Quality Gate**

   - El Dockerfile tenga un error → el pipeline debe detenerse en la etapa **Package**

   - Un escenario BDD falle → el pipeline debe detenerse en la etapa **E2E Tests**

Verifique que en cada caso el pipeline falla **en la etapa correcta** y que **el reporte publicado en la interfaz de Jenkins identifica qué falló** — el nombre de la prueba unitaria o el del escenario BDD, con su mensaje de error. No basta con que el log de consola lo diga.

3. **Documentar en el README.md:**

Breve explicación de qué es CI y por qué se integra en el proyecto

- **Acceso a Jenkins** : URL, credenciales por defecto

- **Instrucciones de configuración** :

- a. Cómo levantar el sistema con Jenkins incluido

- b. Cómo obtener la contraseña inicial de Jenkins

- c. Cómo crear/importar los pipelines

- d. Cómo ejecutar un pipeline manualmente

---

<!-- Pagina 27 de 32 -->

**Descripción de las etapas** del pipeline y qué verifica cada una

- **Tabla de reportes publicados** : qué reporte produce cada etapa, con qué paso se publica y dónde se consulta en la interfaz de Jenkins

- **Cómo interpretar los resultados** : qué significa cada etapa en verde/amarillo/rojo, y la diferencia entre `FAILURE` y `UNSTABLE`

- Capturas de pantalla de:

   - Un pipeline exitoso en Jenkins (vista de etapas)

La pestaña **Test Result** con los resultados de las pruebas unitarias

La pestaña **Coverage** con el porcentaje alcanzado

El **reporte BDD navegable** , mostrando las características y escenarios en español

Un build **fallido** , donde se vea identificada la prueba o el escenario que falló

4. **(Opcional)** Configurar un **webhook** para que el pipeline se dispare automáticamente al hacer push. Esto puede lograrse con:

**Gitea/Gogs** como servidor Git local dentro del Docker Compose

- **Jenkins Generic Webhook Trigger Plugin**

Polling SCM como alternativa simple (configurable en el Jenkinsfile con

- `triggers { pollSCM('H/5 * * * *') }` )

---

<!-- Pagina 28 de 32 -->

## Diagrama de Arquitectura CI

---

<!-- Pagina 29 de 32 -->

<!-- Start of picture text -->
👨‍💻  Desarrollo<br>Desarrollador<br>git push<br>📦  Repositorio<br>Git<br>webhook/polling<br>⚙  Jenkins Pipeline<br>🔔  Trigger<br>Etapas del Pipeline<br>📥  Checkout<br>🔨  Build<br>🧪  Test<br>unit +<br>integración<br>🔍  SonarQube<br>Análisis<br>🚦  Quality<br>Gate<br>✓ Pass<br>🐋  Docker<br>Build<br>🧪  E2E<br>BDD<br>junit.xml cucumber.json + junit.xml docker logs ✅  Éxito ✗ Fail ✗ Fail jacoco.xml / coverage.xml ✗ Fail ✗ Fail<br>📊  Reportes publicados en Jenkins<br>❌  Fallo<br>Test Result Cucumber  Artefactos Coverage<br>(junit) Reports (docker logs) (recordCoverage)<br>(escenarios en<br>español)<br><!-- End of picture text -->

---

<!-- Pagina 30 de 32 -->

<!-- Start of picture text -->
español)<br><!-- End of picture text -->


<!-- Start of picture text -->
español)<br>webhook resultado docker push envía análisis<br>🐳  Docker Compose<br>🗄  Docker<br>⚙  Jenkins 🔍  SonarQube<br>Registry<br>:9090 :9000<br>:5000<br>docker pull<br>Microservicios<br>📧<br>👥  empleados 🔐  auth 📋  perfiles<br>notificaciones<br><!-- End of picture text -->

## **Entregables**

- `docker-compose.yml` actualizado con Jenkins, SonarQube (y opcionalmente Docker Registry) como servicios.

- Un `Jenkinsfile` por microservicio (mínimo 2, en lenguajes diferentes), **con publicación de resultados y cobertura** .

- Etapa E2E con **publicación del reporte BDD** y archivado de los logs del sistema.

- `Dockerfile` personalizado de Jenkins con los plugins de reportes pre-instalados.

- `README.md` actualizado según lo especificado en el Punto 5, con la tabla de reportes publicados y las capturas solicitadas.

- Código versionado en GitHub.

## **Consideraciones**

- Jenkins debe ejecutarse como **servicio del Docker Compose** , no como instalación local. El

- sistema completo debe levantarse con `docker compose up --build` .

- Los `Jenkinsfile` deben estar **versionados junto al código** de cada microservicio, no configurados solo en la interfaz de Jenkins.

- Las credenciales y configuraciones sensibles deben manejarse mediante **variables de entorno** o **Jenkins Credentials** , no hardcodeadas en el Jenkinsfile.

---

<!-- Pagina 31 de 32 -->

Si Jenkins necesita herramientas específicas (Maven, Node, Python, Go), se recomienda usar

**imágenes Docker como agentes** del pipeline para evitar instalar todo en el contenedor Jenkins. El pipeline debe ser **idempotente** : ejecutar el mismo pipeline múltiples veces debe producir el mismo resultado.

## **Criterios de Evaluación**

El reto se evalúa sobre **5 puntos** , correspondiendo **1 punto** a cada uno de los retos:

|**#**|**Reto**|**Valor**|**Aspectos a evaluar**|
|---|---|---|---|
|1|**Configuración de**<br>**Jenkins**|1.0|Jenkins accesible como servicio Docker. Dockerfile<br>personalizado con plugins pre-instalados,**incluidos los de**<br>**publicación de reportes**(<br>`junit`,<br>`coverage`,<br>`cucumber-reports`/<br>`htmlpublisher`). Acceso a Docker<br>configurado. Pipeline de verificación funcional. Configuración<br>reproducible sin pasos manuales.|
|2|**Jenkinsfile – Build,**<br>**Test y reportes**|1.0|Jenkinsfile declarativo con etapas Checkout, Build y Test.<br>**Publicación de resultados con**<br>**`junit` y de cobertura con**<br>**`recordCoverage`**, en bloque<br>`post { always { } }`para que<br>se publiquen aun cuando las pruebas fallen. Pipelines<br>aprovisionados como código. Pruebas del Reto 6<br>ejecutándose. Gráficas de tendencia visibles tras varios<br>builds.|
|3|**Calidad con**<br>**SonarQube**|1.0|SonarQube dockerizado y accesible. Proyecto configurado<br>con análisis de calidad y cobertura,**importando el reporte**<br>**generado en el Reto 6**. Quality Gate personalizado con<br>cobertura ≥70%. Pipeline falla si el Quality Gate no pasa.<br>Dashboard de SonarQube con métricas visibles.|

---

<!-- Pagina 32 de 32 -->

|**#**|**Reto**|**Valor**|**Aspectos a evaluar**|
|---|---|---|---|
||**Empaquetado**||Etapa Package construye imagen Docker. Etapa E2E levanta<br>el sistema y ejecuta la suite BDD del Reto 6 automáticamente.<br>**Reporte BDD publicado y navegable desde Jenkins**,|
|4|**Docker, E2E y**<br>**reporte BDD**|1.0|mostrando características y escenarios en español. Logs del<br>sistema archivados como artefacto. Al menos 2 Jenkinsfiles (2<br>microservicios, 2 lenguajes). Cleanup con<br>`down -v`después<br>de E2E.|
|5|**Reproducibilidad y**<br>**documentación**|1.0|Pipelines consistentes en múltiples ejecuciones. Los cuatro<br>fallos simulados se reportan**en la etapa correcta y quedan**<br>**identificados en el reporte publicado**, no solo en el log.<br>README completo con tabla de reportes, acceso a Jenkins y<br>las capturas solicitadas.|


**Nota:** Se valorará especialmente que los pipelines sean **claros y mantenibles** . Un buen `Jenkinsfile` debe poder ser leído y entendido por cualquier miembro del equipo, actuando como documentación ejecutable del proceso de integración del servicio.

**Criterio transversal:** un pipeline que ejecuta pruebas pero no publica su reporte **no se considera completo** . La diferencia entre un build que dice "FAILED" y uno que dice "falló el escenario «El empleado retirado no puede iniciar sesión»" es la razón de ser de este reto.
