# Leer primero — IA responsable de infraestructura del Reto 7

## 1. Objetivo

Este archivo es el punto de entrada para continuar la integración del Reto 7. La parte lógica de
CI está implementada y validada localmente. Tu responsabilidad es conectarla con Jenkins,
SonarQube, Package y el ecosistema desplegado sin reescribir sus contratos.

> **ANTES DE MODIFICAR INFRAESTRUCTURA, LEER COMPLETAMENTE
> `docs/GUIA_MAESTRA_IA_COMPANERO.md` Y `docs/INTEGRACION_INFRAESTRUCTURA.md`.**

No necesitas el historial de conversaciones: ambos documentos contienen rutas, parámetros,
credenciales por ID, reportes, estados y pendientes.

## 2. Estado actual

- Siete pipelines de servicio y un pipeline E2E existen en `Reto_7/jenkins`.
- Tres corridas locales finales aprobaron 128/128 pruebas disponibles y 21/21 pruebas CI.
- `npm audit` reporta cero vulnerabilidades.
- Vacaciones compila sin warnings.
- Siete configuraciones Sonar fueron verificadas estáticamente.
- Jenkins, SonarQube, Package y BDD real siguen pendientes de infraestructura.

No afirmar que el Reto 7 completo está aprobado hasta ejecutar esas validaciones reales.

## 3. Restricciones de modificación

- No sobrescribir `Reto_7/jenkins`, `Reto_7/ci`, `Reto_7/tests` ni la lógica funcional.
- No cambiar nombres de parámetros, project keys, IDs de credenciales o rutas sin coordinación.
- No fijar contraseñas ni tokens en SCM.
- No eliminar pruebas ni exclusiones para elevar cobertura.
- No presentar reportes históricos como builds Jenkins nuevos.

## 4. Separación de responsabilidades

| Parte lógica entregada | Trabajo de infraestructura |
|---|---|
| Jenkinsfiles y comandos | Servidor, jobs, agentes y plugins |
| Configuración de scanners | SonarQube Server, proyectos, gate y webhook |
| Rutas/reportes | Ejecución y publicación real |
| Contrato Package | Imágenes, registry, tags y job externo |
| Wrapper E2E | Despliegue, credencial ADMIN y Gateway accesible |

## 5. Rutas para inspeccionar primero

1. `Reto_7/docs/GUIA_MAESTRA_IA_COMPANERO.md`.
2. `Reto_7/docs/INTEGRACION_INFRAESTRUCTURA.md`.
3. `Reto_7/docs/CHECKLIST_ENTREGA_LOGICA.md`.
4. `Reto_7/docs/RESULTADOS_VERIFICACION.md`.
5. `Reto_7/jenkins/`.
6. `Reto_7/ci/config/sonar/`.
7. `Reto_7/ci/scripts/run_e2e.py`.

## 6. Orden de lectura

```text
LEER_PRIMERO
  -> GUIA_MAESTRA_IA_COMPANERO
  -> INTEGRACION_INFRAESTRUCTURA
  -> CHECKLIST_ENTREGA_LOGICA
  -> RESULTADOS_VERIFICACION
  -> Jenkinsfiles/configuraciones concretas
```

## 7. Resumen de los ocho pipelines

| Job | Script Path | Tecnología |
|---|---|---|
| `reto7-empleados` | `Reto_7/jenkins/Jenkinsfile.empleados` | Python/pytest |
| `reto7-auth` | `Reto_7/jenkins/Jenkinsfile.auth` | Python/pytest |
| `reto7-api-gateway` | `Reto_7/jenkins/Jenkinsfile.api-gateway` | Python/pytest |
| `reto7-departamentos` | `Reto_7/jenkins/Jenkinsfile.departamentos` | Node.js/node:test |
| `reto7-perfiles` | `Reto_7/jenkins/Jenkinsfile.perfiles` | Go |
| `reto7-notificaciones` | `Reto_7/jenkins/Jenkinsfile.notificaciones` | Java/Maven |
| `reto7-vacaciones` | `Reto_7/jenkins/Jenkinsfile.vacaciones` | .NET/xUnit |
| `reto7-integracion-e2e` | `Reto_7/jenkins/Jenkinsfile.integration` | Python/Behave |

Los siete servicios siguen Checkout, Build, Test + Coverage, Sonar, Quality Gate, Package y E2E.
Package/E2E están deshabilitados por defecto. El pipeline de integración usa un Gateway externo.

## 8. Contratos imprescindibles

- Jenkins Sonar installation: `sonarqube-reto7`.
- Credencial username/password E2E: `reto7-e2e-admin`.
- Webhook: `<JENKINS_URL>/sonarqube-webhook/`.
- Package: `COMPONENT_ID`, `SOURCE_DIR`, `SOURCE_BUILD`.
- E2E: `GATEWAY_BASE_URL`; health 200 con
  `{"status":"ok","service":"api-gateway"}`.
- Códigos E2E: 0 éxito, 20 infraestructura, 21 runner, otro no cero fallo de ejecución.

## 9. Problemas conocidos

- Vacaciones: cobertura global 16,39 %.
- Falta validar los Jenkinsfiles con Declarative Linter.
- Falta ejecutar Go, Java e integración PostgreSQL.
- Falta ejecutar los 25 escenarios BDD contra el ecosistema actual.
- Falta probar webhook, Quality Gate y Package reales.
- Los cambios siguen locales y sin commit por instrucción del propietario.

## 10. Siguiente acción

Lee la [guía maestra](docs/GUIA_MAESTRA_IA_COMPANERO.md), aprovisiona herramientas sin cambiar los
contratos y sigue su plan de integración de diez etapas. Registra número, URL y resultado de cada
build. La transferencia se considera cerrada cuando los ocho jobs, siete análisis Sonar, Package y
BDD tengan evidencia real y tres ejecuciones consecutivas.
