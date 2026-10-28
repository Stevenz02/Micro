# Plan de verificación

## Verificación local permitida

1. Ejecutar tests de las utilidades CI con `unittest`.
2. Comprobar los siete Jenkinsfiles y el pipeline E2E con `verify_ci_config.py`.
3. Ejecutar suites nativas cuando el toolchain esté instalado, sin contenedores.
4. Validar JUnit, cobertura y Cucumber con `validate_reports.py`.
5. Revisar XML de JaCoCo/Cobertura/OpenCover y nombres de pruebas.
6. Ejecutar `run_e2e.py` únicamente si infraestructura entrega un Gateway; el script nunca lo crea.

## Casos de fallo reproducibles

### 1. Prueba unitaria fallida

En una rama o workspace temporal de Jenkins, cambiar una expectativa de test, nunca producción.
El comando debe devolver código no cero; `post/always` publicará JUnit con el nombre y mensaje, y
el pipeline terminará FAILURE o UNSTABLE según la política Jenkins. Revertir el cambio después.

### 2. Cobertura inferior al Quality Gate

Crear temporalmente código nuevo no cubierto en un workspace de demostración o ajustar el gate de
un proyecto de prueba. SonarQube debe responder un gate rechazado y `waitForQualityGate` debe
detener Package y E2E. No modificar porcentajes dentro del Jenkinsfile.

### 3. Package fallido

Infraestructura configura `RUN_PACKAGE=true` y un `PACKAGE_JOB` de prueba que devuelva FAILURE.
El paso `build(... propagate: true)` debe marcar el pipeline como FAILURE. La simulación no se
implementa en este repositorio porque el empaquetado es responsabilidad externa.

### 4. Escenario BDD fallido

En un workspace temporal, cambiar una expectativa de un `.feature` o dirigir la suite a un entorno
controlado que incumpla el contrato. Behave debe devolver no cero y generar JUnit/Cucumber con el
escenario en español. El pipeline publica los archivos antes de finalizar. Revertir el cambio.

## Verificación en Jenkins

Para cada pipeline:

1. Validar Jenkinsfile con el linter declarativo del servidor.
2. Ejecutar tres builds consecutivos sobre el mismo commit.
3. Registrar número de build, duración, resultado y URL.
4. Confirmar Test Result y Coverage.
5. Confirmar proyecto Sonar y Quality Gate.
6. Probar por separado los cuatro casos de fallo.
7. Ejecutar el job E2E una sola vez por ciclo integrado.

No se contabilizan las ejecuciones locales como builds Jenkins.

## Casos automatizados de robustez de reportes

Las pruebas de `Reto_7/tests/test_ci_tools.py` deben cubrir, como mínimo:

1. JSON Go vacío, malformado, acción desconocida, fallo, omisión y prueba interrumpida.
2. Coverprofile sin mediciones, rutas con espacios y separadores Windows, y cobertura real de 0 %.
3. JUnit vacío, corrupto, sin nombre, con conteos contradictorios, fallos, errores y omisiones.
4. Normalización Node con casos directos y rechazo de una suite sin pruebas.
5. Cobertura .NET con raíces correctas, líneas y puntos de secuencia medibles.
6. Cucumber JSON malformado, pasos sin resultado y estados de ejecución reconocidos.
7. Códigos de `junit_status.py`: `0` aprobado, `1` fallos/errores, `2` ausente y `3` corrupto.
8. Configuración CI, rutas físicas, project keys, orden de etapas y ausencia de tolerancias vacías.

La validación estática detecta contratos comprobables en archivos. El Declarative Linter del
servidor sigue siendo obligatorio porque esta utilidad no interpreta Groovy ni plugins de Jenkins.

