# Plantillas de secretos

Esta carpeta **solo documenta** qué archivos espera `docker-compose.yml` en `secrets/`.
Ningún archivo de aquí contiene un valor real: son marcadores de posición.

Los secretos reales se generan localmente y nunca se versionan (`secrets/` está en `.gitignore`):

```bash
cp .env.example .env
bash scripts/setup-secrets.sh        # Windows: .\scripts\setup-secrets.ps1
```

| Archivo en `secrets/` | Contenido |
|---|---|
| `jwt_secret.txt` | Clave de firma HS256 de los JWT (auth-service firma, api-gateway valida) |
| `rabbitmq_password.txt` | Contrasena del usuario RABBITMQ_USER del broker |
| `db_empleados_password.txt` | Contrasena de la base de datos de Empleados |
| `db_departamentos_password.txt` | Contrasena de la base de datos de Departamentos |
| `db_perfiles_password.txt` | Contrasena de la base de datos de Perfiles |
| `db_notificaciones_password.txt` | Contrasena de la base de datos de Notificaciones |
| `db_vacaciones_password.txt` | Contrasena de la base de datos de Vacaciones |
| `db_auth_password.txt` | Contrasena de la base de datos de Autenticacion |
| `admin_password.txt` | Contrasena en claro del administrador semilla (solo para iniciar sesion y para las pruebas E2E) |
| `admin_password_hash.txt` | Hash bcrypt de la anterior; es lo unico que recibe auth-service |
| `grafana_admin_password.txt` | Contrasena del usuario GRAFANA_ADMIN_USER |
| `discord_webhook_url.txt` | URL del webhook de Discord para las alertas de Grafana (se pega a mano; puede quedar vacio) |
| `jenkins_admin_password.txt` | Contrasena del usuario JENKINS_ADMIN_ID |
| `sonar_admin_password.txt` | Contrasena del usuario admin de SonarQube |
| `sonar_db_password.txt` | Contrasena de la base de datos interna de SonarQube |

Cada archivo se monta en los contenedores que lo necesitan como `/run/secrets/<nombre>`
(Docker Compose Secrets). Los microservicios lo leen al arrancar mediante
`docker-entrypoint.sh`; PostgreSQL y Grafana usan su soporte nativo de `*_FILE`.

Rotación: `bash scripts/setup-secrets.sh --force` y después
`docker compose down -v && docker compose up --build`.
