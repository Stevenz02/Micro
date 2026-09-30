FROM golang:1.23-alpine AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go test ./...
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /perfiles .

FROM alpine:3.21
RUN addgroup -S app && adduser -S -G app app
COPY --from=builder /perfiles /usr/local/bin/perfiles
USER app
EXPOSE 8083
ENTRYPOINT ["/usr/local/bin/perfiles"]
