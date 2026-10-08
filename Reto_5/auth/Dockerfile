# Contexto de build: Reto_5 (auth importa el paquete compartido Reto_5/shared)
# ---------- Etapa 1: build ----------
FROM python:3.12 AS builder

WORKDIR /build

COPY auth/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app

# /usr/local es legible por cualquier usuario, a diferencia de /root/.local
COPY --from=builder /install /usr/local

COPY shared ./shared
COPY auth/auth_app ./auth_app
COPY auth/hash_admin.py ./hash_admin.py
COPY logging.json ./logging.json

RUN useradd --create-home appuser
USER appuser

EXPOSE 8086

CMD ["uvicorn", "auth_app.main:app", "--host", "0.0.0.0", "--port", "8086", "--log-config", "logging.json"]
