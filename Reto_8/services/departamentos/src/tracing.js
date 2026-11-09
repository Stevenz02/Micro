// Reto 8 - Trazabilidad distribuida con OpenTelemetry (se carga ANTES de la app: node --import ./src/tracing.js)
// - service.name  : OTEL_SERVICE_NAME (departamentos-service)
// - exportador    : Zipkin en OTEL_EXPORTER_ZIPKIN_ENDPOINT (http://zipkin:9411/api/v2/spans)
// - propagación   : W3C Trace Context + Baggage (OTEL_PROPAGATORS=tracecontext,baggage, valor por defecto del SDK)
import { register } from 'node:module';
import { NodeSDK } from '@opentelemetry/sdk-node';
import { ZipkinExporter } from '@opentelemetry/exporter-zipkin';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { PgInstrumentation } from '@opentelemetry/instrumentation-pg';

// La app es ESM: este hook permite instrumentar módulos cargados con `import`
register('@opentelemetry/instrumentation/hook.mjs', import.meta.url);

const IGNORED = new Set(['/health', '/metrics']);

if ((process.env.OTEL_SDK_DISABLED || 'false').toLowerCase() !== 'true') {
  const sdk = new NodeSDK({
    serviceName: process.env.OTEL_SERVICE_NAME || 'departamentos-service',
    traceExporter: new ZipkinExporter({
      url: process.env.OTEL_EXPORTER_ZIPKIN_ENDPOINT || 'http://zipkin:9411/api/v2/spans',
    }),
    instrumentations: [
      new HttpInstrumentation({
        // Las sondas de salud y el scraping de Prometheus no generan trazas
        ignoreIncomingRequestHook: (req) => IGNORED.has((req.url || '').split('?')[0]),
      }),
      new ExpressInstrumentation(),
      // Solo spans de BD dentro de una petición (sin trazas sueltas del /health)
      new PgInstrumentation({ requireParentSpan: true }),
    ],
  });
  sdk.start();
  for (const signal of ['SIGTERM', 'SIGINT']) process.once(signal, () => sdk.shutdown().catch(() => {}));
}
