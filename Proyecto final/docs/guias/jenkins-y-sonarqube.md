# Guía: Jenkins, SonarQube y registry

Los tres arrancan con el mismo `docker compose up --build` (perfil `ci`, activo por defecto en
`.env.example`). No requieren pasos manuales:

- **Jenkins** se configura con JCasC (`infra/jenkins/casc.yaml`): usuario, credenciales,
  conexión a SonarQube y los ocho pipelines. Su imagen incluye las herramientas de los cinco
  lenguajes y el cliente Docker.
- **SonarQube** lo aprovisiona `infra/sonarqube/init_sonar.py`: cambia la contraseña inicial,
  genera el token de análisis, crea el Quality Gate de cobertura mínima 70 % y el webhook hacia Jenkins.
- **Registry** local en `localhost:5001`.

| Herramienta | URL | Usuario | Contraseña |
|---|---|---|---|
| Jenkins | <http://localhost:8090> | `JENKINS_ADMIN_ID` de `.env` | `secrets/jenkins_admin_password.txt` |
| SonarQube | <http://localhost:9000> | `admin` | `secrets/sonar_admin_password.txt` |

El primer arranque tarda varios minutos: se construye la imagen de Jenkins y SonarQube
inicializa su base de datos.

## Pipelines

| Job | Jenkinsfile | Qué hace |
|---|---|---|
| `ms-empleados`, `ms-departamentos`, `ms-auth`, `ms-perfiles`, `ms-vacaciones`, `ms-notificaciones`, `ms-api-gateway` | `microservicios/<servicio>/Jenkinsfile` | build → test → quality → package de un servicio |
| `proyecto-final` | `Jenkinsfile` | Los cinco lenguajes, Quality Gate global, las 7 imágenes y la suite BDD |

Etapas:

1. **Checkout**: copia el proyecto (montado en solo lectura) al workspace, sin `.env` ni `secrets/`.
2. **Build**: instala dependencias y compila.
3. **Test**: pruebas unitarias con cobertura.
4. **Quality**: análisis de SonarQube y espera del Quality Gate; **si la cobertura es menor
   al 70 % el pipeline falla**.
5. **Package**: construye la imagen Docker y la publica en el registry
   (`localhost:5001/rrhh/<servicio>:<build>` y `:latest`).
6. **BDD** (solo `proyecto-final`): ejecuta Behave contra el sistema desplegado.

Para ejecutar: abra el job y pulse **Build Now**. Tras editar un Jenkinsfile:
`docker compose restart jenkins`.

Imágenes publicadas: `curl http://localhost:5001/v2/_catalog`.

## Alcance de la cobertura

El 70 % se exige sobre la lógica de negocio. Los adaptadores de E/S (repositorios SQL,
consumidores y publicadores AMQP, arranque e instrumentación) se analizan igual en SonarQube,
pero quedan fuera de la métrica de cobertura unitaria porque se validan con las pruebas de
integración y la suite BDD. Las exclusiones exactas están en cada `sonar-project.properties`.

## Arrancar sin CI

Deje `COMPOSE_PROFILES=` vacío en `.env` (ahorra unos 3 GB de memoria).
