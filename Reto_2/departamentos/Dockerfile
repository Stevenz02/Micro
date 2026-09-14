# ---------- Etapa 1: build ----------
# Instalamos TODAS las dependencias (incluidas devDependencies, por si
# usan TypeScript, linters, etc. en el futuro) en una imagen completa.
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# Si en el futuro usan TypeScript, aquí iría: RUN npm run build

# ---------- Etapa 2: imagen final ----------
# Imagen liviana que solo lleva las dependencias de producción y el
# código ya listo para ejecutar.
FROM node:20-alpine

WORKDIR /app

# curl es necesario para el healthcheck definido en docker-compose.yml
RUN apk add --no-cache curl

COPY package*.json ./
RUN npm install --omit=dev

COPY --from=builder /app/src ./src

EXPOSE 8081

CMD ["node", "src/index.js"]