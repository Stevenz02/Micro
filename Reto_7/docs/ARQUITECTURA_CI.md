# Arquitectura lógica de CI

## Decisiones

1. **Pipeline por componente.** Cada servicio compila, prueba, mide cobertura y analiza únicamente
   su código. Los fallos se aíslan y las tendencias no mezclan lenguajes.
2. **E2E coordinado.** Behave se ejecuta en un job separado contra un entorno proporcionado por
   infraestructura. Los pipelines no levantan ni destruyen servicios.
3. **Quality Gate bloqueante.** `waitForQualityGate(abortPipeline: true)` impide Package y E2E si
   SonarQube rechaza el análisis.
4. **Reportes siempre.** El bloque `post/always` publica resultados después de cualquier ejecución
   de tests, incluso si el comando devuelve un código no cero.
5. **Package externo.** El pipeline invoca un job de infraestructura y propaga su resultado. La
   etapa se muestra como omitida mientras `RUN_PACKAGE=false`.
6. **Sin dependencia Windows.** Los jobs utilizan `sh` y comandos disponibles en agentes Linux.

## Flujo de servicio

```text
SCM -> Checkout -> Build -> Test/Coverage -> Sonar -> Quality Gate
                                                   |
                          Package externo (opcional y bloqueado por el gate)
                                                   |
                          Job E2E coordinado (opcional, una sola vez)
```

## Separación de responsabilidades

| Parte lógica implementada aquí | Parte de infraestructura pendiente |
|---|---|
| Jenkinsfiles declarativos | Servidor y agentes Jenkins |
| Comandos de build/test | Instalación de toolchains |
| Configuración Sonar por proyecto | Servidor, proyectos, gate y webhook |
| Publicación JUnit/Coverage/Cucumber | Instalación de plugins Jenkins |
| Contrato Package | Build y publicación de imágenes |
| Runner E2E externo | Levantar/apagar el ecosistema |

## Política de resultados

Los comandos mantienen su código de salida. No se usa `|| true`. Los conversores se ejecutan
después de capturar el resultado nativo y el pipeline vuelve a fallar si la prueba falló. Un
reporte ausente después de iniciar tests también falla por `allowEmptyResults: false` o
`allowEmptyArchive: false`.

La publicación Cucumber puede marcar UNSTABLE según la configuración del plugin. Para promoción,
SUCCESS es el único estado aceptable.

