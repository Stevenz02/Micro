# Checklist de entrega lógica — Reto 7

Fecha de corte: **27 de octubre de 2026**.

Estados permitidos:

- **COMPLETADO Y VERIFICADO**.
- **IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS**.
- **PENDIENTE DE INFRAESTRUCTURA**.
- **NO IMPLEMENTADO**.

## 1. Pipelines

| Elemento | Estado | Evidencia actual | Evidencia pendiente |
|---|---|---|---|
| Pipeline Empleados | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Estructura, rutas y pruebas locales | Build Jenkins/linter |
| Pipeline Auth | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Estructura, rutas y pruebas locales | Build Jenkins/linter |
| Pipeline API Gateway | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Estructura, rutas y pruebas locales | Build Jenkins/linter |
| Pipeline Departamentos | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Node, JUnit y LCOV verificados | Publicación Jenkins |
| Pipeline Perfiles | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Conversores probados | Agente Go 1.23/build real |
| Pipeline Notificaciones | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Contrato Surefire/JaCoCo probado estáticamente | JDK 21/Maven/build real |
| Pipeline Vacaciones | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | 16 pruebas, TRX/Cobertura/OpenCover | Publicación Jenkins/Sonar |
| Pipeline integración | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Wrapper y errores probados | BDD contra ecosistema |

## 2. Funciones CI

| Requisito | Estado | Resultado comprobado |
|---|---|---|
| Checkout único desde monorepo | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | `skipDefaultCheckout` + `checkout scm` |
| Build nativo por lenguaje | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Cinco toolchains locales; Go/Java pendientes |
| Tests unitarios | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | 128/128 por corrida; faltan 12 Go/Java |
| Cobertura | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | XML, LCOV y OpenCover validados; JaCoCo/Go pendientes reales |
| JUnit | COMPLETADO Y VERIFICADO | Conteos y estados consistentes; errores negativos probados |
| TRX/MSTest | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | TRX generado localmente |
| JaCoCo | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Plugin/configuración presentes; Maven ausente localmente |
| Cucumber JSON | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Histórico 25 escenarios/116 pasos validado |
| Cucumber HTML | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Histórico con 25 escenarios validado |
| HTML Publisher | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Paso configurado, plugin pendiente |
| `post/always` | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Ocho Jenkinsfiles auditados |
| Reportes ausentes fallan | COMPLETADO Y VERIFICADO | `allowEmpty* = false` y casos CI negativos |
| Fallo bloquea Package/E2E | COMPLETADO Y VERIFICADO | Estados nativos y detectores conservados |
| Package externo | PENDIENTE DE INFRAESTRUCTURA | Contrato definido, job sin implementar |
| E2E funcional | PENDIENTE DE INFRAESTRUCTURA | Requiere despliegue y credencial |

## 3. Calidad y SonarQube

| Requisito | Estado | Evidencia pendiente |
|---|---|---|
| Siete project keys | COMPLETADO Y VERIFICADO | Keys/rutas comprobadas estáticamente |
| Scanners correctos | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | CLI y Scanner for .NET en agentes |
| Reportes Sonar | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Formatos/rutas locales; JaCoCo pendiente de Maven |
| Credenciales externas | COMPLETADO Y VERIFICADO | No hay tokens en SCM |
| Quality Gate bloqueante | PENDIENTE DE INFRAESTRUCTURA | Ejecutar `waitForQualityGate` con webhook real |
| Cobertura nueva >=70 % | PENDIENTE DE INFRAESTRUCTURA | Configurar/evaluar en servidor |
| Duplicación nueva <=3 % | PENDIENTE DE INFRAESTRUCTURA | Configurar/evaluar en servidor |
| Bugs/vulnerabilidades nuevas = 0 | PENDIENTE DE INFRAESTRUCTURA | Resultado real Sonar |

## 4. Robustez, compatibilidad y seguridad

| Requisito | Estado | Evidencia |
|---|---|---|
| Conversores Go robustos | COMPLETADO Y VERIFICADO | Vacío, malformado, fallo, skip e interrupción |
| Normalizador Node | COMPLETADO Y VERIFICADO | Conserva fallos y rechaza suites vacías |
| Normalizador .NET | COMPLETADO Y VERIFICADO | Valida raíces, líneas y puntos de secuencia |
| Validador de reportes | COMPLETADO Y VERIFICADO | JUnit, Cobertura, JaCoCo, OpenCover, LCOV, Cucumber JSON/HTML |
| Códigos JUnit | COMPLETADO Y VERIFICADO | 0 aprobado, 1 fallos, 2 ausente, 3 corrupto |
| Códigos E2E | COMPLETADO Y VERIFICADO | 20 infraestructura; 21 runner |
| Agentes Linux | IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS | Jenkinsfiles usan `sh`; falta agente real |
| Rutas con espacios/separadores | COMPLETADO Y VERIFICADO | Casos automatizados |
| npm audit | COMPLETADO Y VERIFICADO | 0 vulnerabilidades |
| Warning nullable Vacaciones | COMPLETADO Y VERIFICADO | Build Release 0 warnings |
| Ausencia de secretos | COMPLETADO Y VERIFICADO | Solo IDs y variables Jenkins |
| Ausencia de comandos de contenedor | COMPLETADO Y VERIFICADO | Auditoría de Jenkinsfiles/scripts |

## 5. Documentación y transferencia

| Documento/requisito | Estado |
|---|---|
| README de Reto 7 | COMPLETADO Y VERIFICADO |
| Arquitectura CI | COMPLETADO Y VERIFICADO |
| Matriz de pipelines | COMPLETADO Y VERIFICADO |
| Contrato infraestructura | COMPLETADO Y VERIFICADO |
| Plan/resultados de verificación | COMPLETADO Y VERIFICADO |
| Guía maestra para otra IA | COMPLETADO Y VERIFICADO |
| Punto de entrada `LEER_PRIMERO` | COMPLETADO Y VERIFICADO |
| Inventario y archivos protegidos | COMPLETADO Y VERIFICADO |
| Evidencias gráficas Jenkins/Sonar | PENDIENTE DE INFRAESTRUCTURA |

## 6. Cinco criterios de evaluación del Reto 7

### 1. Pipelines Jenkins por microservicio

- Estado: **IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS**.
- Implementado: siete pipelines de servicio, uno de integración, stages, fallos y publicación.
- Falta: linter real, URLs y tres builds por job.

### 2. Pruebas y cobertura automatizadas

- Estado: **IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS**; las suites disponibles sí fueron verificadas.
- Implementado: comandos nativos, reportes y validadores.
- Falta: Go, Java e integración PostgreSQL en el entorno oficial.

### 3. SonarQube y Quality Gate

- Estado: **PENDIENTE DE INFRAESTRUCTURA**.
- Implementado: siete keys, scanners, rutas y gate bloqueante en código.
- Falta: análisis del servidor, webhook y resultados de calidad reales.

### 4. Package y entrega del artefacto

- Estado: **PENDIENTE DE INFRAESTRUCTURA**.
- Implementado: parámetros, espera y propagación del job externo.
- Falta: job, imagen/artefacto, registry y evidencia de fallo.

### 5. E2E, reportes y evidencia integral

- Estado: **IMPLEMENTADO, PENDIENTE DE VALIDACIÓN EN JENKINS**.
- Implementado: wrapper, health, polling, credenciales por ID, JUnit/Cucumber/HTML.
- Falta: ejecución funcional, publicación Jenkins, tres corridas y capturas.

## 7. Criterio de cierre

La parte lógica puede entregarse a infraestructura. El Reto 7 completo solo se cierra cuando:

- los ocho Jenkinsfiles pasan el linter y builds reales;
- las 140 unitarias y la integración aplicable se ejecutan en el entorno habilitado;
- los siete análisis y Quality Gates tienen respuesta real;
- Package produce su artefacto;
- BDD ejecuta 25 escenarios y publica Cucumber/HTML;
- existen tres ejecuciones consecutivas y evidencias de fallos controlados.
