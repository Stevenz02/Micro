#!/usr/bin/env python3
"""Copia la cobertura .NET generada en carpetas UUID a rutas estables de CI."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET


def newest(results: Path, name: str, destination: Path) -> Path:
    candidates = [
        item for item in results.rglob(name)
        if item.resolve() != destination.resolve()
    ]
    if not candidates:
        raise FileNotFoundError(f"No se encontró {name} bajo {results}")
    return max(candidates, key=lambda item: item.stat().st_mtime_ns)


def normalize(results: Path, cobertura: Path, opencover: Path) -> tuple[Path, Path]:
    source_cobertura = newest(results, "coverage.cobertura.xml", cobertura)
    source_opencover = newest(results, "coverage.opencover.xml", opencover)
    cobertura_root = ET.parse(source_cobertura).getroot()
    opencover_root = ET.parse(source_opencover).getroot()
    if cobertura_root.tag != "coverage":
        raise ValueError(f"{source_cobertura}: raíz Cobertura inesperada {cobertura_root.tag}")
    if opencover_root.tag != "CoverageSession":
        raise ValueError(f"{source_opencover}: raíz OpenCover inesperada {opencover_root.tag}")
    if not cobertura_root.findall(".//line"):
        raise ValueError(f"{source_cobertura}: no contiene líneas de cobertura")
    summary = opencover_root.find("Summary")
    if summary is None or int(summary.get("numSequencePoints", "0")) <= 0:
        raise ValueError(f"{source_opencover}: no contiene puntos de secuencia")
    cobertura.parent.mkdir(parents=True, exist_ok=True)
    opencover.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_cobertura, cobertura)
    shutil.copy2(source_opencover, opencover)
    return source_cobertura, source_opencover


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--cobertura", required=True, type=Path)
    parser.add_argument("--opencover", required=True, type=Path)
    args = parser.parse_args()
    sources = normalize(args.results, args.cobertura, args.opencover)
    print(f"Cobertura .NET normalizada desde {sources[0].parent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

