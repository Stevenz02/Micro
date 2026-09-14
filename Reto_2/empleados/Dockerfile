# ---------- Etapa 1: build ----------
# Instalamos las dependencias en una imagen que trae herramientas de
# compilación, por si alguna librería de requirements.txt las necesita.
FROM python:3.12 AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---------- Etapa 2: imagen final ----------
# Imagen liviana que solo lleva lo necesario para EJECUTAR la app,
# sin compiladores ni cachés de instalación.
FROM python:3.12-slim

WORKDIR /app

# Copiamos únicamente las dependencias ya instaladas desde la etapa builder
COPY --from=builder /root/.local /root/.local
COPY app ./app

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]