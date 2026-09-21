# ---------- Etapa 1: build ----------
FROM node:22-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# ---------- Etapa 2: imagen final ----------
FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

COPY --from=builder /app/src ./src

EXPOSE 8082

CMD ["node", "src/index.js"]