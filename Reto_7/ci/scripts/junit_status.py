#!/usr/bin/env python3
"""Resume JUnit sin ocultar fallos, suites vacías ni reportes corruptos."""

from __future__ import annotations

import argparse
import glob
from pathlib import Path
from xml.etree import ElementTree as ET

try:
    from .validate_reports import inspect_junit
except ImportError:  # Ejecución directa desde Jenkins.
    from validate_reports import inspect_junit


def summarize(paths: list[Path]) -> dict[str, int]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for path in paths:
        report = inspect_junit(path)
        for key, value in report.items():
            totals[key] += value
    if totals["tests"] <= 0:
        raise ValueError("los reportes JUnit no contienen pruebas")
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--glob", required=True, dest="pattern")
    args = parser.parse_args()
    paths = [Path(item) for item in sorted(glob.glob(args.pattern))]
    if not paths:
        print(f"No se encontraron reportes JUnit con: {args.pattern}")
        return 2
    try:
        totals = summarize(paths)
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"Reporte JUnit corrupto o inconsistente: {exc}")
        return 3
    print(
        f"JUnit: {totals['tests']} pruebas, {totals['failures']} fallos, "
        f"{totals['errors']} errores, {totals['skipped']} omitidas"
    )
    return 1 if totals["failures"] or totals["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
