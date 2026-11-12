FROM golang:1.23-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
COPY . .
# Reto 8: `go mod tidy` completa go.sum con las dependencias de OpenTelemetry y Prometheus
RUN go mod tidy && go mod download
RUN go test ./...
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /perfiles .

FROM alpine:3.21
RUN addgroup -S app && adduser -S -G app app
COPY --from=builder /perfiles /usr/local/bin/perfiles
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
USER app
EXPOSE 8083
# Carga los Docker Secrets (variables *_FILE) y luego ejecuta el servicio
ENTRYPOINT ["/bin/sh","/usr/local/bin/docker-entrypoint.sh","/usr/local/bin/perfiles"]
