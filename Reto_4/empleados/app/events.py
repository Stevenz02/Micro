"""Publicación AMQP según el Catálogo de Eventos del Ecosistema, versión 1."""

import json
import os
import uuid
from datetime import datetime, timezone

import pika


EXCHANGE = "rrhh.events"
PRODUCER = "empleados-service"


def utc_iso(value):
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def envelope(event_type, data):
    return {
        "id": str(uuid.uuid4()),
        "type": event_type,
        "version": 1,
        "occurredAt": utc_iso(datetime.now(timezone.utc)),
        "producer": PRODUCER,
        "data": data,
    }


def created_data(empleado):
    return {
        "empleadoId": empleado.id,
        "nombre": empleado.nombre,
        "apellido": empleado.apellido,
        "email": empleado.email,
        "numeroEmpleado": empleado.numeroEmpleado,
        "cargo": empleado.cargo,
        "area": empleado.area,
        "departamentoId": empleado.departamentoId,
        "fechaIngreso": empleado.fechaIngreso.isoformat(),
        "estado": "ACTIVO",
    }


def updated_data(empleado):
    return {
        "empleadoId": empleado.id,
        "nombre": empleado.nombre,
        "apellido": empleado.apellido,
        "email": empleado.email,
        "cargo": empleado.cargo,
        "area": empleado.area,
        "departamentoId": empleado.departamentoId,
    }


def retired_data(empleado, motivo):
    return {
        "empleadoId": empleado.id,
        "email": empleado.email,
        "fechaRetiro": utc_iso(empleado.fechaRetiro),
        "motivo": motivo,
    }


class RabbitPublisher:
    def __init__(self):
        self.host = os.environ["RABBITMQ_HOST"]
        self.user = os.environ["RABBITMQ_USER"]
        self.password = os.environ["RABBITMQ_PASSWORD"]

    def publish(self, event_type, data):
        message = envelope(event_type, data)
        params = pika.ConnectionParameters(
            host=self.host,
            credentials=pika.PlainCredentials(self.user, self.password),
            heartbeat=30,
            blocked_connection_timeout=5,
            socket_timeout=5,
            connection_attempts=3,
            retry_delay=2,
        )
        connection = pika.BlockingConnection(params)
        try:
            channel = connection.channel()
            channel.confirm_delivery()
            channel.basic_publish(
                exchange=EXCHANGE,
                routing_key=event_type,
                body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=message["id"],
                    type=event_type,
                ),
                mandatory=True,
            )
        finally:
            if connection.is_open:
                connection.close()
        return message
