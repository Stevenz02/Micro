"""Merge Graphify AST and deterministic documentation extraction safely.

Graphify's default undirected graph stores one edge per endpoint pair. This
assembler preserves repeated relationships as provenance on a single edge,
materializes referenced external symbols, and removes self-loops before build.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def readable_label(node_id: str) -> str:
    label = re.sub(r"[_:.\\/]+", " ", node_id).strip()
    return label[:120] or node_id


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ast", type=Path, default=Path("graphify-out/.graphify_ast.json"))
    parser.add_argument("--semantic", type=Path, default=Path("graphify-out/.graphify_semantic.json"))
    parser.add_argument("--output", type=Path, default=Path("graphify-out/.graphify_extract.json"))
    args = parser.parse_args()

    ast = json.loads(args.ast.read_text(encoding="utf-8"))
    semantic = json.loads(args.semantic.read_text(encoding="utf-8"))

    nodes: dict[str, dict] = {}
    for node in [*ast.get("nodes", []), *semantic.get("nodes", [])]:
        nodes.setdefault(node["id"], node)

    raw_edges = [*ast.get("edges", []), *semantic.get("edges", [])]
    materialized = 0
    for edge in raw_edges:
        for endpoint in (edge.get("source"), edge.get("target")):
            if endpoint and endpoint not in nodes:
                nodes[endpoint] = {
                    "id": endpoint,
                    "label": readable_label(endpoint),
                    "file_type": "external_reference",
                    "source_file": edge.get("source_file", ""),
                    "source_location": "referenced symbol",
                    "_origin": "semantic",
                }
                materialized += 1

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    self_loops = 0
    for edge in raw_edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            continue
        if source == target:
            self_loops += 1
            continue
        grouped[tuple(sorted((source, target)))].append(edge)

    edges = []
    collapsed = 0
    for variants in grouped.values():
        first = dict(variants[0])
        if len(variants) > 1:
            collapsed += len(variants) - 1
            relations = list(dict.fromkeys(str(edge.get("relation", "related_to")) for edge in variants))
            contexts = list(dict.fromkeys(str(edge.get("context", "")) for edge in variants if edge.get("context")))
            first["relation"] = " | ".join(relations)
            if contexts:
                first["context"] = " | ".join(contexts)[:1000]
            first["confidence"] = "EXTRACTED" if any(edge.get("confidence") == "EXTRACTED" for edge in variants) else "INFERRED"
            first["weight"] = max(float(edge.get("weight", 1.0)) for edge in variants)
            first["provenance"] = [
                {
                    "relation": edge.get("relation", "related_to"),
                    "confidence": edge.get("confidence", "EXTRACTED"),
                    "source_file": edge.get("source_file", ""),
                    "source_location": edge.get("source_location", ""),
                }
                for edge in variants
            ]
        edges.append(first)

    output = {
        "nodes": list(nodes.values()),
        "edges": edges,
        "hyperedges": semantic.get("hyperedges", []),
        "input_tokens": semantic.get("input_tokens", 0),
        "output_tokens": semantic.get("output_tokens", 0),
        "assembly": {
            "materialized_endpoint_nodes": materialized,
            "removed_self_loops": self_loops,
            "merged_parallel_edges": collapsed,
        },
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Assembled: {len(output['nodes'])} nodes, {len(edges)} edges; "
        f"materialized {materialized} endpoints, removed {self_loops} self-loops, "
        f"merged {collapsed} parallel edges"
    )


if __name__ == "__main__":
    main()
