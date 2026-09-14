# Reto 2: microservicios de Empleados y Departamentos

> **Estado actual:** en progreso. Este README documenta únicamente la parte
> de infraestructura Docker ya implementada. El código de los servicios
> (`empleados/app` y `departamentos/src`) está pendiente.

## Estructura

```text
Reto_2/
 ├── docker-compose.yml
 ├── .env.example
 ├── empleados/
 │    ├── Dockerfile        # multi-stage
 │    ├── init.sql
 │    └── app/              # PENDIENTE (código del servicio)
 └── departamentos/
      ├── Dockerfile        # multi-stage
      ├── init.sql
      └── src/              # PENDIENTE (código del servicio)
```

## Arquitectura

El sistema está compuesto por 4 contenedores:

| Servicio               | Tecnología      | Puerto host | Rol                              |
| ---------------------- | --------------- | ----------: | --------------------------------- |
| `empleados-service`    | Python/FastAPI  |        8080 | Gestión de empleados              |
| `departamentos-service`| Node.js/Express |        8081 | Gestión de departamentos          |
| `database-empleados`   | PostgreSQL 16   |     (interno)| Persistencia de empleados        |
| `database-departamentos`| PostgreSQL 16 |     (interno)| Persistencia de departamentos    |

Se usa **PostgreSQL para ambos servicios**: el reto permite usar motores
distintos por servicio, pero decidimos usar uno solo para reducir lo que el
equipo tiene que aprender y operar (un único tipo de healthcheck, un único
cliente). El modelo de datos de ambos servicios es simple y relacional, así
que no hay una razón concreta todavía para justificar un segundo motor.

## Decisiones de la parte de Docker

- **Health checks en las bases de datos** con `pg_isready`, y en
  `departamentos-service` con `curl` contra su propio endpoint. Esto permite
  que `empleados-service` use `depends_on: condition: service_healthy` tanto
  para su base de datos como para `departamentos-service`, garantizando que
  no arranque hasta que ambas dependencias estén realmente listas (no solo
  "iniciadas").
- **Multi-stage builds** en ambos Dockerfiles: una etapa de build donde se
  instalan las dependencias, y una etapa final más liviana que solo lleva lo
  necesario para ejecutar la aplicación.
- **Red interna** (`microservices-network`): los servicios se comunican entre
  sí por nombre de contenedor (ej. `http://departamentos-service:8081`), no
  por `localhost`.
- **Volúmenes nombrados** (`vol-empleados`, `vol-departamentos`) para que los
  datos persistan entre reinicios (`docker compose down` sin `-v`).
- **Solo se exponen al host** los puertos de los servicios de negocio (8080 y
  8081); las bases de datos no son accesibles desde fuera de la red interna.
- **Esquema de base de datos** (`init.sql`) con restricciones `UNIQUE` en
  `email` y `numero_empleado`, para que la unicidad se garantice a nivel de
  base de datos y no solo con validaciones en el código.

## Cómo levantar el sistema (cuando el código esté listo)

```powershell
# 1. Copiar el archivo de variables de entorno
copy .env.example .env

# 2. Construir y levantar todo
docker compose up --build

# 3. Verificar que todo esté "healthy"
docker compose ps
```

Para probar que los datos persisten entre reinicios:

```powershell
docker compose down        # detiene los contenedores, conserva los volúmenes
docker compose up          # los datos siguen ahí
```

Para empezar desde cero (borra todos los datos):

```powershell
docker compose down -v
```

## Pendiente (a cargo de mi compañero)

- [ ] Código de `empleados-service`: conexión a PostgreSQL, llamada HTTP a
      `departamentos-service` con timeout y reintentos.
- [ ] Código de `departamentos-service`: endpoints, conexión a PostgreSQL,
      documentación Swagger.
- [ ] Pruebas automatizadas de ambos servicios.
- [ ] Actualizar este README con instrucciones de uso de cada API una vez
      esté el código.