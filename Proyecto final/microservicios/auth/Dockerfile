# Reto 8 - Contexto de build: Reto_8/services (el servicio importa el paquete compartido shared/,
# que incluye shared/observability.py con métricas, trazas OTel, logs JSON y /health)
# ---------- Etapa 1: build ----------
FROM python:3.12 AS builder

WORKDIR /build

COPY auth/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY --from=builder /install /usr/local

COPY shared ./shared
COPY auth/auth_app ./auth_app
COPY auth/hash_admin.py ./hash_admin.py
COPY logging.json ./logging.json
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN useradd --create-home appuser
USER appuser

EXPOSE 8086

# Carga los Docker Secrets (variables *_FILE) y luego ejecuta el servicio
ENTRYPOINT ["/bin/sh", "/usr/local/bin/docker-entrypoint.sh"]

# --log-config: logs JSON (timestamp, level, service, traceId, message) para Loki
CMD ["uvicorn", "auth_app.main:app", "--host", "0.0.0.0", "--port", "8086", "--log-config", "logging.json"]
