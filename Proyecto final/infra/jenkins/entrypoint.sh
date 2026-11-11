#!/bin/bash
# Arranca como root solo para dar al usuario jenkins acceso al socket Docker montado desde el host
# (su GID cambia según el sistema: Docker Desktop, Linux nativo...). Después baja a jenkins.
set -euo pipefail
SOCK=/var/run/docker.sock

if [ -S "$SOCK" ]; then
  sock_gid="$(stat -c '%g' "$SOCK")"
  if ! gosu jenkins test -w "$SOCK"; then
    if [ "$sock_gid" != "0" ]; then
      group_name="$(getent group "$sock_gid" | cut -d: -f1 || true)"
      if [ -z "$group_name" ]; then group_name=docker-host; groupadd -g "$sock_gid" "$group_name"; fi
      usermod -aG "$group_name" jenkins
    else
      usermod -aG root jenkins
    fi
  fi
  if ! gosu jenkins test -w "$SOCK"; then
    echo "[reto7] El socket Docker no da permiso de escritura al grupo; se abre a 666 (entorno académico)."
    chmod 666 "$SOCK"
  fi
  echo "[reto7] Acceso al socket Docker configurado (GID ${sock_gid})."
else
  echo "[reto7] ADVERTENCIA: no se montó ${SOCK}; los pasos docker fallarán."
fi

exec gosu jenkins /usr/local/bin/jenkins.sh "$@"
