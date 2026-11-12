# ---------- Etapa 1: build ----------
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# ---------- Etapa 2: imagen final ----------
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/src ./src
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

EXPOSE 8082

USER node

# Carga los Docker Secrets (variables *_FILE) y luego ejecuta el servicio
ENTRYPOINT ["/bin/sh", "/usr/local/bin/docker-entrypoint.sh"]

# Reto 8: tracing.js se carga antes que la app para que OpenTelemetry instrumente http, express y pg
CMD ["node", "--import", "./src/tracing.js", "src/index.js"]
