#!/usr/bin/env python3
"""Convierte el JSON de Behave al formato Cucumber JSON que entiende el plugin 'Cucumber Reports'.

Behave genera un JSON parecido pero sin los campos que exige cucumber-reporting (uri, id, line,
duraciones en nanosegundos). Uso: behave_to_cucumber.py <behave.json> <cucumber.json>
"""
import json
import re
import sys

STATUS = {"passed": "passed", "failed": "failed", "skipped": "skipped", "undefined": "undefined",
          "untested": "skipped", "executing": "skipped", "error": "failed", "hook_error": "failed"}


def slug(text):
    return re.sub(r"[^0-9a-z]+", "-", (text or "").lower()).strip("-") or "x"


def split_location(location, default_uri=""):
    if location and ":" in location:
        uri, _, line = location.rpartition(":")
        return uri, int(line) if line.isdigit() else 1
    return location or default_uri, 1


def text(value):
    return "\n".join(value) if isinstance(value, list) else (value or "")


def tags(values, line):
    return [{"name": t if str(t).startswith("@") else f"@{t}", "line": line} for t in values or []]


def convert(features):
    result = []
    for feature in features:
        uri, fline = split_location(feature.get("location"), feature.get("name", "feature"))
        fid = slug(feature.get("name"))
        out = {"uri": uri, "id": fid, "keyword": feature.get("keyword", "Característica"),
               "name": feature.get("name", ""), "line": fline, "description": text(feature.get("description")),
               "tags": tags(feature.get("tags"), fline), "elements": []}
        for element in feature.get("elements", []):
            kind = element.get("type", "scenario")
            if kind not in ("scenario", "scenario_outline", "background"):
                continue
            _, eline = split_location(element.get("location"))
            steps = []
            for step in element.get("steps", []):
                res = step.get("result", {})
                _, sline = split_location(step.get("location"))
                converted = {"keyword": step.get("keyword", "").strip() + " ", "name": step.get("name", ""),
                             "line": sline, "match": {"location": (step.get("match") or {}).get("location", "")},
                             "result": {"status": STATUS.get(res.get("status", "skipped"), "skipped"),
                                        "duration": int(float(res.get("duration") or 0) * 1_000_000_000)}}
                if res.get("error_message"):
                    converted["result"]["error_message"] = text(res["error_message"])
                steps.append(converted)
            out["elements"].append({
                "id": f"{fid};{slug(element.get('name'))}", "keyword": element.get("keyword", "Escenario"),
                "name": element.get("name", ""), "line": eline, "description": text(element.get("description")),
                "type": "background" if kind == "background" else "scenario",
                "tags": tags(element.get("tags"), eline), "steps": steps})
        result.append(out)
    return result


if __name__ == "__main__":
    source, target = sys.argv[1], sys.argv[2]
    with open(source, encoding="utf-8") as fh:
        data = json.load(fh)
    converted = convert(data)
    with open(target, "w", encoding="utf-8") as fh:
        json.dump(converted, fh, ensure_ascii=False, indent=2)
    scenarios = sum(len([e for e in f["elements"] if e["type"] == "scenario"]) for f in converted)
    print(f"Cucumber JSON: {len(converted)} características, {scenarios} escenarios -> {target}")
