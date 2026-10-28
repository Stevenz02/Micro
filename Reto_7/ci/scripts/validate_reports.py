#!/usr/bin/env python3
"""Valida que la evidencia CI sea legible, completa y consistente."""

from __future__ import annotations

import argparse
import json
import math
import sys
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


def _tag(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node if _tag(child) == name]


def _non_negative_int(raw: str | None, label: str, *, required: bool = False) -> int | None:
    if raw is None:
        if required:
            raise ValueError(f"falta {label}")
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{label} no es un entero: {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{label} no puede ser negativo")
    return value


def _finite_number(raw: str | int | float | None, label: str) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} no es numérico: {raw!r}") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} debe ser finito y no negativo")
    return value


def inspect_junit(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    root_tag = _tag(root)
    if root_tag not in {"testsuite", "testsuites"}:
        raise ValueError(f"{path}: raíz JUnit inesperada {root_tag}")
    if root_tag == "testsuite":
        suites = [root]
    else:
        if _children(root, "testcase"):
            raise ValueError(f"{path}: testcase directo bajo testsuites; falta testsuite")
        suites = _children(root, "testsuite")
    if not suites:
        raise ValueError(f"{path}: no contiene testsuite")

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for index, suite in enumerate(suites, 1):
        cases = _children(suite, "testcase")
        if not cases:
            raise ValueError(f"{path}: testsuite {index} no contiene testcase")
        actual = {"tests": len(cases), "failures": 0, "errors": 0, "skipped": 0}
        for case_index, case in enumerate(cases, 1):
            if not (case.get("name") or "").strip():
                raise ValueError(f"{path}: testcase {case_index} de suite {index} no tiene nombre")
            states = {
                "failures": len(_children(case, "failure")),
                "errors": len(_children(case, "error")),
                "skipped": len(_children(case, "skipped")),
            }
            if sum(states.values()) > 1:
                raise ValueError(f"{path}: testcase {case.get('name')!r} tiene estados incompatibles")
            for key, value in states.items():
                actual[key] += value
            _finite_number(case.get("time"), f"{path}: tiempo de {case.get('name')}")

        for key, value in actual.items():
            declared = _non_negative_int(suite.get(key), f"{path}: {key} de testsuite {index}")
            if declared is not None and declared != value:
                raise ValueError(
                    f"{path}: testsuite {index} declara {key}={declared}, pero contiene {value}"
                )
            totals[key] += value
        _finite_number(suite.get("time"), f"{path}: tiempo de testsuite {index}")

    if root_tag == "testsuites":
        for key, value in totals.items():
            declared = _non_negative_int(root.get(key), f"{path}: {key} de testsuites")
            if declared is not None and declared != value:
                raise ValueError(f"{path}: testsuites declara {key}={declared}, pero suma {value}")
        _finite_number(root.get("time"), f"{path}: tiempo de testsuites")
    return totals


def validate_junit(path: Path) -> tuple[int, int, int]:
    totals = inspect_junit(path)
    return totals["tests"], totals["failures"], totals["errors"]


def validate_coverage(path: Path) -> str:
    root = ET.parse(path).getroot()
    root_tag = _tag(root)
    if root_tag == "coverage":
        valid = _non_negative_int(root.get("lines-valid"), f"{path}: lines-valid", required=True)
        covered = _non_negative_int(root.get("lines-covered"), f"{path}: lines-covered", required=True)
        assert valid is not None and covered is not None
        if valid == 0:
            raise ValueError(f"{path}: cobertura Cobertura sin líneas medibles")
        if covered > valid:
            raise ValueError(f"{path}: lines-covered supera lines-valid")
        rate = _finite_number(root.get("line-rate"), f"{path}: line-rate")
        if rate is None or rate > 1:
            raise ValueError(f"{path}: line-rate debe estar entre 0 y 1")
        if abs(rate - (covered / valid)) > 0.001:
            raise ValueError(f"{path}: line-rate no coincide con lines-covered/lines-valid")
        line_nodes = [node for node in root.iter() if _tag(node) == "line"]
        if not line_nodes:
            raise ValueError(f"{path}: cobertura Cobertura sin nodos line")
        for node in line_nodes:
            number = _non_negative_int(node.get("number"), f"{path}: número de línea", required=True)
            hits = _non_negative_int(node.get("hits"), f"{path}: hits", required=True)
            if number == 0 or hits is None:
                raise ValueError(f"{path}: línea de cobertura inválida")
    elif root_tag == "report":
        counters = [node for node in root.iter() if _tag(node) == "counter" and node.get("type") == "LINE"]
        if not counters:
            raise ValueError(f"{path}: JaCoCo sin contador LINE")
        summary = counters[-1]
        missed = _non_negative_int(summary.get("missed"), f"{path}: LINE missed", required=True)
        covered = _non_negative_int(summary.get("covered"), f"{path}: LINE covered", required=True)
        if (missed or 0) + (covered or 0) == 0:
            raise ValueError(f"{path}: JaCoCo sin líneas medibles")
    elif root_tag == "CoverageSession":
        summaries = _children(root, "Summary")
        if len(summaries) != 1:
            raise ValueError(f"{path}: OpenCover requiere un Summary raíz")
        valid = _non_negative_int(
            summaries[0].get("numSequencePoints"), f"{path}: numSequencePoints", required=True
        )
        covered = _non_negative_int(
            summaries[0].get("visitedSequencePoints"), f"{path}: visitedSequencePoints", required=True
        )
        if valid == 0 or covered is None or covered > valid:
            raise ValueError(f"{path}: conteos OpenCover inválidos")
    else:
        raise ValueError(f"{path}: formato de cobertura no reconocido ({root_tag})")
    return root_tag


def validate_cucumber(path: Path) -> tuple[int, int]:
    features = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features:
        raise ValueError(f"{path}: Cucumber JSON no contiene características")
    allowed_statuses = {
        "passed", "failed", "skipped", "undefined", "untested", "pending", "ambiguous", "error",
    }
    scenarios = 0
    steps = 0
    for feature_index, feature in enumerate(features, 1):
        if not isinstance(feature, dict) or not isinstance(feature.get("elements"), list):
            raise ValueError(f"{path}: característica {feature_index} incompleta")
        for item in feature["elements"]:
            if not isinstance(item, dict) or item.get("type") not in {"scenario", "scenario_outline"}:
                continue
            scenarios += 1
            scenario_steps = item.get("steps")
            if not isinstance(scenario_steps, list) or not scenario_steps:
                raise ValueError(f"{path}: escenario {item.get('name', scenarios)!r} sin pasos")
            for step_index, step in enumerate(scenario_steps, 1):
                if not isinstance(step, dict) or not isinstance(step.get("result"), dict):
                    raise ValueError(f"{path}: resultado ausente en paso {step_index} del escenario {scenarios}")
                status = step["result"].get("status")
                if status not in allowed_statuses:
                    raise ValueError(f"{path}: estado Cucumber inesperado {status!r}")
                _finite_number(step["result"].get("duration"), f"{path}: duración de paso")
                steps += 1
    if scenarios <= 0 or steps <= 0:
        raise ValueError(f"{path}: conteos Cucumber inválidos")
    return scenarios, steps


def validate_lcov(path: Path) -> tuple[int, int, int]:
    records: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("SF:"):
            if current is not None:
                raise ValueError(f"{path}:{line_number}: falta end_of_record")
            source = line[3:].strip()
            if not source:
                raise ValueError(f"{path}:{line_number}: SF vacío")
            current = {"source": source, "lines": {}, "LF": None, "LH": None}
        elif line.startswith("DA:"):
            if current is None:
                raise ValueError(f"{path}:{line_number}: DA fuera de un registro SF")
            try:
                parts = line[3:].split(",")
                number, hits = int(parts[0]), int(parts[1])
            except (IndexError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: DA inválido") from exc
            if number <= 0 or hits < 0:
                raise ValueError(f"{path}:{line_number}: línea o hits LCOV inválidos")
            lines = current["lines"]
            assert isinstance(lines, dict)
            lines[number] = max(int(lines.get(number, 0)), hits)
        elif line.startswith(("LF:", "LH:")):
            if current is None:
                raise ValueError(f"{path}:{line_number}: métrica fuera de un registro SF")
            key, raw_value = line.split(":", 1)
            current[key] = _non_negative_int(raw_value, f"{path}:{line_number}: {key}", required=True)
        elif line == "end_of_record":
            if current is None:
                raise ValueError(f"{path}:{line_number}: end_of_record sin SF")
            lines = current["lines"]
            assert isinstance(lines, dict)
            if not lines:
                raise ValueError(f"{path}:{line_number}: registro LCOV sin líneas DA")
            actual_found = len(lines)
            actual_hit = sum(int(hits) > 0 for hits in lines.values())
            if current["LF"] is not None and current["LF"] != actual_found:
                raise ValueError(f"{path}:{line_number}: LF no coincide con las líneas DA")
            if current["LH"] is not None and current["LH"] != actual_hit:
                raise ValueError(f"{path}:{line_number}: LH no coincide con las líneas cubiertas")
            records.append(current)
            current = None
    if current is not None:
        raise ValueError(f"{path}: último registro LCOV sin end_of_record")
    if not records:
        raise ValueError(f"{path}: LCOV no contiene registros")
    total_lines = sum(len(record["lines"]) for record in records)  # type: ignore[arg-type]
    total_covered = sum(
        sum(int(hits) > 0 for hits in record["lines"].values())  # type: ignore[union-attr]
        for record in records
    )
    return len(records), total_lines, total_covered


class _CucumberHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.scenarios = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.add(tag)
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if tag == "article" and "scenario" in classes:
            self.scenarios += 1


def validate_cucumber_html(path: Path) -> int:
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        raise ValueError(f"{path}: HTML vacío")
    parser = _CucumberHtmlParser()
    parser.feed(content)
    parser.close()
    if not {"html", "head", "body", "title"}.issubset(parser.tags):
        raise ValueError(f"{path}: estructura HTML incompleta")
    if parser.scenarios <= 0:
        raise ValueError(f"{path}: HTML Cucumber sin escenarios")
    return parser.scenarios


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--junit", action="append", type=Path, default=[])
    parser.add_argument("--coverage", action="append", type=Path, default=[])
    parser.add_argument("--cucumber-json", action="append", type=Path, default=[])
    parser.add_argument("--lcov", action="append", type=Path, default=[])
    parser.add_argument("--cucumber-html", action="append", type=Path, default=[])
    args = parser.parse_args()
    if not (args.junit or args.coverage or args.cucumber_json or args.lcov or args.cucumber_html):
        parser.error("indique al menos un reporte")
    try:
        for path in args.junit:
            print(f"JUnit {path}: tests/failures/errors={validate_junit(path)}")
        for path in args.coverage:
            print(f"Cobertura {path}: raíz={validate_coverage(path)}")
        for path in args.cucumber_json:
            print(f"Cucumber {path}: scenarios/steps={validate_cucumber(path)}")
        for path in args.lcov:
            print(f"LCOV {path}: files/lines/covered={validate_lcov(path)}")
        for path in args.cucumber_html:
            print(f"Cucumber HTML {path}: scenarios={validate_cucumber_html(path)}")
    except (OSError, ET.ParseError, json.JSONDecodeError, ValueError) as exc:
        print(f"Reporte inválido: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
