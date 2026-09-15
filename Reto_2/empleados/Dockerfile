FROM python:3.12-slim AS builder
WORKDIR /build
COPY Reto_2/empleados/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=builder /install /usr/local
# Solo se comparte el contrato, no el repositorio en memoria ni los endpoints.
COPY Reto_1/app/models.py ./Reto_1/app/models.py
COPY Reto_2/empleados/app ./Reto_2/empleados/app
RUN useradd --create-home appuser
USER appuser
EXPOSE 8080
CMD ["uvicorn", "Reto_2.empleados.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
