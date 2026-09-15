import logging
import time
from urllib.parse import quote

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class DepartamentosClient:
    def __init__(self, settings, client, sleep=time.sleep):
        self.settings = settings
        self.client = client
        self.sleep = sleep

    def validar(self, departamento_id):
        url = f"{self.settings.departamentos_url}/departamentos/{quote(departamento_id, safe='')}"
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.get(url, timeout=self.settings.timeout)
                if response.status_code == 404:
                    raise HTTPException(400, f"El departamento con id {departamento_id} no existe")
                if response.status_code == 200:
                    body = response.json()
                    if (isinstance(body, dict) and body.get("id") == departamento_id
                            and all(isinstance(body.get(key), str) for key in ("nombre", "descripcion"))):
                        return
                # Solo errores transitorios se reintentan. Un 2xx inválido o un
                # 4xx diferente a 429 indica un contrato/configuración incorrecto.
                if response.status_code < 500 and response.status_code != 429:
                    break
            except (httpx.TimeoutException, httpx.TransportError):
                pass
            except ValueError:  # Respuesta 200 con JSON inválido: no validar a ciegas.
                break
            if attempt < self.settings.max_retries:
                delay = self.settings.backoff * (2 ** attempt)
                logger.warning("Departamentos no disponible; reintento %s en %ss", attempt + 1, delay)
                self.sleep(delay)
        raise HTTPException(503, "No se pudo validar el departamento; empleado no registrado. Intente más tarde")
