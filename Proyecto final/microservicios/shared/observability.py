"""Reto 8 - Observabilidad común de los servicios Python (gateway, auth, empleados).

Reúne los tres pilares en un solo módulo para no repetir código en cada servicio:
  * Métricas  -> prometheus-fastapi-instrumentator expone GET /metrics (formato Prometheus).
  * Trazas    -> OpenTelemetry SDK + exportador Zipkin (OTEL_EXPORTER_ZIPKIN_ENDPOINT) y
                 propagación W3C (OTEL_PROPAGATORS=tracecontext,baggage).
  * Logs      -> JsonFormatter: una línea JSON por evento con timestamp, level, service,
                 traceId y message (Promtail los recoge de stdout y los envía a Loki).
Además: /health con el formato del reto y ayudas para propagar el contexto por RabbitMQ.
"""

from __future__ import annotations

import json
import logging
import os
import socket
from contextlib import contextmanager
from datetime import datetime, timezone

from opentelemetry import propagate, trace
from opentelemetry.trace import SpanKind, Status, StatusCode

SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "python-service")
EXCHANGE = "rrhh.events"

_STANDARD_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "color_message"}


# --------------------------------------------------------------------------- logs
class JsonFormatter(logging.Formatter):
    """Formatter JSON con los campos mínimos exigidos por el reto (y los extra=...)."""

    def format(self, record: logging.LogRecord) -> str:
        ctx = trace.get_current_span().get_span_context()
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc)
            .isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "traceId": format(ctx.trace_id, "032x") if ctx.is_valid else None,
            "spanId": format(ctx.span_id, "016x") if ctx.is_valid else None,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class NoiseFilter(logging.Filter):
    """Descarta del access log las sondas periódicas (/health cada 5 s y /metrics cada 15 s)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(f"{path} HTTP" in message for path in ("/health", "/metrics"))


# ------------------------------------------------------------------ trazas + métricas
def setup_observability(app, *, instrument_httpx: bool = False) -> None:
    """Configura OpenTelemetry (Zipkin) y expone /metrics. Llamar justo después de crear la app."""
    if os.getenv("OTEL_SDK_DISABLED", "false").lower() != "true":
        from opentelemetry.exporter.zipkin.json import ZipkinExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            provider = TracerProvider(resource=Resource.create({"service.name": SERVICE_NAME}))
            # El endpoint sale de OTEL_EXPORTER_ZIPKIN_ENDPOINT (http://zipkin:9411/api/v2/spans)
            provider.add_span_processor(BatchSpanProcessor(ZipkinExporter()))
            trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app, excluded_urls="health,metrics")
        if instrument_httpx:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()

    _install_chaos(app)

    from prometheus_fastapi_instrumentator import Instrumentator

    # Métricas: http_requests_total{method,handler,status} y el histograma
    # http_request_duration_seconds{method,handler}; prometheus_client agrega CPU y memoria
    # del proceso (process_cpu_seconds_total, process_resident_memory_bytes).
    Instrumentator(
        should_group_status_codes=False,
        excluded_handlers=["/metrics", "/health"],
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def _install_chaos(app) -> None:
    """Simulación de caos (punto 7 del reto): latencia artificial activable por variables de entorno.

    CHAOS_LATENCY_SECONDS=5 y CHAOS_LATENCY_PROBABILITY=0.5 equivalen al ejemplo del enunciado
    (`if random.random() < 0.5: time.sleep(5)`). Con 0 (por defecto) no hace nada.
    """
    delay = float(os.getenv("CHAOS_LATENCY_SECONDS", "0") or 0)
    probability = float(os.getenv("CHAOS_LATENCY_PROBABILITY", "0.5") or 0)
    if delay <= 0:
        return
    import asyncio
    import random

    log = logging.getLogger("chaos")
    log.warning("Simulación de caos ACTIVA: %.1fs de latencia con probabilidad %.2f", delay, probability)

    @app.middleware("http")
    async def chaos_latency(request, call_next):
        if request.url.path not in ("/health", "/metrics") and random.random() < probability:
            log.warning("Latencia artificial inyectada", extra={"delaySeconds": delay, "path": request.url.path})
            await asyncio.sleep(delay)
        return await call_next(request)


def add_instance_header(app) -> None:
    """Servicios replicados: cada respuesta indica qué instancia la atendió (demo del balanceo)."""
    instance = socket.gethostname()

    @app.middleware("http")
    async def instance_header(request, call_next):
        response = await call_next(request)
        response.headers["X-Instance-Id"] = instance
        return response


def tracer():
    return trace.get_tracer(SERVICE_NAME)


# ----------------------------------------------------------------------- RabbitMQ
@contextmanager
def publish_span(routing_key: str, headers: dict | None = None):
    """Span PRODUCER del envío; devuelve las cabeceras AMQP con traceparent/tracestate inyectados."""
    headers = dict(headers or {})
    with tracer().start_as_current_span(
        f"{EXCHANGE} publish {routing_key}",
        kind=SpanKind.PRODUCER,
        attributes={
            "messaging.system": "rabbitmq",
            "messaging.destination.name": EXCHANGE,
            "messaging.rabbitmq.destination.routing_key": routing_key,
        },
    ) as span:
        propagate.inject(headers)
        try:
            yield headers
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise


@contextmanager
def consume_span(queue: str, routing_key: str | None, headers: dict | None):
    """Extrae el contexto W3C de las cabeceras del mensaje y abre un span CONSUMER hijo."""
    carrier = {k: v.decode() if isinstance(v, bytes) else str(v) for k, v in (headers or {}).items()}
    parent = propagate.extract(carrier)
    with tracer().start_as_current_span(
        f"{queue} process {routing_key or ''}".strip(),
        context=parent,
        kind=SpanKind.CONSUMER,
        attributes={
            "messaging.system": "rabbitmq",
            "messaging.source.name": queue,
            "messaging.rabbitmq.destination.routing_key": routing_key or "",
        },
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise


# ------------------------------------------------------------------------- health
def tcp_check(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def broker_up() -> bool:
    return tcp_check(os.getenv("RABBITMQ_HOST", "rabbitmq"), int(os.getenv("RABBITMQ_PORT", "5672")))


def health_response(checks: dict[str, bool]):
    """Formato del reto: status UP/DOWN, service y checks. HTTP 200 si UP, 503 si DOWN."""
    from fastapi.responses import JSONResponse

    up = all(checks.values())
    body = {
        "status": "UP" if up else "DOWN",
        "service": SERVICE_NAME,
        "checks": {name: "UP" if ok else "DOWN" for name, ok in checks.items()},
    }
    return JSONResponse(status_code=200 if up else 503, content=body)


@contextmanager
def no_tracing():
    """Evita que las sondas de salud generen trazas basura en Zipkin."""
    from opentelemetry.instrumentation.utils import suppress_instrumentation

    with suppress_instrumentation():
        yield
