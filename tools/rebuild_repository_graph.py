"""Rebuild the repository graph without an external semantic provider.

Run this file with Graphify's isolated Python interpreter. It performs fresh
detection, cached AST extraction, deterministic documentation extraction,
integrity-preserving assembly, community labeling, and report generation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from graphify.detect import detect, save_manifest
from graphify.extract import collect_files, extract
from graphify.paths import out_path
from graphify.watch import _read_build_excludes, _read_build_gitignore


def run_script(script: Path, *arguments: str) -> None:
    subprocess.run([sys.executable, str(script), *arguments], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--keep-intermediate", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    output = root / "graphify-out"
    tools = root / "tools"
    output.mkdir(parents=True, exist_ok=True)
    (output / ".graphify_python").write_text(sys.executable, encoding="utf-8")
    (output / ".graphify_root").write_text(str(root), encoding="utf-8")

    detection = detect(
        root,
        extra_excludes=_read_build_excludes(out_path()),
        gitignore=_read_build_gitignore(out_path()),
    )
    detect_path = output / ".graphify_detect.json"
    detect_path.write_text(json.dumps(detection, ensure_ascii=False), encoding="utf-8")
    print(f"Detected {detection['total_files']} supported files")

    code_files = []
    for filename in detection.get("files", {}).get("code", []):
        path = Path(filename)
        code_files.extend(collect_files(path) if path.is_dir() else [path])
    ast = extract(code_files, cache_root=root, root=root, parallel=True)
    ast_path = output / ".graphify_ast.json"
    ast_path.write_text(json.dumps(ast, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"AST: {len(ast['nodes'])} nodes, {len(ast['edges'])} edges")

    run_script(tools / "build_document_graph.py", "--root", str(root), "--ast", str(ast_path), "--output", str(output / ".graphify_semantic.json"))
    run_script(tools / "assemble_graphify_graph.py", "--ast", str(ast_path), "--semantic", str(output / ".graphify_semantic.json"), "--output", str(output / ".graphify_extract.json"))
    run_script(tools / "finalize_graphify_graph.py", "--root", str(root), "--extract", str(output / ".graphify_extract.json"), "--detect", str(detect_path), "--out", str(output))

    extraction = json.loads((output / ".graphify_extract.json").read_text(encoding="utf-8"))
    corpus = detection.get("all_files") or detection["files"]
    scan_corpus = {filename for files in corpus.values() for filename in files}
    save_manifest(corpus, root=root, scan_corpus=scan_corpus)

    cost_path = output / "cost.json"
    cost = json.loads(cost_path.read_text(encoding="utf-8")) if cost_path.exists() else {
        "runs": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
    }
    cost["runs"].append(
        {
            "date": datetime.now(timezone.utc).isoformat(),
            "input_tokens": 0,
            "output_tokens": 0,
            "files": detection.get("total_files", 0),
            "semantic_method": "deterministic-document-structure",
        }
    )
    cost_path.write_text(json.dumps(cost, indent=2, ensure_ascii=False), encoding="utf-8")

    if not args.keep_intermediate:
        for filename in (
            ".graphify_detect.json",
            ".graphify_ast.json",
            ".graphify_semantic.json",
            ".graphify_extract.json",
            ".graphify_analysis.json",
        ):
            (output / filename).unlink(missing_ok=True)

    print(f"Graph ready: {output / 'graph.json'}")
    print("Next: graphify export html && graphify tree --label Microservicios")


if __name__ == "__main__":
    main()
