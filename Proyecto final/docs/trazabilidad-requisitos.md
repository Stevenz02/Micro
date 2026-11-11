# Trazabilidad del enunciado

| Requisito | Implementación | Estado inicial |
|---|---|---|
| Empleados y departamentos | `microservicios/empleados`, `departamentos` | Implementado |
| Autenticación JWT sin registro público | `microservicios/auth`, Gateway | Implementado |
| Perfil propio y autorización | `microservicios/perfiles` | Implementado |
| Vacaciones y planificador | `microservicios/vacaciones` | Implementado |
| Notificaciones por eventos | `microservicios/notificaciones` | Implementado |
| Gateway único | `microservicios/api-gateway` | Implementado |
| Catálogo e idempotencia | `docs/catalogo-de-eventos.md` y consumidores | Implementado; requiere auditoría final |
| Logs, métricas, trazas y alertas | `observabilidad/` | Smoke test sano; 7/7 targets Prometheus `up` |
| Pruebas unitarias y BDD | `microservicios/tests`, pruebas por lenguaje, `e2e-tests/` | 76 Python + 12 Node + Go + 8 Java + 19 .NET; BDD 25 escenarios/116 pasos |
| Quality Gate ≥ 70 % | SonarQube + `sonar-project.properties` | Configurado; falta ejecución limpia |
| Jenkins + Registry | perfil Compose `ci`, `Jenkinsfile` | Configurado; falta ejecución limpia |
| Un comando de despliegue | `docker compose up --build -d --wait` | Validado con todos los health checks sanos |
| Cuatro o más lenguajes | Python, Node.js, Go, Java y .NET | Cumplido |
| Cero secretos versionados | `.env.example`, `.gitignore`, `scripts/setup.*` | Árbol nuevo limpio; webhook histórico debe rotarse y purgarse del historial |

## Criterio para cerrar la implementación

La configuración no se considera terminada hasta completar una ejecución desde cero que:

1. genere credenciales locales;
2. construya todas las imágenes;
3. deje todos los health checks sanos;
4. supere las pruebas unitarias y BDD;
5. publique coberturas y alcance el Quality Gate;
6. demuestre trazas, logs, métricas y al menos una alerta;
7. pase un escaneo de secretos del árbol y del historial Git.
