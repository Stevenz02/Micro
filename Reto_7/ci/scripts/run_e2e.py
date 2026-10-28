#!/usr/bin/env python3
"""Espera un Gateway externo y ejecuta el runner BDD existente sin gestionar Docker."""

from __future__ import annotations

import os
import json
import math
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen


INFRASTRUCTURE_UNAVAILABLE = 20
RUNNER_UNAVAILABLE = 21


def positive_number(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser numérico, se recibió {raw!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} debe ser positivo")
    return value


def wait_for_gateway(base_url: str, path: str, timeout: float, interval: float, request_timeout: float) -> None:
    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("BASE_URL debe ser una URL HTTP(S) absoluta, sin query ni fragmento")
    target = base_url.rstrip("/") + "/" + path.lstrip("/")
    deadline = time.monotonic() + timeout
    attempts = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempts += 1
        try:
            with urlopen(target, timeout=request_timeout) as response:
                if response.status == 200:
                    try:
                        payload = json.loads(response.read().decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ValueError(f"{target} devolvió 200 sin JSON válido") from exc
                    if payload != {"status": "ok", "service": "api-gateway"}:
                        raise ValueError(f"{target} no corresponde al health esperado del API Gateway")
                    print(f"Gateway disponible en {target} después de {attempts} intento(s)")
                    return
                last_error = RuntimeError(f"HTTP {response.status}")
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(interval, remaining))
    raise TimeoutError(
        f"Gateway no disponible en {target} tras {attempts} intentos y {timeout:g} s; "
        f"último error: {last_error}"
    )


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    base_url = os.getenv("BASE_URL", "").strip()
    if not base_url:
        print("ERROR DE INFRAESTRUCTURA: falta BASE_URL para el Gateway externo", file=sys.stderr)
        return INFRASTRUCTURE_UNAVAILABLE
    try:
        wait_for_gateway(
            base_url,
            os.getenv("E2E_READY_PATH", "/health"),
            positive_number("E2E_READY_TIMEOUT_SECONDS", "60"),
            positive_number("E2E_READY_INTERVAL_SECONDS", "2"),
            positive_number("HTTP_TIMEOUT_SECONDS", "10"),
        )
    except (ValueError, TimeoutError) as exc:
        print(f"ERROR DE INFRAESTRUCTURA: {exc}", file=sys.stderr)
        return INFRASTRUCTURE_UNAVAILABLE
    runner = root / "Reto_6" / "e2e-tests" / "run.py"
    if not runner.is_file():
        print(f"ERROR DEL RUNNER E2E: no existe {runner}", file=sys.stderr)
        return RUNNER_UNAVAILABLE
    try:
        result = subprocess.run([sys.executable, str(runner)], cwd=runner.parent, check=False)
    except OSError as exc:
        print(f"ERROR DEL RUNNER E2E: {exc}", file=sys.stderr)
        return RUNNER_UNAVAILABLE
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

