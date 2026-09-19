# Departamentos - Reto 3

Servicio JavaScript/Express heredado de `Reto_2`. Mantiene el contrato funcional
de departamentos y no contiene Circuit Breaker.

## Endpoints

| Metodo | Ruta | Respuesta |
| --- | --- | --- |
| POST | `/departamentos` | 201; 400 por id duplicado o datos invalidos |
| GET | `/departamentos` | 200, lista de departamentos |
| GET | `/departamentos/{id}` | 200; 404 descriptivo |
| GET | `/health` | 200 si la tabla propia responde |

## Organizacion

| Archivo | Responsabilidad |
| --- | --- |
| `src/app.js` | Rutas, validaciones y errores HTTP |
| `src/repository.js` | Consultas SQL |
| `src/config.js` | Variables de base de datos |
| `src/openapi.js` | Contrato Swagger/OpenAPI |
| `init.sql` | Esquema reproducible |

## Pruebas

```powershell
npm --prefix Reto_3/departamentos ci
npm --prefix Reto_3/departamentos test
```

Docker y publicacion de puertos quedan pendientes para la fase final de `Reto_3`.
