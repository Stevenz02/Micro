# Guía: gestión de secretos (Docker Compose Secrets)

## Principio

El repositorio puede publicarse como código abierto en cualquier momento sin comprometer
ninguna credencial: no hay contraseñas, tokens ni claves en el código, en `docker-compose.yml`
ni en `.env.example`.

## Cómo funciona

1. `scripts/setup-secrets.sh` (o `.ps1`) genera valores aleatorios y los escribe en
   `secrets/<nombre>.txt`. La carpeta está en `.gitignore`.
2. `docker-compose.yml` declara cada archivo en la sección `secrets:` y lo asigna solo a los
   servicios que lo necesitan. Compose lo monta en `/run/secrets/<nombre>`.
3. Cada microservicio recibe la **ruta**, no el valor (`DB_PASSWORD_FILE=/run/secrets/...`).
   Su `docker-entrypoint.sh` lee el archivo y exporta la variable solo para el proceso del servicio.
4. PostgreSQL (`POSTGRES_PASSWORD_FILE`) y Grafana (`GF_SECURITY_ADMIN_PASSWORD__FILE`) usan su
   soporte nativo. RabbitMQ y SonarQube no lo tienen: su `entrypoint` del Compose exporta el
   secreto y continúa con el arranque original de la imagen.
5. Jenkins los recibe como archivos `/run/secrets/JENKINS_ADMIN_PASSWORD` y
   `/run/secrets/E2E_ADMIN_PASSWORD`, que JCasC resuelve por nombre.

Comprobación: `docker compose config` y `docker inspect <contenedor>` no muestran ningún valor
sensible, solo rutas.

## Secretos

La lista completa, con la descripción de cada archivo, está en
[secrets.example/README.md](../../secrets.example/README.md).

## Webhook de alertas

Pegue la URL del webhook de Discord (una sola línea) en `secrets/discord_webhook_url.txt` y
ejecute `docker compose up -d --force-recreate grafana`. El script de secretos nunca lo sobrescribe.

## Rotación

```bash
bash scripts/setup-secrets.sh --force
docker compose down -v
docker compose up --build
```

`down -v` es necesario porque PostgreSQL y RabbitMQ fijan su contraseña al inicializar el
volumen. Para conservar los datos, cambie la contraseña dentro del motor
(`ALTER USER ... PASSWORD ...`) antes de reemplazar el archivo.

## Si un secreto se filtra

Rótelo de inmediato en el sistema de origen (por ejemplo, borre y vuelva a crear el webhook) y
regenere los secretos locales. Eliminar el valor del historial de Git no basta por sí solo.
