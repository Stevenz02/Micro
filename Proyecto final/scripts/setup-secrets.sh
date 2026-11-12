#!/usr/bin/env sh
# Genera la configuracion local del proyecto:
#   - .env                 (copia de .env.example: solo configuracion NO sensible)
#   - secrets/<nombre>.txt (Docker Compose Secrets con valores aleatorios; Git los ignora)
#
# Uso:   bash scripts/setup-secrets.sh           # primera vez (no pisa secretos existentes)
#        bash scripts/setup-secrets.sh --force   # ROTAR todos los secretos
# Tras rotar hay que recrear los datos: docker compose down -v && docker compose up --build
# (PostgreSQL y RabbitMQ fijan su contrasena al inicializar el volumen).
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env_path="$project_root/.env"
secrets_dir="$project_root/secrets"
force=0
[ "${1:-}" = "--force" ] && force=1

command -v docker >/dev/null 2>&1 || { echo "Docker es obligatorio." >&2; exit 1; }

if [ ! -f "$env_path" ]; then
  cp "$project_root/.env.example" "$env_path"
  echo ".env creado a partir de .env.example"
fi

if [ -f "$secrets_dir/jwt_secret.txt" ] && [ "$force" -eq 0 ]; then
  echo "Los secretos ya existen en secrets/. Use --force para rotarlos."
  exit 0
fi

rand() {
  { openssl rand -base64 "$1" 2>/dev/null || head -c "$1" /dev/urandom | base64; } | tr '+/' '-_' | tr -d '=\n'
}
put() { printf '%s' "$2" > "$secrets_dir/$1.txt"; }

mkdir -p "$secrets_dir"

# El webhook de alertas no se genera: se conserva el que ya este configurado
webhook=""
[ -f "$secrets_dir/discord_webhook_url.txt" ] && webhook=$(cat "$secrets_dir/discord_webhook_url.txt")
[ -z "$webhook" ] && webhook="${DISCORD_WEBHOOK_URL:-}"

admin_password=$(rand 18)
# El sistema solo guarda el hash bcrypt; la contrasena en claro queda unicamente en secrets/
admin_hash=$(docker run --rm -e ADMIN_PASSWORD="$admin_password" python:3.12-alpine sh -c \
  'pip install --disable-pip-version-check -q bcrypt==4.3.0 >/dev/null 2>&1 && python -c "import os, bcrypt; print(bcrypt.hashpw(os.environ[\"ADMIN_PASSWORD\"].encode(), bcrypt.gensalt(rounds=12)).decode())"')
case "$admin_hash" in '$2'*) ;; *) echo "No se pudo generar el hash bcrypt (revise Docker y la red)." >&2; exit 1 ;; esac

put jwt_secret "$(rand 48)"
put rabbitmq_password "$(rand 32)"
for db in empleados departamentos perfiles notificaciones vacaciones auth; do
  put "db_${db}_password" "$(rand 32)"
done
put admin_password "$admin_password"
put admin_password_hash "$admin_hash"
put grafana_admin_password "$(rand 24)"
put jenkins_admin_password "$(rand 24)"
# SonarQube exige mayuscula, minuscula, numero y caracter especial: el sufijo lo garantiza
put sonar_admin_password "$(rand 24)_aA1"
put sonar_db_password "$(rand 32)"
put discord_webhook_url "$webhook"

# Carpeta privada para el usuario; los archivos se dejan legibles porque Compose los monta
# tal cual y los contenedores se ejecutan con usuarios sin privilegios
chmod 700 "$secrets_dir"
chmod 644 "$secrets_dir"/*.txt

echo "Secretos generados en secrets/ (15 archivos, ignorados por Git)."
echo "  - Administrador semilla: usuario ADMIN_EMAIL de .env, contrasena en secrets/admin_password.txt"
[ -z "$webhook" ] && echo "  - Alertas: pegue la URL del webhook de Discord en secrets/discord_webhook_url.txt"
echo "Siguiente paso: docker compose up --build"
