# Auditoría previa a la implementación

## Reto 1

Se inspeccionaron todos los archivos versionados y los archivos locales relevantes
antes de modificar código. El árbol de trabajo inicial no tenía cambios. No se
encontraron instrucciones `AGENTS.md` aplicables.

| Aspecto | Hallazgo |
|---------|----------|
| Ubicación | `Reto_1/` |
| Stack | Python, FastAPI 0.115.6, Uvicorn 0.34.0 y Pydantic |
| Estructura | `app/main.py`, `models.py`, `repository.py`, `tests/`, Dockerfile y README |
| Endpoints | POST `/empleados` → 200; GET `/empleados/{id}` → 200/404 |
| Contrato | Los diez campos requeridos, incluidos `departamentoId`, fecha y `estado=ACTIVO` |
| Validación | Texto no vacío, fecha válida, comprobación sencilla de email y normalización a minúsculas; duplicados de id, email y número → 400 |
| Orden original | id, email, número; no consulta departamentos |
| Errores | Rutas y métodos no admitidos → 404; entrada inválida → 422 |
| Almacenamiento | Diccionario Python, sin persistencia ni protección transaccional |
| Configuración | Puerto 8080 en Docker/CMD; sin variables de BD |
| OpenAPI | `/docs`, `/redoc`, `/openapi.json`, ejemplos y descripciones |
| Dockerfile | Python 3.12 slim; instala requirements y copia `app/` |
| Pruebas | 15 casos pytest y evidencia manual `pruebas.ps1` |
| Artefactos | `dockerignore` sin punto: Docker no lo interpreta como `.dockerignore` |

Resultado inicial real: **15 pruebas aprobadas** después de instalar dependencias
en un entorno virtual local. El Reto 1 funciona conforme al contrato documentado.
No había listado, persistencia ni validación remota: son incorporaciones de Reto 2.
Sin un enunciado adicional del Reto 1 no se certifican requisitos ajenos a ese contrato.

Limitaciones originales conservadas: validación de email deliberadamente sencilla,
sin garantía de unicidad entre múltiples procesos; datos perdidos al reiniciar.
El script manual imprime resultados pero no falla el proceso por una aserción;
por eso la comprobación automática se basa en pytest.

## Reto 2: checklist inicial

| Requisito | Antes | Qué faltaba |
|-----------|-------|-------------|
| Cuatro contenedores Compose | PARCIAL | Código y dependencias para construir las imágenes |
| Healthchecks y dependencias | PARCIAL | Salud de empleados, verificación del esquema listo |
| Departamentos en otro lenguaje | FALTA | Solo existía un Dockerfile previsto para Node.js |
| API empleados persistente | FALTA | Aplicación, repositorio SQL y listado |
| Modelo completo | PARCIAL | SQL tenía campos, faltaba implementar mapeo y validación |
| Validación ordenada y UNIQUE | PARCIAL | UNIQUE en SQL, faltaban consultas previas y manejo de colisiones |
| HTTP, timeout y reintentos | FALTA | Cliente configurable y respuesta controlada |
| Bases independientes | PARCIAL | Configuración y esquemas presentes, sin aplicaciones consumidoras |
| Persistencia | PARCIAL | Volúmenes declarados, comportamiento no probado |
| Swagger de ambos servicios | FALTA | Endpoints y schemas |
| Pruebas completas | FALTA | Pruebas unitarias y E2E |
| Variables | PARCIAL | `.env` versionado; no había `.env.example` |
| Documentación | PARCIAL | README de infraestructura con tareas pendientes |
| README general | FALTA | No existía |

## Cambios justificados

- Reutilizar el modelo original sin modificar su código ni los endpoints de Reto 1.
- Renombrar `Reto_1/dockerignore` a `.dockerignore`: corrige un archivo que Docker ignoraba.
- Conservar PostgreSQL 16 y los dos volúmenes previstos; completar aplicaciones.
- Usar Node.js 22 en vez de 20 para departamentos, con dependencias bloqueadas en
  `package-lock.json` y construcción mediante `npm ci`.
- Usar `TEXT` en esquemas nuevos: el modelo original no impone máximos y los
  límites `VARCHAR` iniciales podían rechazar entradas válidas con errores de BD.
- Añadir `CHECK` para ACTIVO y email normalizado, sin FK entre microservicios.
- Retirar `.env` del índice de Git conservando el archivo local; añadir plantilla
  de demostración. El historial anterior de Git permanece intacto.
- No se encontraron `node_modules`, binarios, compilados, IDE o logs versionados.
  Los artefactos generados durante el trabajo quedan cubiertos por `.gitignore`.

Los resultados posteriores están en [VERIFICACION.md](VERIFICACION.md).
