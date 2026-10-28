#!/usr/bin/env python3
"""Auditoría estática de contratos CI; no sustituye el parser declarativo de Jenkins."""

from __future__ import annotations

import re
import sys
from pathlib import Path


SERVICES = (
    "empleados", "auth", "api-gateway", "departamentos", "perfiles", "notificaciones", "vacaciones",
)
REQUIRED_STAGES = (
    "Checkout", "Build", "Test + Coverage", "SonarQube Analysis", "Quality Gate", "Package", "E2E Tests",
)
EXPECTED_KEYS = {service: f"uq-reto7-{service}" for service in SERVICES}
SOURCE_PATHS = {
    "empleados": ("Reto_4/empleados/app", "Reto_4/tests"),
    "auth": ("Reto_5/auth/auth_app", "Reto_5/shared", "Reto_5/tests"),
    "api-gateway": ("Reto_5/api-gateway/gateway_app", "Reto_5/tests"),
    "departamentos": ("Reto_4/departamentos/src", "Reto_4/departamentos/tests"),
    "perfiles": ("Reto_4/perfiles",),
    "notificaciones": ("Reto_5/notificaciones/src/main/java", "Reto_5/notificaciones/src/test/java"),
    "vacaciones": ("Reto_5/vacaciones", "Reto_5/vacaciones.tests"),
}
REPORT_TOKENS = {
    "empleados": ("Reto_4/empleados/reports/junit.xml", "Reto_4/empleados/reports/coverage.xml"),
    "auth": ("Reto_5/auth/reports/junit.xml", "Reto_5/auth/reports/coverage.xml"),
    "api-gateway": ("Reto_5/api-gateway/reports/junit.xml", "Reto_5/api-gateway/reports/coverage.xml"),
    "departamentos": ("Reto_4/departamentos/reports/junit.xml", "Reto_4/departamentos/coverage/lcov.info"),
    "perfiles": ("Reto_4/perfiles/reports/junit.xml", "Reto_4/perfiles/reports/coverage.xml"),
    "notificaciones": ("Reto_5/notificaciones/target/surefire-reports/TEST-*.xml", "target/site/jacoco/jacoco.xml"),
    "vacaciones": ("Reto_5/vacaciones.tests/reports/vacaciones.trx", "reports/coverage.opencover.xml"),
}


def _properties(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path.name}:{number}: propiedad inválida")
        key, value = line.split("=", 1)
        if not key.strip() or not value.strip():
            raise ValueError(f"{path.name}:{number}: propiedad vacía")
        result[key.strip()] = value.strip()
    return result


def verify(root: Path) -> list[str]:
    errors: list[str] = []
    jenkins_dir = root / "Reto_7" / "jenkins"
    for service in SERVICES:
        path = jenkins_dir / f"Jenkinsfile.{service}"
        if not path.is_file():
            errors.append(f"Falta {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        if not text.lstrip().startswith("pipeline {"):
            errors.append(f"{path.name}: no inicia como pipeline declarativo")
        positions = [text.find(f"stage('{stage}')") for stage in REQUIRED_STAGES]
        for stage, position in zip(REQUIRED_STAGES, positions):
            if position < 0:
                errors.append(f"{path.name}: falta etapa {stage}")
        if all(position >= 0 for position in positions) and positions != sorted(positions):
            errors.append(f"{path.name}: las etapas no siguen el flujo requerido")
        required_tokens = (
            "disableConcurrentBuilds()", "post {", "always {", "waitForQualityGate abortPipeline: true",
            "recordCoverage", "propagate: true", "COMPONENT_ID", "SOURCE_DIR", "SOURCE_BUILD",
            "booleanParam(name: 'RUN_PACKAGE', defaultValue: false",
            "booleanParam(name: 'TRIGGER_E2E', defaultValue: false",
        ) + REPORT_TOKENS[service]
        for token in required_tokens:
            if token not in text:
                errors.append(f"{path.name}: falta contrato {token}")
        for source in SOURCE_PATHS[service]:
            if not (root / source).exists():
                errors.append(f"{path.name}: ruta física inexistente {source}")
        if re.search(r"\b(docker|podman)\b", text, re.IGNORECASE):
            errors.append(f"{path.name}: contiene una operación de contenedores prohibida")
        if "|| true" in text or "allowEmptyResults: true" in text or "allowEmptyArchive: true" in text:
            errors.append(f"{path.name}: contiene una tolerancia que puede ocultar evidencia ausente")
        if text.count("{") != text.count("}"):
            errors.append(f"{path.name}: llaves desbalanceadas")
        if service in {"perfiles", "notificaciones"} and "junit_status.py" not in text:
            errors.append(f"{path.name}: debe validar JUnit antes de continuar a SonarQube")

    integration = jenkins_dir / "Jenkinsfile.integration"
    if not integration.is_file():
        errors.append("Falta Jenkinsfile.integration")
    else:
        text = integration.read_text(encoding="utf-8")
        for token in (
            "disableConcurrentBuilds()", "run_e2e.py", "junit ", "cucumber ", "publishHTML",
            "BDD_REPORTS_EXPECTED", "status == 20", "status == 21", "reto7-e2e-admin",
        ):
            if token not in text:
                errors.append(f"Jenkinsfile.integration: falta {token}")
        if re.search(r"\b(docker|podman)\b", text, re.IGNORECASE):
            errors.append("Jenkinsfile.integration contiene una operación de contenedores prohibida")
        if "allowEmptyResults: true" in text or "allowEmptyArchive: true" in text:
            errors.append("Jenkinsfile.integration permite evidencia vacía")
        if text.count("{") != text.count("}"):
            errors.append("Jenkinsfile.integration: llaves desbalanceadas")

    sonar_dir = root / "Reto_7" / "ci" / "config" / "sonar"
    found_keys: dict[str, Path] = {}
    for service in SERVICES[:-1]:
        path = sonar_dir / f"{service}.properties"
        if not path.is_file():
            errors.append(f"Falta configuración Sonar {path.name}")
            continue
        try:
            props = _properties(path)
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        key = props.get("sonar.projectKey", "")
        if key != EXPECTED_KEYS[service]:
            errors.append(f"{path.name}: projectKey esperado {EXPECTED_KEYS[service]}, recibido {key!r}")
        if key in found_keys:
            errors.append(f"Project key duplicado {key}: {found_keys[key].name} y {path.name}")
        found_keys[key] = path
        for property_name in ("sonar.sources", "sonar.tests"):
            for item in props.get(property_name, "").split(","):
                if not item or not (root / item).exists():
                    errors.append(f"{path.name}: {property_name} apunta a ruta inexistente {item!r}")
        if any("token" in key.lower() or "password" in key.lower() for key in props):
            errors.append(f"{path.name}: no debe declarar credenciales")

    vacation_text = (jenkins_dir / "Jenkinsfile.vacaciones").read_text(encoding="utf-8")
    for token in (
        EXPECTED_KEYS["vacaciones"], "dotnet sonarscanner begin", "dotnet sonarscanner end",
        "sonar.cs.opencover.reportsPaths", "sonar.cs.vstest.reportsPaths", "SONAR_AUTH_TOKEN",
    ):
        if token not in vacation_text:
            errors.append(f"Jenkinsfile.vacaciones: falta configuración Sonar {token}")
    if set(found_keys) != {EXPECTED_KEYS[service] for service in SERVICES[:-1]}:
        errors.append("Las seis configuraciones SonarScanner CLI no tienen exactamente las llaves esperadas")

    docs = root / "Reto_7" / "docs" / "INTEGRACION_INFRAESTRUCTURA.md"
    if docs.is_file():
        doc_text = docs.read_text(encoding="utf-8")
        for name in (*SERVICES, "integration"):
            script_path = f"Reto_7/jenkins/Jenkinsfile.{name}"
            if script_path not in doc_text:
                errors.append(f"INTEGRACION_INFRAESTRUCTURA.md: falta Script Path {script_path}")
    else:
        errors.append("Falta INTEGRACION_INFRAESTRUCTURA.md")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    errors = verify(root)
    if errors:
        print("Configuración CI inválida:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Configuración CI verificada estáticamente: 7 pipelines, 1 E2E y 7 project keys.")
    print("Esta revisión no sustituye Jenkins Declarative Linter ni una ejecución real de SonarQube.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
