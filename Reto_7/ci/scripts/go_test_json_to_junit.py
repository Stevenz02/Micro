#!/usr/bin/env python3
"""Convierte la salida de ``go test -json`` a JUnit XML sin ocultar fallos."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclass
class TestResult:
    name: str
    package: str
    elapsed: float = 0.0
    outcome: str = "running"
    output: list[str] = field(default_factory=list)


def convert(input_path: Path, output_path: Path) -> dict[str, int]:
    tests: dict[tuple[str, str], TestResult] = {}
    package_output: dict[str, list[str]] = defaultdict(list)
    package_outcome: dict[str, str] = {}

    event_count = 0
    known_actions = {"start", "run", "pause", "cont", "output", "pass", "fail", "skip", "bench"}
    for line_number, raw in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON Go inválido en la línea {line_number}: {exc}") from exc
        if not isinstance(event, dict):
            raise ValueError(f"JSON Go inválido en la línea {line_number}: se esperaba un objeto")
        event_count += 1
        package = event.get("Package", "unknown-package")
        test_name = event.get("Test")
        action = event.get("Action")
        if not isinstance(package, str) or not package.strip():
            raise ValueError(f"Paquete Go inválido en la línea {line_number}")
        if action not in known_actions:
            raise ValueError(f"Acción Go inesperada en la línea {line_number}: {action!r}")
        if test_name:
            key = (package, test_name)
            result = tests.setdefault(key, TestResult(test_name, package))
            if "Output" in event:
                result.output.append(str(event["Output"]))
            if action in {"pass", "fail", "skip"}:
                result.outcome = action
                try:
                    result.elapsed = float(event.get("Elapsed", 0) or 0)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Elapsed Go inválido en la línea {line_number}") from exc
                if result.elapsed < 0:
                    raise ValueError(f"Elapsed Go negativo en la línea {line_number}")
        else:
            if "Output" in event:
                package_output[package].append(str(event["Output"]))
            if action in {"pass", "fail", "skip"}:
                package_outcome[package] = action

    if event_count == 0:
        raise ValueError("La salida go test -json está vacía")
    packages = sorted(set(package_outcome) | {item.package for item in tests.values()})
    for package in packages:
        has_failed_test = any(
            item.package == package and item.outcome == "fail" for item in tests.values()
        )
        if package_outcome.get(package) == "fail" and not has_failed_test:
            synthetic = TestResult("package setup", package, outcome="fail")
            synthetic.output.extend(package_output.get(package, []))
            tests[(package, synthetic.name)] = synthetic

    if not tests:
        raise ValueError("La salida go test -json no contiene pruebas")

    root = ET.Element("testsuites")
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for package in packages:
        package_tests = sorted(
            (item for item in tests.values() if item.package == package),
            key=lambda item: item.name,
        )
        if not package_tests:
            continue
        suite = ET.SubElement(root, "testsuite", name=package)
        suite_counts = {"tests": len(package_tests), "failures": 0, "errors": 0, "skipped": 0}
        suite_time = 0.0
        for item in package_tests:
            suite_time += item.elapsed
            case = ET.SubElement(
                suite,
                "testcase",
                name=item.name,
                classname=package,
                time=f"{item.elapsed:.6f}",
            )
            details = "".join(item.output).strip()
            if item.outcome == "fail":
                suite_counts["failures"] += 1
                ET.SubElement(case, "failure", message="go test falló").text = details
            elif item.outcome == "skip":
                suite_counts["skipped"] += 1
                ET.SubElement(case, "skipped")
            elif item.outcome == "running":
                suite_counts["errors"] += 1
                ET.SubElement(case, "error", message="go test terminó sin resultado final").text = details
            elif item.outcome != "pass":
                suite_counts["errors"] += 1
                ET.SubElement(case, "error", message=f"Estado Go desconocido: {item.outcome}").text = details
            if details:
                ET.SubElement(case, "system-out").text = details
        suite.set("time", f"{suite_time:.6f}")
        for key, value in suite_counts.items():
            suite.set(key, str(value))
            totals[key] += value

    for key, value in totals.items():
        root.set(key, str(value))
    ET.indent(root, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    totals = convert(args.input, args.output)
    print(f"JUnit Go generado: {args.output} ({totals['tests']} pruebas, {totals['failures']} fallos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

