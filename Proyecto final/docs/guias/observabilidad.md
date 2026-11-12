# Guía: observabilidad

| Herramienta | URL | Uso |
|---|---|---|
| Grafana | <http://localhost:3000> | Dashboard "Proyecto final - Ecosistema RRHH", Explore (Loki, Zipkin) y alertas |
| Prometheus | <http://localhost:9090> | *Status → Targets*: un target por instancia de cada servicio |
| Zipkin | <http://localhost:9411> | Trazas distribuidas |

Credenciales de Grafana: usuario `GRAFANA_ADMIN_USER` de `.env`, contraseña en
`secrets/grafana_admin_password.txt`. Todo (datasources, dashboard, reglas y canal de alertas) se
aprovisiona desde `observabilidad/grafana/provisioning/`.

## Logs centralizados

Todos los servicios escriben JSON en stdout con `timestamp`, `level`, `service`, `message`,
`traceId` y contexto. Promtail los recoge del socket de Docker y los envía a Loki.

En Grafana → Explore → Loki:

```logql
{service="empleados-service"} | json | level="ERROR"
{service=~".+"} | json | traceId="<id-de-la-traza>"
```

## Métricas

- **Salud**: `up` por instancia y `/health` de cada servicio.
- **HTTP**: `http_requests_total`, `http_request_duration_seconds` (Spring: `http_server_requests_*`).
- **Negocio**: `empleados_creados_total`, `empleados_retirados_total`, `empleados_pendientes_total`,
  `notificaciones_enviadas_total{tipo,evento,correo}`, `auth_logins_total{resultado}`,
  `cuentas_activadas_total`, `eventos_publicacion_errores_total{tipo}`.

## Trazabilidad distribuida

Cree un empleado y busque en Zipkin por `serviceName=api-gateway`. La traza del onboarding
muestra la cascada completa:

`api-gateway → empleados-service → departamentos-service` (validación) y, a través de RabbitMQ,
`auth-service`, `perfiles-service`, `vacaciones-service` y `notificaciones-service`, hasta el
consumo de `usuario.creado`.

El `traceId` de la traza es el mismo que aparece en los logs: desde el panel de logs de Grafana
el enlace del campo `traceId` abre la traza en Zipkin.

## Alertas hacia un canal externo

Reglas (`observabilidad/grafana/provisioning/alerting/alert-rules.yml`): **Servicio Caído**,
**Alta Tasa de Errores 5xx** y **Alta Latencia**. Canal: Discord.

1. Pegue el webhook en `secrets/discord_webhook_url.txt` y recree Grafana:
   `docker compose up -d --force-recreate grafana`.
2. Provoque la alerta: `docker compose stop perfiles-service`.
3. Cuando la regla cumple su tiempo de espera llega el mensaje a Discord; al iniciar de nuevo el
   servicio llega "RESUELTA".

## Simulación de latencia

`CHAOS_EMPLEADOS_LATENCY_SECONDS` y `CHAOS_DEPARTAMENTOS_LATENCY_SECONDS` en `.env` inyectan
latencia artificial para observar la alerta de latencia y el Circuit Breaker.
