#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env_path="$project_root/.env"
secrets_path="$project_root/secrets"

if [ -f "$env_path" ] && [ "${1:-}" != "--force" ]; then
  echo "Ya existe $env_path. Use --force solo para rotar todas las credenciales locales." >&2
  exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "Docker es obligatorio." >&2; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "OpenSSL es obligatorio." >&2; exit 1; }

secret() { openssl rand -base64 32 | tr '+/' '-_' | tr -d '=\n'; }
admin_password=$(openssl rand -base64 18 | tr '+/' '-_' | tr -d '=\n')
admin_email=${ADMIN_EMAIL:-admin@proyecto.local}
bcrypt=$(docker run --rm -e ADMIN_PASSWORD="$admin_password" \
  --mount "type=bind,source=$project_root,target=/work" -w /work \
  python:3.12-alpine sh -c 'pip install --disable-pip-version-check -q bcrypt==4.3.0 && python scripts/hash_password.py')
compose_bcrypt=$(printf '%s' "$bcrypt" | sed 's/\$/$$/g')

cat > "$env_path" <<EOF
GATEWAY_PORT=8080
GRAFANA_PORT=3000
PROMETHEUS_PORT=9091
ZIPKIN_PORT=9411
RABBITMQ_MANAGEMENT_PORT=15672
JENKINS_PORT=8090
JENKINS_AGENT_PORT=50000
SONAR_PORT=9000
REGISTRY_PORT=5001
JWT_SECRET=$(secret)
RABBITMQ_USER=rrhh
RABBITMQ_PASSWORD=$(secret)
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=$(secret)
JENKINS_ADMIN_ID=admin
JENKINS_ADMIN_PASSWORD=$(secret)
SONAR_ADMIN_PASSWORD=$(secret)
SONAR_DB_PASSWORD=$(secret)
E2E_ADMIN_EMAIL=$admin_email
E2E_ADMIN_PASSWORD=$admin_password
ADMIN_EMPLOYEE_ID=00000000-0000-0000-0000-000000000001
ADMIN_EMAIL=$admin_email
ADMIN_PASSWORD_HASH=$compose_bcrypt
DISCORD_WEBHOOK_URL=
DB_EMPLEADOS_NAME=empleados
DB_EMPLEADOS_USER=empleados
DB_EMPLEADOS_PASSWORD=$(secret)
DB_DEPARTAMENTOS_NAME=departamentos
DB_DEPARTAMENTOS_USER=departamentos
DB_DEPARTAMENTOS_PASSWORD=$(secret)
DB_PERFILES_NAME=perfiles
DB_PERFILES_USER=perfiles
DB_PERFILES_PASSWORD=$(secret)
DB_NOTIFICACIONES_NAME=notificaciones
DB_NOTIFICACIONES_USER=notificaciones
DB_NOTIFICACIONES_PASSWORD=$(secret)
DB_VACACIONES_NAME=vacaciones
DB_VACACIONES_USER=vacaciones
DB_VACACIONES_PASSWORD=$(secret)
DB_AUTH_NAME=auth
DB_AUTH_USER=auth
DB_AUTH_PASSWORD=$(secret)
JWT_ACCESS_TTL_SECONDS=900
JWT_RESET_TTL_SECONDS=1800
GATEWAY_REQUEST_TIMEOUT_SECONDS=20
VACACIONES_SCHEDULER_INTERVAL_SECONDS=5
DEPARTAMENTOS_TIMEOUT_SECONDS=2
DEPARTAMENTOS_MAX_RETRIES=3
DEPARTAMENTOS_BACKOFF_SECONDS=1
DEPARTAMENTOS_CB_FAIL_MAX=3
DEPARTAMENTOS_CB_RESET_TIMEOUT_SECONDS=30
PENDIENTES_RECONCILIATION_INTERVAL_SECONDS=15
POLL_TIMEOUT_SECONDS=30
POLL_INTERVAL_MS=500
POLL_MAX_ATTEMPTS=60
HTTP_TIMEOUT_SECONDS=20
CHAOS_EMPLEADOS_LATENCY_SECONDS=0
CHAOS_DEPARTAMENTOS_LATENCY_SECONDS=0
CHAOS_LATENCY_PROBABILITY=0.5
SONAR_MIN_COVERAGE=70
SONARQUBE_IMAGE=sonarqube:community
REPO_URL=file:///repo
REPO_BRANCH=*/main
EOF

mkdir -p "$secrets_path"
printf '%s' "$admin_password" > "$secrets_path/admin-password.txt"
printf '%s\n' "Credenciales locales generadas. Esta carpeta está ignorada por Git." > "$secrets_path/README.txt"
chmod 600 "$env_path" "$secrets_path/admin-password.txt"
echo "Configuración creada. Siguiente paso: docker compose up --build -d --wait --wait-timeout 600"
