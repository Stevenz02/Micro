"""Declara de forma idempotente la topologia; no define payloads de eventos."""

import base64
import json
import os
import time
from urllib.request import Request, urlopen


BASE = "http://rabbitmq:15672/api"
AUTH = base64.b64encode(
    f"{os.environ['RABBITMQ_USER']}:{os.environ['RABBITMQ_PASSWORD']}".encode()
).decode()


def request(method, path, body):
    http_request = Request(
        BASE + path,
        data=json.dumps(body).encode(),
        method=method,
        headers={"Authorization": f"Basic {AUTH}", "Content-Type": "application/json"},
    )
    last_error = None
    for _ in range(30):
        try:
            with urlopen(http_request, timeout=10) as response:
                if response.status not in {201, 204}:
                    raise RuntimeError(f"RabbitMQ devolvio {response.status} para {path}")
                return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"No se pudo configurar RabbitMQ en {path}: {last_error}")


def put(path, body):
    request("PUT", path, body)


def post(path, body):
    request("POST", path, body)


put("/exchanges/%2F/rrhh.events", {"type": "topic", "durable": True, "auto_delete": False, "internal": False, "arguments": {}})

bindings = {
    "perfiles.events": ["empleado.creado", "empleado.actualizado", "empleado.retirado"],
    "notificaciones.events": ["empleado.creado", "empleado.retirado", "vacaciones.programadas"],
    "vacaciones.empleados": ["empleado.creado", "empleado.retirado"],
}
for queue, routing_keys in bindings.items():
    put(f"/queues/%2F/{queue}", {"durable": True, "auto_delete": False, "arguments": {}})
    for routing_key in routing_keys:
        post(
            f"/bindings/%2F/e/rrhh.events/q/{queue}",
            {"routing_key": routing_key, "arguments": {}},
        )
