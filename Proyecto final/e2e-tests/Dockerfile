# Suite BDD (Behave + httpx) empaquetada para ejecutarse dentro de la red de Compose.
# No incluye .env ni credenciales: todo llega por variables de entorno desde docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Los reportes se escriben en /app/reports, que Compose monta como volumen del host
# (Reto_6/e2e-tests/reports) para que sobrevivan al contenedor y Jenkins los publique.
# Se ejecuta como root a propósito: así puede escribir en el bind mount sin importar
# el UID del host (Windows o el agente de Jenkins en el Reto 7).
CMD ["python", "run.py"]
