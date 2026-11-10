// Reto 8 - Observabilidad de vacaciones-service (.NET 8)
//   * Métricas : prometheus-net -> GET /metrics (http_requests_total, http_request_duration_seconds,
//                process_cpu_seconds_total, process_working_set_bytes, dotnet_*)
//   * Trazas   : OpenTelemetry .NET (ActivitySource) + OpenTelemetry.Exporter.Zipkin, propagación W3C
//   * Logs     : Serilog con formatter JSON propio (timestamp, level, service, traceId, message)
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using OpenTelemetry;
using OpenTelemetry.Context.Propagation;
using Serilog.Events;
using Serilog.Formatting;

public static class Telemetry {
    public static readonly string ServiceName =
        Environment.GetEnvironmentVariable("OTEL_SERVICE_NAME") is { Length: > 0 } name ? name : "vacaciones-service";

    /// <summary>Fuente de spans manuales (scheduler, publicación y consumo en RabbitMQ).</summary>
    public static readonly ActivitySource Source = new("vacaciones-service");

    /// <summary>true mientras el consumidor mantiene una conexión AMQP abierta (lo usa /health).</summary>
    public static volatile bool BrokerUp;

    private static TextMapPropagator Propagator => Propagators.DefaultTextMapPropagator;

    /// <summary>Inyecta traceparent/tracestate del span actual en las cabeceras del mensaje AMQP.</summary>
    public static void Inject(Activity? activity, IDictionary<string, object> headers) {
        var context = activity?.Context ?? Activity.Current?.Context ?? default;
        Propagator.Inject(new PropagationContext(context, Baggage.Current), headers,
            (carrier, key, value) => carrier[key] = value);
    }

    /// <summary>Extrae el contexto W3C de las cabeceras AMQP (los valores llegan como byte[]).</summary>
    public static ActivityContext Extract(IDictionary<string, object>? headers) {
        var parent = Propagator.Extract(default, headers, (carrier, key) => {
            if (carrier is null || !carrier.TryGetValue(key, out var value) || value is null) return Array.Empty<string>();
            return new[] { value is byte[] bytes ? Encoding.UTF8.GetString(bytes) : value.ToString() ?? "" };
        });
        return parent.ActivityContext;
    }

    // ------------------------------------------------------------- métricas HTTP
    private static readonly Prometheus.Counter Requests = Prometheus.Metrics.CreateCounter("http_requests_total",
        "Peticiones HTTP recibidas por método, ruta y código de respuesta",
        new Prometheus.CounterConfiguration { LabelNames = new[] { "method", "handler", "status" } });

    private static readonly Prometheus.Histogram Duration = Prometheus.Metrics.CreateHistogram("http_request_duration_seconds",
        "Latencia de las peticiones HTTP en segundos",
        new Prometheus.HistogramConfiguration {
            LabelNames = new[] { "method", "handler", "status" },
            Buckets = new[] { 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10 },
        });

    public static bool IsProbe(PathString path) => path == "/health" || path == "/metrics";

    /// <summary>Middleware: métricas por ruta, log JSON por petición y latencia de caos opcional.</summary>
    public static IApplicationBuilder UseRequestObservability(this IApplicationBuilder app) {
        var delay = double.TryParse(Environment.GetEnvironmentVariable("CHAOS_LATENCY_SECONDS"),
            System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var d) ? d : 0;
        var probability = double.TryParse(Environment.GetEnvironmentVariable("CHAOS_LATENCY_PROBABILITY"),
            System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var p) ? p : 0.5;
        var logger = app.ApplicationServices.GetRequiredService<ILoggerFactory>().CreateLogger("http");
        return app.Use(async (context, next) => {
            if (IsProbe(context.Request.Path)) { await next(context); return; }
            if (delay > 0 && Random.Shared.NextDouble() < probability) {
                logger.LogWarning("Latencia artificial inyectada {DelaySeconds}s", delay);
                await Task.Delay(TimeSpan.FromSeconds(delay));
            }
            var watch = Stopwatch.StartNew();
            try { await next(context); }
            finally {
                watch.Stop();
                var handler = (context.GetEndpoint() as RouteEndpoint)?.RoutePattern.RawText ?? "unmatched";
                var status = context.Response.StatusCode.ToString(System.Globalization.CultureInfo.InvariantCulture);
                Requests.WithLabels(context.Request.Method, handler, status).Inc();
                Duration.WithLabels(context.Request.Method, handler, status).Observe(watch.Elapsed.TotalSeconds);
                var level = context.Response.StatusCode >= 500 ? LogLevel.Error : LogLevel.Information;
                logger.Log(level, "{Method} {Path} {Status} {DurationMs}ms", context.Request.Method,
                    context.Request.Path.Value, context.Response.StatusCode, watch.ElapsedMilliseconds);
            }
        });
    }
}

/// <summary>Una línea JSON por evento con los campos mínimos del reto (+ propiedades estructuradas).</summary>
public sealed class JsonLogFormatter(string service) : ITextFormatter {
    private static string Level(LogEventLevel level) => level switch {
        LogEventLevel.Verbose => "TRACE",
        LogEventLevel.Debug => "DEBUG",
        LogEventLevel.Information => "INFO",
        LogEventLevel.Warning => "WARN",
        LogEventLevel.Error => "ERROR",
        _ => "FATAL",
    };

    private static object? Simplify(LogEventPropertyValue value) =>
        value is ScalarValue scalar ? scalar.Value : value.ToString();

    public void Format(LogEvent logEvent, TextWriter output) {
        var traceId = logEvent.TraceId?.ToHexString() ?? Activity.Current?.TraceId.ToHexString();
        var spanId = logEvent.SpanId?.ToHexString() ?? Activity.Current?.SpanId.ToHexString();
        var entry = new Dictionary<string, object?> {
            ["timestamp"] = logEvent.Timestamp.UtcDateTime.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", System.Globalization.CultureInfo.InvariantCulture),
            ["level"] = Level(logEvent.Level),
            ["service"] = service,
            ["traceId"] = traceId,
            ["spanId"] = spanId,
            ["message"] = logEvent.RenderMessage(),
        };
        foreach (var (key, value) in logEvent.Properties) {
            if (key == "SourceContext") entry["logger"] = Simplify(value);
            else if (!entry.ContainsKey(key)) entry[key] = Simplify(value);
        }
        if (logEvent.Exception is not null) entry["exception"] = logEvent.Exception.ToString();
        output.WriteLine(JsonSerializer.Serialize(entry));
    }
}
