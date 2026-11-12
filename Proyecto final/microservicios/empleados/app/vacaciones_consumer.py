"""Consumidor de vacaciones.iniciadas / vacaciones.finalizadas.

Mantiene el estado del empleado (ACTIVO <-> EN_VACACIONES) en la fuente de verdad de RR. HH.
Es asíncrono (RabbitMQ, cola empleados.vacaciones) e idempotente: el id del envelope se guarda
en eventos_procesados dentro de la misma transacción que cambia el estado.
"""

import json
import logging
import os
import threading
import uuid

import pika

from shared.observability import consume_span

logger = logging.getLogger(__name__)
QUEUE = "empleados.vacaciones"
PRODUCER = "vacaciones-service"
INICIA = {"vacaciones.iniciadas": True, "vacaciones.finalizadas": False}


def procesar(repository, body: bytes) -> bool:
    """Valida el envelope del catálogo y aplica la transición. False si era un duplicado."""
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("Envelope inválido")
    event_id = str(uuid.UUID(str(payload.get("id"))))
    event_type = payload.get("type")
    if event_type not in INICIA:
        raise ValueError("Tipo de evento no soportado")
    if type(payload.get("version")) is not int or payload["version"] != 1:
        raise ValueError("Versión de evento inválida")
    if payload.get("producer") != PRODUCER:
        raise ValueError("Productor de evento inválido")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ValueError("data debe ser un objeto")
    empleado_id = data.get("empleadoId")
    if not isinstance(empleado_id, str) or not empleado_id.strip():
        raise ValueError("Falta empleadoId")

    nuevo, empleado = repository.aplicar_vacaciones(event_id, empleado_id.strip(), INICIA[event_type])
    if not nuevo:
        logger.info("evento_duplicado id=%s type=%s", event_id, event_type)
        return False
    if empleado is None:
        # Retirado, pendiente o fuera de orden: el evento queda registrado y no cambia nada
        logger.info("evento_sin_cambio id=%s type=%s", event_id, event_type,
                    extra={"employeeId": empleado_id, "eventType": event_type})
    else:
        logger.info("Estado de empleado actualizado a %s", empleado.estado,
                    extra={"employeeId": empleado.id, "eventType": event_type})
    return True


class VacacionesConsumer:
    def __init__(self, repository):
        self.repository = repository
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="empleados-vacaciones", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)

    def _run(self):  # pragma: no cover - bucle de E/S contra RabbitMQ, cubierto por las pruebas E2E
        while not self.stop_event.is_set():
            try:
                params = pika.ConnectionParameters(
                    host=os.environ["RABBITMQ_HOST"],
                    credentials=pika.PlainCredentials(os.environ["RABBITMQ_USER"],
                                                      os.environ["RABBITMQ_PASSWORD"]),
                    heartbeat=30,
                    blocked_connection_timeout=5,
                    socket_timeout=5,
                )
                connection = pika.BlockingConnection(params)
                try:
                    channel = connection.channel()
                    channel.basic_qos(prefetch_count=1)
                    logger.info("Consumidor de vacaciones conectado a %s", QUEUE)
                    for method, properties, body in channel.consume(QUEUE, inactivity_timeout=1):
                        if self.stop_event.is_set():
                            break
                        if method is None:
                            continue
                        with consume_span(QUEUE, method.routing_key, properties.headers):
                            try:
                                procesar(self.repository, body)
                                channel.basic_ack(method.delivery_tag)
                            except (ValueError, json.JSONDecodeError, UnicodeError) as exc:
                                logger.error("evento_invalido tag=%s error=%s", method.delivery_tag, exc)
                                channel.basic_reject(method.delivery_tag, requeue=False)
                            except Exception:
                                logger.exception("evento_no_procesado tag=%s", method.delivery_tag)
                                channel.basic_nack(method.delivery_tag, requeue=True)
                    channel.cancel()
                finally:
                    if connection.is_open:
                        connection.close()
            except Exception:
                if not self.stop_event.is_set():
                    logger.exception("Consumidor de vacaciones desconectado; reintentando")
                    self.stop_event.wait(2)
