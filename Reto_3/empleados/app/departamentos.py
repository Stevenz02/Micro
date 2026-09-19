import logging
import time
from urllib.parse import quote

import httpx
import pybreaker
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DepartamentosUnavailable(Exception):
    """Fallo tecnico definitivo al validar departamentos."""


class BreakerLogger(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "Circuit Breaker departamentos: %s -> %s",
            old_state.name.upper(),
            new_state.name.upper(),
        )


class DepartamentosClient:
    def __init__(self, settings, client, sleep=time.sleep, breaker=None):
        self.settings = settings
        self.client = client
        self.sleep = sleep
        self.breaker = breaker or pybreaker.CircuitBreaker(
            fail_max=settings.cb_fail_max,
            reset_timeout=settings.cb_reset_timeout,
            exclude=[HTTPException],
            listeners=[BreakerLogger()],
        )

    def estado(self):
        return {"dependency": "departamentos-service", "state": self.breaker.current_state}

    def validar(self, departamento_id):
        try:
            return self.breaker.call(self._validar_con_reintentos, departamento_id)
        except pybreaker.CircuitBreakerError as exc:
            raise HTTPException(
                503,
                "Departamentos no disponible por Circuit Breaker abierto; empleado no registrado",
            ) from exc
        except DepartamentosUnavailable as exc:
            raise HTTPException(
                503,
                "No se pudo validar el departamento; empleado no registrado. Intente mas tarde",
            ) from exc

    def _validar_con_reintentos(self, departamento_id):
        url = f"{self.settings.departamentos_url}/departamentos/{quote(departamento_id, safe='')}"
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.get(url, timeout=self.settings.timeout)
                if response.status_code == 404:
                    raise HTTPException(400, f"El departamento con id {departamento_id} no existe")
                if response.status_code == 200:
                    body = response.json()
                    if (
                        isinstance(body, dict)
                        and body.get("id") == departamento_id
                        and all(isinstance(body.get(key), str) for key in ("nombre", "descripcion"))
                    ):
                        return
                if response.status_code < 500 and response.status_code != 429:
                    break
            except (httpx.TimeoutException, httpx.TransportError):
                pass
            except ValueError:
                break
            if attempt < self.settings.max_retries:
                delay = self.settings.backoff * (2 ** attempt)
                logger.warning("Departamentos no disponible; reintento %s en %ss", attempt + 1, delay)
                self.sleep(delay)
        raise DepartamentosUnavailable()
