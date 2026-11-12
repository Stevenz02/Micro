"""Exporta la especificacion OpenAPI de cada microservicio a microservicios/<servicio>/openapi.yaml.

Las especificaciones se obtienen del sistema en ejecucion a traves del API Gateway (las rutas de
documentacion son publicas), asi el archivo versionado coincide con lo que realmente se despliega.

Uso, con el ecosistema arriba (no requiere Python en el equipo):

  docker run --rm --network proyecto-final_microservices-network -v "${PWD}:/work" -w /work \
    python:3.12-alpine sh -c "pip install -q pyyaml && python scripts/export_openapi.py"

O, con Python y PyYAML locales:  python scripts/export_openapi.py http://localhost:8080
"""

import json
import sys
import urllib.request
from pathlib import Path

import yaml

RUTAS = {
    "api-gateway": "/openapi.json",
    "auth": "/auth/openapi.json",
    "empleados": "/empleados/openapi.json",
    "departamentos": "/departamentos/openapi.json",
    "perfiles": "/perfiles/openapi.json",
    "notificaciones": "/notificaciones/openapi.json",
    "vacaciones": "/vacaciones/v1/openapi.json",
}


def guardar(servicio: str, especificacion: dict, raiz: Path) -> Path:
    destino = raiz / "microservicios" / servicio / "openapi.yaml"
    texto = yaml.safe_dump(especificacion, sort_keys=False, allow_unicode=True, width=110)
    destino.write_text(texto, encoding="utf-8", newline="\n")
    return destino


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://api-gateway:8080").rstrip("/")
    raiz = Path(__file__).resolve().parents[1]
    fallos = 0
    for servicio, ruta in RUTAS.items():
        try:
            with urllib.request.urlopen(base + ruta, timeout=30) as respuesta:
                especificacion = json.load(respuesta)
            destino = guardar(servicio, especificacion, raiz)
            print(f"ok    {servicio:15} {len(especificacion.get('paths', {})):3} rutas -> {destino.relative_to(raiz)}")
        except Exception as error:  # se informa y se continua con los demas servicios
            fallos += 1
            print(f"ERROR {servicio:15} {base + ruta}: {error}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
