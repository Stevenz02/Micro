# Matriz técnica de pipelines

| Servicio | Directorio | Versión | Build | Tests | Reporte test | Cobertura | Sonar | Dependencias/limitaciones |
|---|---|---|---|---|---|---|---|---|
| Empleados | `Reto_4/empleados` | Python 3.13 validado localmente | `compileall` | pytest | JUnit | Cobertura XML | CLI, key `uq-reto7-empleados` | Integración Testcontainers queda fuera del job unitario porque requiere infraestructura |
| Auth | `Reto_5/auth` | Python 3.13 | `compileall` | pytest | JUnit | Cobertura XML | CLI | Usa `Reto_5/shared/tokens.py` |
| Gateway | `Reto_5/api-gateway` | Python 3.13 | `compileall` | pytest | JUnit | Cobertura XML | CLI | Pruebas con MockTransport, sin upstream real |
| Departamentos | `Reto_4/departamentos` | Node >=22; 22.20 validado | `npm ci` + `node --check` | node:test | JUnit nativo normalizado | LCOV nativo | CLI | Lockfile actualizado a `body-parser` 2.4.0, `proxy-addr` 2.0.8 y `qs` 6.17.0; `npm audit` actual: 0 vulnerabilidades |
| Perfiles | `Reto_4/perfiles` | Go 1.23 | `go build ./...` | `go test -json` | Conversión a JUnit | coverprofile + Cobertura | CLI | Go no está instalado en la estación de verificación actual |
| Notificaciones | `Reto_5/notificaciones` | Java 21 | Maven compile | JUnit 5/Surefire | Surefire XML | JaCoCo XML | CLI sobre bytecode Maven | La estación actual solo tiene Java 8 y no tiene Maven |
| Vacaciones | `Reto_5/vacaciones` | .NET 8 | restore/build | xUnit | TRX | Cobertura + OpenCover | Scanner for .NET | Cobertura global histórica baja por infraestructura incluida |
| BDD | `Reto_6/e2e-tests` | Python/Behave | compileall | 25 escenarios | JUnit | No aplica | No aplica | Requiere Gateway externo y credencial ADMIN |

## Estado Jenkins

Los ocho Jenkinsfiles están implementados. La comprobación local revisa estructura, etapas,
publicación y ausencia de comandos de contenedores. La validación con el linter declarativo y tres
builds consecutivos queda pendiente hasta disponer de Jenkins.

La ubicación centralizada es intencional para el monorepo: cada job usa el Script Path exacto de
la tabla de integración, hace `checkout scm` en la raíz y ejecuta rutas propias del componente.
No se requieren copias de Jenkinsfile dentro de cada microservicio.

## Project keys

| Componente | Project key |
|---|---|
| Empleados | `uq-reto7-empleados` |
| Auth | `uq-reto7-auth` |
| API Gateway | `uq-reto7-api-gateway` |
| Departamentos | `uq-reto7-departamentos` |
| Perfiles | `uq-reto7-perfiles` |
| Notificaciones | `uq-reto7-notificaciones` |
| Vacaciones | `uq-reto7-vacaciones` |

