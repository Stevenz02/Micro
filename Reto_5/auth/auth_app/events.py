"""Contratos del Catálogo de Eventos del Ecosistema, versión 1, secciones 2 y 3."""

import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pika

from shared.tokens import issue_reset, validate_reset

from .repository import ACTIVE


logger = logging.getLogger(__name__)
EXCHANGE = "rrhh.events"
QUEUE = "auth.events"
PRODUCER = "auth-service"
INPUT_PRODUCERS = {
    "empleado.creado": "empleados-service",
    "empleado.retirado": "empleados-service",
    "vacaciones.iniciadas": "vacaciones-service",
    "vacaciones.finalizadas": "vacaciones-service",
}


def build_envelope(event_type: str, data: dict, event_id: uuid.UUID | None = None,
                   occurred_at: datetime | None = None) -> dict:
    return {
        "id": str(event_id or uuid.uuid4()),
        "type": event_type,
        "version": 1,
        "occurredAt": utc_text(occurred_at or datetime.now(timezone.utc)),
        "producer": PRODUCER,
        "data": data,
    }


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def reset_expiration(token: str, secret: str) -> str:
    expiry = validate_reset(token, secret)["exp"]
    return utc_text(datetime.fromtimestamp(expiry, timezone.utc))


def required_text(data: dict, field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Falta {field}")
    return value.strip()


def utc_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("La fecha debe estar en UTC")
    return parsed


@dataclass(frozen=True)
class IncomingEvent:
    id: uuid.UUID
    type: str
    data: dict

    @classmethod
    def from_bytes(cls, body: bytes):
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError("Envelope inválido")
        event_id = uuid.UUID(required_text(payload, "id"))
        event_type = required_text(payload, "type")
        if event_type not in INPUT_PRODUCERS:
            raise ValueError("Tipo de evento no soportado")
        if type(payload.get("version")) is not int or payload["version"] != 1:
            raise ValueError("Versión de evento inválida")
        if required_text(payload, "producer") != INPUT_PRODUCERS[event_type]:
            raise ValueError("Productor de evento inválido")
        utc_datetime(required_text(payload, "occurredAt"))
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("data debe ser un objeto")
        required_text(data, "empleadoId")
        required_text(data, "email")
        if event_type == "empleado.creado":
            for key in ("nombre", "apellido", "numeroEmpleado", "cargo", "area", "departamentoId"):
                required_text(data, key)
            date.fromisoformat(required_text(data, "fechaIngreso"))
            if data.get("estado") != "ACTIVO":
                raise ValueError("Estado inicial inválido")
        elif event_type == "empleado.retirado":
            utc_datetime(required_text(data, "fechaRetiro"))
            required_text(data, "motivo")
        else:
            required_text(data, "vacacionesId")
            date.fromisoformat(required_text(data, "fechaFin"))
            if event_type == "vacaciones.iniciadas":
                date.fromisoformat(required_text(data, "fechaInicio"))
        return cls(event_id, event_type, data)


class RabbitPublisher:
    def __init__(self):
        self.host = os.environ["RABBITMQ_HOST"]
        self.user = os.environ["RABBITMQ_USER"]
        self.password = os.environ["RABBITMQ_PASSWORD"]

    def publish(self, event_type: str, data: dict):
        envelope = build_envelope(event_type, data)
        event_id = envelope["id"]
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
                body=json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
                properties=pika.BasicProperties(content_type="application/json", delivery_mode=2,
                                                message_id=event_id, type=event_type),
                mandatory=True,
            )
        finally:
            if connection.is_open:
                connection.close()
        return envelope


class EventProcessor:
    def __init__(self, repository, publisher, secret: str, reset_ttl_seconds: int):
        self.repository = repository
        self.publisher = publisher
        self.secret = secret
        self.reset_ttl_seconds = reset_ttl_seconds

    def process(self, body: bytes):
        event = IncomingEvent.from_bytes(body)
        changed, account = self.repository.apply_event(event)
        if not changed:
            logger.info("evento_duplicado_o_sin_cambio id=%s type=%s", event.id, event.type)
            return False
        data = None
        outgoing = None
        if event.type == "empleado.creado":
            token = issue_reset(self.secret, account.employee_id, account.credential_version,
                                self.reset_ttl_seconds)
            outgoing = "usuario.creado"
            data = {"empleadoId": account.employee_id, "email": account.email,
                    "tokenActivacion": token, "expiraEn": reset_expiration(token, self.secret)}
        elif event.type == "empleado.retirado":
            outgoing = "cuenta.desactivada"
            data = {"empleadoId": account.employee_id, "email": event.data["email"],
                    "motivo": "RETIRO", "permanente": True}
        elif event.type == "vacaciones.iniciadas":
            outgoing = "cuenta.desactivada"
            data = {"empleadoId": account.employee_id, "email": event.data["email"],
                    "motivo": "VACACIONES", "permanente": False}
        elif event.type == "vacaciones.finalizadas" and account.status == ACTIVE:
            outgoing = "cuenta.activada"
            data = {"empleadoId": account.employee_id, "email": event.data["email"],
                    "motivo": "FIN_VACACIONES"}
        if outgoing:
            try:
                self.publisher.publish(outgoing, data)
            except Exception:
                logger.exception("No se pudo publicar %s tras commit del evento %s", outgoing, event.id)
        logger.info("evento_procesado id=%s type=%s", event.id, event.type)
        return True


class EventConsumer:
    def __init__(self, processor: EventProcessor):
        self.processor = processor
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name="auth-events", daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=3)

    def _run(self):
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
                    logger.info("Consumidor Auth conectado a %s", QUEUE)
                    for method, _properties, body in channel.consume(QUEUE, inactivity_timeout=1):
                        if self.stop_event.is_set():
                            break
                        if method is None:
                            continue
                        try:
                            self.processor.process(body)
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
                    logger.exception("Consumidor Auth desconectado; reintentando")
                    self.stop_event.wait(2)
