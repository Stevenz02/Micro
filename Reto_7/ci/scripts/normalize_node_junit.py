#!/usr/bin/env python3
"""Normaliza el JUnit de node:test para parsers que exigen testsuite intermedio."""

from __future__ import annotations

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET


def normalize(source: Path, destination: Path, suite_name: str = "node:test") -> dict[str, int]:
    root = ET.parse(source).getroot()
    if root.tag == "testsuite":
        suites = [root]
        output_root = ET.Element("testsuites")
        output_root.append(root)
    elif root.tag == "testsuites":
        direct_cases = list(root.findall("testcase"))
        if direct_cases:
            suite = ET.Element("testsuite", name=suite_name)
            for case in direct_cases:
                root.remove(case)
                suite.append(case)
            root.insert(0, suite)
        suites = list(root.findall("testsuite"))
        output_root = root
    else:
        raise ValueError(f"Raíz JUnit Node inesperada: {root.tag}")

    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    total_time = 0.0
    for suite in suites:
        cases = list(suite.findall("testcase"))
        counts = {
            "tests": len(cases),
            "failures": sum(case.find("failure") is not None for case in cases),
            "errors": sum(case.find("error") is not None for case in cases),
            "skipped": sum(case.find("skipped") is not None for case in cases),
        }
        suite_time = sum(float(case.get("time", 0) or 0) for case in cases)
        suite.set("time", f"{suite_time:.6f}")
        for key, value in counts.items():
            suite.set(key, str(value))
            totals[key] += value
        total_time += suite_time
    if totals["tests"] <= 0:
        raise ValueError("El JUnit de node:test no contiene pruebas")
    for key, value in totals.items():
        output_root.set(key, str(value))
    output_root.set("time", f"{total_time:.6f}")
    ET.indent(output_root, space="  ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(output_root).write(destination, encoding="utf-8", xml_declaration=True)
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--suite-name", default="departamentos-node-test")
    args = parser.parse_args()
    totals = normalize(args.input, args.output, args.suite_name)
    print(f"JUnit Node normalizado: {args.output} ({totals['tests']} pruebas, {totals['failures']} fallos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

