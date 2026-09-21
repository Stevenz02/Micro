# ---------- Etapa 1: build ----------
FROM python:3.12 AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# /usr/local es legible por cualquier usuario, a diferencia de /root/.local
COPY --from=builder /install /usr/local

COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]