"""Build a deterministic Graphify semantic layer from repository documentation.

The script complements Graphify's AST extractor when no semantic LLM provider is
configured. It indexes Markdown headings, local links, explicit repository paths,
known architecture concepts, Docker Compose services, and cross-reto evolution.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote

import yaml


EXCLUDED_PARTS = {
    ".codex",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "bin",
    "build",
    "dist",
    "graphify-out",
    "node_modules",
    "obj",
    "target",
}

CONCEPTS = {
    "api gateway": "API Gateway",
    "rabbitmq": "RabbitMQ",
    "postgresql": "PostgreSQL",
    "jwt": "JWT",
    "rbac": "RBAC",
    "circuit breaker": "Circuit Breaker",
    "bdd": "BDD",
    "behave": "Behave",
    "jenkins": "Jenkins",
    "sonarqube": "SonarQube",
    "prometheus": "Prometheus",
    "grafana": "Grafana",
    "loki": "Loki",
    "zipkin": "Zipkin",
    "opentelemetry": "OpenTelemetry",
    "docker compose": "Docker Compose",
    "fastapi": "FastAPI",
    "express": "Express",
    "spring boot": "Spring Boot",
    ".net": ".NET",
    "golang": "Go",
}


def slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", ascii_value.casefold()).strip("_") or "root"


def is_included(path: Path, root: Path) -> bool:
    return not any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts)


class GraphBuilder:
    def __init__(self, root: Path, ast_path: Path) -> None:
        self.root = root.resolve()
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []
        self.edge_keys: set[tuple[str, str, str, str]] = set()
        self.coverage: dict[str, int] = {}
        self.ast_file_nodes: dict[str, str] = {}
        if ast_path.exists():
            ast = json.loads(ast_path.read_text(encoding="utf-8"))
            for node in ast.get("nodes", []):
                source = str(node.get("source_file", "")).replace("\\", "/")
                if source and source not in self.ast_file_nodes:
                    self.ast_file_nodes[source.casefold()] = node["id"]

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def add_node(self, node_id: str, label: str, file_type: str, source_file: str, source_location: str, **extra: object) -> str:
        node = {
            "id": node_id,
            "label": label,
            "file_type": file_type,
            "source_file": source_file,
            "source_location": source_location,
            "_origin": "semantic",
        }
        node.update({key: value for key, value in extra.items() if value not in (None, "")})
        self.nodes.setdefault(node_id, node)
        return node_id

    def add_edge(self, source: str, target: str, relation: str, source_file: str, source_location: str, confidence: str = "EXTRACTED", context: str = "") -> None:
        key = (source, target, relation, source_file)
        if source == target or key in self.edge_keys:
            return
        self.edge_keys.add(key)
        edge = {
            "source": source,
            "target": target,
            "relation": relation,
            "confidence": confidence,
            "source_file": source_file,
            "source_location": source_location,
            "weight": 1.0 if confidence == "EXTRACTED" else 0.7,
            "_origin": "semantic",
        }
        if context:
            edge["context"] = context
        self.edges.append(edge)

    def artifact_node(self, path: Path) -> str:
        rel = self.relative(path)
        ast_node = self.ast_file_nodes.get(rel.casefold())
        if ast_node:
            return ast_node
        return self.add_node(
            f"artifact_{slug(rel)}",
            rel,
            "artifact",
            rel,
            "file",
        )

    def concept_node(self, label: str) -> str:
        return self.add_node(
            f"concept_{slug(label)}",
            label,
            "concept",
            "Docs/ARQUITECTURA_REPOSITORIO.md",
            "architecture concept",
        )

    def reto_node(self, number: int) -> str:
        path = f"Reto_{number}"
        return self.add_node(
            f"reto_{number}",
            f"Reto {number}",
            "project",
            path,
            "directory",
        )

    def build_markdown(self) -> None:
        md_files = sorted(
            (path for path in self.root.rglob("*.md") if is_included(path, self.root)),
            key=lambda path: self.relative(path).casefold(),
        )
        for path in md_files:
            rel = self.relative(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            self.coverage[rel] = len(lines)
            headings = []
            for line_number, line in enumerate(lines, start=1):
                match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
                if match:
                    headings.append((line_number, len(match.group(1)), re.sub(r"[*_`]", "", match.group(2)).strip()))
            title = headings[0][2] if headings else path.stem
            doc_id = self.add_node(
                f"document_{slug(rel)}",
                title,
                "document",
                rel,
                "document",
                description=f"Documento Markdown en {rel}",
            )

            first_part = Path(rel).parts[0] if Path(rel).parts else ""
            reto_match = re.fullmatch(r"Reto_(\d+)", first_part, re.IGNORECASE)
            if reto_match:
                reto_id = self.reto_node(int(reto_match.group(1)))
                self.add_edge(reto_id, doc_id, "documents", rel, "document path")
            elif first_part.casefold() == "docs":
                requirement = re.fullmatch(r"reto0?(\d+)", path.stem, re.IGNORECASE)
                if requirement:
                    reto_id = self.reto_node(int(requirement.group(1)))
                    self.add_edge(doc_id, reto_id, "specifies", rel, "document name")

            for line_number, level, heading in headings:
                section_id = self.add_node(
                    f"section_{slug(rel)}_{line_number}",
                    heading,
                    "section",
                    rel,
                    f"heading line {line_number}",
                    level=level,
                )
                self.add_edge(doc_id, section_id, "contains_section", rel, f"heading line {line_number}")

            lower = text.casefold()
            for needle, label in CONCEPTS.items():
                if needle in lower:
                    self.add_edge(doc_id, self.concept_node(label), "mentions", rel, "document text")

            for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
                raw_target = match.group(1).split("#", 1)[0].strip().strip("<>")
                if not raw_target or re.match(r"^[a-z]+://", raw_target, re.IGNORECASE):
                    continue
                target = (path.parent / unquote(raw_target)).resolve()
                try:
                    target.relative_to(self.root)
                except ValueError:
                    continue
                if target.is_file() and is_included(target, self.root):
                    self.add_edge(doc_id, self.artifact_node(target), "links_to", rel, "markdown link")

            path_pattern = r"(?<![A-Za-z0-9_.-])((?:Reto_[1-8]|Docs|graphify-out|\.codex)/[A-Za-z0-9_./*{}-]+)"
            for match in re.finditer(path_pattern, text.replace("\\", "/")):
                raw = match.group(1).rstrip(".,;:)").replace("*", "")
                if "{" in raw or "}" in raw:
                    continue
                target = (self.root / raw).resolve()
                if target.is_file() and is_included(target, self.root):
                    self.add_edge(doc_id, self.artifact_node(target), "references", rel, "explicit repository path")

    def build_text_documents(self) -> None:
        text_files = sorted(
            (path for path in self.root.rglob("*.txt") if is_included(path, self.root)),
            key=lambda path: self.relative(path).casefold(),
        )
        for path in text_files:
            rel = self.relative(path)
            text = path.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            self.coverage[rel] = len(lines)
            doc_id = self.add_node(
                f"document_{slug(rel)}",
                rel,
                "document",
                rel,
                "document",
                description=f"Documento de texto en {rel}",
            )
            first_part = Path(rel).parts[0] if Path(rel).parts else ""
            reto_match = re.fullmatch(r"Reto_(\d+)", first_part, re.IGNORECASE)
            if reto_match:
                self.add_edge(self.reto_node(int(reto_match.group(1))), doc_id, "documents", rel, "document path")
            for needle, label in CONCEPTS.items():
                if needle in text.casefold():
                    self.add_edge(doc_id, self.concept_node(label), "mentions", rel, "document text")
            if path.name.casefold() == "requirements.txt" or path.name.casefold().endswith("plugins.txt"):
                for line_number, line in enumerate(lines, start=1):
                    dependency = line.strip()
                    if not dependency or dependency.startswith("#"):
                        continue
                    name = re.split(r"[<>=!~\s]", dependency, maxsplit=1)[0].strip()
                    if not name:
                        continue
                    dependency_id = self.add_node(
                        f"dependency_{slug(name)}",
                        name,
                        "dependency",
                        rel,
                        f"line {line_number}",
                    )
                    self.add_edge(doc_id, dependency_id, "declares_dependency", rel, f"line {line_number}")

    def build_compose(self) -> None:
        compose_files = sorted(
            (
                path
                for pattern in ("docker-compose.yml", "docker-compose.yaml")
                for path in self.root.rglob(pattern)
                if is_included(path, self.root)
            ),
            key=lambda path: self.relative(path).casefold(),
        )
        for path in compose_files:
            rel = self.relative(path)
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            compose_id = self.artifact_node(path)
            first_part = Path(rel).parts[0]
            match = re.fullmatch(r"Reto_(\d+)", first_part, re.IGNORECASE)
            reto_id = self.reto_node(int(match.group(1))) if match else None
            if reto_id:
                self.add_edge(reto_id, compose_id, "orchestrated_by", rel, "compose file")
            services = data.get("services") or {}
            service_ids: dict[str, str] = {}
            for name, config in services.items():
                config = config or {}
                service_id = self.add_node(
                    f"compose_service_{slug(rel)}_{slug(name)}",
                    f"{first_part}: {name}",
                    "service",
                    rel,
                    f"service {name}",
                    technology=str(config.get("image", "project build")),
                )
                service_ids[name] = service_id
                self.add_edge(compose_id, service_id, "defines_service", rel, f"service {name}")
                if reto_id:
                    self.add_edge(reto_id, service_id, "contains_service", rel, f"service {name}")
                global_service = self.concept_node(name)
                self.add_edge(service_id, global_service, "implements", rel, f"service {name}")

                build = config.get("build")
                context = build.get("context") if isinstance(build, dict) else build
                if isinstance(context, str) and not context.startswith("$"):
                    target = (path.parent / context).resolve()
                    try:
                        target.relative_to(self.root)
                    except ValueError:
                        target = None
                    if target and target.exists():
                        target_id = self.artifact_node(target) if target.is_file() else self.add_node(
                            f"directory_{slug(self.relative(target))}",
                            self.relative(target),
                            "directory",
                            self.relative(target),
                            "directory",
                        )
                        self.add_edge(service_id, target_id, "builds_from", rel, f"service {name}")

            for name, config in services.items():
                config = config or {}
                depends_on = config.get("depends_on") or []
                dependency_names = depends_on.keys() if isinstance(depends_on, dict) else depends_on
                for dependency in dependency_names:
                    if dependency in service_ids:
                        self.add_edge(service_ids[name], service_ids[dependency], "depends_on", rel, f"service {name}")

    def build_evolution(self) -> None:
        source = "Docs/ARQUITECTURA_REPOSITORIO.md"
        for newer, older in [(2, 1), (3, 2), (4, 3), (5, 4), (6, 5)]:
            self.add_edge(self.reto_node(newer), self.reto_node(older), "evolves_from", source, "Vista rápida")
        for dependency in (4, 5, 6):
            self.add_edge(self.reto_node(7), self.reto_node(dependency), "reuses", source, "Vista rápida")
        self.add_edge(self.reto_node(8), self.reto_node(5), "instrumented_copy_of", source, "Vista rápida")

    def result(self) -> dict:
        return {
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
            "hyperedges": [],
            "coverage": self.coverage,
            "input_tokens": 0,
            "output_tokens": 0,
            "extraction_method": "deterministic-document-structure",
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--ast", type=Path, default=Path("graphify-out/.graphify_ast.json"))
    parser.add_argument("--output", type=Path, default=Path("graphify-out/.graphify_semantic.json"))
    args = parser.parse_args()

    builder = GraphBuilder(args.root, args.ast)
    builder.build_markdown()
    builder.build_text_documents()
    builder.build_compose()
    builder.build_evolution()
    result = builder.result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Documentation: {len(result['nodes'])} nodes, {len(result['edges'])} edges, {len(result['coverage'])} document files")


if __name__ == "__main__":
    main()
