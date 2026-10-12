"""Un comando BDD: Behave, JUnit consolidado, Cucumber JSON y HTML."""

import html
import json
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def consolidate_junit():
    suites = ET.Element("testsuites")
    counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    for file in sorted((REPORTS / "junit_raw").glob("*.xml")):
        root = ET.parse(file).getroot()
        items = [root] if root.tag == "testsuite" else root.findall("testsuite")
        for item in items:
            suites.append(item)
            for key in counts:
                counts[key] += int(item.get(key, "0"))
    for key, count in counts.items():
        suites.set(key, str(count))
    ET.indent(suites, space="  ")
    ET.ElementTree(suites).write(REPORTS / "junit.xml", encoding="utf-8", xml_declaration=True)


def render_html(features):
    scenario_count = 0
    step_count = 0
    cards = []
    for feature in features:
        scenario_cards = []
        for scenario in feature.get("elements", []):
            if scenario.get("type") not in {"scenario", "scenario_outline"}:
                continue
            scenario_count += 1
            steps = []
            statuses = []
            duration = 0.0
            for step in scenario.get("steps", []):
                step_count += 1
                result = step.get("result", {})
                status = result.get("status", "skipped")
                statuses.append(status)
                duration += float(result.get("duration", 0) or 0)
                message = result.get("error_message", "")
                if isinstance(message, list):
                    message = "\n".join(message)
                detail = f"<pre>{html.escape(str(message))}</pre>" if message else ""
                steps.append(
                    f'<li class="{html.escape(status)}"><span>{html.escape(step.get("keyword", ""))}'
                    f'{html.escape(step.get("name", ""))}</span><small>{html.escape(status)}'
                    f' · {float(result.get("duration", 0) or 0):.3f} s</small>{detail}</li>'
                )
            outcome = "failed" if any(s in {"failed", "undefined", "error"} for s in statuses) else (
                "passed" if statuses and all(s == "passed" for s in statuses) else "skipped"
            )
            scenario_cards.append(
                f'<article class="scenario {outcome}"><h3>{html.escape(scenario.get("name", ""))}'
                f'<small>{outcome} · {duration:.3f} s</small></h3><ol>{"".join(steps)}</ol></article>'
            )
        cards.append(f'<section><h2>{html.escape(feature.get("name", ""))}</h2>{"".join(scenario_cards)}</section>')
    page = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Reto 6 · Reporte BDD</title><style>
body{{font:16px system-ui,sans-serif;background:#f5f7fb;color:#1d2939;max-width:1100px;margin:40px auto;padding:0 20px}}
h1{{margin-bottom:4px}}p{{color:#475467}}section{{margin:32px 0}}article{{background:white;border:1px solid #d0d5dd;
border-left:6px solid #98a2b3;border-radius:8px;margin:12px 0;padding:8px 20px}}
article.passed{{border-left-color:#12b76a}}article.failed{{border-left-color:#f04438}}article h3{{display:flex;justify-content:space-between;gap:20px}}
small{{font-size:.82rem;color:#475467;font-weight:normal}}ol{{list-style:none;padding:0}}li{{padding:8px;border-top:1px solid #eaecf0;
display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px}}li.failed{{color:#b42318}}li.passed{{color:#027a48}}
pre{{flex-basis:100%;white-space:pre-wrap;background:#fff3f1;color:#912018;padding:12px;overflow:auto}}
</style></head><body><h1>Reto 6 · Pruebas BDD</h1><p>{len(features)} características · {scenario_count} escenarios · {step_count} pasos</p>
{"".join(cards)}</body></html>"""
    (REPORTS / "cucumber.html").write_text(page, encoding="utf-8")


def main():
    load_dotenv(ROOT / ".env")
    REPORTS.mkdir(exist_ok=True)
    raw = REPORTS / "junit_raw"
    raw.mkdir(exist_ok=True)
    for file in raw.glob("*.xml"):
        file.unlink()
    for name in ("junit.xml", "cucumber.json", "cucumber.html"):
        (REPORTS / name).unlink(missing_ok=True)
    command = [
        sys.executable, "-m", "behave", "--junit", "--junit-directory", str(raw),
        "--logging-level", "ERROR", "-f", "json.pretty", "-o", str(REPORTS / "cucumber.json"),
        "-f", "progress",
        *(sys.argv[1:] or ["features"]),
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if list(raw.glob("*.xml")):
        consolidate_junit()
    json_file = REPORTS / "cucumber.json"
    if json_file.exists():
        render_html(json.loads(json_file.read_text(encoding="utf-8")))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
