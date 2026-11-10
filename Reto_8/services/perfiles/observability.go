package main

// Reto 8 - Observabilidad de perfiles-service (Go)
//   * Métricas : prometheus/client_golang -> GET /metrics (http_requests_total, http_request_duration_seconds,
//                process_cpu_seconds_total, process_resident_memory_bytes, go_*)
//   * Trazas   : OpenTelemetry Go SDK + exportador Zipkin, propagación W3C (tracecontext + baggage)
//   * Logs     : log/slog con JSONHandler (timestamp, level, service, traceId, message)

import (
	"context"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"os"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	amqp "github.com/rabbitmq/amqp091-go"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/zipkin"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

var serviceName = envOr("OTEL_SERVICE_NAME", "perfiles-service")

// brokerUp lo actualiza el consumidor: true mientras hay una conexión AMQP activa.
var brokerUp atomic.Bool

func envOr(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

// ------------------------------------------------------------------ logs JSON
type traceHandler struct{ slog.Handler }

func (h traceHandler) Handle(ctx context.Context, r slog.Record) error {
	if sc := trace.SpanContextFromContext(ctx); sc.IsValid() {
		r.AddAttrs(slog.String("traceId", sc.TraceID().String()), slog.String("spanId", sc.SpanID().String()))
	}
	return h.Handler.Handle(ctx, r)
}

func (h traceHandler) WithAttrs(attrs []slog.Attr) slog.Handler {
	return traceHandler{h.Handler.WithAttrs(attrs)}
}

func setupLogging() {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		ReplaceAttr: func(groups []string, a slog.Attr) slog.Attr {
			switch a.Key {
			case slog.TimeKey:
				a.Key = "timestamp"
				a.Value = slog.StringValue(a.Value.Time().UTC().Format(time.RFC3339Nano))
			case slog.MessageKey:
				a.Key = "message"
			}
			return a
		},
	})
	slog.SetDefault(slog.New(traceHandler{handler}).With("service", serviceName))
}

// ------------------------------------------------------------------ trazas
func setupTracing(ctx context.Context) func(context.Context) error {
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
	if os.Getenv("OTEL_SDK_DISABLED") == "true" {
		return func(context.Context) error { return nil }
	}
	exporter, err := zipkin.New(envOr("OTEL_EXPORTER_ZIPKIN_ENDPOINT", "http://zipkin:9411/api/v2/spans"))
	if err != nil {
		slog.Error("no se pudo crear el exportador Zipkin", "error", err)
		return func(context.Context) error { return nil }
	}
	res, _ := resource.Merge(resource.Default(), resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName(serviceName)))
	provider := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter), sdktrace.WithResource(res))
	otel.SetTracerProvider(provider)
	return provider.Shutdown
}

// amqpCarrier adapta las cabeceras de RabbitMQ (amqp.Table) al TextMapCarrier de OpenTelemetry.
type amqpCarrier amqp.Table

func (c amqpCarrier) Get(key string) string {
	if value, ok := c[key].(string); ok {
		return value
	}
	return ""
}
func (c amqpCarrier) Set(key, value string) { c[key] = value }
func (c amqpCarrier) Keys() []string {
	keys := make([]string, 0, len(c))
	for key := range c {
		keys = append(keys, key)
	}
	return keys
}

// startConsumerSpan extrae traceparent de las cabeceras del mensaje y abre un span CONSUMER hijo.
func startConsumerSpan(delivery amqp.Delivery) (context.Context, trace.Span) {
	headers := delivery.Headers
	if headers == nil {
		headers = amqp.Table{}
	}
	parent := otel.GetTextMapPropagator().Extract(context.Background(), amqpCarrier(headers))
	return otel.Tracer(serviceName).Start(parent, profilesQueue+" process "+delivery.RoutingKey,
		trace.WithSpanKind(trace.SpanKindConsumer),
		trace.WithAttributes(
			attribute.String("messaging.system", "rabbitmq"),
			attribute.String("messaging.source.name", profilesQueue),
			attribute.String("messaging.rabbitmq.destination.routing_key", delivery.RoutingKey),
		))
}

// ------------------------------------------------------------------ métricas
var (
	httpRequests = promauto.NewCounterVec(prometheus.CounterOpts{
		Name: "http_requests_total",
		Help: "Peticiones HTTP recibidas por método, ruta y código de respuesta",
	}, []string{"method", "handler", "status"})
	httpDuration = promauto.NewHistogramVec(prometheus.HistogramOpts{
		Name:    "http_request_duration_seconds",
		Help:    "Latencia de las peticiones HTTP en segundos",
		Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10},
	}, []string{"method", "handler", "status"})
)

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func isProbe(path string) bool { return path == "/health" || path == "/metrics" }

// observe mide cada petición (excepto sondas) y escribe un log JSON con el traceId.
func observe(next http.Handler) http.Handler {
	delay, _ := strconv.ParseFloat(os.Getenv("CHAOS_LATENCY_SECONDS"), 64)
	probability, err := strconv.ParseFloat(envOr("CHAOS_LATENCY_PROBABILITY", "0.5"), 64)
	if err != nil {
		probability = 0.5
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if isProbe(r.URL.Path) {
			next.ServeHTTP(w, r)
			return
		}
		if delay > 0 && rand.Float64() < probability { // simulación de caos (punto 7)
			slog.WarnContext(r.Context(), "Latencia artificial inyectada", "delaySeconds", delay)
			time.Sleep(time.Duration(delay * float64(time.Second)))
		}
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		handler := r.Pattern // lo completa ServeMux (Go 1.22+), p. ej. "GET /perfiles/{empleadoId}"
		if handler == "" {
			handler = "unmatched"
		}
		elapsed := time.Since(start)
		status := strconv.Itoa(rec.status)
		httpRequests.WithLabelValues(r.Method, handler, status).Inc()
		httpDuration.WithLabelValues(r.Method, handler, status).Observe(elapsed.Seconds())
		level := slog.LevelInfo
		if rec.status >= 500 {
			level = slog.LevelError
		}
		slog.Log(r.Context(), level, r.Method+" "+r.URL.Path+" "+status,
			"method", r.Method, "path", r.URL.Path, "status", rec.status, "durationMs", elapsed.Milliseconds())
	})
}

// instrument envuelve el router: otelhttp crea el span SERVER (continúa el traceparent entrante)
// y observe registra métricas y logs dentro de ese span.
func instrument(mux http.Handler) http.Handler {
	return otelhttp.NewHandler(observe(mux), "perfiles-service",
		otelhttp.WithFilter(func(r *http.Request) bool { return !isProbe(r.URL.Path) }),
		otelhttp.WithSpanNameFormatter(func(_ string, r *http.Request) string { return r.Method + " " + r.URL.Path }),
	)
}

func metricsHandler() http.Handler { return promhttp.Handler() }
