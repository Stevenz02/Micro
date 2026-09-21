# ---------- Etapa 1: build ----------
# ---------- Etapa 1: build ----------
FROM python:3.12 AS builder

WORKDIR /build

COPY Reto_3/empleados/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# /usr/local es legible por cualquier usuario, a diferencia de /root/.local
COPY --from=builder /install /usr/local

# El modelo canónico vive en Reto_1; Reto_3 lo reutiliza sin duplicarlo
COPY Reto_1/app/models.py ./Reto_1/app/models.py
COPY Reto_3/empleados/app ./Reto_3/empleados/app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8081

CMD ["uvicorn", "Reto_3.empleados.app.main:app", "--host", "0.0.0.0", "--port", "8081"]