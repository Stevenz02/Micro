"""Build, label, validate, and report the repository Graphify graph."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from graphify.analyze import god_nodes, suggest_questions, surprising_connections
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.diagnostics import diagnose_extraction, format_diagnostic_report
from graphify.export import to_json
from graphify.report import generate


THEMES = [
    ("Observabilidad", ("observability", "observabilidad", "prometheus", "grafana", "loki", "zipkin", "opentelemetry")),
    ("Integración Continua", ("jenkins", "sonarqube", "quality gate", "pipeline", "ci/")),
    ("BDD y E2E", ("behave", "cucumber", "gherkin", "step_definitions", "e2e")),
    ("Autenticación JWT", ("auth", "jwt", "token", "rbac")),
    ("API Gateway", ("api-gateway", "api gateway", "gateway_app")),
    ("Servicio Empleados", ("empleados", "employee")),
    ("Servicio Departamentos", ("departamentos", "department")),
    ("Servicio Perfiles", ("perfiles", "profile")),
    ("Servicio Notificaciones", ("notificaciones", "notification")),
    ("Servicio Vacaciones", ("vacaciones", "vacation")),
    ("Eventos RabbitMQ", ("rabbitmq", "rrhh.events", "eventos", "events.py")),
    ("Persistencia PostgreSQL", ("postgres", "repository", "database", "init.sql")),
    ("Docker Compose", ("docker-compose", "compose_service", "container", "dockerfile")),
    ("Pruebas Automatizadas", ("pytest", "test_", "tests/", "xunit", "junit")),
    ("Documentación", ("document_", "section_", "docs/", "readme")),
]


def community_label(graph, community_id: int, members: list[str]) -> str:
    corpus_parts = []
    roots = Counter()
    for node_id in members:
        data = graph.nodes[node_id]
        source = str(data.get("source_file", "")).replace("\\", "/")
        corpus_parts.extend((str(data.get("label", "")), source, node_id))
        match = re.match(r"(Reto_[1-8]|Docs|tools)(?:/|$)", source, re.IGNORECASE)
        if match:
            roots[match.group(1).replace("_", " ").title()] += 1
    corpus = " ".join(corpus_parts).casefold()
    scores = []
    for label, needles in THEMES:
        score = sum(corpus.count(needle.casefold()) for needle in needles)
        scores.append((score, label))
    score, theme = max(scores)
    if score == 0:
        ranked = sorted(members, key=lambda node: graph.degree(node), reverse=True)
        raw = str(graph.nodes[ranked[0]].get("label", ranked[0])) if ranked else "Comunidad"
        words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+", raw)[:3]
        theme = " ".join(words) or "Comunidad"
    prefix = roots.most_common(1)[0][0] if roots else ""
    if prefix and prefix.casefold() not in theme.casefold() and len(theme.split()) <= 2:
        label = f"{prefix} {theme} C{community_id}"
    else:
        label = f"{theme} C{community_id}"
    return " ".join(label.split()[:5])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--extract", type=Path, default=Path("graphify-out/.graphify_extract.json"))
    parser.add_argument("--detect", type=Path, default=Path("graphify-out/.graphify_detect.json"))
    parser.add_argument("--out", type=Path, default=Path("graphify-out"))
    args = parser.parse_args()

    extraction = json.loads(args.extract.read_text(encoding="utf-8"))
    detection = json.loads(args.detect.read_text(encoding="utf-8"))
    root = str(args.root.resolve())
    graph = build_from_json(extraction, root=root, directed=False)
    if graph.number_of_nodes() == 0:
        raise SystemExit("Graph is empty")

    communities = cluster(graph)
    cohesion = score_all(graph, communities)
    labels = {community_id: community_label(graph, community_id, members) for community_id, members in communities.items()}
    gods = god_nodes(graph)
    surprises = surprising_connections(graph, communities)
    questions = suggest_questions(graph, communities, labels)

    args.out.mkdir(parents=True, exist_ok=True)
    graph_path = args.out / "graph.json"
    if not to_json(graph, communities, str(graph_path), community_labels=labels, force=True):
        raise SystemExit("Graphify refused to write graph.json")
    report = generate(
        graph,
        communities,
        cohesion,
        labels,
        gods,
        surprises,
        detection,
        {"input": 0, "output": 0},
        root,
        suggested_questions=questions,
    )
    (args.out / "GRAPH_REPORT.md").write_text(report, encoding="utf-8")
    (args.out / ".graphify_labels.json").write_text(
        json.dumps({str(key): value for key, value in labels.items()}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (args.out / ".graphify_analysis.json").write_text(
        json.dumps(
            {
                "communities": {str(key): value for key, value in communities.items()},
                "cohesion": {str(key): value for key, value in cohesion.items()},
                "gods": gods,
                "surprises": surprises,
                "questions": questions,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    health = diagnose_extraction(extraction, directed=False, root=root)
    (args.out / ".graphify_health.json").write_text(json.dumps(health, indent=2, ensure_ascii=False), encoding="utf-8")
    print(format_diagnostic_report(health))
    print(f"Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges, {len(communities)} labeled communities")


if __name__ == "__main__":
    main()
