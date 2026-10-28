#!/usr/bin/env python3
"""Convierte el coverprofile nativo de Go a Cobertura XML para Jenkins."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET


def convert(input_path: Path, output_path: Path, source: str = ".") -> dict[str, int]:
    lines_by_file: dict[str, dict[int, int]] = defaultdict(dict)
    raw_lines = input_path.read_text(encoding="utf-8").splitlines()
    if not raw_lines or not raw_lines[0].startswith("mode:"):
        raise ValueError("El archivo no es un coverprofile Go válido")
    mode = raw_lines[0].partition(":")[2].strip()
    if mode not in {"set", "count", "atomic"}:
        raise ValueError(f"Modo de coverprofile Go desconocido: {mode!r}")
    for line_number, raw in enumerate(raw_lines[1:], 2):
        if not raw.strip():
            continue
        try:
            location, statements, hits = raw.rsplit(" ", 2)
            file_name, span = location.rsplit(":", 1)
            start, end = span.split(",", 1)
            start_line = int(start.split(".", 1)[0])
            end_line = int(end.split(".", 1)[0])
            hit_count = int(hits)
            statement_count = int(statements)
        except (ValueError, IndexError) as exc:
            raise ValueError(f"Coverprofile inválido en la línea {line_number}: {raw}") from exc
        if not file_name or start_line <= 0 or end_line < start_line or statement_count <= 0 or hit_count < 0:
            raise ValueError(f"Coverprofile inválido en la línea {line_number}: {raw}")
        file_name = file_name.replace("\\", "/")
        for current in range(start_line, end_line + 1):
            lines_by_file[file_name][current] = max(lines_by_file[file_name].get(current, 0), hit_count)

    valid = sum(len(lines) for lines in lines_by_file.values())
    if valid == 0:
        raise ValueError("El coverprofile Go no contiene líneas medibles")
    covered = sum(1 for lines in lines_by_file.values() for hits in lines.values() if hits > 0)
    rate = covered / valid if valid else 0.0
    root = ET.Element(
        "coverage",
        {
            "line-rate": f"{rate:.6f}",
            "branch-rate": "0",
            "lines-covered": str(covered),
            "lines-valid": str(valid),
            "branches-covered": "0",
            "branches-valid": "0",
            "complexity": "0",
            "version": "reto7-go-cover",
        },
    )
    sources = ET.SubElement(root, "sources")
    ET.SubElement(sources, "source").text = source
    packages_node = ET.SubElement(root, "packages")
    grouped: dict[str, list[str]] = defaultdict(list)
    for file_name in lines_by_file:
        grouped[str(Path(file_name).parent)].append(file_name)
    for package_name in sorted(grouped):
        package_files = grouped[package_name]
        package_valid = sum(len(lines_by_file[name]) for name in package_files)
        package_covered = sum(
            1 for name in package_files for hits in lines_by_file[name].values() if hits > 0
        )
        package = ET.SubElement(
            packages_node,
            "package",
            name=package_name.replace("\\", "/"),
            **{"line-rate": f"{package_covered / package_valid if package_valid else 0:.6f}", "branch-rate": "0"},
        )
        classes = ET.SubElement(package, "classes")
        for file_name in sorted(package_files):
            file_lines = lines_by_file[file_name]
            file_covered = sum(1 for hits in file_lines.values() if hits > 0)
            class_node = ET.SubElement(
                classes,
                "class",
                name=Path(file_name).stem,
                filename=file_name.replace("\\", "/"),
                **{"line-rate": f"{file_covered / len(file_lines) if file_lines else 0:.6f}", "branch-rate": "0"},
            )
            ET.SubElement(class_node, "methods")
            line_nodes = ET.SubElement(class_node, "lines")
            for number, hits in sorted(file_lines.items()):
                ET.SubElement(line_nodes, "line", number=str(number), hits=str(hits), branch="false")

    ET.indent(root, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
    return {"lines-valid": valid, "lines-covered": covered}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source", default=".")
    args = parser.parse_args()
    totals = convert(args.input, args.output, args.source)
    print(
        f"Cobertura Go generada: {args.output} "
        f"({totals['lines-covered']}/{totals['lines-valid']} líneas)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

