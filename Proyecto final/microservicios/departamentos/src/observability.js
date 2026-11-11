// Reto 8 - Métricas Prometheus (prom-client) y logs JSON (winston) con traceId
import client from 'prom-client';
import winston from 'winston';
import { trace } from '@opentelemetry/api';

export const SERVICE_NAME = process.env.OTEL_SERVICE_NAME || 'departamentos-service';

// ------------------------------------------------------------------ logs JSON
const traceFields = winston.format((info) => {
  const ctx = trace.getActiveSpan()?.spanContext();
  info.service = SERVICE_NAME;
  info.traceId = ctx?.traceId ?? null;
  info.spanId = ctx?.spanId ?? null;
  info.level = info.level.toUpperCase();
  return info;
});

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp({ format: () => new Date().toISOString() }),
    traceFields(),
    winston.format.json(),
  ),
  transports: [new winston.transports.Console()],
});

// ------------------------------------------------------------------ métricas
export const registry = new client.Registry();
// CPU y memoria del proceso: process_cpu_seconds_total, process_resident_memory_bytes, nodejs_*
client.collectDefaultMetrics({ register: registry });

const requests = new client.Counter({
  name: 'http_requests_total',
  help: 'Peticiones HTTP recibidas por método, ruta y código de respuesta',
  labelNames: ['method', 'handler', 'status'],
  registers: [registry],
});
const duration = new client.Histogram({
  name: 'http_request_duration_seconds',
  help: 'Latencia de las peticiones HTTP en segundos',
  labelNames: ['method', 'handler', 'status'],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [registry],
});

const IGNORED = new Set(['/health', '/metrics']);

export function metricsMiddleware(req, res, next) {
  if (IGNORED.has(req.path)) return next();
  const end = duration.startTimer();
  res.on('finish', () => {
    // Ruta plantilla (/departamentos/:id) para no disparar la cardinalidad con cada id
    const handler = req.route ? `${req.baseUrl}${req.route.path}` : 'unmatched';
    const labels = { method: req.method, handler, status: String(res.statusCode) };
    requests.inc(labels);
    const seconds = end(labels);
    logger.log(res.statusCode >= 500 ? 'error' : 'info', `${req.method} ${req.originalUrl} ${res.statusCode}`, {
      method: req.method, path: req.originalUrl, status: res.statusCode, durationMs: Math.round(seconds * 1000),
    });
  });
  next();
}

export async function metricsHandler(req, res) {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
}

// Simulación de caos (punto 7): CHAOS_LATENCY_SECONDS>0 agrega latencia con prob. CHAOS_LATENCY_PROBABILITY
export function chaosMiddleware() {
  const delay = Number(process.env.CHAOS_LATENCY_SECONDS || 0);
  const probability = Number(process.env.CHAOS_LATENCY_PROBABILITY || 0.5);
  if (!(delay > 0)) return (req, res, next) => next();
  logger.warn(`Simulación de caos ACTIVA: ${delay}s con probabilidad ${probability}`);
  return (req, res, next) => {
    if (IGNORED.has(req.path) || Math.random() >= probability) return next();
    logger.warn('Latencia artificial inyectada', { delaySeconds: delay, path: req.path });
    setTimeout(next, delay * 1000);
  };
}
