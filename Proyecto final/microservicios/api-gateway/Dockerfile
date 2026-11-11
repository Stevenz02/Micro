# Reto 8 - Contexto de build: Reto_8/services (el servicio importa el paquete compartido shared/,
# que incluye shared/observability.py con métricas, trazas OTel, logs JSON y /health)
# ---------- Etapa 1: build ----------
FROM python:3.12 AS builder

WORKDIR /build

COPY api-gateway/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY --from=builder /install /usr/local

COPY shared ./shared
COPY api-gateway/gateway_app ./gateway_app
COPY logging.json ./logging.json

RUN useradd --create-home appuser
USER appuser

EXPOSE 8080

# --log-config: logs JSON (timestamp, level, service, traceId, message) para Loki
CMD ["uvicorn", "gateway_app.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-config", "logging.json"]
