# Documentación del repositorio

Esta carpeta concentra los enunciados académicos y las referencias transversales del
proyecto. Los PDF originales se convirtieron a Markdown para que la documentación sea
ligera, versionable, buscable y reutilizable por Graphify y por asistentes de código.

## Por dónde empezar

1. Lee el [mapa de arquitectura](ARQUITECTURA_REPOSITORIO.md) para entender la evolución
   de los retos, la ubicación del código y las dependencias entre carpetas.
2. Abre el `README.md` o documento de transferencia del reto que vas a modificar.
3. Contrasta la implementación con el enunciado `reto*.md` correspondiente.
4. Para eventos, seguridad, pruebas, CI u observabilidad, consulta también la referencia
   transversal de la tabla siguiente.
5. Para navegar el grafo generado, abre
   [`graphify-out/graph.html`](../graphify-out/graph.html) o consulta desde terminal:

   ```powershell
   graphify query "¿cómo se conecta auth con vacaciones?"
   graphify path "auth-service" "vacaciones-service"
   graphify explain "api-gateway"
   ```

## Enunciados por reto

| Documento | Alcance | Implementación principal |
| --- | --- | --- |
| [reto01.md](reto01.md) | Servidor web inicial de empleados | [`Reto_1`](../Reto_1/) |
| [reto2.md](reto2.md) | Persistencia, dos servicios y Docker Compose | [`Reto_2`](../Reto_2/) |
| [reto3.md](reto3.md) | API Gateway, timeout, retry y Circuit Breaker | [`Reto_3`](../Reto_3/) |
| [reto4.md](reto4.md) | Eventos, RabbitMQ, perfiles, notificaciones y vacaciones | [`Reto_4`](../Reto_4/) |
| [reto5.md](reto5.md) | JWT, RBAC y ciclo de vida de cuentas | [`Reto_5`](../Reto_5/) |
| [reto6.md](reto6.md) | Pruebas unitarias, integración y BDD | [`Reto_6`](../Reto_6/) |
| [reto7.md](reto7.md) | Integración continua con Jenkins y SonarQube | [`Reto_7`](../Reto_7/) |
| [reto08.md](reto08.md) | Métricas, logs, trazas y alertas | [`Reto_8`](../Reto_8/) |

## Referencias transversales

| Documento | Cuándo usarlo | Retos relacionados |
| --- | --- | --- |
| [catalogo-de-eventos.md](catalogo-de-eventos.md) | Contratos, envelope, routing keys, productores y consumidores | 4, 5, 6, 8 |
| [comunicacion.md](comunicacion.md) | REST, Gateway, resiliencia, mensajería e idempotencia | 2, 3, 4, 5 |
| [seguridad.md](seguridad.md) | JWT, autorización, secretos y endurecimiento | 5 en adelante |
| [bdd2.md](bdd2.md) | Gherkin, Cucumber/Behave, polling y pruebas E2E | 6 y 7 |
| [Integración continua.md](Integraci%C3%B3n%20continua.md) | Jenkinsfile, SonarQube, Quality Gate y despliegue | 7 |
| [observabilidad.md](observabilidad.md) | Métricas, logs, trazas, health checks y alertas | 8 |

## Artefactos de navegación generados

| Archivo | Uso |
| --- | --- |
| [`graphify-out/graph.html`](../graphify-out/graph.html) | Grafo interactivo: búsqueda, filtros y comunidades |
| [`graphify-out/GRAPH_REPORT.md`](../graphify-out/GRAPH_REPORT.md) | Resumen de arquitectura, nodos centrales y conexiones |
| [`graphify-out/graph.json`](../graphify-out/graph.json) | Fuente consultable por Graphify y otras herramientas |
| [`graphify-out/GRAPH_TREE.html`](../graphify-out/GRAPH_TREE.html) | Árbol navegable por carpetas y símbolos |

Cuando cambie código, ejecuta `graphify update .` desde la raíz. Cuando cambie
documentación o quieras recalcular comunidades semánticas, ejecuta `$graphify . --update`
desde Codex.

Si no hay un proveedor semántico configurado, este repositorio incluye una ruta local y
determinista para reconstruir la capa documental antes de exportar:

```powershell
$graphifyPython = (python -m uv tool run --from 'graphifyy[sql]' python -c "import sys; print(sys.executable)").Trim()
& $graphifyPython .\tools\rebuild_repository_graph.py --root .
graphify export html
graphify tree --label Microservicios
```

`rebuild_repository_graph.py` ejecuta las cuatro fases (`build`, `assemble`, `finalize` y
extracción AST). Los scripts no inventan
relaciones de negocio: sólo usan estructura de código, encabezados, enlaces, rutas
explícitas y Docker Compose.

