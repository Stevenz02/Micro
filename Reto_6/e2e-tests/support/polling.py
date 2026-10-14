"""Espera acotada con reloj monotónico para proyecciones asíncronas."""

import time

import httpx


def wait_until(predicate, description, *, timeout, interval, max_attempts):
    if timeout <= 0 or interval <= 0 or max_attempts < 1:
        raise ValueError("Los límites de polling deben ser positivos")
    deadline = time.monotonic() + timeout
    last_error = None
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            value = predicate()
            if value:
                return value
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
        remaining = deadline - time.monotonic()
        if remaining <= 0 or attempts >= max_attempts:
            break
        time.sleep(min(interval, remaining))
    detail = f"; último error transitorio: {last_error}" if last_error else ""
    raise AssertionError(
        f"No se cumplió '{description}' en {attempts} intentos y {timeout:g} s{detail}"
    )
