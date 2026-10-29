#!/usr/bin/env python3
"""Configura SonarQube sin pasos manuales (Punto 3). Es idempotente: puede correr en cada `up`.

1. Espera a que SonarQube esté UP.
2. Cambia la contraseña por defecto admin/admin por SONAR_ADMIN_PASSWORD.
3. Genera (o reutiliza si sigue siendo válido) el token de análisis y lo escribe en
   /run/reto7/sonar-token, que Jenkins lee con JCasC (${readFile:...}). Nunca se versiona.
4. Crea el Quality Gate "Reto 7 - Cobertura 70" (cobertura >= 70 %) y lo deja por defecto.
5. Crea los 7 proyectos con los project keys de Kevin y les asigna el gate.
6. Crea el webhook SonarQube -> Jenkins que necesita waitForQualityGate.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

URL = os.environ.get("SONAR_URL", "http://sonarqube:9000").rstrip("/")
ADMIN_PASSWORD = os.environ["SONAR_ADMIN_PASSWORD"]
TOKEN_FILE = os.environ.get("TOKEN_FILE", "/run/reto7/sonar-token")
TOKEN_NAME = "jenkins-reto7"
WEBHOOK_URL = os.environ.get("JENKINS_WEBHOOK_URL", "http://jenkins:8080/sonarqube-webhook/")
GATE = os.environ.get("SONAR_GATE_NAME", "Reto 7 - Cobertura 70")
MIN_COVERAGE = os.environ.get("SONAR_MIN_COVERAGE", "70")

# Condiciones del gate: cobertura global (lo que pide el reto) + las de código nuevo de "Sonar way"
CONDITIONS = [
    ("coverage", "LT", MIN_COVERAGE),
    ("new_coverage", "LT", MIN_COVERAGE),
    ("new_duplicated_lines_density", "GT", "3"),
    ("new_reliability_rating", "GT", "1"),      # 0 bugs nuevos (calificación A)
    ("new_security_rating", "GT", "1"),         # 0 vulnerabilidades nuevas (A)
    ("new_maintainability_rating", "GT", "1"),  # mantenibilidad A
]

PROJECTS = [
    ("uq-reto7-empleados", "Reto 7 - Empleados"),
    ("uq-reto7-auth", "Reto 7 - Auth"),
    ("uq-reto7-api-gateway", "Reto 7 - API Gateway"),
    ("uq-reto7-departamentos", "Reto 7 - Departamentos"),
    ("uq-reto7-perfiles", "Reto 7 - Perfiles"),
    ("uq-reto7-notificaciones", "Reto 7 - Notificaciones"),
    ("uq-reto7-vacaciones", "Reto 7 - Vacaciones"),
]


def log(msg):
    print(f"[sonar-init] {msg}", flush=True)


def basic(user, password=""):
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()


def call(method, path, params=None, auth=None):
    params = params or {}
    query = urllib.parse.urlencode(params)
    url = URL + path + (f"?{query}" if method == "GET" and query else "")
    data = query.encode() if method == "POST" else None
    req = urllib.request.Request(url, data=data, method=method)
    if auth:
        req.add_header("Authorization", auth)
    if data is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body.strip() else {})
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            return exc.code, json.loads(body)
        except ValueError:
            return exc.code, {"raw": body.decode(errors="replace")}


def wait_until_up(timeout=900):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, body = call("GET", "/api/system/status")
            if status == 200 and body.get("status") == "UP":
                log("SonarQube está UP")
                return
            log(f"SonarQube aún no está listo ({body.get('status', status)})")
        except (urllib.error.URLError, OSError) as exc:
            log(f"SonarQube no responde todavía: {exc}")
        time.sleep(5)
    sys.exit("SonarQube no estuvo UP a tiempo")


def logged_in(auth):
    status, body = call("GET", "/api/users/current", auth=auth)
    return status == 200 and body.get("isLoggedIn") is True


def admin_auth():
    auth = basic("admin", ADMIN_PASSWORD)
    if logged_in(auth):
        log("La contraseña de admin ya estaba cambiada")
        return auth
    default = basic("admin", "admin")
    if not logged_in(default):
        sys.exit("No se pudo entrar ni con SONAR_ADMIN_PASSWORD ni con admin/admin")
    status, body = call("POST", "/api/users/change_password",
                        {"login": "admin", "previousPassword": "admin", "password": ADMIN_PASSWORD}, default)
    if status not in (200, 204):
        sys.exit(f"No se pudo cambiar la contraseña de admin: {status} {body}")
    log("Contraseña por defecto de admin cambiada")
    return auth


def ensure_token(auth):
    if os.path.exists(TOKEN_FILE):
        token = open(TOKEN_FILE, encoding="utf-8").read().strip()
        status, body = call("GET", "/api/authentication/validate", auth=basic(token))
        if token and status == 200 and body.get("valid") and logged_in(basic(token)):
            log("Token existente sigue siendo válido; se reutiliza")
            return
    call("POST", "/api/user_tokens/revoke", {"name": TOKEN_NAME}, auth)
    status, body = call("POST", "/api/user_tokens/generate", {"name": TOKEN_NAME}, auth)
    if status != 200 or "token" not in body:
        sys.exit(f"No se pudo generar el token: {status} {body}")
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as fh:
        fh.write(body["token"])          # sin salto de línea: Jenkins lo lee tal cual
    os.chmod(TOKEN_FILE, 0o644)
    log(f"Token '{TOKEN_NAME}' generado y guardado en {TOKEN_FILE}")


def ensure_gate(auth):
    status, body = call("GET", "/api/qualitygates/show", {"name": GATE}, auth)
    if status != 200:
        status, body = call("POST", "/api/qualitygates/create", {"name": GATE}, auth)
        if status != 200:
            sys.exit(f"No se pudo crear el Quality Gate: {status} {body}")
        log(f"Quality Gate '{GATE}' creado")
        status, body = call("GET", "/api/qualitygates/show", {"name": GATE}, auth)
    existing = {c.get("metric"): c for c in body.get("conditions", [])}
    for metric, op, error in CONDITIONS:
        current = existing.get(metric)
        if current and str(current.get("error")) == str(error) and current.get("op") == op:
            continue
        if current:
            call("POST", "/api/qualitygates/delete_condition", {"id": current["id"]}, auth)
        status, resp = call("POST", "/api/qualitygates/create_condition",
                            {"gateName": GATE, "metric": metric, "op": op, "error": error}, auth)
        if status != 200:
            log(f"ADVERTENCIA: no se pudo crear la condición {metric} {op} {error}: {status} {resp}")
        else:
            log(f"Condición {metric} {op} {error}")
    call("POST", "/api/qualitygates/set_as_default", {"name": GATE}, auth)
    log(f"'{GATE}' es el Quality Gate por defecto")


def ensure_projects(auth):
    for key, name in PROJECTS:
        status, body = call("POST", "/api/projects/create", {"project": key, "name": name}, auth)
        if status == 200:
            log(f"Proyecto {key} creado")
        call("POST", "/api/qualitygates/select", {"gateName": GATE, "projectKey": key}, auth)


def ensure_webhook(auth):
    status, body = call("GET", "/api/webhooks/list", auth=auth)
    if any(w.get("url") == WEBHOOK_URL for w in body.get("webhooks", [])):
        log("Webhook a Jenkins ya existe")
        return
    status, body = call("POST", "/api/webhooks/create", {"name": "Jenkins Reto 7", "url": WEBHOOK_URL}, auth)
    if status != 200:
        sys.exit(f"No se pudo crear el webhook: {status} {body}")
    log(f"Webhook creado -> {WEBHOOK_URL}")


if __name__ == "__main__":
    wait_until_up()
    auth = admin_auth()
    ensure_token(auth)
    ensure_gate(auth)
    ensure_projects(auth)
    ensure_webhook(auth)
    log("SonarQube configurado")
