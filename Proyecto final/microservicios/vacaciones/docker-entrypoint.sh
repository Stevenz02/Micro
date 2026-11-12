#!/bin/sh
# Docker Compose Secrets -> variables del proceso.
# Por cada variable NOMBRE_FILE=/run/secrets/x exporta NOMBRE con el contenido del archivo y
# arranca el servicio. Asi el secreto nunca aparece en docker-compose.yml, en .env ni en
# `docker inspect`; solo existe como archivo montado y en la memoria del proceso.
# Solo se procesan rutas bajo SECRETS_DIR (otras *_FILE, como SSL_CERT_FILE, se respetan).
# (Copia identica en cada microservicio cuyo contexto de build es su propia carpeta.)
set -eu
secrets_dir="${SECRETS_DIR:-/run/secrets}"
for name in $(env | sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)_FILE=.*/\1/p'); do
  eval "file=\${${name}_FILE}"
  case "$file" in "$secrets_dir"/*) ;; *) continue ;; esac
  if [ ! -r "$file" ]; then
    echo "Secreto no disponible: ${name}_FILE=$file (ejecute scripts/setup-secrets.sh)" >&2
    exit 1
  fi
  value=$(cat "$file")
  export "$name=$value"
  unset "${name}_FILE"
done
exec "$@"
