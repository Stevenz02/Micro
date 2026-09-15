# Departamentos — Reto 2

Microservicio en **JavaScript**, Node.js 22 y Express 5, distinto del Python de
empleados. Usa `pg` para su propia base PostgreSQL 16 y `swagger-ui-express` para documentación.

| Método | Ruta | Resultado |
|--------|------|-----------|
| POST | `/departamentos` | 201; 400 por id duplicado o datos inválidos |
| GET | `/departamentos` | 200, lista de departamentos |
| GET | `/departamentos/{id}` | 200; 404 con id y mensaje descriptivo |
| GET | `/health` | 200 si la tabla y la BD responden |

Modelo requerido: `{"id":"IT","nombre":"Tecnología","descripcion":"Departamento de TI"}`.
Los tres campos son textos no vacíos. Se recortan espacios exteriores y se rechazan
campos adicionales. JSON inválido → 400; cuerpo mayor de 64 KiB → 413;
fallo de BD → 500/503 controlado.

Swagger: <http://localhost:8081/docs/>. OpenAPI: <http://localhost:8081/openapi.json>.
Los recursos JavaScript/CSS de Swagger se sirven desde la propia API.

## Ejecución

Usar Compose desde `Reto_2` para disponer de la BD inicializada. Para desarrollo
local, configurar una instancia PostgreSQL accesible con `init.sql` aplicado y
definir `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `PORT` (8081).
La aplicación no carga `.env` automáticamente; Compose sí lo hace.

```powershell
Set-Location D:\Repositorios_UQ\Micro\Reto_2\departamentos
npm ci
npm test
npm start
```

`src/config.js` configura el pool, `repository.js` contiene SQL parametrizado,
`app.js` expone la API, `openapi.js` define el contrato e `index.js` inicia el proceso.
Las pruebas usan `node:test` y HTTP local con repositorio simulado; la prueba E2E
del reto usa PostgreSQL real. No hay credenciales ni acceso a la BD de empleados.
